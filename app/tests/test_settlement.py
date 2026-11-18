from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
from moto import mock_aws

from modules.auctions.repository import AuctionRepository
from modules.bids.service import BidService
from modules.settlement.service import SettlementService
from modules.users.repository import ProfileRepository
from modules.wallets.repository import WalletRepository


@pytest.fixture
def auction_with_bid(tabla_dynamodb, monkeypatch):
    monkeypatch.setattr("modules.bids.service.invalidate_auction_snapshot", lambda _: None)
    monkeypatch.setattr("modules.bids.service.redis.Redis.zadd", lambda *args, **kwargs: 1)
    monkeypatch.setattr("modules.settlement.service.invalidate_auction_snapshot", lambda _: None)
    for uid in ("seller", "winner"):
        ProfileRepository(tabla_dynamodb).create_profile(uid=uid, email=f"{uid}@example.com", display_name=uid, password_hash="hash")
        WalletRepository(tabla_dynamodb).ensure_initial_wallet(uid)
    auction = AuctionRepository(tabla_dynamodb).create("seller", "seller", {"title": "Producto", "description": "", "category": "Test", "imageUrl": "https://example.com/a.jpg", "initialPrice": 100})
    bid = BidService(tabla_dynamodb).place(auction["auctionId"], "winner", 200, str(uuid4()))
    return tabla_dynamodb, auction["auctionId"], bid


@mock_aws
def test_settlement_transfers_once_and_records_win(auction_with_bid):
    table, aid, bid = auction_with_bid
    service = SettlementService(table)
    assert service.close(aid, bid["expiresAt"] - 1)["status"] == "extended"
    assert service.close(aid, bid["expiresAt"])["status"] == "finished"
    assert service.close(aid, bid["expiresAt"])["status"] == "inactive"
    winner = WalletRepository(table).get_wallet("winner")
    seller = WalletRepository(table).get_wallet("seller")
    assert (winner["availableCredits"], winner["reservedCredits"]) == (9800, 0)
    assert (seller["availableCredits"], seller["reservedCredits"]) == (10200, 0)
    assert WalletRepository(table).list_wins("winner", 20, None)["items"][0]["winningAmount"] == 200
    assert WalletRepository(table).list_wins("seller", 20, None)["items"] == []
    assert service.table.get_item(Key={"PK": f"AUCTION#{aid}", "SK": "META"})["Item"]["status"] == "FINISHED"


@mock_aws
def test_two_workers_do_not_transfer_twice(auction_with_bid):
    table, aid, bid = auction_with_bid
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: SettlementService(table).close(aid, bid["expiresAt"]), range(2)))
    assert sum(item["status"] == "finished" for item in outcomes) == 1
    assert WalletRepository(table).get_wallet("seller")["availableCredits"] == 10200
    assert len(WalletRepository(table).list_wins("winner", 20, None)["items"]) == 1
