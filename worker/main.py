import logging
import os
import time

import boto3
import redis
from modules.settlement.service import SettlementService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flashbid.worker")


def synchronize(table, cache):
    query = {"IndexName": "GSI3", "KeyConditionExpression": "GSI3PK = :pk",
             "ExpressionAttributeValues": {":pk": "AUCTIONS#ACTIVE_BIDDING"}, "Limit": 100}
    while True:
        result = table.query(**query)
        for key in result.get("Items", []):
            item = table.get_item(Key={"PK": key["PK"], "SK": key["SK"]}, ConsistentRead=True).get("Item")
            if item and item.get("status") == "ACTIVE_BIDDING":
                # Never replace a later deadline with an outdated index result.
                cache.zadd("auctions:deadlines", {item["auctionId"]: int(item["expiresAt"])}, gt=True)
        if not result.get("LastEvaluatedKey"):
            break
        query["ExclusiveStartKey"] = result["LastEvaluatedKey"]


def process_due(table, cache):
    now = int(time.time() * 1000)
    due = cache.zrangebyscore("auctions:deadlines", "-inf", now, start=0, num=100, withscores=True)
    for auction_id, score in due:
        result = SettlementService(table).close(auction_id)
        if result["status"] == "extended":
            cache.zadd("auctions:deadlines", {auction_id: result["expiresAt"]}, gt=True)
        elif result["status"] in ("finished", "inactive"):
            # A newer bid can update the score while the worker is processing it.
            cache.eval("if redis.call('ZSCORE', KEYS[1], ARGV[1]) == ARGV[2] then return redis.call('ZREM', KEYS[1], ARGV[1]) end return 0", 1, "auctions:deadlines", auction_id, str(int(score)))


def main():
    table = boto3.resource("dynamodb", endpoint_url=os.environ.get("AWS_ENDPOINT_URL")).Table(os.environ["TABLE_NAME"])
    cache = redis.Redis(host=os.environ.get("REDIS_HOST", "redis"), port=int(os.environ.get("REDIS_PORT", "6379")), decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
    last_sync = 0.0
    while True:
        try:
            if time.monotonic() - last_sync >= 30:
                synchronize(table, cache)
                last_sync = time.monotonic()
            process_due(table, cache)
        except Exception:
            logger.exception("Error de worker; se reintentará")
            last_sync = 0.0
        time.sleep(2)


if __name__ == "__main__":
    main()
