"""Cache-aside para instantáneas públicas de subastas."""
import json
import os
import uuid

import redis


def _client():
    return redis.Redis(host=os.environ.get("REDIS_HOST", "redis"),
                       port=int(os.environ.get("REDIS_PORT", "6379")),
                       socket_connect_timeout=1, socket_timeout=1, decode_responses=True)


def _keys(auction_id):
    return f"auction:{auction_id}:snapshot", f"auction:{auction_id}:generation"


def cache_read(auction_id):
    """Devuelve instantánea y generación previa a la lectura de DynamoDB."""
    try:
        client = _client()
        snapshot, generation = _keys(auction_id)
        client.set(generation, uuid.uuid4().hex, nx=True)
        pipe = client.pipeline(transaction=True)
        pipe.get(generation)
        pipe.get(snapshot)
        token, value = pipe.execute()
        return (json.loads(value) if value else None), token
    except (redis.RedisError, ValueError, TypeError):
        return None, None


def cache_write(auction_id, value, generation):
    if generation is None:
        return
    try:
        ttl = max(1, int(os.environ.get("AUCTION_CACHE_TTL", "3")))
        snapshot, key = _keys(auction_id)
        _client().eval(
            "if redis.call('GET', KEYS[1]) == ARGV[1] then "
            "return redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[3]) end return nil",
            2, key, snapshot, generation, json.dumps(value, default=str), ttl,
        )
    except (redis.RedisError, ValueError, TypeError):
        return


def invalidate_auction_snapshot(auction_id):
    try:
        snapshot, generation = _keys(auction_id)
        pipe = _client().pipeline(transaction=True)
        pipe.set(generation, uuid.uuid4().hex)
        pipe.delete(snapshot)
        pipe.execute()
    except redis.RedisError:
        return
