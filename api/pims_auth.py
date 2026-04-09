#!/usr/bin/env python3
"""Shared PIMS dashboard cookie auth helpers."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time

COOKIE_NAME = "pims_sess"
COOKIE_MAX_AGE = 14400  # 4 hours - reduces stolen-token validity window
_CLOCK_SKEW = 30  # seconds tolerance for clock drift

_SECRET = os.getenv("PIMS_SESSION_SECRET", "")
_PASSWORD = os.getenv("PIMS_DASHBOARD_PASSWORD", "")
_ENVIRONMENT = os.getenv("ENVIRONMENT", "").lower()
_IS_PROD = _ENVIRONMENT not in ("development", "local")
# Fail closed: unknown/missing ENVIRONMENT -> secure=True.
# Only explicit "development" or "local" disables secure cookie.


def check_env() -> str | None:
    """Return error string if required env vars are missing/invalid."""
    if not _SECRET:
        return "PIMS_SESSION_SECRET is not set."
    if not _PASSWORD:
        return "PIMS_DASHBOARD_PASSWORD is not set."
    if _ENVIRONMENT not in ("production", "development", "local"):
        return (
            "ENVIRONMENT must be 'production', 'development', or 'local'; "
            f"got '{_ENVIRONMENT}'. Set this env var explicitly."
        )
    return None


def make_session_cookie() -> str:
    """Generate signed session token: '{rand}.{exp}.{mac}'."""
    rand = secrets.token_urlsafe(32)
    exp = str(int(time.time()) + COOKIE_MAX_AGE)
    msg = f"{rand}.{exp}".encode()
    mac = hmac.new(_SECRET.encode(), msg, hashlib.sha256).hexdigest()
    return f"{rand}.{exp}.{mac}"


def verify_session_cookie(value: str | None) -> bool:
    """Return True if cookie has valid HMAC and has not expired."""
    if not value or not _SECRET:
        return False

    parts = value.split(".")
    if len(parts) != 3:
        return False
    rand, exp_str, mac = parts

    try:
        exp = int(exp_str)
        if exp <= 0:
            return False
    except (ValueError, TypeError):
        return False

    msg = f"{rand}.{exp_str}".encode()
    expected = hmac.new(_SECRET.encode(), msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, mac):
        return False

    return int(time.time()) < (exp + _CLOCK_SKEW)


def check_password(submitted: str) -> bool:
    """Timing-safe password comparison."""
    if not _PASSWORD or not submitted:
        return False
    a = hashlib.sha256(submitted.encode()).hexdigest()
    b = hashlib.sha256(_PASSWORD.encode()).hexdigest()
    return hmac.compare_digest(a, b)


def set_session_cookie(response, value: str) -> None:
    """Attach PIMS session cookie to response."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=value,
        httponly=True,
        samesite="strict",
        secure=_IS_PROD,
        max_age=COOKIE_MAX_AGE,
        path="/",
    )


def clear_session_cookie(response) -> None:
    """Clear PIMS session cookie from browser."""
    response.delete_cookie(key=COOKIE_NAME, path="/")
    # NOTE: stateless design - this clears the browser cookie only.
    # To hard-revoke all sessions (e.g. after suspected compromise),
    # rotate PIMS_SESSION_SECRET in Railway env vars and redeploy.
    # All existing tokens will immediately fail HMAC verification.
