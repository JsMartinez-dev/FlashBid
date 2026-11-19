import os
import sys
from time import time

import pytest
from moto import mock_aws

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.auctions.repository import AuctionRepository, AuctionValidationError


def auction_payload() -> dict[str, object]:
    return {
        "title": "Vintage camera",
        "description": "A fictional collectible camera.",
        "category": "Collectibles",
        "imageUrl": "https://images.example.test/camera.png",
        "initialPrice": 500,
    }


@mock_aws
def test_create_auction_persists_active_state_ttl_and_indexes(tabla_dynamodb):
    auction = AuctionRepository(tabla_dynamodb).create("seller-1", "Seller", auction_payload())
    stored = tabla_dynamodb.get_item(
        Key={"PK": f"AUCTION#{auction['auctionId']}", "SK": "META"}
    )["Item"]

    assert auction["status"] == "ACTIVE_NO_BIDS"
    assert auction["expiresAt"] > int(time() * 1000)
    assert stored["ttl"] == auction["expiresAt"] // 1000
    assert stored["GSI1PK"] == "AUCTIONS#ACTIVE"
    assert stored["GSI2PK"] == "SELLER#seller-1"


@mock_aws
def test_only_owner_can_cancel_active_auction(tabla_dynamodb):
    repository = AuctionRepository(tabla_dynamodb)
    auction = repository.create("seller-1", "Seller", auction_payload())

    with pytest.raises(PermissionError):
        repository.cancel(auction["auctionId"], "another-user")

    cancelled = repository.cancel(auction["auctionId"], "seller-1")

    assert cancelled["status"] == "CANCELLED"
    assert cancelled["version"] == 2
    stored = tabla_dynamodb.get_item(
        Key={"PK": f"AUCTION#{auction['auctionId']}", "SK": "META"}
    )["Item"]
    assert "ttl" not in stored
    assert "GSI1PK" not in stored


@mock_aws
def test_cannot_cancel_an_expired_or_invalid_auction(tabla_dynamodb):
    repository = AuctionRepository(tabla_dynamodb)
    auction = repository.create("seller-1", "Seller", auction_payload())
    tabla_dynamodb.update_item(
        Key={"PK": f"AUCTION#{auction['auctionId']}", "SK": "META"},
        UpdateExpression="SET expiresAt = :expired",
        ExpressionAttributeValues={":expired": 0},
    )

    with pytest.raises(AuctionValidationError):
        repository.cancel(auction["auctionId"], "seller-1")


@mock_aws
def test_invalid_auction_payload_is_rejected(tabla_dynamodb):
    payload = auction_payload()
    payload["initialPrice"] = 1.5

    with pytest.raises(AuctionValidationError):
        AuctionRepository(tabla_dynamodb).create("seller-1", "Seller", payload)
