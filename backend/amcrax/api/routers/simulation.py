"""Simulation runs, jobs, sensitivity, scenario comparison."""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from amcrax import paths
from amcrax.schemas import CaseInputs, KPIs, SimulationResult

from .. import jobs, store
from ..errors import ApiError, jsonable

router = APIRouter(prefix="/api")

Engine = Literal["aspen", "python"]


class RunRequest(BaseModel):
    inputs: CaseInputs
    engine: Engine = "python"
    timeout_s: Optional[float] = Field(None, gt=0, le=7200, description="Aspen job wall-clock limit (default env AMCRAX_ASPEN_TIMEOUT_S, 600 s)")


@router.post("/simulation/run", status_code=202)
def run_simulation(req: RunRequest):
    jobs.check_inputs(req.inputs, req.engine)
    job = jobs.submit_case(req.inputs, req.engine, req.timeout_s)
    return JSONResponse(job.to_dict(), status_code=202, headers={"Location": f"/api/jobs/{job.id}"})


@router.get("/jobs")
def list_jobs():
    js = jobs.list_jobs()
    return {"count": len(js), "jobs": js}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    return jobs.get_job(job_id).to_dict()


# ------------------------------------------------------------------ sensitivity
SYNC_LIMIT = 200
_NUMERIC_FIELDS = {n for n, f in CaseInputs.model_fields.items()
                   if f.annotation in (float, int)}


class SensitivityRequest(BaseModel):
    variable: str
    values: list[float] = Field(..., min_length=1, max_length=2000)
    base_inputs: CaseInputs = Field(default_factory=CaseInputs)
    engine: Engine = "python"


@router.post("/sensitivity/run")
def run_sensitivity(req: SensitivityRequest):
    jobs.check_inputs(req.base_inputs)
    if req.variable not in _NUMERIC_FIELDS:
        raise ApiError(422, "invalid_variable", f"'{req.variable}' is not a numeric CaseInputs field",
                       {"allowed": sorted(_NUMERIC_FIELDS)})
    for v in req.values:  # validate every point up-front against the schema bounds
        try:
            CaseInputs.model_validate({**req.base_inputs.model_dump(), req.variable: v})
        except Exception as e:  # noqa: BLE001
            raise ApiError(422, "value_out_of_range", f"{req.variable}={v} violates CaseInputs bounds", {"error": str(e)[:400]})
    if req.engine == "aspen" or len(req.values) > SYNC_LIMIT:
        if req.engine == "python":
            jobs._require_process_model()
        job = jobs.submit_sensitivity(req.variable, req.values, req.base_inputs, req.engine)
        return JSONResponse(job.to_dict(), status_code=202, headers={"Location": f"/api/jobs/{job.id}"})
    jobs._require_process_model()
    rows = []
    for i, v in enumerate(req.values):
        inp = CaseInputs.model_validate({**req.base_inputs.model_dump(), req.variable: v, "case_id": jobs.sens_case_id(req.base_inputs.case_id, i)})
        try:
            rows.append(jobs.sensitivity_row(req.variable, v, jobs.run_python_case(inp)))
        except ApiError:
            raise
        except Exception as e:  # noqa: BLE001
            rows.append({req.variable: v, "converged": False, "error": f"{type(e).__name__}: {e}"[:300]})
    return {"variable": req.variable, "engine": "python", "source": "python_model", "count": len(rows), "rows": jsonable(rows)}


_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")


def _num(x: str):
    if x is None or x == "":
        return None
    try:
        f = float(x)
    except ValueError:
        return x
    return f if f == f and f not in (float("inf"), float("-inf")) else None


@router.get("/sensitivity/datasets")
def sensitivity_datasets():
    d = paths.RESULTS_SENSITIVITY
    out = []
    for p in sorted(d.glob("*.csv")) if d.exists() else []:
        try:
            with p.open(newline="", encoding="utf-8") as f:
                rd = csv.reader(f)
                header = next(rd, [])
                n = sum(1 for _ in rd)
        except Exception as e:  # noqa: BLE001
            out.append({"name": p.stem, "error": str(e)[:200]})
            continue
        meta = p.with_suffix(".json")
        out.append({"name": p.stem, "file": p.name, "columns": header, "rows": n, "size_bytes": p.stat().st_size,
                    "modified_utc": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
                    "has_metadata_json": meta.exists()})
    return {"count": len(out), "datasets": out}


@router.get("/sensitivity/datasets/{name}")
def sensitivity_dataset(name: str):
    if not _NAME_RE.match(name) or ".." in name:
        raise ApiError(422, "invalid_name", "Invalid dataset name")
    p = paths.RESULTS_SENSITIVITY / (name if name.endswith(".csv") else f"{name}.csv")
    if not p.exists():
        raise ApiError(404, "dataset_not_found", f"No sensitivity dataset '{name}'")
    with p.open(newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        rows = [{k: _num(v) for k, v in r.items()} for r in rd]
        cols = rd.fieldnames or []
    return {"name": p.stem, "columns": cols, "rows": rows, "count": len(rows)}


# ------------------------------------------------------------------ scenarios
class CompareRequest(BaseModel):
    case_ids: list[str] = Field(default_factory=list)
    inputs: list[CaseInputs] = Field(default_factory=list)
    engine: Engine = "python"


def _compare_table(results: list[SimulationResult]) -> dict:
    ids = [r.case_id for r in results]
    kp = [r.kpis.model_dump() for r in results]
    rows, diffs = [], []
    for k in KPIs.model_fields:
        vals = [d.get(k) for d in kp]
        rows.append({"kpi": k, "values": dict(zip(ids, vals))})
        base = vals[0]
        diffs.append({"kpi": k, "reference_case": ids[0],
                      "abs": {i: (None if v is None or base is None else v - base) for i, v in zip(ids, vals)},
                      "rel": {i: (None if v is None or base in (None, 0) else (v - base) / abs(base)) for i, v in zip(ids, vals)}})
    changed_inputs = []
    base_in = results[0].inputs.model_dump()
    for k in base_in:
        vals = [r.inputs.model_dump()[k] for r in results]
        if any(v != vals[0] for v in vals):
            changed_inputs.append({"input": k, "values": dict(zip(ids, vals))})
    columns = ["kpi"] + [c for i in ids for c in (i, f"delta_{i}", f"delta_rel_{i}")]
    flat = []
    for row, d in zip(rows, diffs):
        f = {"kpi": row["kpi"]}
        for i in ids:
            f[i], f[f"delta_{i}"], f[f"delta_rel_{i}"] = row["values"][i], d["abs"][i], d["rel"][i]
        flat.append(f)
    return {"cases": [{"case_id": r.case_id, "source": r.source.value, "converged": r.status.converged} for r in results],
            "reference_case": ids[0], "columns": columns, "table": flat,
            "kpi_table": rows, "differences": diffs, "changed_inputs": changed_inputs}


@router.post("/scenarios/compare")
def compare(req: CompareRequest):
    if len(req.case_ids) + len(req.inputs) < 2:
        raise ApiError(422, "too_few_cases", "Provide at least two case_ids and/or inline inputs")
    results = [store.get(c) for c in req.case_ids]
    if req.inputs:
        if req.engine == "aspen":
            raise ApiError(400, "inline_aspen_unsupported",
                           "Inline inputs with the aspen engine must be run as jobs (POST /api/simulation/run) and compared by case_id")
        for inp in req.inputs:
            jobs.check_inputs(inp)
        jobs._require_process_model()
        for inp in req.inputs:
            results.append(jobs.run_python_case(inp))
    return jsonable(_compare_table(results))


@router.get("/scenarios/definitions")
def scenario_definitions():
    p = paths.CONFIG_DIR / "scenarios.json"
    if not p.exists():
        raise ApiError(404, "data_not_found", "config/scenarios.json is missing")
    import json

    return JSONResponse(json.loads(p.read_text(encoding="utf-8")))


@router.get("/scenarios/export")
def scenarios_export(case_ids: str = Query(..., description="comma separated"), format: str = Query("csv", pattern="^csv$")):
    ids = [c.strip() for c in case_ids.split(",") if c.strip()]
    if len(ids) < 1:
        raise ApiError(422, "no_cases", "case_ids is empty")
    results = [store.get(c) for c in ids]
    t = _compare_table(results)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["kpi"] + ids)
    for row in t["kpi_table"]:
        w.writerow([row["kpi"]] + [row["values"][i] for i in ids])
    w.writerow([])
    w.writerow(["source"] + [r.source.value for r in results])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="amcrax_scenarios.csv"'})
