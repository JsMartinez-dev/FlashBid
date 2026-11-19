"""Carga datos visuales cuando CDK crea la tabla en LocalStack."""
import logging
import os
import time
from urllib.parse import urlparse

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from cargar_subastas_visuales import load_catalog, seed

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("flashbid.seed")


def main():
    endpoint = os.environ.get("AWS_ENDPOINT_URL", "")
    parsed = urlparse(endpoint)
    if parsed.scheme != "http" or parsed.hostname != "emulador" or parsed.port != 4566:
        raise RuntimeError("La carga automática solo admite http://emulador:4566")

    name = os.environ.get("TABLE_NAME", "FlashBidTable")
    db = boto3.resource("dynamodb", endpoint_url=endpoint)
    table = db.Table(name)
    seeded_table_id = None
    logger.info("Esperando la tabla %s de LocalStack; despliega CDK para crearla.", name)

    while True:
        try:
            info = db.meta.client.describe_table(TableName=name)["Table"]
            table_id = info["TableId"]
            if info["TableStatus"] == "ACTIVE" and table_id != seeded_table_id:
                created, existing, expires = seed(table, load_catalog())
                seeded_table_id = table_id
                logger.info("Datos visuales listos: %s subastas creadas y %s existentes sin modificar.", created, existing)
                if created:
                    logger.info("Las nuevas subastas vencen a las %s (UTC).", expires.isoformat())
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") != "ResourceNotFoundException":
                logger.warning("No se pudo cargar la tabla; se reintentará: %s", error)
            seeded_table_id = None
        except (BotoCoreError, OSError) as error:
            logger.warning("LocalStack no está disponible; se reintentará: %s", error)
        time.sleep(10)


if __name__ == "__main__":
    main()
