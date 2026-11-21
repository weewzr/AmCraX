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

REPORT_DATE = "21 November 2026"
SUBTITLE = "Ammonia Cracking Simulation and Optimisation Platform"
SCOPE_LINE = ("Aspen Plus V15 flowsheet model of ammonia cracking for hydrogen production, its Python automation, "
              "independent Python models, validation, sensitivity, energy, techno-economic and environmental assessment.")

# AmCraX light-theme colours (docs/reference_projects/design_tokens.md)
PRIMARY = "0369a1"
ACCENT = "c2410c"
INK = "121a2f"
MUTED = "5b6478"
FONT = "Calibri"

EXPECTED = {
    1: ("01_executive_summary.md", "Executive summary"),
    2: ("02_introduction.md", "Introduction and motivation"),
    3: ("03_ammonia_carrier.md", "Ammonia as a hydrogen carrier"),
    4: ("04_fundamentals.md", "Ammonia-cracking fundamentals"),
    5: ("05_literature_review.md", "Literature review"),
    6: ("06_process_design.md", "Overall process design"),
    7: ("07_aspen_methodology.md", "Aspen Plus simulation methodology"),
    8: ("08_components.md", "Component selection"),
    9: ("09_property_methods.md", "Thermodynamic property methods"),
    10: ("10_reactor.md", "Reactor configuration"),
    11: ("11_heat_exchangers.md", "Heat exchangers and process integration"),
    12: ("12_separation.md", "Separation and purification"),
    13: ("13_automation.md", "Python-Aspen automation"),
    14: ("14_validation.md", "Model validation"),
    15: ("15_sensitivity.md", "Sensitivity analysis"),
    16: ("16_energy_efficiency.md", "Energy efficiency"),
    17: ("17_techno_economics.md", "Techno-economic assessment"),
    18: ("18_optimisation.md", "Process optimisation"),
    19: ("19_environment.md", "Environmental implications"),
    20: ("20_limitations.md", "Limitations and future work"),
    21: ("21_conclusion.md", "Conclusion"),
}

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
    s = get("Compact")
    _set_font(s, size=9, color=INK)
    s.paragraph_format.space_before = Pt(1)
    s.paragraph_format.space_after = Pt(1)

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
    missing = [f"{n:02d} {t} ({f})" for n, (f, t) in EXPECTED.items() if f not in found] if sdir.resolve() == (HERE / "sections").resolve() or True else []
    # only expected-file check is meaningful for the real section folder
    summary["missing_sections"] = [m for m in missing]
    for m in missing:
        log(f"WARNING missing section: {m}")
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


def process_section(name: str, path: Path, summary: dict, cites: set[str]) -> str:
    text = path.read_text(encoding="utf-8-sig")
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
        if found is None:
            summary["dropped_figures"].append({"section": name, "path": ptxt.strip(), "caption": alt[:120]})
            log(f"DROPPED FIGURE ({name}): {ptxt.strip()}")
            return ""
        summary["figures_inserted"] += 1
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
    lines = ["# 22 References", ""]
    for r in used:
        body, url = italicise_apa(r["apa7"])
        url = url or r.get("url") or ""
        entry = body + ("\\\n<" + url + ">" if url else "")
        lines.append(f'::: {{custom-style="Bibliography"}}\n{entry}\n:::\n')
    if not used:
        lines.append("No cited references were found in the section files.")
    return "\n".join(lines) + "\n", by_key


def check_intext(all_text: str, cited_refs: list[dict], summary: dict) -> None:
    surnames = {}
    for r in cited_refs:
        m = re.match(r"^([^,]+),.*?\((\d{4}[a-z]?|n\.d\.)\)", r["apa7"])
        if m:
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
            if not cands:
                unresolved.add(m.group(0))
    summary["unresolved_intext"] = sorted(unresolved)
    for u in sorted(unresolved):
        log(f"WARNING in-text citation without listed reference: ({u})")


# ----------------------------------------------------------------------------------------------
# appendices
# ----------------------------------------------------------------------------------------------
def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def appendix_md(summary: dict, cites: set[str]) -> str:
    out = ["# 23 Appendices", "",
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
                pipe_table(["Stream", "T (degC)", "P (bar)", "Vapour fraction", "Molar flow (kmol/h)", "Mass flow (kg/h)"], rows1,
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
                pipe_table(["Block", "Type", "Duty (kW)", "Power (kW)", "Outlet T (degC)", "Key details"], rows, ["l", "l", "r", "r", "r", "l"])]
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
                out += [f"**Root cause `{rc.get('cause')}` ({rc.get('n_items')} items).** {rc.get('description')}", ""]
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
    out += [reproducibility_md(), ""]
    # G
    out += ["## G Aspen screenshot index", ""]
    mp = ROOT / "aspen" / "screenshots" / "manifest.json"
    if mp.exists():
        m = read_json(mp)
        caps = m.get("captures", [])
        rows = [[c.get("file"), c.get("title"), c.get("navigation_path"), c.get("status"),
                 c.get("reason_if_not") or c.get("what_is_shown") or ""] for c in caps]
        nc = [c for c in caps if c.get("status") != "captured"]
        out += [f"Screenshots of the real {m.get('aspen_version', 'Aspen Plus V15')} GUI, captured from `{m.get('model_file')}`. "
                f"{len(caps) - len(nc)} of {len(caps)} planned items are captured; items not captured are listed with the reason.", "",
                "Table: **Table G.1.** Aspen Plus V15 screenshot index. *Source: aspen/screenshots/manifest.json.*", "",
                pipe_table(["File", "Title", "Navigation path", "Status", "What is shown / reason if not captured"], rows)]
        summary["screenshots_not_captured"] = [c.get("file") for c in nc]
    else:
        out += ["aspen/screenshots/manifest.json is not available at build time.", ""]
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


def reproducibility_md() -> str:
    def demote(t: str) -> str:
        t = re.sub(r"^#+\s+(.*)$", r"#### \1", t, flags=re.M)
        return t
    rd = ROOT / "README.md"
    if rd.exists():
        s = _section_by_heading(rd.read_text(encoding="utf-8"), r"reproduc")
        if s:
            return "Source: README.md, section \"Reproducing\".\n\n" + demote(s)
    dg = ROOT / "docs" / "developer_guide.md"
    s = _section_by_heading(dg.read_text(encoding="utf-8"), r"toolchain")
    if s:
        return "Source: docs/developer_guide.md, section \"Toolchain\" (README.md has no \"Reproducing\" section at build time).\n\n" + demote(s)
    return "No reproducibility section was found in README.md or docs/developer_guide.md."


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
    # Sections flow continuously (a forced page break before each of the 23 top-level headings cost
    # about nine pages); only the first section, the references and the appendices start a new page.
    try:
        h1_style = doc.styles["Heading 1"]
        h1_style.paragraph_format.page_break_before = False
        h1_style.paragraph_format.space_before = Pt(26)
    except KeyError:
        pass
    # captions, images
    for p in doc.paragraphs:
        sn = p.style.name if p.style is not None else ""
        if sn == "Heading 1" and p.text.strip().startswith(("1 Executive", "22 References", "23 Appendices")):
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
        for ri, row in enumerate(tbl.rows):
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
    log(f"Missing citation keys: {summary['missing_citation_keys']}")
    log(f"Unresolved in-text   : {summary['unresolved_intext']}")
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



