"""Smoke tests for dependency-sensitive PDF extraction and JWT verification.

These guard the Procore certification risk from the cryptography/python-jose
and pypdf bumps without needing network calls or fixture files on disk.
"""

from __future__ import annotations

import asyncio
import base64
from unittest.mock import AsyncMock

import pytest
from fastapi.security import HTTPAuthorizationCredentials


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _make_pdf(content_stream: bytes) -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        (
            b"<< /Length " + str(len(content_stream)).encode("ascii") + b" >>\n"
            b"stream\n" + content_stream + b"\nendstream"
        ),
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n"

    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += f"{offset:010d} 00000 n \n".encode("ascii")
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n"
    ).encode("ascii")
    return bytes(out)


def _make_text_pdf(lines: list[str]) -> bytes:
    commands = ["BT", "/F1 10 Tf", "36 800 Td", "12 TL"]
    for line in lines:
        commands.append(f"({_escape_pdf_text(line)}) Tj")
        commands.append("T*")
    commands.append("ET")
    return _make_pdf("\n".join(commands).encode("latin-1"))


def _make_textless_pdf() -> bytes:
    return _make_pdf(b"0.9 g\n36 700 200 80 re f\n")


def _base64url_uint(value: int) -> str:
    raw = value.to_bytes(32, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


class TestPdfDependencySmoke:
    def test_document_extractor_reads_real_text_pdf_with_pypdf(self):
        pytest.importorskip("pypdf")
        from core.document_extractor import extract_text_from_pdf

        pdf = _make_text_pdf([
            "SWMS extraction smoke: hazard control step permit PPE hold point."
            for _ in range(8)
        ])

        extracted = extract_text_from_pdf(pdf)

        assert "SWMS extraction smoke" in extracted
        assert "hazard control step" in extracted

    def test_document_extractor_routes_textless_pdf_to_ocr_fallback(self, monkeypatch):
        pytest.importorskip("pypdf")
        import core.document_extractor as extractor

        calls = []

        def fake_ocr(pdf_bytes: bytes, max_pages: int = 2) -> str:
            calls.append((pdf_bytes[:5], max_pages))
            return "OCR fallback text from scanned SWMS"

        monkeypatch.setattr(extractor, "_ocr_pdf_via_vision", fake_ocr)

        extracted = extractor.extract_text_from_pdf(_make_textless_pdf())

        assert extracted == "OCR fallback text from scanned SWMS"
        assert calls == [(b"%PDF-", 2)]

    def test_procore_extract_reads_real_text_pdf_green_path(self, monkeypatch):
        pytest.importorskip("pypdf")
        import core.procore_extract as procore_extract

        async def fail_if_called(*args, **kwargs):
            raise AssertionError("green-path text PDF should not need vision audit")

        monkeypatch.setattr(procore_extract, "_run_vision_audit", fail_if_called)
        line = (
            "hazard control step activity permit ppe hold point safe method statement "
            "review sign-off licence "
        )
        pdf = _make_text_pdf([line for _ in range(35)])

        result = asyncio.run(procore_extract.extract_and_route(pdf, "smoke-pdf"))

        assert result.abort is False
        assert result.confidence_tier == "green"
        assert result.char_count >= 1200
        assert "hazard control step" in result.text.lower()


class TestJwtDependencySmoke:
    def test_get_current_user_decodes_real_es256_jwt(self, monkeypatch):
        pytest.importorskip("cryptography")
        pytest.importorskip("jose")
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from jose import jwt
        import core.auth as auth

        private_key = ec.generate_private_key(ec.SECP256R1())
        public_numbers = private_key.public_key().public_numbers()
        jwks = {
            "keys": [{
                "kty": "EC",
                "crv": "P-256",
                "kid": "smoke-key",
                "alg": "ES256",
                "use": "sig",
                "x": _base64url_uint(public_numbers.x),
                "y": _base64url_uint(public_numbers.y),
            }]
        }
        private_pem = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        token = jwt.encode(
            {
                "sub": "user-smoke",
                "aud": "authenticated",
                "email": "smoke@example.com",
                "user_metadata": {"full_name": "Smoke User"},
            },
            private_pem,
            algorithm="ES256",
            headers={"kid": "smoke-key"},
        )
        monkeypatch.setattr(auth, "get_jwks", AsyncMock(return_value=jwks))

        user = asyncio.run(getattr(auth, "get_current_user")(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        ))

        assert user == {
            "user_id": "user-smoke",
            "email": "smoke@example.com",
            "full_name": "Smoke User",
        }
