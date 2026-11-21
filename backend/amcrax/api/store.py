"""JSON results store: results/simulations/<case_id>.json validated as SimulationResult.

Aspen results (source == aspen_plus_v15) are never rewritten or deleted through the API.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Optional

from amcrax import paths
from amcrax.schemas import DataSource, SimulationResult

from .errors import ApiError

_ID_RE = re.compile(r"[A-Za-z0-9_\-]{1,64}")
_lock = threading.Lock()


def sim_dir() -> Path:
    return paths.RESULTS_SIMULATIONS


def check_id(case_id: str) -> str:
    if not isinstance(case_id, str) or not _ID_RE.fullmatch(case_id):
        raise ApiError(422, "invalid_case_id", "case_id must match ^[A-Za-z0-9_-]{1,64}$ (letters, digits, '_' and '-')",
                       {"case_id": case_id if isinstance(case_id, str) else None})
    return case_id


def _path(case_id: str) -> Path:
    base = sim_dir().resolve()
    p = (base / f"{check_id(case_id)}.json").resolve()
    if p.parent != base:  # defence in depth: the derived file must sit directly in the results folder
        raise ApiError(422, "invalid_case_id", "case_id resolves outside the results folder", {"case_id": case_id})
    return p


def is_protected(r: SimulationResult) -> bool:
    """Aspen results with data are protected; an Aspen record without streams (failed/rejected run) is not."""
    return r.source == DataSource.ASPEN and bool(r.streams)


def _load_file(p: Path) -> SimulationResult:
    return SimulationResult.model_validate_json(p.read_text(encoding="utf-8"))


_CACHE: dict[str, tuple[int, int, Optional[dict]]] = {}


def _summary(p: Path) -> Optional[dict]:
    """Case summary for ``p`` or None if the file is not a valid SimulationResult (cached by mtime+size)."""
    try:
        st = p.stat()
    except OSError:
        return None
    key = str(p)
    hit = _CACHE.get(key)
    if hit and hit[0] == st.st_mtime_ns and hit[1] == st.st_size:
        return hit[2]
    try:
        r = _load_file(p)
        s: Optional[dict] = {
            "case_id": r.case_id, "valid": True, "source": r.source.value, "created_utc": r.created_utc,
            "converged": r.status.converged, "deletable": not is_protected(r),
            "file": p.name, "inputs": r.inputs.model_dump(), "kpis": r.kpis.model_dump(),
        }
    except Exception:  # noqa: BLE001
        s = None
    _CACHE[key] = (st.st_mtime_ns, st.st_size, s)
    return s


def list_cases() -> list[dict]:
    """Summaries of the stored files that validate as SimulationResult. Other JSON files in the
    directory (analysis outputs) are not cases: see :func:`non_case_files`."""
    d = sim_dir()
    if not d.exists():
        return []
    out = []
    for p in sorted(d.glob("*.json")):
        s = _summary(p)
        if s is not None:
            out.append(s)
    return out


def non_case_files() -> list[Path]:
    d = sim_dir()
    return [p for p in sorted(d.glob("*.json")) if _summary(p) is None] if d.exists() else []


def count_cases() -> dict:
    cs = list_cases()
    by: dict[str, int] = {}
    for c in cs:
        by[c["source"]] = by.get(c["source"], 0) + 1
    return {"total": len(cs), "by_source": by, "analysis_files": len(non_case_files())}

def get(case_id: str) -> SimulationResult:
    p = _path(case_id)
    if not p.exists():
        raise ApiError(404, "case_not_found", f"No stored case '{case_id}'", {"case_id": case_id})
    try:
        return _load_file(p)
    except Exception as e:
        raise ApiError(404, "case_not_found", f"'{case_id}.json' exists but is not a SimulationResult (analysis output? see /api/data/analysis/{case_id})", {"error": str(e)[:300]})


def exists(case_id: str) -> bool:
    return _path(case_id).exists()


def _atomic_write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, p)


def save_new(result: SimulationResult) -> SimulationResult:
    """Save a result without ever overwriting an Aspen result.

    If the id is taken by an Aspen result, the new result is stored under a suffixed id
    (``<id>_py`` / ``<id>_run<epoch>``); user results may overwrite earlier user results.
    """
    with _lock:
        cid = check_id(result.case_id)
        p = _path(cid)
        if p.exists():
            try:
                protected = is_protected(_load_file(p))
            except Exception:
                protected = True  # unreadable: be conservative, do not clobber
            if protected:
                suffix = "_py" if result.source == DataSource.PYTHON else f"_run{int(time.time())}"
                cid = f"{cid}{suffix}"
                if _path(cid).exists():
                    cid = f"{cid}{int(time.time())}"
                cid = cid[:64]
                result = result.model_copy(update={"case_id": cid})
                result.notes.append(f"Stored under '{cid}' to avoid overwriting an existing Aspen result.")
        _atomic_write(_path(result.case_id), result.model_dump_json(indent=2))
        return result


def delete(case_id: str) -> None:
    with _lock:
        r = get(case_id)
        if is_protected(r):
            raise ApiError(403, "protected_case", "Aspen Plus results cannot be deleted through the API", {"case_id": case_id})
        _path(case_id).unlink()


def load_json_dir(d: Path, pattern: str = "*.json") -> list[tuple[str, dict]]:
    out = []
    if d.exists():
        for p in sorted(d.glob(pattern)):
            try:
                out.append((p.name, json.loads(p.read_text(encoding="utf-8"))))
            except Exception:
                continue
    return out

