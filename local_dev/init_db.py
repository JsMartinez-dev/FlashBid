"""Create the local table once; never delete or overwrite existing data."""
import os
import time

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError


def main():
    client = boto3.client("dynamodb", endpoint_url=os.environ["AWS_ENDPOINT_URL"])
    table = os.environ.get("TABLE_NAME", "FlashBidTable")
    for attempt in range(60):
        try:
            client.list_tables()
            break
        except EndpointConnectionError:
            if attempt == 59:
                raise
            time.sleep(2)
    try:
        client.describe_table(TableName=table)
    except client.exceptions.ResourceNotFoundException:
        indexes = [
            {"IndexName": f"GSI{i}",
             "KeySchema": [{"AttributeName": f"GSI{i}PK", "KeyType": "HASH"},
                           {"AttributeName": f"GSI{i}SK", "KeyType": "RANGE"}],
             "Projection": ({"ProjectionType": "INCLUDE", "NonKeyAttributes": ["amount", "acceptedAt", "bidId"]}
                            if i == 4 else {"ProjectionType": "KEYS_ONLY"})}
            for i in range(1, 5)
        ]
        attrs = [{"AttributeName": key, "AttributeType": "S"}
                 for key in ["PK", "SK"] + [f"GSI{i}{suffix}" for i in range(1, 5) for suffix in ("PK", "SK")]]
        try:
            client.create_table(TableName=table, BillingMode="PAY_PER_REQUEST", AttributeDefinitions=attrs,
                                KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"},
                                           {"AttributeName": "SK", "KeyType": "RANGE"}],
                                GlobalSecondaryIndexes=indexes)
        except client.exceptions.ResourceInUseException:
            pass
    client.get_waiter("table_exists").wait(TableName=table)
    try:
        status = client.describe_time_to_live(TableName=table)["TimeToLiveDescription"].get("TimeToLiveStatus")
        if status == "DISABLED":
            client.update_time_to_live(TableName=table, TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"})
    except ClientError as error:
        raise RuntimeError("Could not configure TTL on the local table") from error
    print(f"Local table ready: {table}", flush=True)


if __name__ == "__main__":
    main()
