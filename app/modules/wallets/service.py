from typing import Any

from modules.wallets.repository import WalletRepository


class WalletService:
    def __init__(self, table: Any) -> None:
        self._repository = WalletRepository(table)

    def movements(self, uid: str, limit: int, cursor: str | None) -> dict[str, Any]:
        return self._repository.list_movements(uid, limit, cursor)
