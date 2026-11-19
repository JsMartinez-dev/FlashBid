"""Carga subastas visuales exclusivamente en DynamoDB Local.

No modifica subastas existentes ni saldos. La primera puja sigue aplicando
las reglas normales del proyecto y cambia el vencimiento a 20 segundos.
"""
import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

SELLER_ID = "demo-visual-seller"
SELLER_ALIAS = "Colección FlashBid"


def load_catalog():
    path = Path(__file__).with_name("subastas_visuales.json")
    return json.loads(path.read_text(encoding="utf-8"))


def seed(table, items, now=None):
    now = now or datetime.now(timezone.utc)
    expires = now + timedelta(hours=20)
    timestamp = now.isoformat()
    # Perfil reservado para las publicaciones de muestra; no crea credenciales.
    try:
        table.put_item(Item={"PK": f"USER#{SELLER_ID}", "SK": "PROFILE", "uid": SELLER_ID,
                             "displayName": SELLER_ALIAS, "createdAt": timestamp,
                             "email": "demo-visual@example.invalid", "demoVisual": True},
                       ConditionExpression="attribute_not_exists(PK)")
    except ClientError as error:
        if error.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        existing = table.get_item(Key={"PK": f"USER#{SELLER_ID}", "SK": "PROFILE"}, ConsistentRead=True).get("Item")
        if not existing or existing.get("demoVisual") is not True:
            raise RuntimeError("El identificador del vendedor demo ya pertenece a otro perfil") from error
    created, existing_count = 0, 0
    for index, product in enumerate(items, start=1):
        auction_id = f"demo-visual-{index:02d}"
        item = {
            "PK": f"AUCTION#{auction_id}", "SK": "META", "auctionId": auction_id,
            "sellerId": SELLER_ID, "sellerAlias": SELLER_ALIAS, "title": product["title"],
            "description": "Producto de muestra para visualizar el catálogo de FlashBid.",
            "category": "Colección", "imageUrl": product["imageUrl"],
            "initialPrice": 500 + index * 250, "status": "ACTIVE_NO_BIDS", "version": 1,
            "createdAt": timestamp, "expiresAt": int(expires.timestamp() * 1000),
            "ttl": int(expires.timestamp()), "GSI1PK": "AUCTIONS#ACTIVE",
            "GSI1SK": f"{timestamp}#{auction_id}", "GSI2PK": f"SELLER#{SELLER_ID}",
            "GSI2SK": f"{timestamp}#{auction_id}", "demoVisual": True,
        }
        try:
            table.put_item(Item=item, ConditionExpression="attribute_not_exists(PK)")
            created += 1
        except ClientError as error:
            if error.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
            existing_count += 1
    return created, existing_count, expires


def main():
    parser = argparse.ArgumentParser(description="Cargar subastas visuales de 20 horas en DynamoDB Local.")
    parser.add_argument("--endpoint", default=os.environ.get("AWS_ENDPOINT_URL", "http://localhost:8002"))
    parser.add_argument("--table", default=os.environ.get("TABLE_NAME", "FlashBidTable"))
    args = parser.parse_args()
    endpoint = urlparse(args.endpoint)
    if endpoint.scheme != "http" or endpoint.hostname not in {"localhost", "127.0.0.1", "dynamodb"}:
        parser.error("Este script solo permite DynamoDB Local en localhost, 127.0.0.1 o el servicio Docker dynamodb")
    db = boto3.resource("dynamodb", endpoint_url=args.endpoint,
                        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
                        aws_access_key_id="test", aws_secret_access_key="test")
    table = db.Table(args.table)
    table.load()
    created, skipped, expires = seed(table, load_catalog())
    print(f"Subastas creadas: {created}. Ya existentes, sin modificar: {skipped}.")
    if created:
        print(f"Vencimiento de las nuevas subastas sin pujas: {expires.isoformat()} (UTC).")
    print("El vendedor de muestra no tiene credenciales; las cuentas existentes no se modificaron.")


if __name__ == "__main__":
    main()
