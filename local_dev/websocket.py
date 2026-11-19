"""Gateway local de eventos WebSocket por subasta."""
import asyncio
import json
import os

import boto3
import redis.asyncio as redis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool
from modules.shared.auth import AuthenticationError, decode_bearer_token

router = APIRouter()


def _exists(auction_id):
    table = boto3.resource("dynamodb", endpoint_url=os.environ["AWS_ENDPOINT_URL"]).Table(os.environ["TABLE_NAME"])
    item = table.get_item(Key={"PK": f"AUCTION#{auction_id}", "SK": "META"}, ConsistentRead=True).get("Item")
    return bool(item and item.get("status") in ("ACTIVE_NO_BIDS", "ACTIVE_BIDDING", "FINISHED"))


@router.websocket("/ws/auctions/{auction_id}")
async def auction_socket(websocket: WebSocket, auction_id: str):
    origin = websocket.headers.get("origin")
    if origin and origin != "http://localhost:5173":
        await websocket.close(code=1008)
        return
    if not auction_id or len(auction_id) > 128:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try:
        data = await asyncio.wait_for(websocket.receive_json(), timeout=5)
        token = data.get("token") if isinstance(data, dict) else None
        decode_bearer_token(f"Bearer {token}" if isinstance(token, str) else None)
        if not await run_in_threadpool(_exists, auction_id):
            await websocket.close(code=1008)
            return
    except (AuthenticationError, ValueError, asyncio.TimeoutError, WebSocketDisconnect):
        try:
            await websocket.close(code=1008)
        except RuntimeError:
            pass
        return
    except Exception:
        await websocket.close(code=1011)
        return
    client = redis.Redis(host=os.environ.get("REDIS_HOST", "redis"), port=int(os.environ.get("REDIS_PORT", "6379")),
                         decode_responses=True, socket_connect_timeout=2, socket_timeout=3)
    pubsub = client.pubsub()
    tasks = []
    try:
        await pubsub.subscribe(f"events:auction:{auction_id}")
        await websocket.send_json({"type": "subscribed", "auctionId": auction_id})  

        async def forward():
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
                if message:
                    try:
                        event = json.loads(message["data"])
                        if event.get("auctionId") == auction_id:
                            await websocket.send_json(event) #Le enviamos la actualizacion a todoso los navegadores conectados a esa subasta    
                    except (ValueError, TypeError, AttributeError):
                        continue
                await asyncio.sleep(0.01)

        async def receive():
            while True:
                await websocket.receive_text()

        async def check_session():
            while True:
                await asyncio.sleep(1)
                decode_bearer_token(f"Bearer {token}")

        tasks = [asyncio.create_task(forward()), asyncio.create_task(receive()), asyncio.create_task(check_session())]
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    except WebSocketDisconnect:
        pass
    except AuthenticationError:
        try:
            await websocket.close(code=1008)
        except RuntimeError:
            pass
    except Exception:
        try:
            await websocket.close(code=1011)
        except RuntimeError:
            pass
    finally:
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await pubsub.aclose()
        await client.aclose()
