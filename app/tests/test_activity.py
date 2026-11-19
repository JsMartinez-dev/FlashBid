from uuid import uuid4

import boto3
import pytest
from moto import mock_aws

from modules.activity.repository import ActivityRepository
from modules.auctions.repository import AuctionRepository
from modules.bids.service import BidService
from modules.users.repository import ProfileRepository
from modules.wallets.repository import WalletRepository


@pytest.fixture
def activity_table(monkeypatch):
    with mock_aws():
        monkeypatch.setattr("modules.bids.service.invalidate_auction_snapshot", lambda _: None)
        monkeypatch.setattr("modules.bids.service.publish_auction_event", lambda *args: None)
        monkeypatch.setattr("modules.bids.service.redis.Redis.zadd", lambda *args, **kwargs: 1)
        db = boto3.resource("dynamodb", region_name="us-east-1")
        keys = ["PK", "SK", "GSI2PK", "GSI2SK", "GSI4PK", "GSI4SK"]
        indexes = [{"IndexName": name, "KeySchema": [{"AttributeName": name + "PK", "KeyType": "HASH"}, {"AttributeName": name + "SK", "KeyType": "RANGE"}], "Projection": {"ProjectionType": "ALL"}} for name in ("GSI2", "GSI4")]
        table = db.create_table(TableName="activity-test", BillingMode="PAY_PER_REQUEST", AttributeDefinitions=[{"AttributeName": k, "AttributeType": "S"} for k in keys], KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}], GlobalSecondaryIndexes=indexes)
        for uid in ("seller", "one", "two"):
            ProfileRepository(table).create_profile(uid=uid, email=f"{uid}@example.com", display_name=uid, password_hash="hash")
            WalletRepository(table).ensure_initial_wallet(uid)
        yield table


def make_auction(table):
    return AuctionRepository(table).create("seller", "seller", {"title": "Producto", "description": "", "category": "Test", "imageUrl": "https://example.com/a.jpg", "initialPrice": 100})["auctionId"]


def test_latest_bid_per_auction_and_isolation(activity_table):
    table = activity_table
    aid, aid2 = make_auction(table), make_auction(table)
    service = BidService(table)
    service.place(aid, "one", 200, str(uuid4()))
    service.place(aid, "two", 300, str(uuid4()))
    service.place(aid, "one", 400, str(uuid4()))
    service.place(aid2, "one", 250, str(uuid4()))
    repo = ActivityRepository(table)
    page1 = repo.bids("one", 1)
    page2 = repo.bids("one", 1, page1["nextCursor"])
    results = page1["items"] + page2["items"]
    assert {item["auctionId"]: item["amount"] for item in results} == {aid: 400, aid2: 250}
    assert repo.bids("two")["items"][0]["amount"] == 300
    assert repo.auctions("seller")["items"] and repo.auctions("one")["items"] == []
    with pytest.raises(ValueError):
        repo.bids("two", 1, page1["nextCursor"])


def test_legacy_bids_are_migrated_without_overwriting_latest(activity_table):
    table = activity_table
    aid = make_auction(table)
    service = BidService(table)
    service.place(aid, "one", 200, str(uuid4()))
    service.place(aid, "two", 300, str(uuid4()))
    latest = service.place(aid, "one", 400, str(uuid4()))
    table.delete_item(Key={"PK": "USER#one", "SK": f"PARTICIPATION#{aid}"})
    result = ActivityRepository(table).bids("one")
    assert len(result["items"]) == 1
    assert result["items"][0]["bidId"] == latest["bidId"]
    assert result["items"][0]["amount"] == 400
