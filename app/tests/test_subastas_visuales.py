from datetime import datetime, timezone

from moto import mock_aws

from scripts.cargar_subastas_visuales import SELLER_ID, load_catalog, seed


@mock_aws
def test_carga_20_horas_y_no_sobrescribe_pujas(tabla_dynamodb):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    products = load_catalog()
    created, skipped, expiry = seed(tabla_dynamodb, products, now)
    assert created == len(products) and skipped == 0
    item = tabla_dynamodb.get_item(Key={"PK": "AUCTION#demo-visual-01", "SK": "META"})["Item"]
    assert int(item["expiresAt"]) - int(now.timestamp() * 1000) == 20 * 60 * 60 * 1000
    assert item["ttl"] == int(expiry.timestamp())
    assert item["GSI1PK"] == "AUCTIONS#ACTIVE" and item["sellerId"] == SELLER_ID
    tabla_dynamodb.update_item(Key={"PK": item["PK"], "SK": "META"}, UpdateExpression="SET #s = :active, highestBid = :bid", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":active": "ACTIVE_BIDDING", ":bid": 1000})
    created, skipped, _ = seed(tabla_dynamodb, products, now)
    current = tabla_dynamodb.get_item(Key={"PK": item["PK"], "SK": "META"})["Item"]
    assert created == 0 and skipped == len(products)
    assert current["status"] == "ACTIVE_BIDDING" and current["highestBid"] == 1000
    assert tabla_dynamodb.get_item(Key={"PK": f"USER#{SELLER_ID}", "SK": "WALLET"}).get("Item") is None
