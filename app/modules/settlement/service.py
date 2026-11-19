from datetime import datetime, timezone
from uuid import uuid4

from botocore.exceptions import ClientError
from modules.shared.auction_cache import invalidate_auction_snapshot
from modules.shared.auction_events import publish_auction_event
from modules.wallets.repository import WalletRepository
from modules.settlement.repository import SettlementRepository


class SettlementService:
    def __init__(self, table):
        self.table = table
        self.repository = SettlementRepository(table)

    def close(self, auction_id, now_ms=None):
        
        auction = self.repository.get_auction(auction_id)
        
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
        amount = int(auction["highestBid"])
        settlement = str(uuid4())
        timestamp = now.isoformat(timespec="microseconds")
        try:
            self.repository.settle(auction_id, auction, check_ms, timestamp, settlement)
        except ClientError as error:
            if error.response["Error"]["Code"] in ("TransactionCanceledException", "TransactionConflictException"):
                return {"status": "retry"}
            raise
        invalidate_auction_snapshot(auction_id)
        publish_auction_event(auction_id, {"type": "auction.finished", "auctionId": auction_id,
                              "winnerAlias": auction.get("leaderAlias", ""), "winningAmount": amount,
                              "version": int(auction["version"]) + 1})
        return {"status": "finished", "settlementId": settlement}
