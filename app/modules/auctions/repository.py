import json
import base64
import binascii
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from botocore.exceptions import ClientError


class AuctionValidationError(ValueError):
    pass


class AuctionRepository:
    def __init__(self, table: Any) -> None:
        self._table = table

    def create(self, seller_id: str, seller_alias: str, payload: dict[str, Any]) -> dict[str, Any]:
        title = self._text(payload.get("title"), "title", 3, 120)
        description = self._text(payload.get("description"), "description", 0, 2000)
        category = self._text(payload.get("category"), "category", 2, 50)
        image_url = self._image_url(payload.get("imageUrl"))
        initial_price = payload.get("initialPrice")

        if not isinstance(initial_price, int) or isinstance(initial_price, bool) or initial_price < 1:
            raise AuctionValidationError("initialPrice debe ser un entero positivo")
        
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=120)
        auction_id = str(uuid4())
        item = {
            "PK": f"AUCTION#{auction_id}", "SK": "META", "auctionId": auction_id,
            "sellerId": seller_id, "sellerAlias": seller_alias, "title": title,
            "description": description, "category": category, "imageUrl": image_url,
            "initialPrice": initial_price, "status": "ACTIVE_NO_BIDS", "version": 1,
            "createdAt": now.isoformat(), "expiresAt": int(expires_at.timestamp() * 1000),
            "ttl": int(expires_at.timestamp()), "GSI1PK": "AUCTIONS#ACTIVE",
            "GSI1SK": f"{now.isoformat()}#{auction_id}", "GSI2PK": f"SELLER#{seller_id}",
            "GSI2SK": f"{now.isoformat()}#{auction_id}",
        }
        
        self._table.put_item(Item=item, ConditionExpression="attribute_not_exists(PK)")
        return self._public(item)

    def get(self, auction_id: str) -> dict[str, Any] | None:
        item = self._get(auction_id)
        return self._public(item) if item else None

    def list_active(self, limit: int, cursor: str | None, uid: str) -> dict[str, Any]:
        query: dict[str, Any] = {
            "IndexName": "GSI1", "KeyConditionExpression": "GSI1PK = :pk",
            "ExpressionAttributeValues": {":pk": "AUCTIONS#ACTIVE"},
            "ScanIndexForward": False, "Limit": limit,
        }
        if cursor:
            try:
                payload = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
                key = payload["key"]
                if (payload["uid"] != uid or payload["scope"] != "active-auctions"
                        or not isinstance(key, dict) or set(key) != {"PK", "SK", "GSI1PK", "GSI1SK"}
                        or key["GSI1PK"] != "AUCTIONS#ACTIVE"
                        or not all(isinstance(value, str) for value in key.values())):
                    raise ValueError("Invalid cursor")
                query["ExclusiveStartKey"] = key
            except (ValueError, KeyError, TypeError, UnicodeError, binascii.Error) as error:
                raise ValueError("Invalid cursor") from error
        result = self._table.query(**query)
        items = []
        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        for key in result.get("Items", []):
            current = self._table.get_item(Key={"PK": key["PK"], "SK": key["SK"]}, ConsistentRead=True).get("Item")
            if current and self.is_visible(current, now):
                items.append(self._public(current))
        last_key = result.get("LastEvaluatedKey")
        next_cursor = base64.urlsafe_b64encode(json.dumps({"uid": uid, "scope": "active-auctions", "key": last_key}).encode()).decode() if last_key else None
        return {"items": items, "nextCursor": next_cursor, "serverNow": now}

    @staticmethod
    def is_visible(item: dict[str, Any], now: int) -> bool:
        return item.get("status") in ("ACTIVE_NO_BIDS", "ACTIVE_BIDDING") and int(item.get("expiresAt", 0)) > now

    def cancel(self, auction_id: str, user_id: str) -> dict[str, Any]:
        item = self._get(auction_id)
        if item is None:
            raise KeyError("Subasta no encontrada")
        if item["sellerId"] != user_id:
            raise PermissionError("La subasta no pertenece a este usuario")
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        if item["status"] != "ACTIVE_NO_BIDS" or item["expiresAt"] <= now_ms:
            raise AuctionValidationError("La subasta ya no se puede cancelar")
        try:
            self._table.update_item(
                Key={"PK": item["PK"], "SK": item["SK"]},
                UpdateExpression=(
                    "SET #status = :cancelled, cancelledAt = :cancelled_at, "
                    "version = version + :increment REMOVE #ttl, GSI1PK, GSI1SK"
                ),
                ConditionExpression=(
                    "sellerId = :user_id AND #status = :active AND expiresAt > :now"
                ),
                ExpressionAttributeNames={"#status": "status", "#ttl": "ttl"},
                ExpressionAttributeValues={
                    ":cancelled": "CANCELLED", ":cancelled_at": datetime.now(timezone.utc).isoformat(),
                    ":increment": 1, ":user_id": user_id, ":active": "ACTIVE_NO_BIDS", ":now": now_ms,
                },
                ReturnValues="ALL_NEW",
            )
        except ClientError as error:
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise AuctionValidationError("La subasta ya no se puede cancelar") from error
            raise
        return self._public(self._get(auction_id) or item)

    def _get(self, auction_id: str) -> dict[str, Any] | None:
        return self._table.get_item(
            Key={"PK": f"AUCTION#{auction_id}", "SK": "META"}, ConsistentRead=True
        ).get("Item")

    @staticmethod
    def _text(value: Any, field: str, minimum: int, maximum: int) -> str:
        if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
            raise AuctionValidationError(
                f"{field} debe contener entre {minimum} y {maximum} caracteres"
            )
        return value.strip()

    @staticmethod
    def _image_url(value: Any) -> str:
        if not isinstance(value, str) or len(value) > 2048:
            raise AuctionValidationError("imageUrl debe ser una URL HTTP pública")
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise AuctionValidationError("imageUrl debe ser una URL HTTP pública")
        return value

    @staticmethod
    def _public(item: dict[str, Any]) -> dict[str, Any]:
        keys = (
            "auctionId", "sellerId", "sellerAlias", "title", "description", "category", "imageUrl",
            "initialPrice", "status", "version", "createdAt", "expiresAt", "cancelledAt",
            "highestBid", "leaderId", "leaderAlias", "winnerUserId", "winnerAlias", "winningAmount", "winningBidId", "finishedAt",
        )
        return {key: int(item[key]) if key in ("initialPrice", "version", "expiresAt", "highestBid", "winningAmount") else item[key] for key in keys if key in item}
