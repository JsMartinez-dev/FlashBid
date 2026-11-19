import json
import os
from typing import Any

import boto3

from modules.auctions.repository import AuctionValidationError
from modules.auctions.service import AuctionService
from modules.shared.auth import AuthenticationError, decode_bearer_token
from modules.shared.http import error_response, response

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["TABLE_NAME"]


def main(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        user = decode_bearer_token((event.get("headers") or {}).get("Authorization"))
    except AuthenticationError:
        return error_response(401, "unauthorized", "Se requiere una sesión válida")

    service = AuctionService(dynamodb.Table(TABLE_NAME))
    method = event.get("httpMethod")
    auction_id = (event.get("pathParameters") or {}).get("id")

    if method == "GET" and not auction_id:
        params = event.get("queryStringParameters") or {}
        try:
            limit = int(params.get("limit", 20))
            if not 1 <= limit <= 50:
                raise ValueError("Invalid limit")
            return response(200, service.list_active(user.uid, limit, params.get("cursor")))
        except ValueError:
            return error_response(400, "invalid_pagination", "Paginación inválida")
    if method == "GET" and auction_id:
        auction = service.detail(auction_id)
        if auction is None:
            return error_response(404, "auction_not_found", "No se encontró la subasta")
        return response(200, auction)

    if method == "POST" and not auction_id:
        try:
            payload = json.loads(event.get("body") or "{}")
            auction = service.publish(user.uid, payload)
            if auction is None:
                return error_response(403, "profile_unavailable", "El perfil no está disponible")
            return response(201, auction)
        except json.JSONDecodeError:
            return error_response(400, "invalid_json", "El cuerpo de la solicitud debe ser JSON válido")
        except AuctionValidationError as error:
            return error_response(422, "invalid_auction", str(error))
        
    if method == "DELETE" and auction_id:
        try:
            auction = service.cancel(auction_id, user.uid)
            return response(200, auction)
        except KeyError:
            return error_response(404, "auction_not_found", "No se encontró la subasta")
        except PermissionError:
            return error_response(403, "forbidden", "La subasta no pertenece a este usuario")
        except AuctionValidationError as error:
            return error_response(409, "auction_not_cancellable", str(error))
    return error_response(405, "method_not_allowed", "Método no permitido")
