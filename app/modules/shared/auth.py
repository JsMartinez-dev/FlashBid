import os
from dataclasses import dataclass
from typing import Any

import jwt
from jwt import InvalidTokenError


@dataclass(frozen=True)
class AuthenticatedUser:
    uid: str
    email: str


class AuthenticationError(Exception):
    pass


def jwt_settings() -> dict[str, str]:
    environment = os.environ.get("APP_ENV", "local")
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        if environment != "local":
            raise RuntimeError("JWT_SECRET must be configured outside local development")
        secret = "flashbid-local-development-secret"
    return {
        "secret": secret,
        "issuer": os.environ.get("JWT_ISSUER", "flashbid-local-auth"),
        "audience": os.environ.get("JWT_AUDIENCE", "flashbid-web"),
    }


def decode_bearer_token(authorization: str | None) -> AuthenticatedUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    settings = jwt_settings()
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            settings["secret"],
            algorithms=["HS256"],
            issuer=settings["issuer"],
            audience=settings["audience"],
            options={"require": ["sub", "email", "exp", "iat"]},
        )
    except InvalidTokenError as error:
        raise AuthenticationError("Invalid or expired session") from error

    uid = claims.get("sub")
    email = claims.get("email")
    if not isinstance(uid, str) or not isinstance(email, str):
        raise AuthenticationError("Invalid session claims")
    return AuthenticatedUser(uid=uid, email=email)
