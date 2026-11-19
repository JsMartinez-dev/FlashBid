import logging
import os
from typing import Any

import boto3

from modules.shared.auth import AuthenticationError, decode_bearer_token
from modules.shared.http import error_response, response
from modules.users.service import UserService

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["TABLE_NAME"]


def main(event: dict[str, Any], context: Any) -> dict[str, Any]:
    if event.get("httpMethod") == "OPTIONS":
        return response(200, {})
    if event.get("httpMethod") != "GET":
        return error_response(405, "method_not_allowed", "Method not allowed")
    try:
        user = decode_bearer_token((event.get("headers") or {}).get("Authorization"))
    except AuthenticationError:
        return error_response(401, "unauthorized", "A valid session is required")

    profile = UserService(dynamodb.Table(TABLE_NAME)).profile_with_wallet(user.uid)
    if profile is None:
        logger.warning("Authenticated profile not found uid=%s", user.uid)
        return error_response(403, "profile_unavailable", "Profile is unavailable")
    return response(200, profile)
