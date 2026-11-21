"""Generic read-only data endpoints over the results directories.

GET /api/data/{category}          list the files of a category
GET /api/data/{category}/{name}   one file (name with extension, e.g. pareto.csv, or bare stem: JSON preferred over CSV): CSV -> {name, category, columns, rows, source_note}; JSON as stored

Categories: sensitivity (results/sensitivity/*.csv), validation (results/validation/*.csv|json),
optimisation (results/optimisation/*.csv|json), analysis (JSON files in results/simulations that are
not SimulationResult cases, e.g. heat_integration_*.json).
"""
from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

from amcrax import paths

from .. import store
from ..errors import ApiError, jsonable

router = APIRouter(prefix="/api")

CATEGORIES = ("sensitivity", "validation", "optimisation", "analysis")
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,150}$")


def _files(category: str) -> list[Path]:
    if category == "sensitivity":
        d, pats = paths.RESULTS_SENSITIVITY, ("*.csv",)
    elif category == "validation":
        d, pats = paths.RESULTS_VALIDATION, ("*.csv", "*.json")
    elif category == "optimisation":
        d, pats = paths.RESULTS_OPTIMISATION, ("*.csv", "*.json")
    elif category == "analysis":
        return store.non_case_files()
    else:
        raise ApiError(404, "data_not_found", f"Unknown data category '{category}'", {"categories": list(CATEGORIES)})
    if not d.exists():
        return []
    return sorted(p for pat in pats for p in d.glob(pat) if p.is_file())


def _num(x):
    if x is None or x == "":
        return None
    try:
        f = float(x)
    except ValueError:
        return x
    return f if f == f and abs(f) != float("inf") else None


def _read_csv(p: Path) -> tuple[list[str], list[dict]]:
    with p.open(newline="", encoding="utf-8-sig") as f:
        rd = csv.DictReader(f)
        rows = [{k: _num(v) for k, v in r.items()} for r in rd]
        return list(rd.fieldnames or []), rows


def _rel(p: Path) -> str:
    try:
        return p.relative_to(paths.ROOT).as_posix()
    except ValueError:
        return p.name


def _item(p: Path) -> dict:
    st = p.stat()
    d = {"name": p.stem, "file": p.name, "name_with_extension": p.name, "kind": p.suffix.lstrip("."), "bytes": st.st_size,
         "modified_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds")}
    if p.suffix == ".csv":
        try:
            cols, rows = _read_csv(p)
            d.update(columns=cols, rows=len(rows))
        except Exception as e:  # noqa: BLE001
            d["error"] = str(e)[:200]
    return d


def _resolve(category: str, name: str) -> Path:
    if not _NAME_RE.match(name) or ".." in name:
        raise ApiError(404, "data_not_found", f"No data '{name}' in category '{category}'", {"name": name})
    files = _files(category)
    for p in files:  # exact file name (with extension) first
        if p.name == name:
            return p
    same = [p for p in files if p.stem == name]  # bare stem: JSON preferred over CSV
    same.sort(key=lambda p: (p.suffix != ".json", p.suffix))
    if same:
        return same[0]
    raise ApiError(404, "data_not_found", f"No data '{name}' in category '{category}'", {"category": category, "name": name})


@router.get("/data/{category}")
def list_data(category: str):
    items = [_item(p) for p in _files(category)]
    return {"category": category, "count": len(items), "items": items}


@router.get("/data/{category}/{name}")
def get_data(category: str, name: str):
    p = _resolve(category, name)
    if p.suffix == ".csv":
        cols, rows = _read_csv(p)
        srcs = sorted({str(r["source"]) for r in rows if isinstance(r.get("source"), str)}) if "source" in cols else []
        note = f"{_rel(p)}; values as stored, no post-processing"
        if srcs:
            note += f"; source column: {', '.join(srcs)}"
        return {"name": p.stem, "category": category, "columns": cols, "rows": rows, "count": len(rows), "source_note": note}
    try:
        return jsonable(json.loads(p.read_text(encoding="utf-8-sig")))
    except Exception as e:  # noqa: BLE001
        raise ApiError(500, "data_unreadable", f"{p.name} is not valid JSON: {str(e)[:200]}")
