"""
JSON → nicely formatted CV (.docx).
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Dict, List

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, Cm


# ───────────────────────── helpers ───────────────────────── #

def _add_heading(doc: Document, text: str, level: int = 1) -> None:
    p = doc.add_heading(text, level=level)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT


def _add_bullets(doc: Document, items: List[str]) -> None:
    for line in items:
        doc.add_paragraph(line, style="List Bullet")


def _date(span: str) -> str:
    """Return MMM YYYY or the raw string if parsing fails."""
    try:
        dt = datetime.strptime(span, "%Y-%m")
        return dt.strftime("%b %Y")
    except ValueError:
        return span


# ───────────────────────── public API ────────────────────── #

def cv_json_to_docx(payload: Dict) -> bytes:
    """
    Build a one-page CV from the given JSON and return the .docx bytes.
    """
    doc = Document()
    sections = doc.sections
    sections[0].top_margin = Cm(1.5)
    sections[0].bottom_margin = Cm(1.5)
    sections[0].left_margin = Cm(2)
    sections[0].right_margin = Cm(2)

    # personal header ─────────────────────────────────────── #
    personal = payload.get("personal", {})
    full_name = f"{personal.get('first_name', '')} {personal.get('last_name', '')}".strip()
    title = personal.get("title", "")

    h = doc.add_heading(full_name, level=0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    h.runs[0].font.size = Pt(22)

    if title:
        p = doc.add_paragraph(title)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.runs[0].italic = True

    # contact line
    contact = payload.get("contact", {})
    contact_line = " • ".join(filter(None, [
        contact.get("email"),
        contact.get("phone"),
        contact.get("linkedin"),
        contact.get("github"),
        contact.get("address"),
    ]))
    if contact_line:
        p = doc.add_paragraph(contact_line)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # summary
    if personal.get("summary"):
        _add_heading(doc, "Profile", level=2)
        doc.add_paragraph(personal["summary"])

    # experience
    if exp := payload.get("experience"):
        _add_heading(doc, "Experience", level=2)
        for job in exp:
            role_line = f"{job.get('position', '')} — {job.get('company', '')}"
            para = doc.add_paragraph(role_line, style="Heading 3")
            dates = f"{_date(job.get('start', ''))} – {_date(job.get('end', 'Present'))}"
            para.add_run(f" ({dates})").italic = True
            _add_bullets(doc, job.get("responsibilities", []))

    # education
    if edu := payload.get("education"):
        _add_heading(doc, "Education", level=2)
        for ed in edu:
            degree_line = f"{ed.get('degree', '')}, {ed.get('institution', '')}"
            para = doc.add_paragraph(degree_line, style="Heading 3")
            dates = f"{_date(ed.get('start', ''))} – {_date(ed.get('end', ''))}"
            para.add_run(f" ({dates})").italic = True
            if ed.get("grade"):
                doc.add_paragraph(f"Grade: {ed['grade']}")

    # skills
    if skills := payload.get("skills"):
        _add_heading(doc, "Skills", level=2)
        doc.add_paragraph(", ".join(skills))

    # projects
    if projs := payload.get("projects"):
        _add_heading(doc, "Projects", level=2)
        for pr in projs:
            name = pr.get("name", "")
            tech = ", ".join(pr.get("tech", []))
            para = doc.add_paragraph(name, style="Heading 3")
            if tech:
                para.add_run(f" ({tech})").italic = True
            if pr.get("description"):
                doc.add_paragraph(pr["description"])

    # certifications / languages / interests  (optional one-liners)
    for header in ("certifications", "languages", "interests"):
        if items := payload.get(header):
            pretty = header.capitalize()
            _add_heading(doc, pretty, level=2)
            if isinstance(items, list):
                _add_bullets(doc, items)
            else:
                doc.add_paragraph(str(items))

    # output buffer
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
