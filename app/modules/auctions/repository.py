import json
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
            raise AuctionValidationError("initialPrice must be a positive integer")
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

    def cancel(self, auction_id: str, user_id: str) -> dict[str, Any]:
        item = self._get(auction_id)
        if item is None:
            raise KeyError("Auction not found")
        if item["sellerId"] != user_id:
            raise PermissionError("Auction does not belong to this user")
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        if item["status"] != "ACTIVE_NO_BIDS" or item["expiresAt"] <= now_ms:
            raise AuctionValidationError("Auction can no longer be cancelled")
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
                raise AuctionValidationError("Auction can no longer be cancelled") from error
            raise
        return self._public(self._get(auction_id) or item)

    def _get(self, auction_id: str) -> dict[str, Any] | None:
        return self._table.get_item(
            Key={"PK": f"AUCTION#{auction_id}", "SK": "META"}, ConsistentRead=True
        ).get("Item")

    @staticmethod
    def _text(value: Any, field: str, minimum: int, maximum: int) -> str:
        if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
            raise AuctionValidationError(f"{field} must contain between {minimum} and {maximum} characters")
        return value.strip()

    @staticmethod
    def _image_url(value: Any) -> str:
        if not isinstance(value, str) or len(value) > 2048:
            raise AuctionValidationError("imageUrl must be a public HTTP URL")
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise AuctionValidationError("imageUrl must be a public HTTP URL")
        return value

    @staticmethod
    def _public(item: dict[str, Any]) -> dict[str, Any]:
        keys = (
            "auctionId", "sellerId", "sellerAlias", "title", "description", "category", "imageUrl",
            "initialPrice", "status", "version", "createdAt", "expiresAt", "cancelledAt",
        )
        return {key: item[key] for key in keys if key in item}
