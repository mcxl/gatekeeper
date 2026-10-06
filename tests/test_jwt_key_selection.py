import asyncio
import base64
import hashlib
import hmac
import json
from unittest.mock import AsyncMock

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import jwt

import core.auth as auth


def ec_material():
    key = ec.generate_private_key(ec.SECP256R1())
    numbers = key.public_key().public_numbers()
    def encode(number):
        return base64.urlsafe_b64encode(number.to_bytes(32, "big")).rstrip(b"=").decode()
    return key, {"kty": "EC", "crv": "P-256", "kid": "trusted", "alg": "ES256",
                 "use": "sig", "x": encode(numbers.x), "y": encode(numbers.y)}


def test_unknown_kid_rejected_even_with_matching_signature(monkeypatch):
    from cryptography.hazmat.primitives import serialization
    key, jwk = ec_material()
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption())
    token = jwt.encode({"sub": "test-user", "aud": "authenticated"}, pem,
                       algorithm="ES256", headers={"kid": "unknown"})
    monkeypatch.setattr(auth, "get_jwks", AsyncMock(return_value={"keys": [jwk]}))
    with pytest.raises(HTTPException) as error:
        asyncio.run(auth.get_current_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)))
    assert error.value.status_code == 401

def verify(monkeypatch, token, keys):
    monkeypatch.setattr(auth, "get_jwks", AsyncMock(return_value={"keys": keys}))
    return asyncio.run(auth.get_current_user(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)))


def sign_ec(key, payload=None, kid="trusted"):
    return jwt.encode(payload or {"sub": "test-user", "aud": "authenticated"},
                      key, algorithm="ES256", headers={} if kid is None else {"kid": kid})


def test_ec_without_kid_accepts_single_trusted_key(monkeypatch):
    key, jwk = ec_material()
    assert verify(monkeypatch, sign_ec(key, kid=None), [jwk])["user_id"] == "test-user"


def test_symmetric_jwk_preserves_hs256_support(monkeypatch):
    secret = b"test-only-shared-secret-32-bytes!!"
    jwk = {"kty": "oct", "kid": "symmetric", "alg": "HS256",
           "k": base64.urlsafe_b64encode(secret).rstrip(b"=").decode()}
    token = jwt.encode({"sub": "hs-user", "aud": "authenticated"}, secret,
                       algorithm="HS256", headers={"kid": "symmetric"})
    assert verify(monkeypatch, token, [jwk])["user_id"] == "hs-user"


def test_ec_public_bytes_cannot_be_used_as_hmac_secret(monkeypatch):
    from cryptography.hazmat.primitives import serialization
    key, jwk = ec_material()
    public_bytes = key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    # Construct attacker input directly: PyJWT correctly refuses HMAC signing with DER.
    def encoded(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=")
    message = encoded({"alg": "HS256", "kid": "trusted"}) + b"." + encoded(
        {"sub": "attacker", "aud": "authenticated"})
    signature = base64.urlsafe_b64encode(
        hmac.new(public_bytes, message, hashlib.sha256).digest()).rstrip(b"=")
    token = (message + b"." + signature).decode()
    with pytest.raises(HTTPException) as error:
        verify(monkeypatch, token, [jwk])
    assert error.value.status_code == 401


@pytest.mark.parametrize("change", [
    {"alg": "HS256"}, {"crv": "P-384"}, {"use": "enc"}, {"key_ops": ["sign"]},
    {"x": "invalid"}, {"kty": "RSA"}, {"key_ops": None}, {"key_ops": "verify"},
    {"key_ops": ["verify", 7]}, {"key_ops": ["verify", "verify"]},
])
def test_invalid_trusted_key_rejected(monkeypatch, change):
    key, jwk = ec_material()
    jwk.update(change)
    with pytest.raises(HTTPException) as error:
        verify(monkeypatch, sign_ec(key), [jwk])
    assert error.value.status_code == 401


def test_duplicate_kid_rejected(monkeypatch):
    key, jwk = ec_material()
    with pytest.raises(HTTPException) as error:
        verify(monkeypatch, sign_ec(key), [jwk, dict(jwk)])
    assert error.value.status_code == 401


def test_bad_signature_rejected(monkeypatch):
    key, jwk = ec_material()
    other, _ = ec_material()
    with pytest.raises(HTTPException) as error:
        verify(monkeypatch, sign_ec(other), [jwk])
    assert error.value.status_code == 401


@pytest.mark.parametrize("payload", [
    {"sub": "test-user", "aud": "other"},
    {"sub": "test-user", "aud": "authenticated", "exp": 1},
    {"aud": "authenticated"},
    {"sub": "test-user"},
])
def test_invalid_claims_rejected(monkeypatch, payload):
    key, jwk = ec_material()
    with pytest.raises(HTTPException) as error:
        verify(monkeypatch, sign_ec(key, payload), [jwk])
    assert error.value.status_code == 401


def test_optional_invalid_user_returns_none(monkeypatch):
    key, jwk = ec_material()
    monkeypatch.setattr(auth, "get_jwks", AsyncMock(return_value={"keys": [jwk]}))
    token = sign_ec(key, kid="unknown")
    assert asyncio.run(auth.get_optional_user(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))) is None



def test_missing_kid_with_multiple_keys_rejected(monkeypatch):
    key, jwk = ec_material()
    _, other = ec_material()
    other["kid"] = "other"
    with pytest.raises(HTTPException) as error:
        verify(monkeypatch, sign_ec(key, kid=None), [jwk, other])
    assert error.value.status_code == 401
