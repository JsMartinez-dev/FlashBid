from datetime import datetime, timezone

from typing import Any

from modules.auctions.repository import AuctionRepository
from modules.users.repository import ProfileRepository
from modules.shared.auction_cache import cache_read, cache_write, invalidate_auction_snapshot


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

    #Cache-Aside
    def detail(self, auction_id: str) -> dict[str, Any] | None:

        cached, generation = cache_read(auction_id)
        now = int(datetime.now(timezone.utc).timestamp() * 1000)

        if cached is not None and self._auctions.is_visible(cached, now):
            return {**cached, "serverNow": now}
        item = self._auctions.get(auction_id)
        now = int(datetime.now(timezone.utc).timestamp() * 1000)

        if item is None or not self._auctions.is_visible(item, now):
            return None
        cache_write(auction_id, item, generation)
        return {**item, "serverNow": now}

    def cancel(self, auction_id: str, seller_id: str) -> dict[str, Any]:
        result = self._auctions.cancel(auction_id, seller_id)
        invalidate_auction_snapshot(auction_id)
        return result
