"""
Lambda /items
─────────────
Maneja las operaciones CRUD sobre ítems.

Rutas soportadas:
  POST   /items          → Crear ítem  (Write-Through: DynamoDB + Redis)
  GET    /items/{id}     → Obtener ítem (Cache-Aside: Redis → DynamoDB)
  DELETE /items/{id}     → Eliminar ítem (invalida la clave en Redis)

Modelo de datos en DynamoDB (Single Table Design):
  PK = "ITEM#<id>"
  SK = "ITEM#<id>"
  + atributos del ítem
"""
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from cache import cache_get, cache_set, cache_delete, cache_key_item

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cliente DynamoDB — boto3 lee AWS_ENDPOINT_URL del entorno
# para redirigir al emulador local automáticamente.
dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["TABLE_NAME"]


def _tabla():
    return dynamodb.Table(TABLE_NAME)


# ── Helpers ───────────────────────────────────────────────────────────

def _respuesta(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str),
    }


def _respuesta_error(status: int, mensaje: str) -> dict:
    return _respuesta(status, {"error": mensaje})


# ── Handlers por método ───────────────────────────────────────────────

def crear_item(body_raw: str) -> dict:
    """
    POST /items
    Crea un ítem en DynamoDB y lo guarda en Redis (Write-Through).
    """
    try:
        datos = json.loads(body_raw or "{}")
    except json.JSONDecodeError:
        return _respuesta_error(400, "El cuerpo de la petición no es JSON válido")

    item_id = datos.get("id") or str(uuid.uuid4())
    ahora = datetime.now(timezone.utc).isoformat()

    item = {
        "PK": f"ITEM#{item_id}",
        "SK": f"ITEM#{item_id}",
        "id":         item_id,
        "nombre":     datos.get("nombre", "Sin nombre"),
        "precio":     datos.get("precio", 0),
        "descripcion": datos.get("descripcion", ""),
        "creado_en":  ahora,
        "actualizado_en": ahora,
    }

    # 1. Guardar en DynamoDB
    _tabla().put_item(Item=item)
    logger.info("DynamoDB PUT item_id=%s", item_id)

    # 2. Write-Through: guardar también en Redis
    cache_set(cache_key_item(item_id), item)

    return _respuesta(201, item)


def obtener_item(item_id: str) -> dict:
    """
    GET /items/{id}
    Patrón Cache-Aside:
      1. Busca en Redis  → si hay hit, retorna directo
      2. Si miss        → lee DynamoDB, guarda en Redis, retorna
    """
    clave = cache_key_item(item_id)

    # 1. Verificar Redis
    cached = cache_get(clave)
    if cached:
        return _respuesta(200, {**cached, "_fuente": "cache"})

    # 2. Leer DynamoDB
    try:
        respuesta = _tabla().get_item(
            Key={"PK": f"ITEM#{item_id}", "SK": f"ITEM#{item_id}"}
        )
    except ClientError as e:
        logger.error("Error DynamoDB: %s", e)
        return _respuesta_error(500, "Error al consultar la base de datos")

    item = respuesta.get("Item")
    if not item:
        return _respuesta_error(404, f"Ítem '{item_id}' no encontrado")

    logger.info("DynamoDB GET item_id=%s", item_id)

    # 3. Guardar en Redis para próximas consultas
    cache_set(clave, item)

    return _respuesta(200, {**item, "_fuente": "dynamodb"})


def eliminar_item(item_id: str) -> dict:
    """
    DELETE /items/{id}
    Elimina el ítem de DynamoDB e invalida la clave en Redis.
    """
    try:
        _tabla().delete_item(
            Key={"PK": f"ITEM#{item_id}", "SK": f"ITEM#{item_id}"},
            ConditionExpression="attribute_exists(PK)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return _respuesta_error(404, f"Ítem '{item_id}' no encontrado")
        logger.error("Error DynamoDB: %s", e)
        return _respuesta_error(500, "Error al eliminar el ítem")

    logger.info("DynamoDB DELETE item_id=%s", item_id)

    # Invalidar caché
    cache_delete(cache_key_item(item_id))

    return _respuesta(200, {"mensaje": f"Ítem '{item_id}' eliminado"})


# ── Entrada principal ─────────────────────────────────────────────────

def main(event: dict, context) -> dict:
    """
    Handler principal de la Lambda.
    API Gateway inyecta el método HTTP y los parámetros de ruta.
    """
    metodo = event.get("httpMethod", "GET")
    params = event.get("pathParameters") or {}
    item_id = params.get("id")

    logger.info("REQUEST %s /items%s", metodo, f"/{item_id}" if item_id else "")

    if metodo == "POST":
        return crear_item(event.get("body", "{}"))

    if metodo == "GET" and item_id:
        return obtener_item(item_id)

    if metodo == "DELETE" and item_id:
        return eliminar_item(item_id)

    return _respuesta_error(405, f"Método '{metodo}' no soportado en esta ruta")
