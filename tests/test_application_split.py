"""Application split route retirement tests."""

import pytest
from fastapi.testclient import TestClient
from fastapi.routing import APIRoute

from api.application_split import (
    RPD_PIMS_API_ROUTES,
    RPD_PIMS_PAGE_ROUTES,
    STANDALONE_WHS_ROUTES,
)
from api.main import app


WHS_ROUTES = {
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

RPD_API_ROUTES = {
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


def _example_path(path: str) -> str:
    return path.replace(
        "{staging_id}",
        "00000000-0000-0000-0000-000000000000",
    ).replace(
        "{observation_id}",
        "00000000-0000-0000-0000-000000000000",
    )


@pytest.fixture(autouse=True)
def clear_split_env(monkeypatch):
    monkeypatch.delenv("GATEKEEPER_STANDALONE_WHS_RETIRED", raising=False)
    monkeypatch.delenv("GATEKEEPER_RPD_PIMS_RETIRED", raising=False)
    monkeypatch.delenv("AUDIT_CONCIERGE_URL", raising=False)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def test_route_contracts_are_explicit():
    assert STANDALONE_WHS_ROUTES == WHS_ROUTES
    assert RPD_PIMS_PAGE_ROUTES == {
        ("GET", "/pims-rpd"),
        ("GET", "/pims-login/rpd"),
    }
    assert RPD_PIMS_API_ROUTES == RPD_API_ROUTES


def test_all_pims_routes_are_classified_by_owner():
    contracts = {
        (
            method,
            route.path,
            route.endpoint.__name__,
        )
        for route in app.routes
        if isinstance(route, APIRoute)
        and getattr(route.endpoint, "__module__", "") == "pims.routes"
        for method in route.methods
    }
    sdg_names = {
        "sdgroup_observation",
        "promote_pdf_observation_sdgroup",
    }
    rpd_contracts = {
        (method, path) for method, path, name in contracts if name not in sdg_names
    }
    sdg_contracts = {
        (method, path) for method, path, name in contracts if name in sdg_names
    }

    assert len(contracts) == 26
    assert rpd_contracts == {
        route for route in RPD_API_ROUTES if route[1].startswith("/pims/")
    }
    assert sdg_contracts == {
        ("POST", "/pims/observation/sdgroup"),
        ("POST", "/pims/pdf-observation/sdgroup/{observation_id}/promote"),
    }


@pytest.mark.parametrize(("method", "path"), sorted(WHS_ROUTES))
def test_standalone_whs_retirement_returns_gone(client, monkeypatch, method, path):
    monkeypatch.setenv("GATEKEEPER_STANDALONE_WHS_RETIRED", "true")

    response = client.request(method, path)

    assert response.status_code == 410
    assert response.json()["error"] == "standalone_whs_retired"
    cli = response.json()["cli"]
    assert cli.startswith("Run 'whs-toolkit --help'")
    for command in (
        "whs-toolkit swms-generate",
        "whs-toolkit risk-assessment",
        "whs-toolkit control-pack",
        "whs-toolkit swms-review",
    ):
        assert command in cli
    assert response.headers["cache-control"] == "no-store"


def test_whs_trailing_slash_returns_direct_gone(client, monkeypatch):
    monkeypatch.setenv("GATEKEEPER_STANDALONE_WHS_RETIRED", "true")

    response = client.post(
        "/render/docx/",
        json={},
        follow_redirects=False,
    )

    assert response.status_code == 410


def test_wrong_method_remains_unchanged(client, monkeypatch):
    baseline = client.get("/render/docx", follow_redirects=False)
    monkeypatch.setenv("GATEKEEPER_STANDALONE_WHS_RETIRED", "true")
    with_retirement = client.get("/render/docx", follow_redirects=False)

    assert with_retirement.status_code == baseline.status_code == 405
    assert with_retirement.content == baseline.content


def test_standalone_flag_unset_restores_same_handler(client, monkeypatch):
    baseline = client.post("/render/docx", json={})

    monkeypatch.setenv("GATEKEEPER_STANDALONE_WHS_RETIRED", "true")
    assert client.post("/render/docx", json={}).status_code == 410

    monkeypatch.delenv("GATEKEEPER_STANDALONE_WHS_RETIRED")
    restored = client.post("/render/docx", json={})
    assert restored.status_code == baseline.status_code == 401
    assert restored.json() == baseline.json()


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/v1/procore/webhook"),
        ("POST", "/v1/swms/intake"),
        ("POST", "/v1/project/requirements"),
        ("POST", "/v1/swms/capture-edits"),
        ("POST", "/procore/webhook"),
        ("GET", "/health"),
    ],
)
def test_shared_routes_are_unchanged(client, monkeypatch, method, path):
    baseline = client.request(method, path)

    monkeypatch.setenv("GATEKEEPER_STANDALONE_WHS_RETIRED", "true")
    with_retirement = client.request(method, path)

    assert with_retirement.status_code == baseline.status_code
    assert with_retirement.content == baseline.content
    assert with_retirement.status_code != 410


@pytest.mark.parametrize("path", ["/pims-rpd", "/pims-login/rpd"])
def test_rpd_pages_use_fixed_redirect(client, monkeypatch, path):
    target = "https://audit-concierge.example.test/rpd"
    monkeypatch.setenv("GATEKEEPER_RPD_PIMS_RETIRED", "true")
    monkeypatch.setenv("AUDIT_CONCIERGE_URL", target)

    response = client.get(
        f"{path}?next=https://attacker.example",
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"] == target
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("path", ["/pims-rpd/", "/pims-login/rpd/"])
def test_rpd_page_trailing_slash_uses_fixed_redirect(client, monkeypatch, path):
    target = "https://audit-concierge.example.test/rpd"
    monkeypatch.setenv("GATEKEEPER_RPD_PIMS_RETIRED", "true")
    monkeypatch.setenv("AUDIT_CONCIERGE_URL", target)

    response = client.get(
        f"{path}?next=https://attacker.example",
        headers={"host": "attacker.example"},
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"] == target
    assert response.headers["cache-control"] == "no-store"


def test_rpd_api_trailing_slash_returns_direct_gone(client, monkeypatch):
    monkeypatch.setenv("GATEKEEPER_RPD_PIMS_RETIRED", "true")
    response = client.post("/pims/observation/rpd/", json={}, follow_redirects=False)
    assert response.status_code == 410


@pytest.mark.parametrize(
    "unsafe_url",
    [
        "",
        "http://audit-concierge.example.test",
        "//attacker.example",
        "https://user@audit-concierge.example.test",
        "https://audit-concierge.example.test/#fragment",
        "https://audit-concierge.example.test\\@attacker.example",
    ],
)
def test_rpd_redirect_rejects_unsafe_config(client, monkeypatch, unsafe_url):
    monkeypatch.setenv("GATEKEEPER_RPD_PIMS_RETIRED", "true")
    monkeypatch.setenv("AUDIT_CONCIERGE_URL", unsafe_url)

    response = client.get("/pims-rpd", follow_redirects=False)

    assert response.status_code == 503
    assert "location" not in response.headers


def test_generic_rpd_route_retires_before_handler(client, monkeypatch):
    monkeypatch.setenv("GATEKEEPER_RPD_PIMS_RETIRED", "true")

    response = client.post(
        "/pims/upload/observations",
        follow_redirects=False,
    )

    assert response.status_code == 410


@pytest.mark.parametrize("trailing_slash", [False, True])
@pytest.mark.parametrize(("method", "path"), sorted(RPD_API_ROUTES))
def test_explicit_rpd_api_routes_return_gone(
    client, monkeypatch, trailing_slash, method, path
):
    target = "https://audit-concierge.example.test/rpd"
    monkeypatch.setenv("GATEKEEPER_RPD_PIMS_RETIRED", "true")
    monkeypatch.setenv("AUDIT_CONCIERGE_URL", target)
    request_path = _example_path(path)
    if trailing_slash:
        request_path += "/"

    response = client.request(method, request_path, follow_redirects=False)

    assert response.status_code == 410
    assert response.json()["replacement_url"] == target


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("POST", "/pims/observation/sdgroup", {}),
        (
            "POST",
            "/pims/pdf-observation/sdgroup/00000000-0000-0000-0000-000000000000/promote",
            None,
        ),
    ],)
def test_shared_pims_namespace_is_unchanged(
    client,
    monkeypatch,
    method,
    path,
    body,
):
    baseline = client.request(method, path, json=body)

    monkeypatch.setenv("GATEKEEPER_RPD_PIMS_RETIRED", "true")
    monkeypatch.setenv(
        "AUDIT_CONCIERGE_URL",
        "https://audit-concierge.example.test/rpd",
    )
    with_retirement = client.request(method, path, json=body)

    assert with_retirement.status_code == baseline.status_code
    assert with_retirement.content == baseline.content
    assert with_retirement.status_code != 410


def test_rpd_flag_unset_restores_page_and_api_handlers(client, monkeypatch):
    page_baseline = client.get("/pims-login/rpd")
    api_baseline = client.post("/pims/observation/rpd", json={})

    monkeypatch.setenv("GATEKEEPER_RPD_PIMS_RETIRED", "true")
    monkeypatch.setenv(
        "AUDIT_CONCIERGE_URL",
        "https://audit-concierge.example.test/rpd",
    )
    assert client.get("/pims-login/rpd", follow_redirects=False).status_code == 307
    assert client.post("/pims/observation/rpd", json={}).status_code == 410

    monkeypatch.delenv("GATEKEEPER_RPD_PIMS_RETIRED")
    page_restored = client.get("/pims-login/rpd")
    api_restored = client.post("/pims/observation/rpd", json={})
    assert page_restored.status_code == page_baseline.status_code == 200
    assert page_restored.content == page_baseline.content
    assert api_restored.status_code == api_baseline.status_code
    assert api_restored.json() == api_baseline.json()
