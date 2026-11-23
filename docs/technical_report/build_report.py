#!/usr/bin/env python
r"""AmCraX technical report build pipeline.

Usage (from any directory):
    . "<root>\scripts\env.ps1"; python "<root>\docs\technical_report\build_report.py"

Options:
    --sections DIR   folder with NN_*.md files (default docs/technical_report/sections)
    --out-dir DIR    output folder (default docs/technical_report)
    --name NAME      output base name (default AmCraX_Technical_Report)
    --no-pdf         skip the Word COM export (TOC stays unpopulated)
    --no-fail-on-todo  report TODO/TBD/lorem but do not fail the build

Pipeline: collect sections -> drop missing figures -> generate references + appendices + front matter
-> pandoc (reference.docx) -> python-docx post-processing -> Word COM (update fields, export PDF)
-> quality report.  Exit code 0 = success, 1 = tool failure, 2 = forbidden placeholder strings found.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GEN = HERE / "generated"
REFERENCE_DOCX = HERE / "reference.docx"

REPORT_DATE = "23 November 2026"
SUBTITLE = "Ammonia Cracking Simulation and Optimisation Platform"
SCOPE_LINE = ("Aspen Plus V15 flowsheet model of ammonia cracking for hydrogen production, its Python automation, "
              "independent Python models, validation, sensitivity, energy, techno-economic and environmental assessment, "
              "and a test of four research hypotheses for a representative Singapore setting.")

# AmCraX light-theme colours (docs/reference_projects/design_tokens.md)
PRIMARY = "0369a1"
ACCENT = "c2410c"
INK = "121a2f"
MUTED = "5b6478"
FONT = "Calibri"

# The 35-item structure of WRITING_GUIDE.md: 33 written sections, then the generated references (34)
# and appendices (35). A title of None accepts the heading written in the file (sections 27-30 are
# written by another writer); the outline check then uses that heading.
EXPECTED = {
    1: ("01_executive_summary.md", "Executive summary"),
    2: ("02_motivation.md", "Motivation and background"),
    3: ("03_fundamentals.md", "Ammonia-cracking fundamentals"),
    4: ("04_literature_review.md", "Literature review"),
    5: ("05_process_design.md", "Process design and process flow diagram"),
    6: ("06_aspen_methodology.md", "Aspen Plus V15 methodology"),
    7: ("07_components.md", "Component selection"),
    8: ("08_property_method.md", "Thermodynamic property method"),
    9: ("09_reactor.md", "Reactor configuration"),
    10: ("10_heat_exchangers.md", "Heat exchanger modelling"),
    11: ("11_separation.md", "Separation and purification"),
    12: ("12_automation.md", "Python-Aspen automation"),
    13: ("13_equilibrium.md", "Equilibrium modelling"),
    14: ("14_kinetics.md", "Catalyst kinetics"),
    15: ("15_balances.md", "Mass and energy balances"),
    16: ("16_validation.md", "Model validation"),
    17: ("17_sensitivity.md", "Sensitivity analysis"),
    18: ("18_heat_integration.md", "Heat integration"),
    19: ("19_techno_economics.md", "Techno-economic assessment"),
    20: ("20_optimisation.md", "Optimisation"),
    21: ("21_environment.md", "Environmental analysis"),
    22: ("22_dashboard.md", "Interactive dashboard"),
    23: ("23_website.md", "Public website"),
    24: ("24_research_questions.md", "Research questions and hypotheses"),
    25: ("25_aspen_kinetic_reactor.md", "Kinetic reactor modelling in Aspen Plus"),
    26: ("26_catalyst_heat_integration.md", "Catalyst comparison and heat integration"),
    27: ("27_singapore_economics.md", None),
    28: ("28_purification.md", None),
    29: ("29_end_use.md", None),
    30: ("30_life_cycle.md", None),
    31: ("31_evidence_matrix.md", "Four-hypothesis evidence matrix"),
    32: ("32_limitations.md", "Limitations"),
    33: ("33_conclusions.md", "Conclusions and future research"),
}
REFERENCES_HEADING = "# 34 References"
APPENDICES_HEADING = "# 35 Appendices"
EVIDENCE_JSON = ROOT / "results" / "research" / "evidence_matrix.json"
EVIDENCE_MD = ROOT / "docs" / "research" / "evidence_matrix.md"
EVIDENCE_SHOTS = ROOT / "docs" / "images" / "aspen_evidence" / "manifest.json"
RESEARCH_VALIDATION = ROOT / "results" / "research" / "validation"
# In-text abbreviations of group authors (APA 7: "International Organization for Standardization [ISO], 2019",
# then "ISO, 2019").
AUTHOR_ALIASES = {"iso2019hydrogen": ["ISO"]}

LOG: list[str] = []


def log(msg: str = "") -> None:
    print(msg, flush=True)
    LOG.append(msg)


# ----------------------------------------------------------------------------------------------
# reference.docx
# ----------------------------------------------------------------------------------------------
def _rgb(h: str):
    from docx.shared import RGBColor
    return RGBColor.from_string(h.upper())


def _set_font(style, name=FONT, size=None, color=None, bold=None, italic=None):
    from docx.oxml.ns import qn
    f = style.font
    f.name = name
    if size is not None:
        from docx.shared import Pt
        f.size = Pt(size)
    if color:
        f.color.rgb = _rgb(color)
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        from docx.oxml import OxmlElement
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rfonts.get(qn(a)) is not None:
            del rfonts.attrib[qn(a)]
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(a), name)


def _para_border(style, side: str, color: str, sz: int = 8, space: int = 2):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    ppr = style.element.get_or_add_pPr()
    pb = ppr.find(qn("w:pBdr"))
    if pb is None:
        pb = OxmlElement("w:pBdr")
        ppr.append(pb)
    el = OxmlElement(f"w:{side}")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), str(sz))
    el.set(qn("w:space"), str(space))
    el.set(qn("w:color"), color)
    pb.append(el)


def build_reference_docx() -> None:
    from docx import Document
    from docx.enum.style import WD_STYLE_TYPE
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt

    tmp = GEN / "pandoc_default_reference.docx"
    GEN.mkdir(parents=True, exist_ok=True)
    with open(tmp, "wb") as fh:
        subprocess.run(["pandoc", "--print-default-data-file", "reference.docx"], stdout=fh, check=True)
    doc = Document(str(tmp))
    st = doc.styles

    def get(name, kind=WD_STYLE_TYPE.PARAGRAPH, base="Normal"):
        try:
            return st[name]
        except KeyError:
            s = st.add_style(name, kind)
            if kind == WD_STYLE_TYPE.PARAGRAPH and base:
                s.base_style = st[base]
            return s

    _set_font(st["Normal"], size=10.5, color=INK)
    st["Normal"].paragraph_format.space_after = Pt(6)
    for nm in ("Body Text", "First Paragraph"):
        s = get(nm)
        _set_font(s, size=10.5, color=INK)
        s.paragraph_format.space_before = Pt(0)
        s.paragraph_format.space_after = Pt(6)
        s.paragraph_format.line_spacing = 1.12
        s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    # Compact: tight lists and table cells (table runs are set to 9 pt in post-processing). Left-aligned,
    # because justified text in narrow cells and list items spreads the words apart.
    s = get("Compact")
    _set_font(s, size=10.5, color=INK)
    s.paragraph_format.space_before = Pt(1)
    s.paragraph_format.space_after = Pt(2)
    s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    s = get("Title")
    _set_font(s, size=30, color=INK, bold=True)
    s = get("Subtitle")
    _set_font(s, size=14, color=MUTED, bold=False, italic=False)

    heads = {"Heading 1": (18, INK), "Heading 2": (13.5, PRIMARY), "Heading 3": (11.5, INK), "Heading 4": (10.5, PRIMARY)}
    for nm, (sz, col) in heads.items():
        s = get(nm)
        _set_font(s, size=sz, color=col, bold=True, italic=False)
        s.paragraph_format.keep_with_next = True
        s.paragraph_format.space_before = Pt(14 if nm != "Heading 1" else 0)
        s.paragraph_format.space_after = Pt(6 if nm != "Heading 1" else 12)
    h1 = st["Heading 1"]
    h1.paragraph_format.page_break_before = True
    _para_border(h1, "bottom", PRIMARY, 12, 4)

    for nm in ("Caption", "Table Caption", "Image Caption"):
        s = get(nm)
        _set_font(s, size=9, color=INK, bold=False, italic=False)
        s.paragraph_format.space_before = Pt(4)
        s.paragraph_format.space_after = Pt(10)
        s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        s.paragraph_format.keep_together = True
    st["Table Caption"].paragraph_format.keep_with_next = True
    st["Table Caption"].paragraph_format.space_before = Pt(8)
    st["Table Caption"].paragraph_format.space_after = Pt(4)

    s = get("Source Code")
    _set_font(s, name="Consolas", size=7, color=INK)
    s.paragraph_format.space_after = Pt(0)
    s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    s = get("Verbatim Char", WD_STYLE_TYPE.CHARACTER)
    _set_font(s, name="Consolas", size=9, color=INK)
    s = get("Hyperlink", WD_STYLE_TYPE.CHARACTER)
    s.font.color.rgb = _rgb(PRIMARY)
    s.font.underline = False
    s = get("Table")
    try:
        _set_font(s, size=9)
    except Exception:
        pass
    get("Bibliography")
    _set_font(st["Bibliography"], size=10, color=INK)
    st["Bibliography"].paragraph_format.left_indent = Cm(1.0)
    st["Bibliography"].paragraph_format.first_line_indent = Cm(-1.0)
    st["Bibliography"].paragraph_format.space_after = Pt(6)
    st["Bibliography"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    # cover / front-matter styles
    s = get("Cover Wordmark")
    _set_font(s, size=60, color=INK, bold=True)
    s.paragraph_format.space_before = Pt(170)
    s.paragraph_format.space_after = Pt(6)
    s = get("Cover Subtitle")
    _set_font(s, size=15, color=MUTED)
    s.paragraph_format.space_after = Pt(60)
    _para_border(s, "bottom", ACCENT, 12, 8)
    s = get("Cover Title")
    _set_font(s, size=34, color=PRIMARY, bold=True)
    s.paragraph_format.space_before = Pt(30)
    s.paragraph_format.space_after = Pt(14)
    s = get("Cover Meta")
    _set_font(s, size=12, color=INK)
    s.paragraph_format.space_after = Pt(6)
    s = get("Front Heading")
    _set_font(s, size=18, color=INK, bold=True)
    s.paragraph_format.page_break_before = True
    s.paragraph_format.space_after = Pt(12)
    s.paragraph_format.keep_with_next = True
    _para_border(s, "bottom", PRIMARY, 12, 4)
    for nm, col in (("WM Text", INK), ("WM Primary", PRIMARY), ("WM Accent", ACCENT)):
        s = get(nm, WD_STYLE_TYPE.CHARACTER)
        s.font.color.rgb = _rgb(col)
        s.font.bold = True
        s.font.name = FONT

    for sec in doc.sections:
        sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
        sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Cm(2.2)
    doc.save(str(REFERENCE_DOCX))
    tmp.unlink(missing_ok=True)
    log(f"reference.docx written: {REFERENCE_DOCX}")


# ----------------------------------------------------------------------------------------------
# helpers: markdown tables, numbers
# ----------------------------------------------------------------------------------------------
def esc(s) -> str:
    s = "" if s is None else str(s)
    s = s.replace("\r", " ").replace("\n", " ")
    s = re.sub(r"([\\`*_^~\[\]<>$|])", r"\\\1", s)
    return s.strip()


def fnum(v, kind="g") -> str:
    if v is None:
        return "-"
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float)):
        if kind == "frac":
            return f"{v:.2e}" if 0 < abs(v) < 1e-3 else f"{v:.4f}"
        if kind == "T":
            return f"{v:.1f}"
        if kind == "P":
            return f"{v:.2f}"
        if kind == "VF":
            return f"{v:.3f}"
        if kind == "flow":
            return f"{v:.2f}"
        return f"{v:.6g}"
    return str(v)


def pipe_table(headers, rows, aligns=None) -> str:
    n = len(headers)
    aligns = aligns or ["l"] * n
    widths = []
    for j in range(n):
        cells_j = [esc(headers[j])] + [esc(r[j]) for r in rows if j < len(r)]
        m = max(len(x) for x in cells_j)
        lw = max(len(w) for x in cells_j for w in (x.split() or [""]))
        widths.append(int(max(lw + 3, min(m, 40) * 0.7, 5)))
    sep = []
    for j in range(n):
        d = "-" * widths[j]
        sep.append({"l": ":" + d[1:], "r": d[1:] + ":", "c": ":" + d[2:] + ":"}[aligns[j]])
    out = ["| " + " | ".join(esc(h) for h in headers) + " |", "|" + "|".join(sep) + "|"]
    for r in rows:
        cells = [esc(r[j]) if j < len(r) else "" for j in range(n)]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def generic_table_md(obj, caption: str, source: str, max_cols: int = 5) -> str:
    rows, label_key = None, None
    if isinstance(obj, list) and obj and all(isinstance(x, dict) for x in obj):
        rows = obj
    elif isinstance(obj, dict):
        lists = [(k, v) for k, v in obj.items() if isinstance(v, list) and v and all(isinstance(x, dict) for x in v)]
        if lists:
            rows = max(lists, key=lambda kv: len(kv[1]))[1]
        elif obj and all(isinstance(v, dict) for v in obj.values()):
            rows = [{"key": k, **v} for k, v in obj.items()]
        else:
            rows = [{"key": k, "value": v} for k, v in obj.items() if not isinstance(v, (list, dict))]
    if not rows:
        return "No tabular content found in the source file.\n"
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)

    def cell(v):
        if v is None:
            return "-"
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return fnum(v)
        if isinstance(v, list):
            if not v:
                return "-"
            if all(isinstance(x, str) for x in v):
                t = "; ".join(v)
            else:
                return f"{len(v)} item(s), see source file"
        elif isinstance(v, dict):
            return f"{len(v)} field(s), see source file"
        else:
            t = str(v)
        t = t.replace(" degC", " °C").replace("degC", "°C")
        return t if len(t) <= 160 else t[:157] + "..."

    first, rest = cols[0], cols[1:]
    chunks = [rest[i:i + max_cols - 1] for i in range(0, len(rest), max_cols - 1)] or [[]]
    out = []
    for ci, ch in enumerate(chunks):
        hs = [first] + ch
        body = [[cell(r.get(c)) for c in hs] for r in rows]
        part = f" (columns part {ci + 1} of {len(chunks)})" if len(chunks) > 1 else ""
        out.append(f"Table: {caption}{part} *Source: {source}*\n\n" + pipe_table(hs, body))
    return "\n".join(out)


# ----------------------------------------------------------------------------------------------
# sections, figures, citations
# ----------------------------------------------------------------------------------------------
COMMENT_RE = re.compile(r"<!--(.*?)-->", re.S)
CITES_RE = re.compile(r"cites:\s*(.*)", re.S)
IMG_RE = re.compile(r"^[ \t]*!\[(?P<alt>.*)\]\((?P<path>[^)]+?)\)(?P<attr>\{[^}]*\})?[ \t]*$", re.M)


def collect_sections(sdir: Path, summary: dict) -> list[tuple[str, Path]]:
    files = sorted(p for p in sdir.glob("*.md") if re.match(r"\d\d_", p.name))
    found = {p.name for p in files}
    missing = [f"{n:02d} {t or '(title set by its writer)'} ({f})" for n, (f, t) in EXPECTED.items() if f not in found]
    expected_files = {f for f, _ in EXPECTED.values()}
    unexpected = [p.name for p in files if not p.name.startswith("00_") and p.name not in expected_files]
    summary["missing_sections"] = missing
    summary["unexpected_section_files"] = unexpected
    for m in missing:
        log(f"WARNING missing section: {m}")
    for u in unexpected:
        log(f"WARNING section file not in the 35-item structure: {u}")
    # heading of each file must match the table in WRITING_GUIDE.md
    by_file = {f: (n, t) for n, (f, t) in EXPECTED.items()}
    bad = []
    titles = {}
    for p in files:
        if p.name in by_file:
            n, t = by_file[p.name]
            first = next((ln for ln in p.read_text(encoding="utf-8-sig").splitlines() if ln.startswith("# ")), "")
            titles[n] = first.strip()[2:]
            if t is None:
                if not re.match(rf"^# {n} \S", first.strip()):
                    bad.append(f"{p.name}: '{first.strip()}' (expected '# {n} <title>')")
            elif first.strip() != f"# {n} {t}":
                bad.append(f"{p.name}: '{first.strip()}' (expected '# {n} {t}')")
    summary["section_titles"] = titles
    summary["heading_mismatches"] = bad
    for b in bad:
        log(f"WARNING heading mismatch: {b}")
    return [(p.name, p) for p in files if not p.name.startswith("00_")]


def resolve_image(path_txt: str, section_file: Path) -> Path | None:
    p = urllib.parse.unquote(path_txt.strip().strip("<>").split(' "')[0])
    cand = Path(p)
    options = [cand] if cand.is_absolute() else [HERE / cand, section_file.parent / cand, ROOT / cand]
    for o in options:
        try:
            if o.is_file():
                return o.resolve()
        except OSError:
            pass
    return None


def pandoc_image_path(p: Path) -> str:
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        dst = GEN / "img"
        dst.mkdir(parents=True, exist_ok=True)
        tgt = dst / re.sub(r"[^A-Za-z0-9_.-]", "_", p.name)
        shutil.copy2(p, tgt)
        return tgt.relative_to(ROOT).as_posix()


# ----------------------------------------------------------------------------------------------
# evidence matrix (results/research/evidence_matrix.json): verdicts are never retyped in the sections
# ----------------------------------------------------------------------------------------------
_EVIDENCE_CACHE: dict = {}


def load_evidence() -> dict | None:
    if "data" not in _EVIDENCE_CACHE:
        d = None
        if EVIDENCE_JSON.exists():
            try:
                d = read_json(EVIDENCE_JSON)
            except Exception as e:  # noqa: BLE001
                log(f"WARNING evidence_matrix.json unreadable: {e!r}")
        _EVIDENCE_CACHE["data"] = d
    return _EVIDENCE_CACHE["data"]


def _hyp(hid: str) -> dict | None:
    d = load_evidence()
    if not d:
        return None
    return next((h for h in d.get("hypotheses", []) if str(h.get("id")).upper() == hid.upper()), None)


def _fmt_val(v) -> str:
    if isinstance(v, bool) or v is None:
        return "-" if v is None else str(v)
    if isinstance(v, int):
        return f"{v}"
    if isinstance(v, float):
        a = abs(v)
        if a != 0 and (a < 1e-3 or a >= 1e6):
            return f"{v:.3g}"
        return f"{v:.4g}"
    return str(v)


def _short_txt(v, n: int) -> str:
    t = "" if v is None else " ".join(str(v).split())
    t = re.sub(r"\s?degC\b", " °C", t).replace(" — ", ", ").replace("—", ", ")
    return t if len(t) <= n else t[: n - 3].rstrip() + "..."


_EVIDENCE_TABLE_NO = [0]


def evidence_table_caption(text: str) -> str:
    _EVIDENCE_TABLE_NO[0] += 1
    return f"Table: **Table 31.{_EVIDENCE_TABLE_NO[0]}.** {text}"


def evidence_summary_table_md() -> str:
    d = load_evidence()
    if not d:
        return ("*The evidence matrix (results/research/evidence_matrix.json) was not available at build time.*\n")
    rows = [[h.get("id"), h.get("verdict"), _row_outcomes(h), _short_txt(h.get("summary"), 400)]
            for h in d.get("hypotheses", [])]
    gen = (d.get("provenance") or {}).get("generated_utc", "-")
    return (evidence_table_caption("Verdicts of the four hypotheses with the outcome of each evidence row, read from the evidence "
                                   f"matrix at build time. *Source: results/research/evidence_matrix.json (generated {gen}).*") + "\n\n"
            + pipe_table(["H", "Verdict", "Row outcomes", "Summary"], rows))


def _row_outcomes(h: dict) -> str:
    groups: dict[str, list[str]] = {}
    for r in h.get("rows", []):
        groups.setdefault(str(r.get("verdict")), []).append(str(r.get("row_id")))
    if groups and "None" not in groups:
        return "; ".join(f"{k}: {', '.join(v)}" for k, v in groups.items())
    vc = _short_txt(h.get("verdict_conditions"), 100000)
    return vc.split("Row outcomes:", 1)[1].strip() if "Row outcomes:" in vc else vc


def _row_conditions(r: dict) -> str:
    c = _short_txt(r.get("conclusion_conditions"), 100000)
    if "Conditions:" in c:
        return c.split("Conditions:", 1)[1].strip()
    return "" if c.startswith("Rule:") else c


def evidence_rows_md(hid: str) -> str:
    h = _hyp(hid)
    if h is None:
        return f"*Hypothesis {hid} is not in the evidence matrix available at build time.*\n"
    out = []
    if h.get("summary"):
        out.append(f"**Verdict: {h.get('verdict')}.** {esc(_short_txt(h.get('summary'), 100000))}\n")
    rows = []
    for r in h.get("rows", []):
        nums = []
        for f in (r.get("numerical_findings") or [])[:4]:
            u = (" " + _short_txt(f.get("unit"), 30).strip()) if f.get("unit") not in (None, "", "-") else ""
            nums.append(f"{_short_txt(f.get('quantity'), 70)} = {_fmt_val(f.get('value'))}{u} ({f.get('source_type')})")
        extra = len(r.get("numerical_findings") or []) - 4
        if extra > 0:
            nums.append(f"{extra} further value(s) in the matrix")
        concl = _short_txt(r.get("conclusion"), 100000)
        cond = _row_conditions(r)
        if cond:
            concl += " Conditions: " + cond
        rows.append([r.get("row_id"), r.get("verdict") or "-", _short_txt(r.get("sub_claim"), 200), "; ".join(nums) or "-", concl])
    if rows:
        out.append(evidence_table_caption(f"Evidence rows for {hid}: sub-claim, row verdict, key numbers with their origin, and the "
                                          "row conclusion with its conditions. *Source: results/research/evidence_matrix.json; models, "
                                          "cases, assumptions, references, uncertainty ranges and evidence files of each row are in "
                                          "docs/research/evidence_matrix.md.*")
                   + "\n\n" + pipe_table(["Row", "Verdict", "Sub-claim", "Key numbers (origin)", "Conclusion"], rows))
    return "\n".join(out) + "\n"


def substitute_tokens(text: str, summary: dict) -> str:
    def verdict(m):
        h = _hyp(m.group(1))
        if h is None:
            summary.setdefault("unresolved_tokens", []).append(m.group(0))
            return "not available at build time"
        return f"**{h.get('verdict')}**"

    def cond(m):
        h = _hyp(m.group(1))
        return esc(_short_txt(h.get("verdict_conditions"), 100000)) if h and h.get("verdict_conditions") else "conditions not available at build time"

    text = re.sub(r"\{\{VERDICT:(H\d)\}\}", verdict, text)
    text = re.sub(r"\{\{VERDICT_CONDITIONS:(H\d)\}\}", cond, text)

    def summ(m):
        h = _hyp(m.group(1))
        return esc(_short_txt(h.get("summary"), 100000)) if h and h.get("summary") else "summary not available at build time"

    text = re.sub(r"\{\{VERDICT_SUMMARY:(H\d)\}\}", summ, text)

    def row_verdict(m):
        h = _hyp(m.group(1).split("-")[0])
        r = next((x for x in (h or {}).get("rows", []) if str(x.get("row_id")) == m.group(1)), None)
        if r is None:
            summary.setdefault("unresolved_tokens", []).append(m.group(0))
            return f"row {m.group(1)}: not available at build time"
        return f"row {m.group(1)}: {r.get('verdict')}"

    text = re.sub(r"\{\{ROW_VERDICT:(H\d-[a-z])\}\}", row_verdict, text)
    text = re.sub(r"\{\{ROW_OUTCOMES:(H\d)\}\}", lambda m: esc(_row_outcomes(_hyp(m.group(1)) or {})) or "not available", text)
    if "{{EVIDENCE_SUMMARY_TABLE}}" in text:
        text = text.replace("{{EVIDENCE_SUMMARY_TABLE}}", evidence_summary_table_md())
    text = re.sub(r"\{\{EVIDENCE_ROWS:(H\d)\}\}", lambda m: evidence_rows_md(m.group(1)), text)
    if "{{" in text:
        for t in sorted(set(re.findall(r"\{\{[^}]*\}\}", text))):
            log(f"WARNING unknown template token left in text: {t}")
            summary.setdefault("unresolved_tokens", []).append(t)
    if EVIDENCE_JSON.exists():
        summary["evidence_matrix_source"] = f"results/research/evidence_matrix.json ({(load_evidence() or {}).get('provenance', {}).get('generated_utc', '-')})"
    else:
        summary["evidence_matrix_source"] = "not available"
    return text


def unpublishable_screenshots() -> set[str]:
    if not EVIDENCE_SHOTS.exists():
        return set()
    m = read_json(EVIDENCE_SHOTS)
    return {c.get("file") for c in m.get("captures", []) if c.get("publish") is False or c.get("status") != "captured"}


def process_section(name: str, path: Path, summary: dict, cites: set[str]) -> str:
    text = path.read_text(encoding="utf-8-sig")
    text = substitute_tokens(text, summary)
    blocked = unpublishable_screenshots()
    for m in COMMENT_RE.finditer(text):
        c = CITES_RE.match(m.group(1).strip())
        if c:
            for k in re.split(r"[,;\s]+", c.group(1).strip()):
                if k:
                    cites.add(k)
    text = COMMENT_RE.sub("", text)

    def img(m):
        alt, ptxt, attr = m.group("alt").strip(), m.group("path"), m.group("attr") or ""
        found = resolve_image(ptxt, path)
        if found is not None and found.name in blocked and "aspen_evidence" in found.as_posix():
            summary.setdefault("unpublishable_screenshots", []).append(found.name)
            log(f"DROPPED FIGURE ({name}): {found.name} is flagged publish:false or not captured in the evidence manifest")
            found = None
        if found is None:
            summary["dropped_figures"].append({"section": name, "path": ptxt.strip(), "caption": alt[:120]})
            log(f"DROPPED FIGURE ({name}): {ptxt.strip()}")
            return ""
        summary["figures_inserted"] += 1
        # optional crop="x0,y0,x1,y1" (pixels of the source image) for screenshots whose form area would
        # otherwise be unreadable at page width; the crop is written to generated/img, the source is untouched
        cm = re.search(r'\s*crop="?(\d+),(\d+),(\d+),(\d+)"?', attr)
        if cm:
            attr = attr.replace(cm.group(0), "")
            from PIL import Image
            box = tuple(int(v) for v in cm.groups())
            dst = GEN / "img"
            dst.mkdir(parents=True, exist_ok=True)
            tgt = dst / (found.stem + "__crop_" + "_".join(cm.groups()) + found.suffix)
            with Image.open(found) as im:
                im.crop(box).save(tgt)
            fm0 = re.match(r"\*\*Figure (\d+\.\d+)\.\*\*", alt)
            if fm0:
                summary.setdefault("figure_map", {}).setdefault(found.name, []).append(fm0.group(1))
            found = tgt
        fm = re.match(r"\*\*Figure (\d+\.\d+)\.\*\*", alt)
        if fm:
            summary.setdefault("figure_map", {}).setdefault(found.name, []).append(fm.group(1))
            summary.setdefault("figure_files", []).append((fm.group(1), found.relative_to(ROOT).as_posix() if found.is_relative_to(ROOT) else str(found)))
        rel = pandoc_image_path(found)
        cap = f'\n\n::: {{custom-style="Caption"}}\n{alt}\n:::\n' if alt else ""
        return f"![]({rel}){attr}\n{cap}"

    text = IMG_RE.sub(img, text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip() + "\n"


def italicise_apa(apa: str) -> tuple[str, str]:
    """Return (markdown text, url).  Italicise journal + volume for journal articles when the pattern is clear."""
    m = re.search(r"\s(https?://\S+)\s*$", apa)
    url = m.group(1) if m else ""
    body = apa[: m.start()].rstrip() if m else apa.rstrip()
    body = re.sub(r"([\\`*_<>\[\]#])", r"\\\1", body)
    jm = re.match(r"^(?P<pre>.*?\(\d{4}[a-z]?\)\.\s.+?\.)\s(?P<jour>[^.]+?),\s(?P<vol>\d+)(?P<iss>\\?\(\d+\\?\))?,\s(?P<pg>[\w\-–]+)\.$", body)
    if jm:
        iss = jm.group("iss") or ""
        body = f"{jm.group('pre')} *{jm.group('jour')}*, *{jm.group('vol')}*{iss}, {jm.group('pg')}."
    return body, url


def build_references(cites: set[str], summary: dict) -> tuple[str, dict]:
    refs = json.loads((ROOT / "research" / "references.json").read_text(encoding="utf-8"))
    by_key = {r["citekey"]: r for r in refs}
    missing = sorted(k for k in cites if k not in by_key)
    for k in missing:
        log(f"WARNING cited key not in references.json: {k}")
    summary["missing_citation_keys"] = missing
    used = [by_key[k] for k in cites if k in by_key]
    used.sort(key=lambda r: re.sub(r"[^a-z0-9 ]", "", r["apa7"].lower()))
    lines = [REFERENCES_HEADING, ""]
    for r in used:
        # house style has no em dashes; an em dash in a source title (e.g. ISO titles) is set as an en dash
        body, url = italicise_apa(r["apa7"].replace(" — ", " – ").replace("—", "–"))
        url = url or r.get("url") or ""
        entry = body + ("\\\n<" + url + ">" if url else "")
        lines.append(f'::: {{custom-style="Bibliography"}}\n{entry}\n:::\n')
    if not used:
        lines.append("No cited references were found in the section files.")
    return "\n".join(lines) + "\n", by_key


def check_intext(all_text: str, cited_refs: list[dict], summary: dict) -> None:
    surnames = {}
    groups = []  # (author string, year, key) for group authors such as organisations
    for r in cited_refs:
        m = re.match(r"^([^,]+),.*?\((\d{4}[a-z]?|n\.d\.)(?:, [A-Z][a-z]+(?: \d{1,2})?)?\)", r["apa7"])
        m_org = re.match(r"^(.+?)\.\s+\((\d{4}[a-z]?|n\.d\.)(?:, [A-Z][a-z]+(?: \d{1,2})?)?\)", r["apa7"])
        if m_org and "," not in m_org.group(1):
            groups.append((m_org.group(1).lower(), m_org.group(2), r["citekey"]))
            for alias in AUTHOR_ALIASES.get(r["citekey"], []):
                groups.append((alias.lower(), m_org.group(2), r["citekey"]))
        elif m:
            surnames[(m.group(1).strip().lower(), m.group(2))] = r["citekey"]
    pat = re.compile(r"((?:[A-Z][\w'’\-]+|van|de|di|del)(?: (?:de|di|del|van|der|Di|Del|Van))*(?: [A-Z][\w'’\-]+)?)(?: et al\.|(?:,? (?:&|and) [A-Z][\w'’\-]+))?, (\d{4}[a-z]?)")
    unresolved = set()
    for par in re.findall(r"\(([^()]*\d{4}[^()]*)\)", all_text):
        for part in par.split(";"):
            m = pat.search(part.strip().lstrip("e.g., ").lstrip("see "))
            if not m:
                continue
            sn = m.group(1).split(" ")[-1].lower() if m.group(1).split(" ")[0].lower() not in ("di", "del", "van", "de") else m.group(1).lower()
            cands = {k for k in surnames if k[1] == m.group(2) and (k[0].lower() == sn or k[0].lower().endswith(sn) or sn in k[0].lower() or k[0].lower() in m.group(1).lower())}
            cands |= {g for g in groups if g[1] == m.group(2) and (m.group(1).lower() in g[0] or g[0] == m.group(1).lower())}
            if not cands:
                unresolved.add(m.group(0))
    summary["unresolved_intext"] = sorted(unresolved)
    for u in sorted(unresolved):
        log(f"WARNING in-text citation without listed reference: ({u})")
    # the reverse check: every listed reference must be cited somewhere in the text
    flat = re.sub(r"\s+", " ", all_text)
    uncited = []
    for r in cited_refs:
        m_org = re.match(r"^(.+?)\.\s+\((\d{4}[a-z]?|n\.d\.)(?:, [A-Z][a-z]+(?: \d{1,2})?)?\)", r["apa7"])
        year = re.search(r"\((\d{4}[a-z]?|n\.d\.)(?:, [A-Z][a-z]+(?: \d{1,2})?)?\)", r["apa7"])
        year = year.group(1) if year else ""
        names = []
        if m_org and "," not in m_org.group(1):
            names = [m_org.group(1)] + AUTHOR_ALIASES.get(r["citekey"], [])
        else:
            names = [r["apa7"].split(",")[0].strip()]
        hit = any(re.search(re.escape(n) + r"[^()]{0,80}?\(?" + re.escape(year), flat) for n in names)
        if not hit:
            uncited.append(r["citekey"])
    summary["listed_but_not_cited"] = uncited
    for u in uncited:
        log(f"WARNING reference listed (cites comment) but not found as an in-text citation: {u}")


# ----------------------------------------------------------------------------------------------
# appendices
# ----------------------------------------------------------------------------------------------
def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def appendix_md(summary: dict, cites: set[str]) -> str:
    out = [APPENDICES_HEADING, "",
           "The appendices are generated automatically from the project result and configuration files by `build_report.py`, "
           "so that they always reflect the current repository state.", ""]
    # A
    out += ["## A Aspen stream table (baseline case)", ""]
    bp = ROOT / "results" / "simulations" / "baseline.json"
    if bp.exists():
        d = read_json(bp)
        order = ["FEED", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "H2PROD", "TAILGAS", "AIR", "FLUE", "STACK"]
        ids = [s for s in order if s in d["streams"]] + sorted(s for s in d["streams"] if s not in order)
        comps = ["NH3", "H2", "N2", "H2O", "O2"]
        rows1 = [[s, fnum(d["streams"][s].get("temperature_C"), "T"), fnum(d["streams"][s].get("pressure_bar"), "P"),
                  fnum(d["streams"][s].get("vapor_fraction"), "VF"), fnum(d["streams"][s].get("mole_flow_kmol_h"), "flow"),
                  fnum(d["streams"][s].get("mass_flow_kg_h"), "flow")] for s in ids]
        rows2 = [[s] + [fnum(d["streams"][s]["mole_frac"].get(c), "frac") for c in comps] for s in ids]
        src = f"Aspen Plus V15 simulation, results/simulations/baseline.json (case {d.get('case_id')}, run {d.get('created_utc')})."
        out += [f"Table: **Table A.1.** Aspen Plus V15 stream conditions and flows for the baseline case. *Source: {src}*", "",
                pipe_table(["Stream", "T (°C)", "P (bar)", "Vapour fraction", "Molar flow (kmol/h)", "Mass flow (kg/h)"], rows1,
                           ["l", "r", "r", "r", "r", "r"]),
                f"Table: **Table A.2.** Aspen Plus V15 stream compositions (mole fractions) for the baseline case. *Source: {src}*", "",
                pipe_table(["Stream"] + comps, rows2, ["l"] + ["r"] * 5)]
        # B
        out += ["## B Aspen block summary (baseline case)", ""]
        rows = []
        for bid, b in d["blocks"].items():
            det = {k: v for k, v in (b.get("details") or {}).items() if k != "aspen_status"}
            det_s = "; ".join(f"{k} = {fnum(v) if not isinstance(v, str) else v}" for k, v in list(det.items())[:6])
            rows.append([bid, b.get("block_type"), fnum(b.get("duty_kW")), fnum(b.get("power_kW")), fnum(b.get("outlet_temperature_C")), det_s])
        out += [f"Table: **Table B.1.** Aspen Plus V15 block summary for the baseline case (duty positive = heat added). *Source: {src}*", "",
                pipe_table(["Block", "Type", "Duty (kW)", "Power (kW)", "Outlet T (°C)", "Key details"], rows, ["l", "l", "r", "r", "r", "l"])]
    else:
        out += ["results/simulations/baseline.json is not available at build time.", "", "## B Aspen block summary (baseline case)", "",
                "results/simulations/baseline.json is not available at build time.", ""]
    # C
    out += ["## C Aspen input file listing (baseline.inp)", "",
            "Generated by `backend/amcrax/aspen/inp_writer.py`; listing of `aspen/models/baseline.inp`.", ""]
    inp = ROOT / "aspen" / "models" / "baseline.inp"
    if inp.exists():
        out += ["~~~~", inp.read_text(encoding="utf-8", errors="replace").rstrip(), "~~~~", ""]
    else:
        out += ["aspen/models/baseline.inp is not available at build time.", ""]
    summary["inp_in_appendix"] = inp.exists()
    # D
    out += ["## D Validation matrix", ""]
    vm = ROOT / "results" / "validation" / "validation_matrix.json"
    if vm.exists():
        vmd = read_json(vm)
        items = vmd.get("items") if isinstance(vmd, dict) else None
        if items and all(isinstance(x, dict) for x in items):
            def _short(v, n):
                t = "-" if v is None else str(v)
                return t if len(t) <= n else t[: n - 3].rstrip() + "..."
            sm = vmd.get("summary", {})
            out += [f"The matrix holds {sm.get('n_items', len(items))} items: {sm.get('pass', '-')} pass, {sm.get('fail', '-')} fail, "
                    f"{sm.get('not_run', '-')} not run and {sm.get('informational', '-')} informational "
                    f"(generated {vmd.get('generated_utc', '-')}). Method and metric texts are shortened; the full text, the actual result, "
                    "the root cause of each failure and the evidence files are in the source file.", ""]
            def _num(v):
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    return f"{v:.3g}"
                return _short(v, 20)
            # Compact form: counts by family, every failing item, and the root causes. The full
            # one-row-per-item matrix is docs/validation/validation_matrix.md (13 pages when printed).
            fam = sm.get("by_family") or {}
            if fam:
                frows = [[k, v.get("n_items"), v.get("pass"), v.get("fail"), v.get("not_run"), v.get("informational")]
                         for k, v in fam.items()]
                out += ["Table: **Table D.1.** Validation matrix: number of items by family and status. "
                        "*Source: results/validation/validation_matrix.json.*", "",
                        pipe_table(["Family", "Items", "Pass", "Fail", "Not run", "Informational"], frows,
                                   ["l", "r", "r", "r", "r", "r"])]
            failing = [it for it in items if it.get("status") == "fail"]
            if failing:
                rows = [[it.get("id"), _short(it.get("model_component"), 34), _short(it.get("metric"), 70),
                         _num(it.get("value")), _num(it.get("tolerance")), it.get("root_cause") or "-"] for it in failing]
                out += ["Table: **Table D.2.** Every failing item of the validation matrix. "
                        "*Source: results/validation/validation_matrix.json.*", "",
                        pipe_table(["ID", "Component", "Metric", "Value", "Tolerance", "Root cause"], rows,
                                   ["l", "l", "l", "r", "r", "l"])]
            for rc in sm.get("failure_root_causes") or []:
                out += [f"**Root cause `{rc.get('cause')}` ({rc.get('n_items')} items).** {esc(rc.get('description'))}", ""]
            out += ["The complete matrix with one row per item (method, reference, expected behaviour, actual result, "
                    "limitations and evidence files) is `docs/validation/validation_matrix.md`.", ""]
        else:
            out += [generic_table_md(vmd, "**Table D.1.** Validation matrix.", "results/validation/validation_matrix.json")]
    else:
        out += ["The validation matrix (results/validation/validation_matrix.json) is generated later and was not available at build time.", ""]
    # E
    out += ["## E Model-parameter traceability", ""]
    tj = ROOT / "research" / "traceability.json"
    if tj.exists():
        out += [generic_table_md(read_json(tj), "**Table E.1.** Model-parameter traceability.", "research/traceability.json")]
    else:
        out += ["The traceability table (research/traceability.json) was not available at build time.", ""]
    # F
    out += ["## F Reproducibility instructions", ""]
    out += [reproducibility_md(summary), ""]
    # G
    out += ["## G Aspen screenshot index", ""]
    mp = ROOT / "aspen" / "screenshots" / "manifest.json"
    if mp.exists():
        m = read_json(mp)
        caps = m.get("captures", [])
        fmap = summary.get("figure_map", {})
        rows = []
        for c in caps:
            shown = c.get("reason_if_not") or c.get("what_is_shown") or ""
            if c.get("redaction"):
                shown += " Masked: " + c["redaction"].split(";")[0].rstrip(".") + "."
            rows.append([c.get("file"), ", ".join(fmap.get(c.get("file"), [])) or "-", c.get("title"),
                         c.get("navigation_path"), c.get("status"), shown])
        nc = [c for c in caps if c.get("status") != "captured"]
        out += [f"Screenshots of the real {m.get('aspen_version', 'Aspen Plus V15')} GUI, captured from `{m.get('model_file')}`. "
                f"{len(caps) - len(nc)} of {len(caps)} planned items are captured; items not captured are listed with the reason. "
                "Each captured image appears once in the report, as the figure listed.", "",
                "Table: **Table G.1.** Aspen Plus V15 screenshot index. *Source: aspen/screenshots/manifest.json.*", "",
                pipe_table(["File", "Figure", "Title", "Navigation path", "Status", "What is shown / reason if not captured"], rows)]
        summary["screenshots_not_captured"] = [c.get("file") for c in nc]
    else:
        out += ["aspen/screenshots/manifest.json is not available at build time.", ""]
    # G.2 research-expansion screenshots (kinetic RPLUG cases)
    if EVIDENCE_SHOTS.exists():
        m = read_json(EVIDENCE_SHOTS)
        caps = m.get("captures", [])
        fmap = summary.get("figure_map", {})
        rows = []
        for c in caps:
            pub = "no" if c.get("publish") is False else "yes"
            rows.append([c.get("file"), ", ".join(fmap.get(c.get("file"), [])) or "-", c.get("title"),
                         c.get("navigation_path"), "yes" if c.get("visually_verified") else "no", pub])
        n_pub = sum(1 for c in caps if c.get("publish") is not False)
        out += [f"The research expansion added {len(caps)} screenshots of kinetic RPLUG cases, captured from the sanitised "
                f"`.bkp` files in `aspen/models/research/` after a re-run through COM, with personal identifiers masked. "
                f"{n_pub} are cleared for publication; only those can appear as figures.", "",
                "Table: **Table G.2.** Aspen Plus V15 screenshot index of the kinetic reactor cases. "
                "*Source: docs/images/aspen_evidence/manifest.json.*", "",
                pipe_table(["File", "Figure", "Title", "Navigation path", "Inspected", "Publishable"], rows)]
    # H research-expansion validation items
    out += ["## H Research-expansion validation summary", ""]
    if RESEARCH_VALIDATION.exists():
        frows, fails = [], []
        for p in sorted(RESEARCH_VALIDATION.glob("*.json")):
            try:
                items = read_json(p)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(items, dict):
                items = items.get("items", [])
            if not isinstance(items, list):
                continue
            cnt = {"pass": 0, "fail": 0, "informational": 0}
            for it in items:
                s = it.get("status")
                cnt[s] = cnt.get(s, 0) + 1
                if s == "fail":
                    fails.append([p.stem, it.get("id"), _short_txt(it.get("description"), 120), _fmt_val(it.get("observed")) if not isinstance(it.get("observed"), str) else _short_txt(it.get("observed"), 50),
                                  _fmt_val(it.get("tolerance")) if not isinstance(it.get("tolerance"), str) else _short_txt(it.get("tolerance"), 30)])
            frows.append([p.stem, len(items), cnt.get("pass", 0), cnt.get("fail", 0), cnt.get("informational", 0)])
        out += ["Each research workstream wrote its validation items to `results/research/validation/<area>.json` with honest "
                "pass, fail or informational statuses. The counts and every failing item are listed here as they stand at build time.", "",
                "Table: **Table H.1.** Research-expansion validation items by workstream and status. "
                "*Source: results/research/validation/\\*.json.*", "",
                pipe_table(["Workstream file", "Items", "Pass", "Fail", "Informational"], frows, ["l", "r", "r", "r", "r"])]
        if fails:
            out += ["Table: **Table H.2.** Every failing research-expansion validation item. "
                    "*Source: results/research/validation/\\*.json.*", "",
                    pipe_table(["File", "ID", "Description", "Observed", "Tolerance"], fails)]
    return "\n".join(out) + "\n"


def _section_by_heading(text: str, pat: str) -> str | None:
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        m = re.match(r"^(#+)\s+(.*)$", ln)
        if m and re.search(pat, m.group(2), re.I):
            lvl, body = len(m.group(1)), []
            for ln2 in lines[i + 1:]:
                m2 = re.match(r"^(#+)\s", ln2)
                if m2 and len(m2.group(1)) <= lvl:
                    break
                body.append(ln2)
            return "\n".join(body).strip()
    return None


REPRO_DOC = ROOT / "docs" / "reproducing.md"


def reproducibility_md(summary: dict | None = None) -> str:
    """Appendix F from docs/reproducing.md (the whole page below its title).

    Headings are demoted below the appendix level, and relative Markdown links (which would point at
    files outside the report) become the repository path in code font."""
    if not REPRO_DOC.exists():
        log("WARNING docs/reproducing.md not found; appendix F is empty")
        return "docs/reproducing.md was not available at build time."
    t = REPRO_DOC.read_text(encoding="utf-8-sig")
    t = re.sub(r"\A\s*#\s+[^\n]*\n", "", t)                       # drop the page title
    t = re.sub(r"^#+\s+(.*)$", r"#### \1", t, flags=re.M)

    def link(m):
        txt, target = m.group(1), m.group(2)
        if re.match(r"https?://", target):
            return m.group(0)
        path = (REPRO_DOC.parent / target.split("#")[0]).resolve()
        try:
            rel = path.relative_to(ROOT).as_posix()
        except ValueError:
            rel = target
        return f"{txt} (`{rel}`)" if txt.strip("`") != rel else f"`{rel}`"
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, t)
    flagged = sorted(set(re.findall(r"[^.\n]*\b(?:[Pp]laceholder|to be confirmed)\b[^.\n]*\.", t)))
    if summary is not None:
        summary["reproducing_placeholders"] = flagged
    for f in flagged:
        log(f"WARNING docs/reproducing.md contains placeholder text: {f.strip()[:140]}")
    return "Source: docs/reproducing.md, reproduced as it stands at build time.\n\n" + t.strip()


# ----------------------------------------------------------------------------------------------
# front matter
# ----------------------------------------------------------------------------------------------
ABBR = [
    ("AmCraX", "Ammonia Cracking Simulation and Optimisation Platform"),
    ("APA", "American Psychological Association (citation style, 7th edition)"),
    ("API", "Application programming interface"),
    ("COM", "Component Object Model (Windows automation interface of Aspen Plus)"),
    ("DOI", "Digital object identifier"),
    ("EOS", "Equation of state"),
    ("FEHE", "Feed/effluent heat exchanger"),
    ("GRI-Mech", "Gas Research Institute reaction mechanism (source of the NASA-7 thermochemical data)"),
    ("KPI", "Key performance indicator"),
    ("LCA", "Life-cycle assessment"),
    ("LCOH", "Levelised cost of hydrogen"),
    ("LHV", "Lower heating value"),
    ("LMTD", "Logarithmic-mean temperature difference"),
    ("NASA-7", "Seven-coefficient NASA polynomial thermochemical data format"),
    ("PENG-ROB", "Peng-Robinson equation-of-state property method in Aspen Plus"),
    ("PR", "Peng-Robinson"),
    ("PSA", "Pressure-swing adsorption"),
    ("RGibbs", "Aspen Plus Gibbs-energy-minimisation reactor model"),
    ("RStoic", "Aspen Plus stoichiometric reactor model"),
    ("UA", "Overall heat-transfer coefficient times area"),
]


def front_matter_md(sdir: Path) -> str:
    wm = '[Am]{custom-style="WM Text"}[Cra]{custom-style="WM Primary"}[X]{custom-style="WM Accent"}'
    author = ""
    af = HERE / "author.txt"
    if af.exists():
        a = af.read_text(encoding="utf-8").strip()
        if a:
            author = f'\n::: {{custom-style="Cover Meta"}}\n{a}\n:::\n'
    toc = ('```{=openxml}\n<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> TOC \\o "1-2" \\h \\z \\u </w:instrText></w:r>'
           '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>Table of contents (update field to populate).</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>\n```\n')
    md = f'''::: {{custom-style="Cover Wordmark"}}
{wm}
:::

::: {{custom-style="Cover Subtitle"}}
{SUBTITLE}
:::

::: {{custom-style="Cover Title"}}
Technical Report
:::

::: {{custom-style="Cover Meta"}}
{SCOPE_LINE}
:::

::: {{custom-style="Cover Meta"}}
{REPORT_DATE}
:::
{author}
::: {{custom-style="Front Heading"}}
Contents
:::

{toc}
'''
    nom = sdir / "00_nomenclature.md"
    if nom.exists():
        md += "\n" + COMMENT_RE.sub("", nom.read_text(encoding="utf-8-sig")).strip() + "\n"
    else:
        md += '\n::: {custom-style="Front Heading"}\nList of abbreviations and nomenclature\n:::\n\n'
        md += pipe_table(["Abbreviation", "Meaning"], [list(x) for x in ABBR]) + "\n"
    return md


# ----------------------------------------------------------------------------------------------
# docx post-processing
# ----------------------------------------------------------------------------------------------
def _fld(par, instr: str, size=9, color=MUTED):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt
    def run_with(child):
        r = par.add_run()
        r.font.size = Pt(size)
        r.font.color.rgb = _rgb(color)
        r._r.append(child)
    b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "begin"); run_with(b)
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = f" {instr} "; run_with(it)
    s = OxmlElement("w:fldChar"); s.set(qn("w:fldCharType"), "separate"); run_with(s)
    t = OxmlElement("w:t"); t.text = "1"; run_with(t)
    e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end"); run_with(e)


def _set_column_widths(tbl, text_w) -> None:
    """Column widths from the cell text: each column gets at least its longest word, then a share that
    grows with its typical text length (pandoc gives every column of a short pipe table the same width)."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    rows = tbl.rows
    if not rows:
        return
    ncol = len(rows[0].cells)
    if ncol < 2:
        return
    longest_word, avg_len, max_len = [1] * ncol, [0.0] * ncol, [1] * ncol
    for j in range(ncol):
        lens = []
        for row in rows:
            cells = row.cells
            if j >= len(cells):
                continue
            t = cells[j].text.strip()
            lens.append(len(t))
            for w in t.split():
                longest_word[j] = max(longest_word[j], min(len(w), 28))
        if lens:
            avg_len[j] = sum(lens) / len(lens)
            max_len[j] = max(lens)
    weight = [max(longest_word[j] + 1.5, 0.55 * avg_len[j] + 0.15 * min(max_len[j], 90) + 3) for j in range(ncol)]
    tot = sum(weight)
    total_tw = int(text_w / 635)  # EMU -> twips
    widths = [total_tw * w / tot for w in weight]
    # every column at least as wide as its longest word (9 pt Calibri, about 105 twips per character, plus cell
    # margins), so that short codes and words such as "INCONCLUSIVE" never break inside the word
    minw = [min(longest_word[j], 18) * 105 + 160 for j in range(ncol)]
    if sum(minw) < total_tw:
        fixed: list[int] = []
        for _ in range(ncol):
            new = [j for j in range(ncol) if j not in fixed and widths[j] < minw[j]]
            if not new:
                break
            fixed += new
            free = [j for j in range(ncol) if j not in fixed]
            rest = total_tw - sum(minw[j] for j in fixed)
            wfree = sum(weight[j] for j in free) or 1.0
            widths = [minw[j] if j in fixed else rest * weight[j] / wfree for j in range(ncol)]
    widths = [int(w) for w in widths]
    grid = tbl._tbl.tblGrid
    if grid is not None:
        for j, gc in enumerate(grid.findall(qn("w:gridCol"))):
            if j < ncol:
                gc.set(qn("w:w"), str(widths[j]))
    for row in rows:
        for j, cell in enumerate(row.cells):
            if j < ncol:
                tcpr = cell._tc.get_or_add_tcPr()
                for old in tcpr.findall(qn("w:tcW")):
                    tcpr.remove(old)
                tw = OxmlElement("w:tcW"); tw.set(qn("w:w"), str(widths[j])); tw.set(qn("w:type"), "dxa")
                tcpr.insert(0, tw)
    tblpr = tbl._tbl.tblPr
    for old in tblpr.findall(qn("w:tblLayout")):
        tblpr.remove(old)
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblpr.append(lay)


def postprocess_docx(path: Path) -> None:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, Emu

    doc = Document(str(path))
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Cm(2.2)
    sec.header_distance = sec.footer_distance = Cm(1.1)
    sec.different_first_page_header_footer = True
    text_w = sec.page_width - sec.left_margin - sec.right_margin

    # header
    hp = sec.header.paragraphs[0]
    hp.text = ""
    r = hp.add_run("AmCraX - Technical Report")
    r.font.size = Pt(9); r.font.color.rgb = _rgb(MUTED); r.font.name = FONT
    hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    ppr = hp._p.get_or_add_pPr()
    pb = OxmlElement("w:pBdr"); bt = OxmlElement("w:bottom")
    for k, v in (("val", "single"), ("sz", "4"), ("space", "3"), ("color", PRIMARY)):
        bt.set(qn(f"w:{k}"), v)
    pb.append(bt); ppr.append(pb)
    # footer
    fp = sec.footer.paragraphs[0]
    fp.text = ""
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run("Page "); r.font.size = Pt(9); r.font.color.rgb = _rgb(MUTED)
    _fld(fp, "PAGE")
    for hf in (sec.first_page_header, sec.first_page_footer):
        for p in hf.paragraphs:
            p.text = ""

    body = doc.element.body
    cap_style = next(s for s in doc.styles if s.name == "Caption")
    # Sections flow continuously (a forced page break before each of the 27 top-level headings would cost
    # about ten pages); only the first section, the references and the appendices start a new page.
    try:
        h1_style = doc.styles["Heading 1"]
        h1_style.paragraph_format.page_break_before = False
        h1_style.paragraph_format.space_before = Pt(26)
    except KeyError:
        pass
    # captions, images
    for p in doc.paragraphs:
        sn = p.style.name if p.style is not None else ""
        if sn == "Heading 1" and p.text.strip().startswith(("1 Executive", REFERENCES_HEADING[2:], APPENDICES_HEADING[2:])):
            p.paragraph_format.page_break_before = True
        if sn in ("Table Caption", "Image Caption"):
            p.style = doc.styles["Caption"] if False else cap_style
            sn = "Caption"
        if sn == "Caption":
            nxt = p._p.getnext()
            if nxt is not None and nxt.tag == qn("w:tbl"):
                p.paragraph_format.keep_with_next = True
            p.paragraph_format.keep_together = True
        if p._p.findall(".//" + qn("w:drawing")):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_after = Pt(2)
    max_h = Cm(21)
    for sh in doc.inline_shapes:
        w, h = sh.width, sh.height
        f = min(1.0, text_w / w, max_h / h)
        if f < 1.0:
            sh.width, sh.height = Emu(int(w * f)), Emu(int(h * f))

    # tables
    def shade(cell, fill):
        tcpr = cell._tc.get_or_add_tcPr()
        for old in tcpr.findall(qn("w:shd")):
            tcpr.remove(old)
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), fill)
        tcpr.append(shd)

    for ti, tbl in enumerate(doc.tables):
        tblpr = tbl._tbl.tblPr
        for tag in ("w:tblW", "w:tblBorders", "w:tblCellMar"):
            for old in tblpr.findall(qn(tag)):
                tblpr.remove(old)
        w = OxmlElement("w:tblW"); w.set(qn("w:type"), "pct"); w.set(qn("w:w"), "5000"); tblpr.append(w)
        bd = OxmlElement("w:tblBorders")
        for side, col, sz in (("top", PRIMARY, 8), ("bottom", PRIMARY, 8), ("insideH", "cfd6e4", 4)):
            e = OxmlElement(f"w:{side}")
            e.set(qn("w:val"), "single"); e.set(qn("w:sz"), str(sz)); e.set(qn("w:space"), "0"); e.set(qn("w:color"), col)
            bd.append(e)
        tblpr.append(bd)
        cm = OxmlElement("w:tblCellMar")
        for side, v in (("top", 30), ("left", 70), ("bottom", 30), ("right", 70)):
            e = OxmlElement(f"w:{side}"); e.set(qn("w:w"), str(v)); e.set(qn("w:type"), "dxa"); cm.append(e)
        tblpr.append(cm)
        _set_column_widths(tbl, text_w)
        nrows = len(tbl.rows)
        # short tables are kept on one page; long ones keep the header with the first two body rows
        keep_upto = nrows - 1 if nrows <= 22 else 3
        for ri, row in enumerate(tbl.rows):
            if ri < keep_upto:
                for cell in row.cells:
                    for par in cell.paragraphs:
                        par.paragraph_format.keep_with_next = True
            trpr = row._tr.get_or_add_trPr()
            cs = OxmlElement("w:cantSplit"); trpr.append(cs)
            if ri == 0:
                th = OxmlElement("w:tblHeader"); trpr.append(th)
            for cell in row.cells:
                if ri == 0:
                    shade(cell, PRIMARY)
                elif ri % 2 == 0:
                    shade(cell, "f1f5f9")
                for par in cell.paragraphs:
                    par.paragraph_format.space_before = Pt(1)
                    par.paragraph_format.space_after = Pt(1)
                    par.paragraph_format.alignment = par.paragraph_format.alignment if par.paragraph_format.alignment is not None else None
                    for run in par.runs:
                        run.font.size = Pt(9)
                        if ri == 0:
                            run.font.bold = True
                            run.font.color.rgb = _rgb("ffffff")
    # keep list: remove empty paragraphs directly before tables? (none created)
    doc.core_properties.title = "AmCraX Technical Report"
    doc.core_properties.subject = SUBTITLE
    doc.save(str(path))


# ----------------------------------------------------------------------------------------------
# Word export
# ----------------------------------------------------------------------------------------------
def _pid_alive(pid: int) -> bool:
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
    return str(pid) in out


def export_pdf(docx: Path, pdf: Path) -> None:
    import pythoncom
    import win32com.client
    import win32process

    pythoncom.CoInitialize()
    app = None
    pid = None
    try:
        app = win32com.client.DispatchEx("Word.Application")
        app.Visible = False
        app.DisplayAlerts = 0
        try:
            pid = win32process.GetWindowThreadProcessId(app.Hwnd)[1]
        except Exception:
            pid = None
        doc = app.Documents.Open(str(docx), False, False, False)
        try:
            for _ in range(2):  # twice: page numbers in the TOC depend on the final pagination
                doc.Repaginate()
                doc.Fields.Update()
                for i in range(1, doc.TablesOfContents.Count + 1):
                    doc.TablesOfContents(i).Update()
            for s in doc.Sections:
                for hf in list(s.Headers) + list(s.Footers):
                    hf.Range.Fields.Update()
            if pdf.exists():
                pdf.unlink()
            doc.ExportAsFixedFormat(str(pdf), 17, False, 0, 0, 1, 1, 0, True, True, 1, True, True, False)
            doc.Save()
        finally:
            doc.Close(0)
    finally:
        try:
            if app is not None:
                app.Quit(0)
        except Exception:
            pass
        app = None
        pythoncom.CoUninitialize()
        if pid:
            time.sleep(1.5)
            if _pid_alive(pid):
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
                log(f"WARNING: WINWORD pid {pid} had to be killed")


# ----------------------------------------------------------------------------------------------
# quality report
# ----------------------------------------------------------------------------------------------
def quality(docx: Path, pdf: Path | None, summary: dict, scan_text: str, fail_on_todo: bool) -> int:
    from docx import Document
    from docx.oxml.ns import qn
    doc = Document(str(docx))
    words = 0
    for p in doc.paragraphs:
        if p.style is not None and p.style.name == "Source Code":
            continue
        words += len(p.text.split())
    for t in doc.tables:
        for row in t.rows:
            for c in row.cells:
                words += len(c.text.split())
    body = doc.element.body
    summary["figures_in_docx"] = len(doc.inline_shapes)
    summary["tables_in_docx"] = len(doc.tables)
    summary["equations_display"] = len(body.findall(".//" + qn("m:oMathPara")))
    summary["equations_total"] = len(body.findall(".//" + qn("m:oMath")))
    summary["word_count"] = words
    h1 = [p.text.strip() for p in doc.paragraphs if p.style is not None and p.style.name == "Heading 1"]
    st = summary.get("section_titles", {})
    want = [st.get(n) or f"{n} {t}" for n, (_, t) in EXPECTED.items()] + [REFERENCES_HEADING[2:], APPENDICES_HEADING[2:]]
    summary["docx_heading1"] = h1
    summary["docx_outline_ok"] = h1 == want
    summary["pdf_pages"] = None
    summary["toc_populated"] = None
    if pdf and pdf.exists():
        import pymupdf
        pd = pymupdf.open(str(pdf))
        summary["pdf_pages"] = pd.page_count
        summary["toc_populated"] = not any("update field to populate" in pd[i].get_text() for i in range(min(4, pd.page_count)))
        pd.close()
    hits = sorted(set(m.group(0) for m in re.finditer(r"\bTODO\b|\bTBD\b|lorem ipsum|\blorem\b", scan_text, re.I)))
    summary["forbidden_strings"] = hits
    log("")
    log("=== QUALITY REPORT ===")
    log(f"PDF pages            : {summary['pdf_pages']}")
    log(f"Word count           : {words}")
    log(f"Figures in document  : {summary['figures_in_docx']}")
    log(f"Tables in document   : {summary['tables_in_docx']} (incl. generated appendix and abbreviation tables)")
    log(f"Equations (display)  : {summary['equations_display']} (total OMML {summary['equations_total']})")
    log(f"TOC populated in PDF : {summary['toc_populated']}")
    log(f"Dropped figures      : {len(summary['dropped_figures'])}")
    for d in summary["dropped_figures"]:
        log(f"   - {d['section']}: {d['path']}")
    log(f"Missing sections     : {len(summary['missing_sections'])}")
    for m in summary["missing_sections"]:
        log(f"   - {m}")
    log(f"DOCX outline = 35 items: {summary['docx_outline_ok']} ({len(h1)} level-1 headings)")
    log(f"Evidence matrix      : {summary.get('evidence_matrix_source')}")
    log(f"Unpublishable screenshots dropped: {summary.get('unpublishable_screenshots')}")
    if not summary["docx_outline_ok"]:
        for x in sorted(set(want) ^ set(h1)):
            log(f"   - outline difference: {x}")
    log(f"Heading mismatches   : {summary.get('heading_mismatches')}")
    log(f"Unexpected sections  : {summary.get('unexpected_section_files')}")
    log(f"Missing citation keys: {summary['missing_citation_keys']}")
    log(f"Unresolved in-text   : {summary['unresolved_intext']}")
    log(f"Listed, not cited    : {summary.get('listed_but_not_cited')}")
    log(f"Placeholders in docs/reproducing.md: {len(summary.get('reproducing_placeholders') or [])}")
    log(f"Screenshots not captured: {summary.get('screenshots_not_captured')}")
    log(f"TODO/TBD/lorem found : {hits}")
    if hits and fail_on_todo:
        log("BUILD FAILED: placeholder strings present")
        return 2
    return 0


# ----------------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sections", default=str(HERE / "sections"))
    ap.add_argument("--out-dir", default=str(HERE))
    ap.add_argument("--name", default="AmCraX_Technical_Report")
    ap.add_argument("--no-pdf", action="store_true")
    ap.add_argument("--no-fail-on-todo", action="store_true")
    a = ap.parse_args()
    sdir, odir = Path(a.sections).resolve(), Path(a.out_dir).resolve()
    odir.mkdir(parents=True, exist_ok=True)
    GEN.mkdir(parents=True, exist_ok=True)
    summary = {"build_time": _dt.datetime.now().isoformat(timespec="seconds"), "sections_dir": str(sdir),
               "dropped_figures": [], "figures_inserted": 0, "missing_sections": [], "missing_citation_keys": [],
               "unresolved_intext": []}
    log(f"AmCraX report build, sections: {sdir}")
    try:
        build_reference_docx()
        secs = collect_sections(sdir, summary)
        log(f"sections found: {len(secs)}")
        cites: set[str] = set()
        parts = []
        for name, p in secs:
            parts.append(process_section(name, p, summary, cites))
        appendices = appendix_md(summary, cites)
        refs_md, by_key = build_references(cites, summary)
        front = front_matter_md(sdir)
        (GEN / "front_matter.md").write_text(front, encoding="utf-8")
        (GEN / "references.md").write_text(refs_md, encoding="utf-8")
        (GEN / "appendices.md").write_text(appendices, encoding="utf-8")
        scan_text = "\n".join(parts) + refs_md
        check_intext("\n".join(parts), [by_key[k] for k in cites if k in by_key], summary)
        full = front + "\n" + "\n\n".join(parts) + "\n\n" + refs_md + "\n" + appendices
        full_md = GEN / "report_full.md"
        full_md.write_text(full, encoding="utf-8")
        docx = odir / f"{a.name}.docx"
        pdf = odir / f"{a.name}.pdf"
        cmd = ["pandoc", str(full_md), "-f", "markdown+tex_math_dollars+pipe_tables+raw_attribute+fenced_divs+bracketed_spans-implicit_figures",
               "-t", "docx", "--wrap=none", "--syntax-highlighting=none", f"--reference-doc={REFERENCE_DOCX}",
               f"--resource-path={ROOT}{';'}{HERE}{';'}{GEN}", "-o", str(docx)]
        log("pandoc: " + " ".join(f'"{c}"' if " " in c else c for c in cmd))
        pr = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        if pr.stderr.strip():
            log("pandoc stderr: " + pr.stderr.strip()[:3000])
        if pr.returncode != 0:
            log("BUILD FAILED: pandoc")
            return 1
        postprocess_docx(docx)
        log(f"docx written: {docx}")
        if not a.no_pdf:
            export_pdf(docx, pdf)
            log(f"pdf written: {pdf}")
        rc = quality(docx, None if a.no_pdf else pdf, summary, scan_text, not a.no_fail_on_todo)
        summary["exit_code"] = rc
        (GEN / "build_log.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        (GEN / "build_log.txt").write_text("\n".join(LOG), encoding="utf-8")
        return rc
    except Exception as e:  # noqa: BLE001
        import traceback
        log("BUILD FAILED: " + repr(e))
        log(traceback.format_exc())
        summary["exit_code"] = 1
        (GEN / "build_log.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        return 1


if __name__ == "__main__":
    sys.exit(main())



