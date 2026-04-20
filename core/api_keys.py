#!/usr/bin/env python3
"""
core/api_keys.py — Service account API key authentication.

Provides:
  - validate_api_key()        — look up key in Supabase api_keys table
  - log_api_key_usage()       — fire-and-forget usage logging
  - get_api_key_user()        — FastAPI dependency for X-API-Key header
  - get_user_or_api_key()     — combined JWT + API key dependency for /v1/
"""

import asyncio
import logging
import os

import httpx
from fastapi import Depends, Header, HTTPException, status

from core.auth import get_optional_user

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


def _supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Content-Type": "application/json",
    }


async def validate_api_key(key: str) -> dict | None:
    """Look up key in Supabase api_keys table.

    Returns {"key_id", "name", "user_id", "active"} if valid and active.
    Returns None if not found or inactive.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.debug("Supabase not configured — API key validation skipped")
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/api_keys",
                headers={**_supabase_headers(), "Prefer": "return=representation"},
                params={"key": f"eq.{key}", "active": "eq.true", "select": "id,key,name,user_id,active"},
            )
            if resp.status_code != 200:
                logger.warning(f"API key lookup failed: {resp.status_code}")
                return None
            rows = resp.json()
            if not rows:
                return None
            row = rows[0]
            return {
                "key_id": row["id"],
                "name": row["name"],
                "user_id": row.get("user_id"),
                "active": row["active"],
            }
    except Exception as e:
        logger.error(f"API key validation error: {e}")
        return None


async def log_api_key_usage(
    key_id: str,
    endpoint: str,
    description_length: int,
    duration_ms: int,
    success: bool,
) -> None:
    """Insert a row into Supabase api_key_usage. Fire-and-forget — never blocks."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return

    async def _insert():
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{SUPABASE_URL}/rest/v1/api_key_usage",
                    headers=_supabase_headers(),
                    json={
                        "key_id": key_id,
                        "endpoint": endpoint,
                        "description_length": description_length,
                        "duration_ms": duration_ms,
                        "success": success,
                    },
                )
        except Exception as e:
            logger.warning(f"API key usage log failed (non-blocking): {e}")

    asyncio.create_task(_insert())


async def get_api_key_user(
    x_api_key: str | None = Header(default=None),
) -> dict | None:
    """FastAPI dependency: validate X-API-Key header.

    Returns api_key dict if header present and valid.
    Returns None if header absent.
    Raises HTTP 401 if header present but key invalid or inactive.
    """
    if x_api_key is None:
        return None

    result = await validate_api_key(x_api_key)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )
    return result


async def get_user_or_api_key(
    user: dict | None = Depends(get_optional_user),
    api_key: dict | None = Depends(get_api_key_user),
) -> dict:
    """Combined auth dependency for /v1/ endpoints.

    Returns user dict if Supabase JWT present and valid.
    Returns api_key dict if X-API-Key present and valid.
    Raises HTTP 401 if neither present.
    """
    if user is not None:
        return user
    if api_key is not None:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required — provide Authorization Bearer token or X-API-Key header",
    )
