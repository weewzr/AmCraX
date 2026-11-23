"""Deliverables: whitelisted read-only file downloads, Aspen screenshot manifest."""
from __future__ import annotations

import json
import mimetypes
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from amcrax import paths

from ..errors import ApiError

router = APIRouter()

# key -> (relative path from project root, title, kind)
WHITELIST: dict[str, tuple[str, str, str]] = {
    "technical_report_pdf": ("docs/technical_report/AmCraX_Technical_Report.pdf", "Technical report (PDF)", "report"),
    "technical_report_docx": ("docs/technical_report/AmCraX_Technical_Report.docx", "Technical report (Word)", "report"),
    "pitch_deck_pptx": ("docs/pitch_deck/AmCraX_Pitch_Deck.pptx", "Pitch deck (PowerPoint)", "deck"),
    "pitch_deck_pdf": ("docs/pitch_deck/AmCraX_Pitch_Deck.pdf", "Pitch deck (PDF)", "deck"),
    "speaker_script": ("docs/pitch_deck/speaker_script.md", "Pitch deck speaker script", "deck"),
    "validation_matrix": ("docs/validation/validation_matrix.md", "Validation matrix", "validation"),
    "discrepancy_analysis": ("docs/validation/discrepancy_analysis.md", "Discrepancy analysis", "validation"),
    "api_docs": ("docs/api.md", "API documentation", "docs"),
    "developer_guide": ("docs/developer_guide.md", "Developer guide", "docs"),
    "readme": ("README.md", "README", "docs"),
    "aspen_baseline_bkp": ("aspen/models/baseline.bkp", "Aspen Plus backup: baseline (.bkp)", "aspen_model"),
    "aspen_baseline_inp": ("aspen/models/baseline.inp", "Aspen Plus input: baseline (.inp)", "aspen_model"),
    "aspen_baseline_no_hi_bkp": ("aspen/models/baseline_no_hi.bkp", "Aspen Plus backup: no heat integration (.bkp)", "aspen_model"),
    "aspen_baseline_no_hi_inp": ("aspen/models/baseline_no_hi.inp", "Aspen Plus input: no heat integration (.inp)", "aspen_model"),
    "literature_summary": ("research/literature_summary.md", "Literature summary", "research"),
    "references_apa": ("research/references_apa.md", "References (APA)", "research"),
}


def _resolve(key: str) -> Path:
    if key not in WHITELIST:
        raise ApiError(404, "file_not_found", f"'{key}' is not a downloadable deliverable", {"keys": sorted(WHITELIST)})
    p = (paths.ROOT / WHITELIST[key][0]).resolve()
    if not p.is_file() or paths.ROOT.resolve() not in p.parents:
        raise ApiError(404, "file_not_found", f"Deliverable '{key}' does not exist yet", {"key": key})
    return p


@router.get("/api/reports")
def reports():
    items = []
    for key, (rel, title, kind) in WHITELIST.items():
        p = paths.ROOT / rel
        if p.is_file():
            st = p.stat()
            items.append({"key": key, "title": title, "kind": kind, "file": p.name, "path": rel, "bytes": st.st_size,
                          "modified_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds"),
                          "url": f"/files/{key}"})
    return {"count": len(items), "reports": items}


@router.get("/files/{key}")
def download(key: str):
    p = _resolve(key)
    mt = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    return FileResponse(p, media_type=mt, filename=p.name)


#: file pattern of the dashboard captures inside docs/screenshots (shared with scripts/export_snapshot.py)
DASHBOARD_SHOT_GLOB = "dashboard_*.png"


def _shots(base: Path, mount: str, pattern: str = "*.png") -> list[dict]:
    if not base.exists():
        return []
    meta: dict[str, dict] = {}
    mp = base / "manifest.json"
    if mp.exists():
        try:
            for c in json.loads(mp.read_text(encoding="utf-8-sig")).get("captures", []):
                meta[c.get("file")] = c
        except Exception:  # noqa: BLE001
            pass
    out = []
    for p in sorted(base.glob(pattern)):
        m = dict(meta.get(p.name, {}))
        m.update(file=p.name, url=f"{mount}/{p.name}", bytes=p.stat().st_size)
        out.append(m)
    return out


@router.get("/api/screenshots")
def screenshots():
    mp = paths.ASPEN_SCREENSHOTS / "manifest.json"
    head: dict = {}
    if mp.exists():
        try:
            d = json.loads(mp.read_text(encoding="utf-8-sig"))
            head = {k: v for k, v in d.items() if k != "captures"}
        except Exception:  # noqa: BLE001
            pass
    aspen = _shots(paths.ASPEN_SCREENSHOTS, "/aspen-screenshots")
    # only the dashboard captures belong in the gallery (docs/screenshots also holds public-site captures)
    dash = _shots(paths.DOCS_DIR / "screenshots", "/dashboard-screenshots", pattern=DASHBOARD_SHOT_GLOB)
    return {"aspen": aspen, "aspen_manifest": head, "dashboard": dash, "count": len(aspen) + len(dash),
            "source": "aspen: genuine Aspen Plus V15 GUI captures (aspen/screenshots); dashboard: AmCraX web UI captures (docs/screenshots)"}
