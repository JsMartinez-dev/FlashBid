import base64
import binascii
import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from botocore.exceptions import ClientError

from modules.auctions.repository import AuctionRepository
from modules.shared.auction_cache import invalidate_auction_snapshot
from modules.shared.auction_events import publish_auction_event
from modules.users.repository import ProfileRepository
from modules.wallets.repository import WalletRepository
import os
import redis


class BidError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


class BidService:
    def __init__(self, table):
        self.table = table
        self.auctions = AuctionRepository(table)

    def _get(self, pk, sk):
        return self.table.get_item(Key={"PK": pk, "SK": sk}, ConsistentRead=True).get("Item")

    def _request(self, uid, request_id, digest):
        item = self._get(f"USER#{uid}", f"REQUEST#{request_id}")
        if item:
            if item["payloadHash"] != digest:
                raise BidError(409, "request_conflict", "El identificador ya se usó con otros datos")
            return json.loads(item["result"])
        return None

    def place(self, auction_id, uid, amount, request_id):
        if type(amount) is not int or amount <= 0:
            raise BidError(422, "invalid_amount", "La puja debe ser un entero positivo")
        try:
            request_id = str(UUID(request_id))
        except (ValueError, TypeError, AttributeError):
            raise BidError(422, "invalid_request", "requestId debe ser un UUID válido")
        digest = hashlib.sha256(json.dumps({"auctionId": auction_id, "amount": amount}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        existing = self._request(uid, request_id, digest)
        if existing:
            return existing
        profile = ProfileRepository(self.table).get_profile(uid)
        if profile is None:
            raise BidError(403, "profile_unavailable", "El perfil no está disponible")
        WalletRepository(self.table).ensure_initial_wallet(uid)
        for attempt in range(3):
            existing = self._request(uid, request_id, digest)
            if existing:
                return existing
            auction = self._get(f"AUCTION#{auction_id}", "META")
            # La operación pudo confirmarse entre la primera lectura del request y la subasta.
            existing = self._request(uid, request_id, digest)
            if existing:
                return existing
            now = datetime.now(timezone.utc)
            now_ms = int(now.timestamp() * 1000)
            if not auction:
                raise BidError(404, "auction_not_found", "No se encontró la subasta")
            if auction.get("sellerId") == uid:
                raise BidError(403, "own_auction", "No puedes pujar en tu propia subasta")
            if auction.get("status") not in ("ACTIVE_NO_BIDS", "ACTIVE_BIDDING") or int(auction["expiresAt"]) <= now_ms:
                raise BidError(409, "auction_expired", "La subasta ya no admite pujas")
            if auction.get("leaderId") == uid:
                raise BidError(409, "already_leading", "Ya eres el líder de esta subasta")
            minimum = int(auction.get("highestBid", auction["initialPrice"]))
            if amount <= minimum:
                raise BidError(409, "bid_too_low", "La puja debe superar el precio actual")
            wallet = self._get(f"USER#{uid}", "WALLET")
            if not wallet or int(wallet["availableCredits"]) < amount:
                raise BidError(422, "insufficient_funds", "Saldo disponible insuficiente")
            bid_id = str(uuid4())
            timestamp = now.isoformat(timespec="microseconds")
            expires = now_ms + 20000
            bid = {"auctionId": auction_id, "bidId": bid_id, "amount": amount,
                   "userId": uid, "publicAlias": profile["displayName"], "acceptedAt": timestamp,
                   "expiresAt": expires, "version": int(auction["version"]) + 1}
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
                        ":uid": uid, ":alias": profile["displayName"], ":expiry": expires, ":gpk": "AUCTIONS#ACTIVE_BIDDING",
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
                    "payloadHash": digest, "auctionId": auction_id, "result": json.dumps(bid), "ttl": int(now.timestamp()) + 604800},
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
            try:
                self.table.meta.client.transact_write_items(TransactItems=tx)
            except ClientError as error:
                if error.response["Error"]["Code"] not in ("TransactionCanceledException", "TransactionConflictException"):
                    raise
                previous_result = self._request(uid, request_id, digest)
                if previous_result:
                    return previous_result
                if attempt == 2:
                    raise BidError(409, "bid_conflict", "La subasta cambió; actualiza e intenta de nuevo") from error
                continue
            invalidate_auction_snapshot(auction_id)
            try:
                redis.Redis(host=os.environ.get("REDIS_HOST", "redis"), port=int(os.environ.get("REDIS_PORT", "6379")), socket_connect_timeout=1, socket_timeout=1).zadd("auctions:deadlines", {auction_id: expires})
            except redis.RedisError:
                pass
            publish_auction_event(auction_id, {"type": "auction.bid_accepted", "auctionId": auction_id,
                                  "bidId": bid_id, "amount": amount, "leaderAlias": profile["displayName"],
                                  "expiresAt": expires, "version": bid["version"]})
            return bid

    def history(self, auction_id, uid, limit=20, cursor=None):
        auction = self._get(f"AUCTION#{auction_id}", "META")
        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        if not auction or not self.auctions.is_visible(auction, now):
            raise BidError(404, "auction_not_found", "No se encontró la subasta")
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
                raise BidError(400, "invalid_cursor", "Cursor inválido") from error
        result = self.table.query(**query)
        items = [{"bidId": item["bidId"], "amount": int(item["amount"]), "publicAlias": item["publicAlias"], "acceptedAt": item["acceptedAt"]} for item in result.get("Items", [])]
        key = result.get("LastEvaluatedKey")
        next_cursor = base64.urlsafe_b64encode(json.dumps({"uid": uid, "auctionId": auction_id, "key": key}).encode()).decode() if key else None
        return {"items": items, "nextCursor": next_cursor}
