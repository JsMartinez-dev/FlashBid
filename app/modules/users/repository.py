from datetime import datetime, timezone
from typing import Any

from botocore.exceptions import ClientError


class EmailAlreadyRegisteredError(Exception):
    pass


class ProfileRepository:
    def __init__(self, table: Any) -> None:
        self._table = table

    def create_profile(
        self,
        uid: str,
        email: str,
        display_name: str,
        password_hash: str,
    ) -> dict[str, str]:
        created_at = datetime.now(timezone.utc).isoformat()
        profile = {
            "PK": f"USER#{uid}",
            "SK": "PROFILE",
            "uid": uid,
            "email": email,
            "displayName": display_name,
            "createdAt": created_at,
        }
        identity = {
            "PK": f"IDENTITY#{email}",
            "SK": "PROFILE",
            "uid": uid,
            "email": email,
            "passwordHash": password_hash,
            "createdAt": created_at,
        }
        try:
            self._table.meta.client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self._table.name,
                            "Item": identity,
                            "ConditionExpression": "attribute_not_exists(PK)",
                        }
                    },
                    {
                        "Put": {
                            "TableName": self._table.name,
                            "Item": profile,
                            "ConditionExpression": "attribute_not_exists(PK)",
                        }
                    },
                ]
            )
        except ClientError as error:
            if error.response["Error"]["Code"] == "TransactionCanceledException":
                raise EmailAlreadyRegisteredError from error
            raise
        return profile

    def get_identity(self, email: str) -> dict[str, Any] | None:
        result = self._table.get_item(
            Key={"PK": f"IDENTITY#{email}", "SK": "PROFILE"},
            ConsistentRead=True,
        )
        return result.get("Item")

    def get_profile(self, uid: str) -> dict[str, Any] | None:
        result = self._table.get_item(
            Key={"PK": f"USER#{uid}", "SK": "PROFILE"},
            ConsistentRead=True,
        )
        return result.get("Item")
