import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from auth_service.main import _hash_password, _verify_password, app


def test_password_hash_is_verified_only_by_matching_password():
    password_hash = _hash_password("correct-password")

    assert _verify_password("correct-password", password_hash)
    assert not _verify_password("wrong-password", password_hash)


def test_identity_health_endpoint_is_public():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
