import base64
import binascii
import json
from datetime import datetime, timezone

from modules.auctions.repository import AuctionRepository
from botocore.exceptions import ClientError


class ActivityRepository:
    def __init__(self, table):
        self.table = table

    def _query(self, uid, kind, limit, cursor):
        index, partition = ("GSI2", f"SELLER#{uid}") if kind == "auctions" else ("GSI4", f"BIDDER#{uid}")
        pk, sk = f"{index}PK", f"{index}SK"
        args = {"IndexName": index, "KeyConditionExpression": f"{pk} = :owner",
                "ExpressionAttributeValues": {":owner": partition}, "Limit": limit, "ScanIndexForward": False}
        if cursor:
            try:
                if len(cursor) > 4096:
                    raise ValueError("Cursor demasiado largo")
                data = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
                key = data["key"]
                if data["uid"] != uid or data["kind"] != kind or not isinstance(key, dict) or set(key) != {"PK", "SK", pk, sk} or key[pk] != partition or not all(isinstance(v, str) for v in key.values()):
                    raise ValueError("Cursor inválido")
                args["ExclusiveStartKey"] = key
            except (ValueError, TypeError, KeyError, UnicodeError, binascii.Error) as error:
                raise ValueError("Cursor inválido") from error
        result = self.table.query(**args)
        key = result.get("LastEvaluatedKey")
        next_cursor = base64.urlsafe_b64encode(json.dumps({"uid": uid, "kind": kind, "key": key}).encode()).decode() if key else None
        return result.get("Items", []), next_cursor

    def auctions(self, uid, limit=20, cursor=None):
        keys, next_cursor = self._query(uid, "auctions", limit, cursor)
        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        items = []
        for key in keys:
            item = self.table.get_item(Key={"PK": key["PK"], "SK": key["SK"]}, ConsistentRead=True).get("Item")
            if not item or item.get("sellerId") != uid:
                continue
            public = AuctionRepository._public(item)
            if public["status"] == "ACTIVE_NO_BIDS" and int(public["expiresAt"]) <= now:
                public["status"] = "EXPIRED_NO_BIDS"
            elif public["status"] == "ACTIVE_BIDDING" and int(public["expiresAt"]) <= now:
                public["status"] = "FINALIZING"
            items.append(public)
        return {"items": items, "nextCursor": next_cursor, "serverNow": now}

    def _migrate_legacy_bids(self, uid):
        """Restaura una vez los resúmenes de pujas creadas antes del spec 09."""
        marker = {"PK": f"USER#{uid}", "SK": "MIGRATION#PARTICIPATIONS_V1"}
        if self.table.get_item(Key=marker, ConsistentRead=True).get("Item"):
            return
        query = {"IndexName": "GSI4", "KeyConditionExpression": "GSI4PK = :uid",
                 "ExpressionAttributeValues": {":uid": f"BIDDER#{uid}"}, "ScanIndexForward": False, "Limit": 100}
        while True:
            page = self.table.query(**query)
            for key in page.get("Items", []):
                bid = self.table.get_item(Key={"PK": key["PK"], "SK": key["SK"]}, ConsistentRead=True).get("Item")
                if not bid or bid.get("userId") != uid:
                    continue
                try:
                    self.table.update_item(
                        Key={"PK": f"USER#{uid}", "SK": f"PARTICIPATION#{bid['auctionId']}"},
                        UpdateExpression="SET #aid=:aid, #bid=:bid, #amount=:amount, #at=:at, #version=:version",
                        ConditionExpression="attribute_not_exists(#version) OR #version < :version",
                        ExpressionAttributeNames={"#aid": "auctionId", "#bid": "bidId", "#amount": "amount", "#at": "acceptedAt", "#version": "auctionVersion"},
                        ExpressionAttributeValues={":aid": bid["auctionId"], ":bid": bid["bidId"],
                            ":amount": bid["amount"], ":at": bid["acceptedAt"], ":version": int(bid.get("version", 0))},
                    )
                except ClientError as error:
                    if error.response["Error"]["Code"] != "ConditionalCheckFailedException":
                        raise
            if not page.get("LastEvaluatedKey"):
                break
            query["ExclusiveStartKey"] = page["LastEvaluatedKey"]
        self.table.put_item(Item=marker)

    def bids(self, uid, limit=20, cursor=None):
        self._migrate_legacy_bids(uid)
        query = {"KeyConditionExpression": "PK = :pk AND begins_with(SK, :prefix)",
                 "ExpressionAttributeValues": {":pk": f"USER#{uid}", ":prefix": "PARTICIPATION#"},
                 "Limit": limit, "ConsistentRead": True}
        if cursor:
            try:
                if len(cursor) > 4096:
                    raise ValueError("Cursor demasiado largo")
                data = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
                key = data["key"]
                if data["uid"] != uid or data["kind"] != "participations" or not isinstance(key, dict) or set(key) != {"PK", "SK"} or key["PK"] != f"USER#{uid}" or not isinstance(key["SK"], str) or not key["SK"].startswith("PARTICIPATION#"):
                    raise ValueError("Cursor inválido")
                query["ExclusiveStartKey"] = key
            except (ValueError, TypeError, KeyError, UnicodeError, binascii.Error) as error:
                raise ValueError("Cursor inválido") from error
        page = self.table.query(**query)
        items = []
        for bid in page.get("Items", []):
            aid = bid["auctionId"]
            auction = self.table.get_item(Key={"PK": f"AUCTION#{aid}", "SK": "META"}, ConsistentRead=True).get("Item")
            result = {"auctionId": aid, "bidId": bid["bidId"], "amount": int(bid["amount"]), "acceptedAt": bid["acceptedAt"], "auction": None}
            if auction:
                now = int(datetime.now(timezone.utc).timestamp() * 1000)
                state = auction.get("status")
                if state == "ACTIVE_BIDDING" and int(auction.get("expiresAt", 0)) <= now:
                    state = "FINALIZING"
                result["auction"] = {"title": auction.get("title"), "imageUrl": auction.get("imageUrl"), "status": state,
                                     "isLeader": auction.get("leaderId") == uid and state != "FINISHED",
                                     "isWinner": auction.get("winnerUserId") == uid if state == "FINISHED" else False}
            items.append(result)
        key = page.get("LastEvaluatedKey")
        next_cursor = base64.urlsafe_b64encode(json.dumps({"uid": uid, "kind": "participations", "key": key}).encode()).decode() if key else None
        return {"items": items, "nextCursor": next_cursor}
