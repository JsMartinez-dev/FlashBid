import json

from modules.shared import auction_events


def test_publish_uses_per_auction_channel_and_public_payload(monkeypatch):
    sent = []
    class FakeRedis:
        def __init__(self, **kwargs):
            pass
        def publish(self, channel, payload):
            sent.append((channel, json.loads(payload)))
    monkeypatch.setattr(auction_events.redis, "Redis", FakeRedis)
    event = {"type": "auction.bid_accepted", "auctionId": "a1", "version": 2}
    auction_events.publish_auction_event("a1", event)
    assert sent == [("events:auction:a1", event)]


def test_redis_failure_does_not_raise(monkeypatch):
    class BrokenRedis:
        def __init__(self, **kwargs):
            pass
        def publish(self, *args):
            raise auction_events.redis.ConnectionError("unavailable")
    monkeypatch.setattr(auction_events.redis, "Redis", BrokenRedis)
    auction_events.publish_auction_event("a1", {"type": "auction.finished"})
