import base64
import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import boto3
import jwt
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

from modules.shared.auth import jwt_settings
from modules.users.repository import EmailAlreadyRegisteredError, ProfileRepository

app = FastAPI(title="FlashBid Local Identity", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=2, max_length=60)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


def _hash_password(password: str, salt: bytes | None = None) -> str:
    password_salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=password_salt, n=2**14, r=8, p=1)
    return f"scrypt${base64.b64encode(password_salt).decode()}${base64.b64encode(digest).decode()}"


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        _, salt_b64, digest_b64 = password_hash.split("$", 2)
        expected = base64.b64decode(digest_b64)
        calculated = hashlib.scrypt(
            password.encode(), salt=base64.b64decode(salt_b64), n=2**14, r=8, p=1
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(expected, calculated)


@lru_cache
def _repository() -> ProfileRepository:
    endpoint_url = os.environ.get("AWS_ENDPOINT_URL")
    dynamodb = boto3.resource("dynamodb", endpoint_url=endpoint_url)
    return ProfileRepository(dynamodb.Table(os.environ["TABLE_NAME"]))


def _session(uid: str, email: str) -> dict[str, str | int]:
    now = datetime.now(timezone.utc)
    settings = jwt_settings()
    expires_in = 3600
    token = jwt.encode(
        {
            "sub": uid,
            "email": email,
            "iss": settings["issuer"],
            "aud": settings["audience"],
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
        },
        settings["secret"],
        algorithm="HS256",
    )
    return {"accessToken": token, "tokenType": "Bearer", "expiresIn": expires_in}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> dict[str, object]:
    email = str(payload.email).lower()
    try:
        profile = _repository().create_profile(
            uid=str(uuid.uuid4()),
            email=email,
            display_name=payload.display_name.strip(),
            password_hash=_hash_password(payload.password),
        )
    except EmailAlreadyRegisteredError as error:
        raise HTTPException(status_code=409, detail="An account already exists for this email") from error
    return {"session": _session(profile["uid"], profile["email"]), "profile": profile}


@app.post("/auth/login")
def login(payload: LoginRequest) -> dict[str, object]:
    identity = _repository().get_identity(str(payload.email).lower())
    if identity is None or not _verify_password(payload.password, identity["passwordHash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"session": _session(identity["uid"], identity["email"])}
