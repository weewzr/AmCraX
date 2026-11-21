"""Health, flowsheet, stored cases, export."""
from __future__ import annotations

import csv
import importlib.metadata as md
import importlib.util
import io
import json
import platform
import sys
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, Response

from amcrax import paths

from .. import jobs, store
from ..errors import ApiError, jsonable

router = APIRouter(prefix="/api")

OPTIONAL_MODULES = ["thermodynamics", "process_model", "kinetics", "reactor", "heat_integration",
                    "economics", "environmental", "separation", "optimisation", "scenarios", "aspen"]


def _ver(pkg: str):
    try:
        return md.version(pkg)
    except Exception:  # noqa: BLE001
        return None


_MOD_CACHE: dict[str, tuple[float, bool, "str | None"]] = {}
_RETRY_FAILED_S = 20.0


def _module_state(mod: str) -> "tuple[bool, str | None]":
    """Real import attempt. Successes are cached for the process lifetime, failures retried after 20 s."""
    import importlib
    import time

    hit = _MOD_CACHE.get(mod)
    if hit and (hit[1] or time.monotonic() - hit[0] < _RETRY_FAILED_S):
        return hit[1], hit[2]
    try:
        importlib.import_module(f"amcrax.{mod}")
        ok, err = True, None
    except Exception as e:  # noqa: BLE001
        ok, err = False, f"{type(e).__name__}: {str(e)[:160]}"
    _MOD_CACHE[mod] = (time.monotonic(), ok, err)
    return ok, err


def _present(mod: str) -> bool:
    return _module_state(mod)[0]


@router.get("/health")
def health():
    reason = jobs.aspen_unavailable_reason()
    return {
        "status": "ok",
        "time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "versions": {"python": platform.python_version(), "fastapi": _ver("fastapi"),
                     "pydantic": _ver("pydantic"), "uvicorn": _ver("uvicorn"), "amcrax": _ver("amcrax"),
                     "platform": platform.platform()},
        "aspen": {"progid": jobs.PROGID, "com_registered": jobs.aspen_progid_registered(),
                  "worker_module_present": jobs.worker_module_present(),
                  "available": reason is None, "reason": reason, "timeout_s": jobs.ASPEN_TIMEOUT_S},
        "modules": {m: _present(m) for m in OPTIONAL_MODULES},
        "module_errors": {m: _module_state(m)[1] for m in OPTIONAL_MODULES if _module_state(m)[1]},
        "cases": store.count_cases(),
    }


@router.get("/flowsheet")
def flowsheet():
    p = paths.CONFIG_DIR / "flowsheet.json"
    if not p.exists():
        raise ApiError(404, "flowsheet_not_found", "config/flowsheet.json is missing")
    return JSONResponse(json.loads(p.read_text(encoding="utf-8")))


@router.get("/cases")
def cases():
    cs = store.list_cases()
    return {"count": len(cs), "cases": cs}


@router.get("/cases/{case_id}")
def case(case_id: str):
    return store.get(case_id).model_dump(mode="json")


@router.get("/cases/{case_id}/streams")
def case_streams(case_id: str):
    r = store.get(case_id)
    return {"case_id": r.case_id, "source": r.source.value, "streams": jsonable(r.streams)}


@router.get("/cases/{case_id}/blocks")
def case_blocks(case_id: str):
    r = store.get(case_id)
    return {"case_id": r.case_id, "source": r.source.value, "blocks": jsonable(r.blocks)}


@router.get("/cases/{case_id}/kpis")
def case_kpis(case_id: str):
    r = store.get(case_id)
    return {"case_id": r.case_id, "source": r.source.value, "kpis": r.kpis.model_dump(), "balances": r.balances.model_dump(),
            "status": r.status.model_dump()}


@router.delete("/cases/{case_id}")
def delete_case(case_id: str):
    store.delete(case_id)
    return {"deleted": case_id}


# ------------------------------------------------------------------ export
def stream_rows(r) -> list[dict]:
    rows = []
    for s in r.streams.values():
        d = {k: v for k, v in s.model_dump().items() if not isinstance(v, dict)}
        for c, v in s.mole_frac.items():
            d[f"y_{c}"] = v
        for c, v in s.component_mole_flow_kmol_h.items():
            d[f"n_{c}_kmol_h"] = v
        rows.append(d)
    return rows


def block_rows(r) -> list[dict]:
    rows = []
    for b in r.blocks.values():
        d = {k: v for k, v in b.model_dump().items() if k != "details"}
        for k, v in b.details.items():
            d[f"detail_{k}"] = v
        rows.append(d)
    return rows


def kpi_rows(r) -> list[dict]:
    return [{"kpi": k, "value": v, "source": r.source.value} for k, v in r.kpis.model_dump().items()]


def _csv_text(rows: list[dict]) -> str:
    if not rows:
        return ""
    cols: list[str] = []
    for row in rows:
        for k in row:
            if k not in cols:
                cols.append(k)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


@router.get("/export/{case_id}")
def export(case_id: str, format: str = Query("json", pattern="^(json|csv|xlsx)$")):
    r = store.get(case_id)
    fname = f"amcrax_{r.case_id}"
    if format == "json":
        return Response(r.model_dump_json(indent=2), media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{fname}.json"'})
    if format == "csv":
        text = ("# streams\n" + _csv_text(stream_rows(r)) + "\n# blocks\n" + _csv_text(block_rows(r))
                + "\n# kpis\n" + _csv_text(kpi_rows(r)))
        return Response(text, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{fname}.csv"'})
    from openpyxl import Workbook

    wb = Workbook()
    wb.remove(wb.active)
    for title, rows in (("Streams", stream_rows(r)), ("Blocks", block_rows(r)), ("KPIs", kpi_rows(r)),
                        ("Inputs", [{"input": k, "value": v} for k, v in r.inputs.model_dump().items()]),
                        ("Info", [{"item": "case_id", "value": r.case_id}, {"item": "source", "value": r.source.value},
                                  {"item": "created_utc", "value": r.created_utc}, {"item": "converged", "value": r.status.converged}])):
        ws = wb.create_sheet(title)
        cols: list[str] = []
        for row in rows:
            for k in row:
                if k not in cols:
                    cols.append(k)
        ws.append(cols)
        for row in rows:
            ws.append([row.get(c) if isinstance(row.get(c), (int, float, str, bool, type(None))) else str(row.get(c)) for c in cols])
    bio = io.BytesIO()
    wb.save(bio)
    return Response(bio.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{fname}.xlsx"'})
