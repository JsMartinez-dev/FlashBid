"""Publicación de eventos efímeros tras confirmar cambios en DynamoDB."""
import json
import logging
import os
import redis

logger = logging.getLogger(__name__)


def publish_auction_event(auction_id: str, event: dict) -> None:
    try:
        client = redis.Redis(host=os.environ.get("REDIS_HOST", "redis"),
                             port=int(os.environ.get("REDIS_PORT", "6379")),
                             socket_connect_timeout=1, socket_timeout=1)
        client.publish(f"events:auction:{auction_id}", json.dumps(event))
    except (redis.RedisError, ValueError, TypeError):
        logger.warning("No se pudo publicar evento para subasta %s", auction_id)
