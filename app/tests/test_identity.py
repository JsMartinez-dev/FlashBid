import os
import sys
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from moto import mock_aws

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.shared.auth import AuthenticationError, decode_bearer_token, jwt_settings
from modules.users.repository import EmailAlreadyRegisteredError, ProfileRepository


@mock_aws
def test_registering_same_email_does_not_duplicate_profile(tabla_dynamodb):
    repository = ProfileRepository(tabla_dynamodb)
    profile = repository.create_profile("user-1", "person@example.com", "Person", "hash")

    assert profile["uid"] == "user-1"
    assert repository.get_profile("user-1")["email"] == "person@example.com"
    assert repository.get_identity("person@example.com")["uid"] == "user-1"

    with pytest.raises(EmailAlreadyRegisteredError):
        repository.create_profile("user-2", "person@example.com", "Other", "hash")

    assert repository.get_profile("user-2") is None


def test_bearer_token_uses_subject_instead_of_client_user_id(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-with-at-least-thirty-two-bytes")
    settings = jwt_settings()
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "trusted-uid",
            "email": "person@example.com",
            "iss": settings["issuer"],
            "aud": settings["audience"],
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "userId": "untrusted-client-value",
        },
        settings["secret"],
        algorithm="HS256",
    )

    user = decode_bearer_token(f"Bearer {token}")

    assert user.uid == "trusted-uid"


def test_missing_bearer_token_is_rejected():
    with pytest.raises(AuthenticationError):
        decode_bearer_token(None)


def test_jwt_secret_is_required_outside_local_development(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(RuntimeError):
        jwt_settings()
