"""Local-only HTTP adapter; shared services remain the source of business logic."""
import os
from typing import Any

import boto3
import redis
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from modules.bids.service import BidError, BidService
from modules.activity.repository import ActivityRepository
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth_service.main import login, register
from local_dev.websocket import router as websocket_router
from modules.auctions.repository import AuctionValidationError
from modules.auctions.service import AuctionService
from modules.shared.auth import AuthenticationError, AuthenticatedUser, decode_bearer_token
from modules.users.service import UserService
from modules.wallets.service import WalletService
from modules.wallets.repository import WalletRepository

app = FastAPI(title="FlashBid — API local", description="Adaptador de desarrollo para DynamoDB Local y Redis.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
                   allow_headers=["Authorization", "Content-Type"])
security = HTTPBearer(auto_error=False)

# Spec 08 — suscripción autenticada a eventos de subasta.
app.include_router(websocket_router)


def table():
    return boto3.resource("dynamodb", endpoint_url=os.environ["AWS_ENDPOINT_URL"]).Table(os.environ["TABLE_NAME"])


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> AuthenticatedUser:
    try:
        return decode_bearer_token(f"Bearer {credentials.credentials}" if credentials else None)
    except AuthenticationError as error:
        raise HTTPException(status_code=401, detail="Se requiere una sesión válida") from error



# Spec 01 — CU-01-03: consultar la salud de DynamoDB y Redis.
@app.get("/health", tags=["Salud"])
def health():
    db_status = "ok"
    redis_status = "ok"
    try:
        table().load()
    except Exception:
        db_status = "error"
    try:
        redis.Redis(host=os.environ.get("REDIS_HOST", "redis"), port=int(os.environ.get("REDIS_PORT", "6379")),
                    socket_connect_timeout=2, socket_timeout=2).ping()
    except redis.RedisError:
        redis_status = "error"
    from fastapi.responses import JSONResponse
    ok = db_status == "ok" and redis_status == "ok"
    return JSONResponse(status_code=200 if ok else 503, content={"estado": "ok" if ok else "degradado",
        "dynamodb": {"estado": db_status}, "redis": {"estado": redis_status}})


# Specs 02 y 03 — CU-02-03 y CU-03-01/02: perfil autenticado y billetera.
@app.get("/me", tags=["Perfil y billetera"])
def me(user: AuthenticatedUser = Depends(current_user)):
    profile = UserService(table()).profile_with_wallet(user.uid)
    if profile is None:
        raise HTTPException(status_code=403, detail="El perfil no está disponible")
    return profile


# Spec 03 — CU-03-02: consultar movimientos de la billetera.
@app.get("/me/wallet/movements", tags=["Perfil y billetera"])
def movements(limit: int = Query(default=20), cursor: str | None = None,
              user: AuthenticatedUser = Depends(current_user)):
    try:
        return WalletService(table()).movements(user.uid, min(max(limit, 1), 50), cursor)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Cursor inválido") from error


# Specs 07 y 09 — CU-07-02 y CU-09-03: consultar subastas ganadas.
@app.get("/me/wins", tags=["Perfil y billetera"])
def wins(limit: int = Query(default=20, ge=1, le=50), cursor: str | None = None,
         user: AuthenticatedUser = Depends(current_user)):
    try:
        return WalletRepository(table()).list_wins(user.uid, limit, cursor)
    except (ValueError, TypeError, KeyError) as error:
        raise HTTPException(status_code=400, detail="Cursor inválido") from error


# Spec 09 — CU-09-01/02: actividad del usuario autenticado.
@app.get("/me/auctions", tags=["Mi actividad"])
def my_auctions(limit: int = Query(default=20, ge=1, le=50), cursor: str | None = None,
                user: AuthenticatedUser = Depends(current_user)):
    try:
        return ActivityRepository(table()).auctions(user.uid, limit, cursor)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Cursor inválido") from error


@app.get("/me/bids", tags=["Mi actividad"])
def my_bids(limit: int = Query(default=20, ge=1, le=50), cursor: str | None = None,
            user: AuthenticatedUser = Depends(current_user)):
    try:
        return ActivityRepository(table()).bids(user.uid, limit, cursor)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Cursor inválido") from error


# Spec 05 — CU-05-01: consultar el catálogo de subastas activas.
@app.get("/auctions", tags=["Subastas"])
def list_auctions(limit: int = Query(default=20, ge=1, le=50), cursor: str | None = None,
                  user: AuthenticatedUser = Depends(current_user)):
    try:
        return AuctionService(table()).list_active(user.uid, limit, cursor)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Cursor inválido") from error


# Specs 05 y 07 — CU-05-02/03 y CU-07-02: detalle y resultado de la subasta.
@app.get("/auctions/{auction_id}", tags=["Subastas"])
def auction_detail(auction_id: str, user: AuthenticatedUser = Depends(current_user)):
    item = AuctionService(table()).detail(auction_id)
    if item is None:
        raise HTTPException(status_code=404, detail="No se encontró la subasta")
    return item


# Spec 04 — CU-04-01: publicar una subasta.
@app.post("/auctions", status_code=status.HTTP_201_CREATED, tags=["Subastas"])
def publish(payload: dict[str, Any], user: AuthenticatedUser = Depends(current_user)):
    try:
        result = AuctionService(table()).publish(user.uid, payload)
        if result is None:
            raise HTTPException(status_code=403, detail="El perfil no está disponible")
        return result
    except AuctionValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.exception_handler(BidError)
def bid_error_handler(request, error: BidError):
    return JSONResponse(status_code=error.status, content={"error": {"code": error.code, "message": error.message}})


# Spec 06 — CU-06-01/02/03: realizar una puja con reserva e idempotencia.
@app.post("/auctions/{auction_id}/bids", status_code=201, tags=["Pujas"])
def place_bid(auction_id: str, payload: dict[str, Any], user: AuthenticatedUser = Depends(current_user)):
    return BidService(table()).place(auction_id, user.uid, payload.get("amount"), payload.get("requestId"))


# Spec 06 — CU-06-04: consultar el historial de pujas de una subasta.
@app.get("/auctions/{auction_id}/bids", tags=["Pujas"])
def bid_history(auction_id: str, limit: int = Query(default=20, ge=1, le=50), cursor: str | None = None,
                user: AuthenticatedUser = Depends(current_user)):
    return BidService(table()).history(auction_id, user.uid, limit, cursor)


# Spec 04 — CU-04-02: cancelar una subasta propia antes de la primera puja.
@app.delete("/auctions/{auction_id}", tags=["Subastas"])
def cancel(auction_id: str, user: AuthenticatedUser = Depends(current_user)):
    try:
        result = AuctionService(table()).cancel(auction_id, user.uid)
        return result
    except KeyError as error:
        raise HTTPException(status_code=404, detail="No se encontró la subasta") from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail="La subasta no pertenece a este usuario") from error
    except AuctionValidationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


# Spec 02 — CU-02-01/02: registro e inicio de sesión.
# Se reutilizan los handlers de auth_service para el entorno local.
app.add_api_route("/auth/register", register, methods=["POST"],
                  status_code=201, tags=["Identidad"])
app.add_api_route("/auth/login", login, methods=["POST"], tags=["Identidad"])
