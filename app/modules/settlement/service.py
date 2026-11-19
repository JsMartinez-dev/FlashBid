from datetime import datetime, timezone
from uuid import uuid4

from botocore.exceptions import ClientError
from modules.shared.auction_cache import invalidate_auction_snapshot
from modules.shared.auction_events import publish_auction_event
from modules.wallets.repository import WalletRepository


class SettlementService:
    def __init__(self, table):
        self.table = table

    def close(self, auction_id, now_ms=None):
        
        auction = self.table.get_item(Key={"PK": f"AUCTION#{auction_id}",
                                            "SK": "META"}, ConsistentRead=True).get("Item")
        
        if not auction or auction.get("status") != "ACTIVE_BIDDING":
            return {"status": "inactive"}
        now = datetime.now(timezone.utc)
        check_ms = int(now.timestamp() * 1000) if now_ms is None else now_ms
        if int(auction["expiresAt"]) > check_ms:
            return {"status": "extended", "expiresAt": int(auction["expiresAt"])}
        winner, seller = auction["leaderId"], auction["sellerId"]
        if winner == seller:
            raise ValueError("El vendedor no puede ser el ganador")
        WalletRepository(self.table).ensure_initial_wallet(seller)
        amount, bid_id = int(auction["highestBid"]), auction["highestBidId"]
        settlement = str(uuid4())
        timestamp = now.isoformat(timespec="microseconds")
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
        try:
            self.table.meta.client.transact_write_items(TransactItems=tx)
        except ClientError as error:
            if error.response["Error"]["Code"] in ("TransactionCanceledException", "TransactionConflictException"):
                return {"status": "retry"}
            raise
        invalidate_auction_snapshot(auction_id)
        publish_auction_event(auction_id, {"type": "auction.finished", "auctionId": auction_id,
                              "winnerAlias": auction.get("leaderAlias", ""), "winningAmount": amount,
                              "version": int(auction["version"]) + 1})
        return {"status": "finished", "settlementId": settlement}
