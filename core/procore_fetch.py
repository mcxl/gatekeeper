"""
core/procore_fetch.py — Fetch PDF from Procore document URL.

Stream to memory only. Never to disk.
Never log URL contents or document body.
"""

from __future__ import annotations

import logging
import os

import httpx

log = logging.getLogger(__name__)


class ProcoreFetchTimeout(Exception):
    pass


class ProcoreFetchError(Exception):
    def __init__(self, status_code: int, url: str):
        self.status_code = status_code
        self.url = url[:80]
        super().__init__(f"Procore fetch failed: HTTP {status_code} from {self.url}")


async def fetch_procore_pdf(
    document_url: str,
    correlation_id: str,
    access_token: str | None = None,
) -> bytes:
    """Fetch a PDF from Procore. Returns raw bytes in memory.

    Raises ProcoreFetchTimeout on 30s timeout.
    Raises ProcoreFetchError on non-200 response.
    """
    token = access_token or os.getenv("PROCORE_ACCESS_TOKEN", "")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    log.info("Procore fetch start: correlation_id=%s", correlation_id)

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(document_url, headers=headers)
    except httpx.TimeoutException:
        log.error("Procore fetch timeout: correlation_id=%s", correlation_id)
        raise ProcoreFetchTimeout(f"Fetch timed out after 30s: correlation_id={correlation_id}")

    if response.status_code != 200:
        log.error(
            "Procore fetch error: correlation_id=%s status=%d",
            correlation_id, response.status_code,
        )
        raise ProcoreFetchError(response.status_code, document_url)

    pdf_bytes = response.content
    log.info(
        "Procore fetch complete: correlation_id=%s size_bytes=%d",
        correlation_id, len(pdf_bytes),
    )
    return pdf_bytes
