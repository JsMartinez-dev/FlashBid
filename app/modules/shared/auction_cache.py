import os

import redis


def invalidate_auction_snapshot(auction_id: str) -> None:
    try:
        client = redis.Redis(
            host=os.environ.get("REDIS_HOST", "redis"),
            port=int(os.environ.get("REDIS_PORT", "6379")),
            socket_connect_timeout=1,
        )
        client.delete(f"auction:{auction_id}:snapshot")
    except redis.RedisError:
        return
