from typing import Any

from modules.users.repository import ProfileRepository
from modules.wallets.repository import WalletRepository


class UserService:
    def __init__(self, table: Any) -> None:
        self._profiles = ProfileRepository(table)
        self._wallets = WalletRepository(table)

    def profile_with_wallet(self, uid: str) -> dict[str, Any] | None:
        profile = self._profiles.get_profile(uid)
        if profile is None:
            return None
        return {
            "uid": profile["uid"], "email": profile["email"], "displayName": profile["displayName"],
            "createdAt": profile["createdAt"], "wallet": self._wallets.ensure_initial_wallet(uid),
        }
