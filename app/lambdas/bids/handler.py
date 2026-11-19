import json
import os

import boto3
from modules.bids.service import BidError, BidService
from modules.shared.auth import AuthenticationError, decode_bearer_token
from modules.shared.http import error_response, response


dynamodb = boto3.resource("dynamodb")


def main(event, context):
    try:
        user = decode_bearer_token((event.get("headers") or {}).get("Authorization"))
    except AuthenticationError:
        return error_response(401, "unauthorized", "Se requiere una sesión válida")
    auction_id = (event.get("pathParameters") or {}).get("id")
    if not auction_id:
        return error_response(400, "invalid_auction", "Falta el identificador de subasta")
    service = BidService(dynamodb.Table(os.environ["TABLE_NAME"]))
    try:
        if event.get("httpMethod") == "POST":
            payload = json.loads(event.get("body") or "{}")
            if not isinstance(payload, dict):
                raise BidError(422, "invalid_body", "El cuerpo debe ser un objeto JSON")
            return response(201, service.place(auction_id, user.uid, payload.get("amount"), payload.get("requestId")))
        if event.get("httpMethod") == "GET":
            params = event.get("queryStringParameters") or {}
            try:
                limit = int(params.get("limit", 20))
            except (TypeError, ValueError):
                raise BidError(400, "invalid_limit", "Límite inválido")
            if not 1 <= limit <= 50:
                raise BidError(400, "invalid_limit", "Límite inválido")
            return response(200, service.history(auction_id, user.uid, limit, params.get("cursor")))
        return error_response(405, "method_not_allowed", "Método no permitido")
    except json.JSONDecodeError:
        return error_response(400, "invalid_json", "El cuerpo debe ser JSON válido")
    except BidError as error:
        return error_response(error.status, error.code, error.message)
