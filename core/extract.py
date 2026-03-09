#!/usr/bin/env python3
"""
core/extract.py — Claude-powered field extraction from text and images.

Follows the core/generate.py pattern: uses Anthropic SDK, returns structured data.

Functions:
  extract_from_text(text) -> dict
  extract_from_image(image_bytes, media_type) -> dict
"""

import json
import os

from dotenv import load_dotenv
load_dotenv()

import anthropic

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024

EXTRACTION_PROMPT = """Extract SWMS (Safe Work Method Statement) fields from the provided content.
Return a JSON object with these fields (use empty string if not found):

{
  "description": "brief work description suitable as a SWMS task name",
  "site_name": "project or site name/address",
  "principal_contractor": "principal contractor name",
  "trade_type": "one of: Remedial, Painting, Waterproofing, Cladding, Structural, Civil, Mechanical, Electrical, Work at Height, Demolition, Groundworks, Scaffolding",
  "plant_equipment": "any plant or equipment mentioned",
  "permits": "any permits or licences mentioned"
}

PLAIN ENGLISH WRITING RULES (WorkCover NSW Guidelines):
- Use simple words: start not commence, use not utilise, before not
  prior to, check not inspect, fix not rectify, need not require
- Use active voice and action verbs
- Keep descriptions concise and direct

Return ONLY the JSON object. No markdown, no commentary."""


def _get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set.")
    return anthropic.Anthropic(api_key=api_key)


def extract_from_text(text: str) -> dict:
    """Extract structured SWMS fields from plain text via Claude."""
    client = _get_client()
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(raw)


def extract_from_image(image_bytes: bytes, media_type: str) -> dict:
    """Extract structured SWMS fields from an image via Claude vision."""
    import base64
    client = _get_client()
    b64 = base64.b64encode(image_bytes).decode()
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=EXTRACTION_PROMPT,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": b64,
                    },
                },
                {"type": "text", "text": "Extract SWMS fields from this document image."},
            ],
        }],
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(raw)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file using pypdf."""
    import io
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file using python-docx."""
    import io
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
