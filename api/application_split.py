"""Opt-in route retirement controls for the Gatekeeper application split."""

from __future__ import annotations

import os
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.routing import compile_path


STANDALONE_WHS_ROUTES = frozenset(
    {
        ("GET", "/app"),
        ("GET", "/dashboard"),
        ("GET", "/ra"),
        ("GET", "/control-pack"),
        ("GET", "/swms"),
        ("GET", "/review"),
        ("GET", "/demo"),
        ("GET", "/tasks"),
        ("POST", "/generate"),
        ("GET", "/infer"),
        ("GET", "/generate/route"),
        ("POST", "/generate/auto"),
        ("POST", "/generate/full"),
        ("POST", "/generate/stream"),
        ("POST", "/generate/ra"),
        ("POST", "/render/docx"),
        ("POST", "/render/pdf"),
        ("POST", "/render/both"),
        ("POST", "/render/ra"),
        ("POST", "/render/ra/pdf"),
        ("POST", "/render/ra/both"),
        ("POST", "/control-pack/generate"),
        ("POST", "/upload/analyse-swms"),
        ("POST", "/upload/extract-scope"),
        ("POST", "/upload/extract"),
        ("POST", "/upload/swms-gap"),
        ("POST", "/intake/extract"),
        ("GET", "/check-jurisdiction"),
        ("POST", "/v1/generate/stream"),
        ("POST", "/v1/render/docx"),
        ("POST", "/v1/render/pdf"),
    }
)

RPD_PIMS_PAGE_ROUTES = frozenset(
    {
        ("GET", "/pims-rpd"),
        ("GET", "/pims-login/rpd"),
    }
)

# pims/routes.py owns two SD Group routes. Every other route in that module is
# RPD-owned at this revision, including paths that do not contain an RPD slug.
RPD_PIMS_API_ROUTES = frozenset(
    {
        ("POST", "/pims-login/rpd"),
        ("POST", "/pims/observation/rpd"),
        ("POST", "/pims/staging/{staging_id}/delete"),
        ("POST", "/pims/observation/{observation_id}/delete"),
        ("POST", "/pims/staging/{staging_id}/approve"),
        ("POST", "/pims/staging/{staging_id}/retry-enrichment"),
        ("POST", "/pims/pdf-observation/{observation_id}/promote"),
        ("POST", "/pims/observation/{observation_id}/send-to-staging"),
        ("POST", "/pims/staging/rpd/docx"),
        ("POST", "/pims/staging/rpd/xlsx"),
        ("POST", "/pims/upload/observations"),
        ("POST", "/pims/staging/rpd/reenrich"),
        ("POST", "/pims/observations/rpd/reenrich-ncr"),
        ("POST", "/pims/observations/rpd/reenrich-live"),
        ("GET", "/pims/observations/rpd"),
        ("GET", "/pims/report/rpd"),
        ("GET", "/pims/sites/active"),
        ("GET", "/pims/sites/eligible"),
        ("GET", "/pims/health/data-quality"),
        ("POST", "/pims/audit-report/rpd"),
        ("POST", "/pims/site-visit-report/xlsx"),
        ("POST", "/pims/site-visit-report"),
        ("POST", "/pims/observation/{observation_id}/approve"),
        ("POST", "/pims/observation/{observation_id}/reject"),
        ("POST", "/pims/site/observations/approve-pending"),
    }
)

def _enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() == "true"


_RPD_PIMS_API_MATCHERS = tuple(
    (method, compile_path(path)[0]) for method, path in RPD_PIMS_API_ROUTES
)


def _matches_rpd_api_route(route: tuple[str, str]) -> bool:
    method, path = route
    return any(
        candidate_method == method and pattern.fullmatch(path)
        for candidate_method, pattern in _RPD_PIMS_API_MATCHERS
    )


def validate_audit_concierge_url(value: str | None) -> str:
    """Return a safe fixed HTTPS redirect URL or raise ValueError."""
    if not value or value != value.strip():
        raise ValueError("AUDIT_CONCIERGE_URL must be a fixed HTTPS URL.")
    if any(ord(char) <= 0x20 or ord(char) == 0x7F for char in value):
        raise ValueError("AUDIT_CONCIERGE_URL contains invalid characters.")
    if "\\" in value:
        raise ValueError("AUDIT_CONCIERGE_URL contains an invalid separator.")

    parsed = urlsplit(value)
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("AUDIT_CONCIERGE_URL has an invalid port.") from exc

    if (
        parsed.scheme.lower() != "https"
        or not parsed.netloc
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError("AUDIT_CONCIERGE_URL must be a fixed HTTPS URL.")
    return value


def _gone(content: dict[str, str]) -> JSONResponse:
    return JSONResponse(
        status_code=410,
        content=content,
        headers={"Cache-Control": "no-store"},
    )


class ApplicationSplitMiddleware(BaseHTTPMiddleware):
    """Retire migrated application routes without removing their handlers."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        path = request.url.path
        if path != "/" and path.endswith("/"):
            path = path[:-1]
        route = (request.method.upper(), path)
        if _enabled("GATEKEEPER_STANDALONE_WHS_RETIRED") and route in STANDALONE_WHS_ROUTES:
            return _gone(
                {
                    "error": "standalone_whs_retired",
                    "detail": "This standalone WHS route has moved to the whs-toolkit CLI.",
                    "cli": (
                        "Run 'whs-toolkit --help'. Migrated commands: "
                        "'whs-toolkit swms-generate', "
                        "'whs-toolkit risk-assessment', 'whs-toolkit control-pack', "
                        "and 'whs-toolkit swms-review'."
                    ),
                }
            )
        if _enabled("GATEKEEPER_RPD_PIMS_RETIRED"):
            if route in RPD_PIMS_PAGE_ROUTES:
                try:
                    target = validate_audit_concierge_url(os.getenv("AUDIT_CONCIERGE_URL"))
                except ValueError:
                    return JSONResponse(
                        status_code=503,
                        content={
                            "error": "rpd_pims_retirement_misconfigured",
                            "detail": "A valid HTTPS AUDIT_CONCIERGE_URL is required.",
                        },
                        headers={"Cache-Control": "no-store"},
                    )
                return RedirectResponse(
                    url=target,
                    status_code=307,
                    headers={"Cache-Control": "no-store"},
                )
            if _matches_rpd_api_route(route):
                content = {
                    "error": "rpd_pims_retired",
                    "detail": "This legacy RPD PIMS route has moved to Audit Concierge.",
                }
                try:
                    content["replacement_url"] = validate_audit_concierge_url(
                        os.getenv("AUDIT_CONCIERGE_URL")
                    )
                except ValueError:
                    content["next_step"] = "Contact the administrator for the Audit Concierge URL."
                return _gone(content)

        return await call_next(request)
