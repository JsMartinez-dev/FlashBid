import os
import boto3
from modules.activity.repository import ActivityRepository
from modules.shared.auth import AuthenticationError, decode_bearer_token
from modules.shared.http import error_response, response


dynamodb = boto3.resource("dynamodb")


def main(event, context):
    try:
        user = decode_bearer_token((event.get("headers") or {}).get("Authorization"))
    except AuthenticationError:
        return error_response(401, "unauthorized", "Se requiere una sesión válida")
    params = event.get("queryStringParameters") or {}
    try:
        limit = int(params.get("limit", 20))
        if not 1 <= limit <= 50:
            raise ValueError("Límite inválido")
        repo = ActivityRepository(dynamodb.Table(os.environ["TABLE_NAME"]))
        path = (event.get("resource") or event.get("path") or "").rstrip("/")
        if path.endswith("/auctions"):
            return response(200, repo.auctions(user.uid, limit, params.get("cursor")))
        if path.endswith("/bids"):
            return response(200, repo.bids(user.uid, limit, params.get("cursor")))
        return error_response(404, "not_found", "Ruta no encontrada")
    except (ValueError, TypeError, KeyError):
        return error_response(400, "invalid_pagination", "Paginación inválida")
