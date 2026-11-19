class SettlementRepository:
    """Lectura y transacción de liquidación en DynamoDB."""

    def __init__(self, table):
        self.table = table

    def get_auction(self, auction_id):
        return self.table.get_item(
            Key={"PK": f"AUCTION#{auction_id}", "SK": "META"}, ConsistentRead=True
        ).get("Item")

    def settle(self, auction_id, auction, check_ms, timestamp, settlement):
        winner, seller = auction["leaderId"], auction["sellerId"]
        amount, bid_id = int(auction["highestBid"]), auction["highestBidId"]
        table = self.table.name
        def movement(uid, kind, avail, reserved, other):
            return {"PK": f"USER#{uid}", "SK": f"MOVEMENT#{timestamp}#{settlement}#{kind}", "type": kind,
                    "amount": amount, "availableDelta": avail, "reservedDelta": reserved,
                    "auctionId": auction_id, "relatedUserId": other, "operationId": settlement, "createdAt": timestamp}
        tx = [
            {"Update": {"TableName": table, "Key": {"PK": f"AUCTION#{auction_id}", "SK": "META"},
                "UpdateExpression": "SET #st=:finished, #v=:next, winnerUserId=:winner, winnerAlias=:alias, winningBidId=:bid, winningAmount=:amount, finishedAt=:finishedAt, settlementId=:settlement REMOVE GSI1PK, GSI1SK, GSI3PK, GSI3SK",
                "ConditionExpression": "#st=:active AND #v=:version AND expiresAt<=:now AND leaderId=:winner AND highestBidId=:bid AND highestBid=:amount",
                "ExpressionAttributeNames": {"#st": "status", "#v": "version"},
                "ExpressionAttributeValues": {":finished": "FINISHED", ":active": "ACTIVE_BIDDING", ":version": auction["version"],
                    ":next": int(auction["version"]) + 1, ":winner": winner, ":alias": auction.get("leaderAlias", ""),
                    ":bid": bid_id, ":amount": amount, ":finishedAt": timestamp, ":settlement": settlement, ":now": check_ms}}},
            {"Update": {"TableName": table, "Key": {"PK": f"USER#{winner}", "SK": "WALLET"},
                "UpdateExpression": "SET reservedCredits=reservedCredits-:amount, #v=#v+:one",
                "ConditionExpression": "reservedCredits>=:amount", "ExpressionAttributeNames": {"#v": "version"},
                "ExpressionAttributeValues": {":amount": amount, ":one": 1}}},
            {"Update": {"TableName": table, "Key": {"PK": f"USER#{seller}", "SK": "WALLET"},
                "UpdateExpression": "SET availableCredits=availableCredits+:amount, #v=#v+:one",
                "ConditionExpression": "attribute_exists(PK)", "ExpressionAttributeNames": {"#v": "version"},
                "ExpressionAttributeValues": {":amount": amount, ":one": 1}}},
            {"Put": {"TableName": table, "Item": movement(winner, "PURCHASE", 0, -amount, seller), "ConditionExpression": "attribute_not_exists(PK)"}},
            {"Put": {"TableName": table, "Item": movement(seller, "SALE", amount, 0, winner), "ConditionExpression": "attribute_not_exists(PK)"}},
            {"Put": {"TableName": table, "Item": {"PK": f"USER#{winner}", "SK": f"WON#{timestamp}#{auction_id}",
                "auctionId": auction_id, "winningBidId": bid_id, "winningAmount": amount, "finishedAt": timestamp,
                "settlementId": settlement, "sellerId": seller, "title": auction["title"], "imageUrl": auction["imageUrl"]},
                "ConditionExpression": "attribute_not_exists(PK)"}},
        ]
        self.table.meta.client.transact_write_items(TransactItems=tx)
