#!/usr/bin/env python3
"""
Smoke-test for the PDF-to-JSON API deployed on Railway.

Reads BASE_URL from a .env file (or the real environment)
and POSTs a PDF to /convert.

Usage
-----
python smoke_test.py /path/to/document.pdf
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# ─── Load environment variables from .env (if present) ───────────────────── #
load_dotenv()                                   # silently does nothing if .env missing
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
ENDPOINT = f"{BASE_URL}/convert"
TIMEOUT = 30  # seconds
# ──────────────────────────────────────────────────────────────────────────── #


def main(pdf_path: str) -> None:
    pdf_file = Path(pdf_path)
    if not pdf_file.is_file():
        sys.exit(f"❌  File not found: {pdf_file}")

    print(f"▶  Uploading {pdf_file} → {ENDPOINT}")

    try:
        with pdf_file.open("rb") as f:
            resp = requests.post(
                ENDPOINT,
                files={"file": (pdf_file.name, f, "application/pdf")},
                timeout=TIMEOUT,
            )
    except requests.RequestException as exc:
        sys.exit(f"❌  Request failed: {exc}")

    print(f"✓  HTTP {resp.status_code}")
    if resp.ok:
        print("JSON response:")
        print(resp.json())
    else:
        print("Error response:")
        print(resp.text)


if __name__ == "__main__":
    main("tests/temp/dummy_data/270601-01_Application_Details.pdf")
