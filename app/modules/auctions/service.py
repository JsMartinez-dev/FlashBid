from datetime import datetime, timezone

from typing import Any

from modules.auctions.repository import AuctionRepository
from modules.users.repository import ProfileRepository
from modules.shared.auction_cache import cache_read, cache_write, invalidate_auction_snapshot
from modules.shared.auction_events import publish_auction_event


class AuctionService:
    def __init__(self, table: Any) -> None:
        self._auctions = AuctionRepository(table)
        self._profiles = ProfileRepository(table)

    def publish(self, seller_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        profile = self._profiles.get_profile(seller_id)
        if profile is None:
            return None
        return self._auctions.create(seller_id, profile["displayName"], payload)

    def list_active(self, uid: str, limit: int = 20, cursor: str | None = None) -> dict[str, Any]:
        return self._auctions.list_active(min(max(limit, 1), 50), cursor, uid)

    #Cache-aside
    def detail(self, auction_id: str) -> dict[str, Any] | None:
        cached, generation = cache_read(auction_id)
        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        if cached is not None and (cached.get("status") == "FINISHED" or self._auctions.is_visible(cached, now)):
            return {**cached, "serverNow": now}
        item = self._auctions.get(auction_id)
        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        if item is None:
            return None
        if item.get("status") == "ACTIVE_BIDDING" and int(item["expiresAt"]) <= now:
            return {**item, "status": "FINALIZING", "serverNow": now}
        if item.get("status") != "FINISHED" and not self._auctions.is_visible(item, now):
            return None
        cache_write(auction_id, item, generation)
        return {**item, "serverNow": now}

    def cancel(self, auction_id: str, seller_id: str) -> dict[str, Any]:
        result = self._auctions.cancel(auction_id, seller_id)
        invalidate_auction_snapshot(auction_id)
        publish_auction_event(auction_id, {"type": "auction.cancelled", "auctionId": auction_id, "version": result["version"]})
        return result
