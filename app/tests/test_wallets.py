import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from moto import mock_aws

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.wallets.repository import INITIAL_CREDITS, WalletRepository


@mock_aws
def test_initial_credit_is_created_once(tabla_dynamodb):
    repository = WalletRepository(tabla_dynamodb)

    first = repository.ensure_initial_wallet("user-1")
    second = repository.ensure_initial_wallet("user-1")

    assert first == second
    assert first["availableCredits"] == INITIAL_CREDITS
    assert first["reservedCredits"] == 0
    movements = repository.list_movements("user-1", 20, None)
    assert len(movements["items"]) == 1
    assert movements["items"][0]["type"] == "INITIAL_CREDIT"


@mock_aws
def test_movements_are_queried_only_for_the_authenticated_user(tabla_dynamodb):
    repository = WalletRepository(tabla_dynamodb)
    repository.ensure_initial_wallet("user-1")
    repository.ensure_initial_wallet("user-2")

    result = repository.list_movements("user-1", 20, None)

    assert len(result["items"]) == 1
    assert result["items"][0]["amount"] == INITIAL_CREDITS


@mock_aws
def test_invalid_movement_cursor_is_rejected(tabla_dynamodb):
    with pytest.raises(ValueError):
        WalletRepository(tabla_dynamodb).list_movements("user-1", 20, "not-a-cursor")


@mock_aws
def test_concurrent_initialization_keeps_a_single_credit(tabla_dynamodb):
    repository = WalletRepository(tabla_dynamodb)

    with ThreadPoolExecutor(max_workers=4) as executor:
        wallets = list(executor.map(lambda _: repository.ensure_initial_wallet("user-1"), range(4)))

    assert {wallet["availableCredits"] for wallet in wallets} == {INITIAL_CREDITS}
    assert len(repository.list_movements("user-1", 20, None)["items"]) == 1


@mock_aws
def test_movements_support_pagination(tabla_dynamodb):
    repository = WalletRepository(tabla_dynamodb)
    repository.ensure_initial_wallet("user-1")
    timestamp = datetime.now(timezone.utc).isoformat()
    tabla_dynamodb.put_item(Item={
        "PK": "USER#user-1", "SK": f"MOVEMENT#{timestamp}#SECOND", "type": "RELEASE",
        "amount": 10, "availableDelta": 10, "reservedDelta": -10,
        "operationId": "second", "createdAt": timestamp,
    })

    first_page = repository.list_movements("user-1", 1, None)
    second_page = repository.list_movements("user-1", 1, first_page["nextCursor"])

    assert len(first_page["items"]) == 1
    assert first_page["nextCursor"] is not None
    assert len(second_page["items"]) == 1
