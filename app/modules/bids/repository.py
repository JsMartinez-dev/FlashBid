import base64
import binascii
import json


class BidRepository:
    """Consultas y transacciones DynamoDB de pujas."""

    def __init__(self, table):
        self.table = table

    def get(self, pk, sk):
        return self.table.get_item(Key={"PK": pk, "SK": sk}, ConsistentRead=True).get("Item")

    def commit_bid(self, auction, bid, request_id, digest, now_ms):
        auction_id = bid["auctionId"]
        uid = bid["userId"]
        amount = bid["amount"]
        bid_id = bid["bidId"]
        timestamp = bid["acceptedAt"]
        expires = bid["expiresAt"]
        alias = bid["publicAlias"]
        table = self.table.name
        def movement(user, kind, value, available_delta, reserved_delta):
            return {"PK": f"USER#{user}", "SK": f"MOVEMENT#{timestamp}#{bid_id}#{kind}",
                    "type": kind, "amount": value, "availableDelta": available_delta,
                    "reservedDelta": reserved_delta, "operationId": bid_id,
                    "auctionId": auction_id, "createdAt": timestamp}
        tx = [
            {"Update": {"TableName": table, "Key": {"PK": f"AUCTION#{auction_id}", "SK": "META"},
                "UpdateExpression": "SET #st=:active, #v=:newv, highestBid=:amount, highestBidId=:bid, leaderId=:uid, leaderAlias=:alias, expiresAt=:expiry, GSI3PK=:gpk, GSI3SK=:gsk REMOVE #ttl",
                "ConditionExpression": "#st=:oldst AND #v=:oldv AND expiresAt>:now",
                "ExpressionAttributeNames": {"#st": "status", "#v": "version", "#ttl": "ttl"},
                "ExpressionAttributeValues": {":active": "ACTIVE_BIDDING", ":newv": bid["version"], ":amount": amount, ":bid": bid_id,
                    ":uid": uid, ":alias": alias, ":expiry": expires, ":gpk": "AUCTIONS#ACTIVE_BIDDING",
                    ":gsk": f"{expires:013d}#{auction_id}", ":oldst": auction["status"], ":oldv": auction["version"], ":now": now_ms}}},
            {"Update": {"TableName": table, "Key": {"PK": f"USER#{uid}", "SK": "WALLET"},
                "UpdateExpression": "SET availableCredits=availableCredits-:amount, reservedCredits=reservedCredits+:amount, #v=#v+:one",
                "ConditionExpression": "availableCredits>=:amount", "ExpressionAttributeNames": {"#v": "version"},
                "ExpressionAttributeValues": {":amount": amount, ":one": 1}}},
            {"Put": {"TableName": table, "Item": {"PK": f"AUCTION#{auction_id}", "SK": f"BID#{timestamp}#{bid_id}",
                **bid, "requestId": request_id, "GSI4PK": f"BIDDER#{uid}", "GSI4SK": f"{timestamp}#{bid_id}"},
                "ConditionExpression": "attribute_not_exists(PK)"}},
            {"Update": {"TableName": table, "Key": {"PK": f"USER#{uid}", "SK": f"PARTICIPATION#{auction_id}"},
                "UpdateExpression": "SET #aid=:aid, #bid=:bid, #amount=:amount, #at=:at, #version=:version",
                "ExpressionAttributeNames": {"#aid": "auctionId", "#bid": "bidId", "#amount": "amount", "#at": "acceptedAt", "#version": "auctionVersion"},
                "ExpressionAttributeValues": {":aid": auction_id, ":bid": bid_id, ":amount": amount,
                                              ":at": timestamp, ":version": bid["version"]}}},
            {"Put": {"TableName": table, "Item": movement(uid, "RESERVE", amount, -amount, amount),
                "ConditionExpression": "attribute_not_exists(PK)"}},
            {"Put": {"TableName": table, "Item": {"PK": f"USER#{uid}", "SK": f"REQUEST#{request_id}",
                "payloadHash": digest, "auctionId": auction_id, "result": json.dumps(bid), "ttl": now_ms // 1000 + 604800},
                "ConditionExpression": "attribute_not_exists(PK)"}},
        ]
        previous = auction.get("leaderId")
        if previous:
            old_amount = int(auction["highestBid"])
            tx.extend([
                {"Update": {"TableName": table, "Key": {"PK": f"USER#{previous}", "SK": "WALLET"},
                    "UpdateExpression": "SET availableCredits=availableCredits+:amount, reservedCredits=reservedCredits-:amount, #v=#v+:one",
                    "ConditionExpression": "reservedCredits>=:amount", "ExpressionAttributeNames": {"#v": "version"},
                    "ExpressionAttributeValues": {":amount": old_amount, ":one": 1}}},
                {"Put": {"TableName": table, "Item": movement(previous, "RELEASE", old_amount, old_amount, -old_amount),
                    "ConditionExpression": "attribute_not_exists(PK)"}},
            ])
        self.table.meta.client.transact_write_items(TransactItems=tx)

    def history(self, auction_id, uid, limit, cursor):
        query = {"KeyConditionExpression": "PK = :pk AND begins_with(SK, :prefix)",
                 "ExpressionAttributeValues": {":pk": f"AUCTION#{auction_id}", ":prefix": "BID#"},
                 "ScanIndexForward": False, "Limit": limit, "ConsistentRead": True}
        if cursor:
            try:
                data = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
                key = data["key"]
                if data["uid"] != uid or data["auctionId"] != auction_id or set(key) != {"PK", "SK"} or key["PK"] != f"AUCTION#{auction_id}" or not isinstance(key["SK"], str) or not key["SK"].startswith("BID#"):
                    raise ValueError("cursor")
                query["ExclusiveStartKey"] = key
            except (ValueError, TypeError, KeyError, UnicodeError, binascii.Error) as error:
                raise ValueError("Cursor inválido") from error
        result = self.table.query(**query)
        items = [{"bidId": item["bidId"], "amount": int(item["amount"]), "publicAlias": item["publicAlias"], "acceptedAt": item["acceptedAt"]} for item in result.get("Items", [])]
        key = result.get("LastEvaluatedKey")
        next_cursor = base64.urlsafe_b64encode(json.dumps({"uid": uid, "auctionId": auction_id, "key": key}).encode()).decode() if key else None
        return {"items": items, "nextCursor": next_cursor}
