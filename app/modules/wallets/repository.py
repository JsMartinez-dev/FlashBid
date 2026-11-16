import base64
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from botocore.exceptions import ClientError

INITIAL_CREDITS = 10_000


class WalletRepository:
    def __init__(self, table: Any) -> None:
        self._table = table

    def ensure_initial_wallet(self, uid: str) -> dict[str, Any]:
        wallet = self.get_wallet(uid)
        if wallet is not None:
            return self._public_wallet(wallet)
        now = datetime.now(timezone.utc).isoformat()
        wallet_item = {
            "PK": f"USER#{uid}", "SK": "WALLET", "availableCredits": INITIAL_CREDITS,
            "reservedCredits": 0, "version": 1, "initializedAt": now,
        }
        movement_item = {
            "PK": f"USER#{uid}", "SK": f"MOVEMENT#{now}#INITIAL", "type": "INITIAL_CREDIT",
            "amount": INITIAL_CREDITS, "availableDelta": INITIAL_CREDITS, "reservedDelta": 0,
            "operationId": str(uuid4()), "createdAt": now,
        }
        try:
            self._table.meta.client.transact_write_items(
                TransactItems=[
                    {"Put": {"TableName": self._table.name, "Item": wallet_item,
                             "ConditionExpression": "attribute_not_exists(PK)"}},
                    {"Put": {"TableName": self._table.name, "Item": movement_item,
                             "ConditionExpression": "attribute_not_exists(PK)"}},
                ]
            )
            return self._public_wallet(wallet_item)
        except ClientError as error:
            if error.response["Error"]["Code"] != "TransactionCanceledException":
                raise
            existing = self.get_wallet(uid)
            if existing is None:
                raise
            return self._public_wallet(existing)

    def get_wallet(self, uid: str) -> dict[str, Any] | None:
        result = self._table.get_item(
            Key={"PK": f"USER#{uid}", "SK": "WALLET"}, ConsistentRead=True
        )
        return result.get("Item")

    def list_movements(self, uid: str, limit: int, cursor: str | None) -> dict[str, Any]:
        query: dict[str, Any] = {
            "KeyConditionExpression": "PK = :pk AND begins_with(SK, :prefix)",
            "ExpressionAttributeValues": {":pk": f"USER#{uid}", ":prefix": "MOVEMENT#"},
            "ScanIndexForward": False,
            "Limit": limit,
            "ConsistentRead": True,
        }
        if cursor:
            query["ExclusiveStartKey"] = self._decode_cursor(cursor)
        result = self._table.query(**query)
        return {
            "items": [self._public_movement(item) for item in result.get("Items", [])],
            "nextCursor": self._encode_cursor(result["LastEvaluatedKey"])
            if result.get("LastEvaluatedKey") else None,
        }

    @staticmethod
    def _public_wallet(wallet: dict[str, Any]) -> dict[str, Any]:
        return {key: wallet[key] for key in ("availableCredits", "reservedCredits", "version", "initializedAt")}

    @staticmethod
    def _public_movement(item: dict[str, Any]) -> dict[str, Any]:
        return {key: item[key] for key in ("type", "amount", "availableDelta", "reservedDelta", "operationId", "createdAt")}

    @staticmethod
    def _encode_cursor(key: dict[str, Any]) -> str:
        return base64.urlsafe_b64encode(json.dumps(key).encode()).decode()

    @staticmethod
    def _decode_cursor(cursor: str) -> dict[str, Any]:
        try:
            return json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        except (ValueError, json.JSONDecodeError) as error:
            raise ValueError("Invalid cursor") from error
