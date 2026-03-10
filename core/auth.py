#!/usr/bin/env python3
"""
core/auth.py — Supabase authentication via REST API.

Uses httpx to call Supabase Auth API directly (avoids heavy supabase-py SDK).
JWT verification done locally with python-jose using JWKS (ES256).
"""

import logging
import os

import httpx
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8000")

_AUTH_BASE = f"{SUPABASE_URL}/auth/v1" if SUPABASE_URL else ""
_HEADERS = {
    "apikey": SUPABASE_ANON_KEY,
    "Content-Type": "application/json",
}

security = HTTPBearer()


def _auth_headers(access_token: str = "") -> dict:
    """Build headers for Supabase Auth API calls."""
    h = dict(_HEADERS)
    if access_token:
        h["Authorization"] = f"Bearer {access_token}"
    return h


# ── Supabase Auth API calls ──────────────────────────────────────────────────

def signup(email: str, password: str, full_name: str = "") -> dict:
    """Register a new user via Supabase Auth."""
    payload = {
        "email": email,
        "password": password,
        "data": {"full_name": full_name} if full_name else {},
    }
    r = httpx.post(f"{_AUTH_BASE}/signup", json=payload, headers=_HEADERS, timeout=15)
    if r.status_code >= 400:
        detail = r.json().get("msg") or r.json().get("error_description") or r.text
        raise HTTPException(status_code=r.status_code, detail=detail)
    return r.json()


def login(email: str, password: str) -> dict:
    """Sign in with email + password. Returns session with tokens."""
    payload = {"email": email, "password": password}
    r = httpx.post(
        f"{_AUTH_BASE}/token?grant_type=password",
        json=payload,
        headers=_HEADERS,
        timeout=15,
    )
    if r.status_code >= 400:
        detail = r.json().get("msg") or r.json().get("error_description") or "Invalid email or password"
        raise HTTPException(status_code=401, detail=detail)
    return r.json()


def refresh_session(refresh_token: str) -> dict:
    """Refresh an expired access token."""
    payload = {"refresh_token": refresh_token}
    r = httpx.post(
        f"{_AUTH_BASE}/token?grant_type=refresh_token",
        json=payload,
        headers=_HEADERS,
        timeout=15,
    )
    if r.status_code >= 400:
        raise HTTPException(status_code=401, detail="Token refresh failed")
    return r.json()


def sign_out(access_token: str) -> None:
    """Sign out (invalidate token server-side)."""
    httpx.post(
        f"{_AUTH_BASE}/logout",
        headers=_auth_headers(access_token),
        timeout=10,
    )


def reset_password(email: str) -> None:
    """Send password reset email."""
    payload = {"email": email}
    r = httpx.post(
        f"{_AUTH_BASE}/recover",
        json=payload,
        headers=_HEADERS,
        timeout=15,
    )
    if r.status_code >= 400:
        detail = r.json().get("msg") or "Password reset failed"
        raise HTTPException(status_code=r.status_code, detail=detail)


# ── JWKS cache + JWT verification ─────────────────────────────────────────────

_jwks_cache = None


async def get_jwks() -> dict:
    """Fetch and cache JWKS from Supabase."""
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json",
                timeout=10,
            )
            _jwks_cache = resp.json()
            logger.info(f"JWKS fetched: {len(_jwks_cache.get('keys', []))} keys")
    return _jwks_cache


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Verify JWT using Supabase JWKS and return user dict. Raises 401 if invalid."""
    token = credentials.credentials
    try:
        jwks = await get_jwks()
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["ES256", "HS256"],
            audience="authenticated",
            options={"verify_aud": True},
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: no sub claim",
            )
        meta = payload.get("user_metadata") or {}
        return {
            "user_id": user_id,
            "email": payload.get("email"),
            "full_name": meta.get("full_name", ""),
        }
    except JWTError as e:
        logger.error(f"JWT decode failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
        )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> dict | None:
    """Return user dict if valid token present, None otherwise."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
