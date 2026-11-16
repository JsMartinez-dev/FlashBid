from typing import Any

from modules.auctions.repository import AuctionRepository
from modules.users.repository import ProfileRepository


class AuctionService:
    def __init__(self, table: Any) -> None:
        self._auctions = AuctionRepository(table)
        self._profiles = ProfileRepository(table)

    def publish(self, seller_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        profile = self._profiles.get_profile(seller_id)
        if profile is None:
            return None
        return self._auctions.create(seller_id, profile["displayName"], payload)

    def cancel(self, auction_id: str, seller_id: str) -> dict[str, Any]:
        return self._auctions.cancel(auction_id, seller_id)
