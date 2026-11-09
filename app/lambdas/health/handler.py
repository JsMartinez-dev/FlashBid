"""
Lambda /health
──────────────
Health check del servicio.
Verifica conectividad con DynamoDB y Redis
y retorna el estado de cada componente.
"""
import json
import logging
import os

import boto3
import redis
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["TABLE_NAME"]


def _check_dynamodb() -> dict:
    try:
        tabla = dynamodb.Table(TABLE_NAME)
        tabla.load()   # describe la tabla; falla si no existe
        return {"estado": "ok", "tabla": TABLE_NAME}
    except ClientError as e:
        return {"estado": "error", "detalle": str(e)}
    except Exception as e:
        return {"estado": "error", "detalle": str(e)}


def _check_redis() -> dict:
    try:
        cliente = redis.Redis(
            host=os.environ.get("REDIS_HOST", "redis"),
            port=int(os.environ.get("REDIS_PORT", 6379)),
            decode_responses=True,
            socket_connect_timeout=2,
        )
        cliente.ping()
        return {"estado": "ok", "host": os.environ.get("REDIS_HOST", "redis")}
    except redis.RedisError as e:
        return {"estado": "error", "detalle": str(e)}


def main(event: dict, context) -> dict:
    logger.info("Health check solicitado")

    db_status    = _check_dynamodb()
    redis_status = _check_redis()

    todo_ok = (
        db_status["estado"] == "ok"
        and redis_status["estado"] == "ok"
    )

    return {
        "statusCode": 200 if todo_ok else 503,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "estado":   "ok" if todo_ok else "degradado",
            "dynamodb": db_status,
            "redis":    redis_status,
        }),
    }
