from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from moto import mock_aws

from modules.auctions.repository import AuctionRepository
from modules.bids.service import BidError, BidService
from modules.users.repository import ProfileRepository
from modules.wallets.repository import WalletRepository


@pytest.fixture
def scenario(tabla_dynamodb, monkeypatch):
    monkeypatch.setattr("modules.bids.service.invalidate_auction_snapshot", lambda _: None)
    monkeypatch.setattr("modules.bids.service.redis.Redis.zadd", lambda *args, **kwargs: 1)
    profiles = ProfileRepository(tabla_dynamodb)
    for uid in ("seller", "one", "two"):
        profiles.create_profile(uid=uid, email=f"{uid}@example.com", display_name=uid, password_hash="hash")
        WalletRepository(tabla_dynamodb).ensure_initial_wallet(uid)
    auction = AuctionRepository(tabla_dynamodb).create("seller", "seller", {
        "title": "Producto", "description": "Prueba", "category": "Test",
        "imageUrl": "https://example.com/image.jpg", "initialPrice": 500,
    })
    return BidService(tabla_dynamodb), auction["auctionId"], tabla_dynamodb


@mock_aws
def test_bids_reserve_release_and_deduplicate(scenario):
    service, aid, table = scenario
    request_id = str(uuid4())
    with pytest.raises(BidError) as equal:
        service.place(aid, "one", 500, str(uuid4()))
    assert equal.value.status == 409
    first = service.place(aid, "one", 501, request_id)
    assert service.place(aid, "one", 501, request_id) == first
    with pytest.raises(BidError):
        service.place(aid, "one", 502, request_id)
    with pytest.raises(BidError):
        service.place(aid, "one", 502, str(uuid4()))
    service.place(aid, "two", 600, str(uuid4()))
    one = WalletRepository(table).get_wallet("one")
    two = WalletRepository(table).get_wallet("two")
    assert (one["availableCredits"], one["reservedCredits"]) == (10000, 0)
    assert (two["availableCredits"], two["reservedCredits"]) == (9400, 600)
    meta = service._get(f"AUCTION#{aid}", "META")
    assert meta["leaderId"] == "two" and "ttl" not in meta
    assert len(service.history(aid, "one")["items"]) == 2


@mock_aws
def test_rejected_bids_do_not_change_wallet(scenario):
    service, aid, table = scenario
    for user, amount in (("seller", 600), ("one", 10001), ("one", 1.5)):
        with pytest.raises(BidError):
            service.place(aid, user, amount, str(uuid4()))
    wallet = WalletRepository(table).get_wallet("one")
    assert (wallet["availableCredits"], wallet["reservedCredits"]) == (10000, 0)
    assert service.history(aid, "one")["items"] == []


@mock_aws
def test_same_request_concurrent_only_reserves_once(scenario):
    service, aid, table = scenario
    request_id = str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: service.place(aid, "one", 700, request_id), range(2)))
    assert results[0] == results[1]
    wallet = WalletRepository(table).get_wallet("one")
    assert (wallet["availableCredits"], wallet["reservedCredits"]) == (9300, 700)
    assert len(service.history(aid, "one")["items"]) == 1


@mock_aws
def test_expired_auction_cannot_reserve(scenario):
    service, aid, table = scenario
    table.update_item(Key={"PK": f"AUCTION#{aid}", "SK": "META"}, UpdateExpression="SET expiresAt=:zero", ExpressionAttributeValues={":zero": 0})
    with pytest.raises(BidError) as failure:
        service.place(aid, "one", 700, str(uuid4()))
    assert failure.value.code == "auction_expired"
    assert WalletRepository(table).get_wallet("one")["reservedCredits"] == 0


@mock_aws
def test_multiple_auctions_cannot_reuse_reserved_money(scenario):
    service, aid, table = scenario
    other = AuctionRepository(table).create("seller", "seller", {
        "title": "Otro producto", "description": "Prueba", "category": "Test",
        "imageUrl": "https://example.com/image.jpg", "initialPrice": 500,
    })["auctionId"]
    service.place(aid, "one", 7000, str(uuid4()))
    with pytest.raises(BidError) as failure:
        service.place(other, "one", 4000, str(uuid4()))
    assert failure.value.code == "insufficient_funds"
    wallet = WalletRepository(table).get_wallet("one")
    assert (wallet["availableCredits"], wallet["reservedCredits"]) == (3000, 7000)
