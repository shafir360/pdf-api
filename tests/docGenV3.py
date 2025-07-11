'''
cv_generator.py
────────────────
Single-file utility that turns a CV JSON payload (new schema) into a magazine-style
.docx with controlled randomness so successive runs look different, yet remain
professional.

Randomised elements (current implementation)
    • Font family (safe Office fonts)
    • Primary accent colour for headings
    • Divider style   (single / dual line, dotted, long dash…)
    • Bullet glyph    (•, –, ◦, ▹ …)
    • Heading case    (UPPER vs Title Case)
    • Name alignment  (left / centre)
    • Optional dividers before headings

Ideas for later:
    • Re-order entire sections (e.g. Education before Work)
    • One- vs two-column page layouts
    • Light header/footer shading or side-bar
    • Alternate date formats (“Jan 2025” vs “2025-01”)
    • Iconography (phone/mail/link icons in header)
    • Variable spacing & paragraph styles
'''

from __future__ import annotations

import io
import os
import random
from datetime import datetime
from typing import Dict, List

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, Cm, RGBColor
#from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import docx 


# ── style pools ──────────────────────────────────────────────────────────
FONTS     = ['Calibri', 'Cambria', 'Arial', 'Garamond', 'Georgia', 'Verdana']
BULLETS   = ['•', '–', '◦', '▹']
DIVIDERS  = [
    '─' * 40,
    '─' * 20 + ' § ' + '─' * 20,
    '·' * 40,
    '—' * 40,
]
COLOURS   = [
    RGBColor(0x00, 0x4C, 0x99),   # blue
    RGBColor(0x4E, 0x9A, 0x06),   # green
    RGBColor(0xAA, 0x00, 0x00),   # red
    RGBColor(0x2E, 0x34, 0x36),   # charcoal
]


def _rand_style() -> Dict:
    '''Pick a fresh random style bundle each run.'''
    return dict(
        font          = random.choice(FONTS),
        colour        = random.choice(COLOURS),
        bullet        = random.choice(BULLETS),
        divider       = random.choice(DIVIDERS),
        headings_upper= random.choice([True, False]),
        name_align    = random.choice(
            [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER]),
        show_dividers = random.choice([True, False]),
    )


# ── tiny helpers ─────────────────────────────────────────────────────────
def _get(d: Dict, *keys, default=''):
    for k in keys:
        if k in d:
            return d[k]
    return default


def _fmt_date(span: str | None) -> str:
    if not span:
        return 'Present'
    try:
        return datetime.strptime(span, '%Y-%m').strftime('%b %Y')
    except Exception:
        return span


# ── builder helpers ─────────────────────────────────────────────────────
def _add_divider(doc: Document, style: Dict):
    p = doc.add_paragraph(style['divider'])
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4)
    p.runs[0].font.color.rgb = style['colour']


def _add_heading(doc: Document, text: str, style: Dict):
    p = doc.add_paragraph()
    r = p.add_run(text.upper() if style['headings_upper'] else text.title())
    r.bold = True
    r.font.size = Pt(12)
    r.font.color.rgb = style['colour']

    fmt = p.paragraph_format
    fmt.space_before = Pt(8)
    fmt.space_after  = Pt(4)
    fmt.keep_with_next = True

    # Bottom border acts as divider
    p_border = docx.oxml.OxmlElement('w:pBdr')
    bottom   = docx.oxml.OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'),  '4')
    bottom.set(qn('w:color'), 'C0C0C0')  # light grey
    p_border.append(bottom)
    p._p.get_or_add_pPr().append(p_border)



def _add_bullets(doc: Document, items: List[str], style: Dict):
    for line in items:
        para = doc.add_paragraph()
        para.add_run(f"{style['bullet']} ")
        para.add_run(line)
        fmt = para.paragraph_format
        fmt.space_before = Pt(0)
        fmt.space_after  = Pt(1)


def _add_two_cols(doc: Document, items: List[str], style: Dict):
    half = (len(items) + 1) // 2
    tbl  = doc.add_table(rows=half, cols=2)
    for r in range(half):
        for c in range(2):
            try:
                cell_txt = items[r + c * half]
            except IndexError:
                cell_txt = ''
            tbl.cell(r, c).text = f'{style["bullet"]} {cell_txt}'
            tbl.cell(r, c).paragraphs[0].paragraph_format.left_indent = Cm(0.2)


# ── main API ─────────────────────────────────────────────────────────────
def cv_json_to_docx(payload: Dict) -> bytes:
    '''Turn *new-schema* JSON payload into .docx bytes (one-pager).'''
    sty = _rand_style()
    doc = Document()
    doc.styles['Normal'].font.name = sty['font']
    doc.styles['Normal'].font.size = Pt(10.5)

    sec = doc.sections[0]
    for m in ('top_margin', 'bottom_margin'):
        setattr(sec, m, Cm(1.2))
    for m in ('left_margin', 'right_margin'):
        setattr(sec, m, Cm(1.5))

    # ─── Header ────────────────────────────────────────────
    first = _get(payload, 'first_name', 'first name')
    last  = _get(payload, 'last_name',  'last name', 'surname')
    h = doc.add_heading(f'{first} {last}'.strip(), level=0)
    h.alignment = sty['name_align']
    h.runs[0].font.size = Pt(22)
    h.runs[0].font.color.rgb = sty['colour']

    contact = ' ◆ '.join(filter(None, [
        payload.get('email'),
        payload.get('phone_number', payload.get('phone')),
        payload.get('address'),
    ]))
    if contact:
        pc = doc.add_paragraph(contact)
        pc.alignment = sty['name_align']
        pc.runs[0].font.size = Pt(9)

    # ─── Work History ─────────────────────────────────────
    if (jobs := payload.get('work_history')):
        _add_heading(doc, 'Work History', sty)
        for job in jobs:
            head = f'{job.get("position","")} — {job.get("company","")}'
            p    = doc.add_paragraph(head)
            p.paragraph_format.space_after = Pt(0)
            dates = f'{_fmt_date(job.get("start"))} – {_fmt_date(job.get("end"))}'
            p.add_run(f'  {dates}').italic = True
            _add_bullets(doc, job.get('responsibilities', []), sty)

    # ─── Skills ───────────────────────────────────────────
    if (skills := payload.get('skills')):
        _add_heading(doc, 'Skills', sty)
        _add_two_cols(doc, skills, sty)

    # ─── Education ────────────────────────────────────────
    if (edu := payload.get('education')):
        _add_heading(doc, 'Education', sty)
        for ed in edu:
            head = f'{ed.get("degree","")}, {ed.get("institution","")}'
            p    = doc.add_paragraph(head)
            dates = f'{_fmt_date(ed.get("start"))} – {_fmt_date(ed.get("end"))}'
            p.add_run(f'  {dates}').italic = True
            if ed.get('grade'):
                doc.add_paragraph(f'Grade: {ed["grade"]}')

    # ─── Languages ────────────────────────────────────────
    if (langs := payload.get('language_qualification')):
        _add_heading(doc, 'Languages', sty)
        lang_str = [f'{l["language"]} ({l["proficiency"]})' for l in langs]
        _add_two_cols(doc, lang_str, sty)

    # ─── Certifications ───────────────────────────────────
    if (certs := payload.get('certification')):
        _add_heading(doc, 'Certifications', sty)
        for c in certs:
            line = f'{c["name"]} — {c["issuer"]} ({_fmt_date(c["date"])})'
            doc.add_paragraph(line)

    # ─── Export ───────────────────────────────────────────
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ── tiny manual test harness ─────────────────────────────────────────────
def _test():
    '''Generate a demo CV at ./output/test_cv.docx'''
    sample = {
        'first name': 'Ada',
        'last_name' : 'Lovelace',
        'address'   : '12 St James’s Sq, London',
        'phone_number': '+44 20 7946 0958',
        'email'     : 'ada@example.com',
        'work_history': [{
            'position': 'Analyst',
            'company' : 'Analytical Engine Lab',
            'location': 'London, UK',
            'start'   : '1840-01',
            'end'     : '1843-12',
            'responsibilities': [
                'Wrote the first algorithm intended for a machine',
                'Collaborated with Charles Babbage on design notes',
            ],
        }],
        'skills'  : ['Python', 'LaTeX', 'Numerical Analysis'],
        'education': [{
            'degree'     : 'BSc Mathematics',
            'field'      : 'Mathematics',
            'institution': 'University of London',
            'location'   : 'London, UK',
            'start'      : '1831-10',
            'end'        : '1835-07',
            'grade'      : 'First-class honours',
        }],
        'language_qualification': [
            {'language': 'English', 'proficiency': 'native'},
            {'language': 'French',  'proficiency': 'fluent'},
        ],
        'certification': [{
            'name'  : 'Royal Society Fellowship',
            'issuer': 'Royal Society',
            'date'  : '1848-05',
        }],
    }
    data = cv_json_to_docx(sample)
    os.makedirs('output', exist_ok=True)
    with open('output/test_cv.docx', 'wb') as f:
        f.write(data)
    print('Generated → output/test_cv.docx')


if __name__ == '__main__':
    _test()
