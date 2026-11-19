import asyncio
from datetime import datetime, timedelta, timezone

import jwt
from starlette.websockets import WebSocketDisconnect

from local_dev import websocket


class FakeSocket:
    headers = {"origin": "http://localhost:5173"}
    def __init__(self, token):
        self.token = token
        self.sent = []
        self.finished = asyncio.Event()
        self.close_code = None
    async def accept(self):
        pass
    async def receive_json(self):
        return {"token": self.token}
    async def receive_text(self):
        await self.finished.wait()
        raise WebSocketDisconnect()
    async def send_json(self, value):
        self.sent.append(value)
        if value.get("type") == "auction.bid_accepted":
            self.finished.set()
    async def close(self, code):
        self.close_code = code


class FakePubSub:
    def __init__(self):
        self.sent = False
    async def subscribe(self, channel):
        self.channel = channel
    async def get_message(self, **kwargs):
        if not self.sent:
            self.sent = True
            return {"data": '{"type":"auction.bid_accepted","auctionId":"a1","version":2}'}
        await asyncio.sleep(0.01)
        return None
    async def aclose(self):
        pass


class FakeRedis:
    def __init__(self, **kwargs):
        pass
    def pubsub(self):
        return FakePubSub()
    async def aclose(self):
        pass


def token():
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": "u1", "email": "u@example.com", "iss": "flashbid-local-auth", "aud": "flashbid-web", "iat": now, "exp": now + timedelta(minutes=5)}, "flashbid-local-development-secret", algorithm="HS256")


def test_websocket_authentication_and_event_forwarding(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "flashbid-local-development-secret")
    monkeypatch.setattr(websocket.redis, "Redis", FakeRedis)
    async def exists(*args):
        return True
    monkeypatch.setattr(websocket, "run_in_threadpool", exists)
    async def run():
        ws = FakeSocket(token())
        await asyncio.wait_for(websocket.auction_socket(ws, "a1"), timeout=3)
        assert ws.sent[0] == {"type": "subscribed", "auctionId": "a1"}
        assert ws.sent[1]["type"] == "auction.bid_accepted"
        invalid = FakeSocket("invalid")
        await asyncio.wait_for(websocket.auction_socket(invalid, "a1"), timeout=3)
        assert invalid.close_code == 1008
    asyncio.run(run())
