#!/usr/bin/env python
r"""Build the AmCraX research paper and executive summary (DOCX and PDF).

Usage (from any directory):
    . "<root>\scripts\env.ps1"; python "<root>\docs\paper\build_paper.py" [--docx-only]

Inputs:  docs/paper/amcrax_paper.md, docs/executive_summary.md
Style:   docs/technical_report/reference.docx (read only; the same reference style as the technical report)
Outputs: docs/paper/build/AmCraX_Paper.docx|pdf, docs/paper/build/AmCraX_Executive_Summary.docx|pdf,
         docs/paper/build/build_log.json

Pipeline: privacy scan of the sources -> pandoc to DOCX -> python-docx post-processing (page size, header,
footer, table and caption formatting, bibliography style) -> Word automation to PDF in its OWN Word instance
(never an existing one) -> privacy scan of the outputs -> page and figure counts.
Exit code: 0 success, 1 tool failure, 3 privacy scan hit.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import getpass
import json
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BUILD = HERE / "build"
REFERENCE_DOCX = ROOT / "docs" / "technical_report" / "reference.docx"

DOCS = [
    # (source markdown, output base name, running header)
    (HERE / "amcrax_paper.md", "AmCraX_Paper", "AmCraX - Research paper"),
    (ROOT / "docs" / "executive_summary.md", "AmCraX_Executive_Summary", "AmCraX - Executive summary"),
]

PRIMARY = "0369a1"
INK = "121a2f"
MUTED = "5b6478"
FONT = "Calibri"

LOG: list[str] = []


def _redact(msg: str) -> str:
    """Logs are written next to public outputs: replace the repository root and the home folder."""
    for p, rep in ((str(ROOT), "<root>"), (str(Path.home()), "<home>")):
        msg = msg.replace(p, rep).replace(p.replace("\\", "/"), rep)
    return msg


def log(msg: str = "") -> None:
    msg = _redact(msg)
    print(msg, flush=True)
    LOG.append(msg)


# ----------------------------------------------------------------------------------------------
# privacy scan: personal paths, e-mail addresses, identifier-like tokens, and the user and host
# names of the machine that runs the build (read at run time, never stored in this file)
# ----------------------------------------------------------------------------------------------
def privacy_patterns() -> list[tuple[str, re.Pattern]]:
    pats = [
        ("windows user path", re.compile(r"[A-Za-z]:\\Users\\", re.I)),
        ("posix home path", re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+/")),
        ("e-mail address", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
        ("student-number-like token", re.compile(r"\b[AaEe]\d{7}[A-Za-z]?\b")),
    ]
    # Optional extra patterns, one regular expression per line, kept outside version control.
    extra = ROOT / "docs" / "internal" / "privacy_patterns.txt"
    if extra.exists():
        for line in extra.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                pats.append(("local pattern", re.compile(line.strip(), re.I)))
    for label, val in (("user name", _safe(getpass.getuser)), ("host name", _safe(socket.gethostname))):
        if val and len(val) >= 3:
            pats.append((label, re.compile(re.escape(val), re.I)))
    return pats


def _safe(fn):
    try:
        return fn()
    except Exception:  # noqa: BLE001
        return ""


def privacy_scan(text: str, where: str) -> list[str]:
    hits = []
    for label, pat in privacy_patterns():
        for m in pat.finditer(text):
            hits.append(f"{where}: {label} at offset {m.start()}")
    return hits


def docx_text(path: Path) -> str:
    from docx import Document
    d = Document(str(path))
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            parts += [c.text for c in row.cells]
    for s in d.sections:
        parts += [p.text for p in s.header.paragraphs] + [p.text for p in s.footer.paragraphs]
    cp = d.core_properties
    parts += [cp.author or "", cp.last_modified_by or "", cp.title or "", cp.subject or ""]
    return "\n".join(parts)


def pdf_text(path: Path) -> str:
    import pymupdf
    with pymupdf.open(str(path)) as pd:
        meta = " ".join(str(v) for v in (pd.metadata or {}).values() if v)
        return meta + "\n" + "\n".join(pd[i].get_text() for i in range(pd.page_count))


# ----------------------------------------------------------------------------------------------
# markdown pre-processing: the References section becomes the Bibliography paragraph style
# ----------------------------------------------------------------------------------------------
def preprocess(md: str) -> str:
    m = re.search(r"^# References[ \t]*$", md, re.M)
    if not m:
        return md
    head, refs = md[: m.end()], md[m.end():]
    entries = [e.strip() for e in re.split(r"\n\s*\n", refs) if e.strip()]
    body = "\n\n".join(f'::: {{custom-style="Bibliography"}}\n{e}\n:::' for e in entries)
    return head + "\n\n" + body + "\n"


# ----------------------------------------------------------------------------------------------
# docx post-processing
# ----------------------------------------------------------------------------------------------
def _rgb(h: str):
    from docx.shared import RGBColor
    return RGBColor.from_string(h.upper())


def _page_field(par):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt

    def run_with(child):
        r = par.add_run()
        r.font.size = Pt(9)
        r.font.color.rgb = _rgb(MUTED)
        r._r.append(child)
    b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "begin"); run_with(b)
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = " PAGE "; run_with(it)
    s = OxmlElement("w:fldChar"); s.set(qn("w:fldCharType"), "separate"); run_with(s)
    t = OxmlElement("w:t"); t.text = "1"; run_with(t)
    e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end"); run_with(e)


def postprocess(path: Path, header: str, title: str) -> None:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Emu, Pt

    doc = Document(str(path))
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Cm(2.2)
    sec.header_distance = sec.footer_distance = Cm(1.1)
    text_w = sec.page_width - sec.left_margin - sec.right_margin

    hp = sec.header.paragraphs[0]
    hp.text = ""
    r = hp.add_run(header)
    r.font.size = Pt(9); r.font.color.rgb = _rgb(MUTED); r.font.name = FONT
    fp = sec.footer.paragraphs[0]
    fp.text = ""
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run("Page "); r.font.size = Pt(9); r.font.color.rgb = _rgb(MUTED)
    _page_field(fp)

    # sections flow continuously; the reference style starts every Heading 1 on a new page
    for name in ("Heading 1",):
        try:
            st = doc.styles[name]
            st.paragraph_format.page_break_before = False
            st.paragraph_format.space_before = Pt(18)
        except KeyError:
            pass
    try:
        t = doc.styles["Title"]
        t.font.size = Pt(20)
    except KeyError:
        pass

    for p in doc.paragraphs:
        sn = p.style.name if p.style is not None else ""
        if sn in ("Table Caption", "Image Caption", "Caption"):
            p.paragraph_format.keep_together = True
            nxt = p._p.getnext()
            if nxt is not None and nxt.tag == qn("w:tbl"):
                p.paragraph_format.keep_with_next = True
        if p._p.findall(".//" + qn("w:drawing")):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_with_next = True
    max_h = Cm(17)
    for sh in doc.inline_shapes:
        w, h = sh.width, sh.height
        f = min(1.0, text_w / w, max_h / h)
        if f < 1.0:
            sh.width, sh.height = Emu(int(w * f)), Emu(int(h * f))

    def shade(cell, fill):
        tcpr = cell._tc.get_or_add_tcPr()
        for old in tcpr.findall(qn("w:shd")):
            tcpr.remove(old)
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), fill)
        tcpr.append(shd)

    for tbl in doc.tables:
        tblpr = tbl._tbl.tblPr
        for tag in ("w:tblW", "w:tblBorders"):
            for old in tblpr.findall(qn(tag)):
                tblpr.remove(old)
        w = OxmlElement("w:tblW"); w.set(qn("w:type"), "pct"); w.set(qn("w:w"), "5000"); tblpr.append(w)
        bd = OxmlElement("w:tblBorders")
        for side, col, sz in (("top", PRIMARY, 8), ("bottom", PRIMARY, 8), ("insideH", "cfd6e4", 4)):
            e = OxmlElement(f"w:{side}")
            e.set(qn("w:val"), "single"); e.set(qn("w:sz"), str(sz)); e.set(qn("w:space"), "0"); e.set(qn("w:color"), col)
            bd.append(e)
        tblpr.append(bd)
        n = len(tbl.rows)
        for ri, row in enumerate(tbl.rows):
            trpr = row._tr.get_or_add_trPr()
            trpr.append(OxmlElement("w:cantSplit"))
            if ri == 0:
                trpr.append(OxmlElement("w:tblHeader"))
            for cell in row.cells:
                if ri == 0:
                    shade(cell, PRIMARY)
                elif ri % 2 == 0:
                    shade(cell, "f1f5f9")
                for par in cell.paragraphs:
                    par.paragraph_format.space_before = Pt(1)
                    par.paragraph_format.space_after = Pt(1)
                    if ri < n - 1 and n <= 20:
                        par.paragraph_format.keep_with_next = True
                    for run in par.runs:
                        run.font.size = Pt(9)
                        if ri == 0:
                            run.font.bold = True
                            run.font.color.rgb = _rgb("ffffff")
    cp = doc.core_properties
    cp.title = title
    cp.author = "AmCraX project"
    cp.last_modified_by = "AmCraX project"
    cp.comments = ""
    doc.save(str(path))


# ----------------------------------------------------------------------------------------------
# Word export in its own instance; an existing Word process is never touched
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
        app = win32com.client.DispatchEx("Word.Application")  # new instance, not GetActiveObject
        app.Visible = False
        app.DisplayAlerts = 0
        try:
            pid = win32process.GetWindowThreadProcessId(app.Hwnd)[1]
        except Exception:  # noqa: BLE001
            pid = None
        doc = app.Documents.Open(str(docx), False, False, False)
        try:
            doc.Repaginate()
            doc.Fields.Update()
            for s in doc.Sections:
                for hf in list(s.Headers) + list(s.Footers):
                    hf.Range.Fields.Update()
            if pdf.exists():
                pdf.unlink()
            doc.ExportAsFixedFormat(str(pdf), 17, False, 0, 0, 1, 1, 0, True, True, 1, True, True, False)
        finally:
            doc.Close(0)
    finally:
        try:
            if app is not None:
                app.Quit(0)
        except Exception:  # noqa: BLE001
            pass
        app = None
        pythoncom.CoUninitialize()
        if pid:
            time.sleep(1.5)
            if _pid_alive(pid):  # only the pid of the instance started here
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
                log(f"WARNING: Word instance pid {pid} started by this build had to be stopped")


# ----------------------------------------------------------------------------------------------
def build_one(src: Path, name: str, header: str, docx_only: bool, summary: dict) -> int:
    info: dict = {"source": src.relative_to(ROOT).as_posix()}
    summary["documents"].append(info)
    md = src.read_text(encoding="utf-8-sig")
    hits = privacy_scan(md, src.name)
    if hits:
        info["privacy_hits"] = hits
        for h in hits:
            log("PRIVACY " + h)
        return 3
    info["words_markdown_body"] = len(re.sub(r"^---.*?---", "", md, flags=re.S).split())
    m = re.search(r'^title:\s*"?(.*?)"?\s*$', md, re.M)
    title = m.group(1) if m else name
    tmp = BUILD / f"{name}.pre.md"
    tmp.write_text(preprocess(md), encoding="utf-8")
    docx = BUILD / f"{name}.docx"
    pdf = BUILD / f"{name}.pdf"
    cmd = ["pandoc", str(tmp), "-f",
           "markdown+tex_math_dollars+pipe_tables+fenced_divs+bracketed_spans+implicit_figures+superscript+subscript",
           "-t", "docx", "--wrap=none", f"--reference-doc={REFERENCE_DOCX}",
           f"--resource-path={src.parent};{ROOT};{HERE}", "-o", str(docx)]
    log("pandoc: " + " ".join(f'"{c}"' if " " in c else c for c in cmd))
    pr = subprocess.run(cmd, cwd=str(src.parent), capture_output=True, text=True)
    if pr.stderr.strip():
        log("pandoc stderr: " + pr.stderr.strip()[:3000])
        info["pandoc_stderr"] = pr.stderr.strip()[:3000]
    if pr.returncode != 0:
        log("BUILD FAILED: pandoc")
        return 1
    tmp.unlink(missing_ok=True)
    postprocess(docx, header, title)
    from docx import Document
    d = Document(str(docx))
    info["figures"] = len(d.inline_shapes)
    info["tables"] = len(d.tables)
    log(f"docx written: {docx.relative_to(ROOT).as_posix()} ({info['figures']} figures, {info['tables']} tables)")
    hits = privacy_scan(docx_text(docx), docx.name)
    if not docx_only:
        export_pdf(docx, pdf)
        import pymupdf
        with pymupdf.open(str(pdf)) as pd:
            info["pdf_pages"] = pd.page_count
        log(f"pdf written: {pdf.relative_to(ROOT).as_posix()} ({info['pdf_pages']} pages)")
        hits += privacy_scan(pdf_text(pdf), pdf.name)
    if hits:
        info["privacy_hits"] = hits
        for h in hits:
            log("PRIVACY " + h)
        return 3
    info["privacy_scan"] = "clean"
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx-only", action="store_true", help="skip the Word automation (no PDF)")
    a = ap.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    if not REFERENCE_DOCX.exists():
        log(f"BUILD FAILED: reference style not found: {REFERENCE_DOCX.relative_to(ROOT).as_posix()}")
        return 1
    summary = {"build_time": _dt.datetime.now().isoformat(timespec="seconds"), "docx_only": a.docx_only, "documents": []}
    rc = 0
    try:
        for src, name, header in DOCS:
            rc = max(rc, build_one(src, name, header, a.docx_only, summary))
    except Exception as e:  # noqa: BLE001
        import traceback
        log("BUILD FAILED: " + repr(e))
        log(traceback.format_exc())
        rc = 1
    summary["exit_code"] = rc
    summary["log"] = LOG
    (BUILD / "build_log.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return rc


if __name__ == "__main__":
    sys.exit(main())
