import os
from typing import Any

import boto3

from modules.shared.auth import AuthenticationError, decode_bearer_token
from modules.shared.http import error_response, response
from modules.wallets.service import WalletService

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["TABLE_NAME"]


def main(event: dict[str, Any], context: Any) -> dict[str, Any]:
    if event.get("httpMethod") != "GET":
        return error_response(405, "method_not_allowed", "Method not allowed")
    try:
        user = decode_bearer_token((event.get("headers") or {}).get("Authorization"))
    except AuthenticationError:
        return error_response(401, "unauthorized", "A valid session is required")
    params = event.get("queryStringParameters") or {}
    try:
        limit = min(max(int(params.get("limit", 20)), 1), 50)
        data = WalletService(dynamodb.Table(TABLE_NAME)).movements(
            user.uid, limit, params.get("cursor")
        )
    except ValueError:
        return error_response(400, "invalid_cursor", "Cursor is invalid")
    return response(200, data)
