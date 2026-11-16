import json
import os
from typing import Any

import boto3

from modules.auctions.repository import AuctionValidationError
from modules.auctions.service import AuctionService
from modules.shared.auth import AuthenticationError, decode_bearer_token
from modules.shared.auction_cache import invalidate_auction_snapshot
from modules.shared.http import error_response, response

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["TABLE_NAME"]


def main(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        user = decode_bearer_token((event.get("headers") or {}).get("Authorization"))
    except AuthenticationError:
        return error_response(401, "unauthorized", "A valid session is required")
    service = AuctionService(dynamodb.Table(TABLE_NAME))
    method = event.get("httpMethod")
    auction_id = (event.get("pathParameters") or {}).get("id")
    if method == "POST" and not auction_id:
        try:
            payload = json.loads(event.get("body") or "{}")
            auction = service.publish(user.uid, payload)
            if auction is None:
                return error_response(403, "profile_unavailable", "Profile is unavailable")
            return response(201, auction)
        except json.JSONDecodeError:
            return error_response(400, "invalid_json", "Request body must be valid JSON")
        except AuctionValidationError as error:
            return error_response(422, "invalid_auction", str(error))
    if method == "DELETE" and auction_id:
        try:
            auction = service.cancel(auction_id, user.uid)
            invalidate_auction_snapshot(auction_id)
            return response(200, auction)
        except KeyError:
            return error_response(404, "auction_not_found", "Auction was not found")
        except PermissionError:
            return error_response(403, "forbidden", "Auction does not belong to this user")
        except AuctionValidationError as error:
            return error_response(409, "auction_not_cancellable", str(error))
    return error_response(405, "method_not_allowed", "Method not allowed")
