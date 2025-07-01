"""
PDF → dict adapter used by the FastAPI layer.
Only `pdf_bytes_to_dict()` is imported elsewhere.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

import fitz  # PyMuPDF

# ────── helpers (identical to your refactor, just renamed with “_”) ────── #
_LINE_BREAKS = re.compile(r"\r\n?")
_SPACE_BEFORE_NL = re.compile(r"[ \t]+\n")


def _clean_text(raw: str) -> str:
    raw = _LINE_BREAKS.sub("\n", raw)
    raw = _SPACE_BEFORE_NL.sub("\n", raw)
    return raw


def _find_value(text: str, label: str, default: str = "") -> str:
    pat_inline = rf"{re.escape(label)}[^\S\r\n]*\.?\s*:\s*(.+)"
    if m := re.search(pat_inline, text, flags=re.I):
        return m.group(1).strip()

    pat_next = rf"{re.escape(label)}[^\S\r\n]*\n(.+)"
    if m := re.search(pat_next, text, flags=re.I):
        return m.group(1).strip()

    return default


def _extract_employment(text: str) -> List[Dict[str, str]]:
    if "Employer" not in text:
        return []

    block = text.split("Employer", 1)[1]
    block = block.split("Employment List", 1)[0] if "Employment List" in block else block
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]

    try:
        header_end = lines.index("Contact Name")
        data_lines = lines[header_end + 1 :]
    except ValueError:
        data_lines = lines

    if data_lines and re.fullmatch(r"No Records Found", data_lines[0], flags=re.I):
        return []

    jobs: List[Dict[str, str]] = []
    for i in range(0, len(data_lines), 5):
        chunk = data_lines[i : i + 5]
        if len(chunk) == 5:
            jobs.append(
                {
                    "employer": chunk[0],
                    "job_description": chunk[1],
                    "start_date": chunk[2],
                    "end_date": chunk[3],
                    "contact_name": chunk[4],
                }
            )
    return jobs


def _extract_info(text: str) -> Dict[str, Any]:
    """Return the full data payload expected by the front-end."""
    return {
        "application_ref":  _find_value(text, "Application Ref"),
        "title":            _find_value(text, "Title"),
        "first_name":       _find_value(text, "First Name"),
        "middle_name":      _find_value(text, "Middle Name"),
        "last_name":        _find_value(text, "Last Name"),
        "dob":              _find_value(text, "Date of Birth"),
        "email":            _find_value(text, "Email Address"),
        "mobile":           _find_value(text, "Mobile"),
        "nationality":      _find_value(text, "Nationality"),
        "program":          _find_value(text, "Program"),
        "intake":           _find_value(text, "Intake"),
        "campus":           _find_value(text, "Campus"),
        "term_postcode":    _find_value(text, "Term time Postcode"),
        "permanent_address": {
            "address_line_1": _find_value(text, "Address Line 1"),
            "city":           _find_value(text, "City"),
            "postcode":       _find_value(text, "Postcode"),
            "country":        _find_value(text, "Country"),
        },
        "fee_payer":        _find_value(text, "Who will pay your fees?"),
        "previous_loan":    _find_value(text, "Have you previously received a student loan?"),
        "reference_name":   _find_value(text, "Reference 1 Name"),
        "reference_email":  _find_value(text, "Reference 1 Email/Mobile"),
        "employment":       _extract_employment(text),
    }


# ───────────────────────── Public helpers ────────────────────────── #
def pdf_bytes_to_dict(pdf_bytes: bytes) -> Dict[str, Any]:
    """Open an in-memory PDF and return the extracted information."""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        raw = "\n".join(p.get_text() for p in doc)
    return _extract_info(_clean_text(raw))
