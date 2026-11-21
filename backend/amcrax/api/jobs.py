"""Job runner. Python engine: thread pool. Aspen engine: ONE job at a time in a separate process
(``python -m amcrax.aspen.worker --inputs in.json --output out.json``), FIFO queue, timeout with kill.
This module never imports or launches Aspen itself and never falls back to the python engine."""
from __future__ import annotations

import importlib.util
import json
import logging
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from amcrax import paths
from amcrax.schemas import CaseInputs, DataSource, SimulationResult

from . import store
from .errors import ApiError, jsonable

log = logging.getLogger("amcrax.api.jobs")

#: Wall-clock limit of one Aspen job (includes waiting for the cross-process Aspen lock). Env AMCRAX_ASPEN_TIMEOUT_S.
ASPEN_TIMEOUT_S: float = float(os.environ.get("AMCRAX_ASPEN_TIMEOUT_S", "600"))
#: Limit passed to the worker for the Aspen solve itself (worker --timeout). Env AMCRAX_ASPEN_SOLVE_TIMEOUT_S.
ASPEN_SOLVE_TIMEOUT_S: float = float(os.environ.get("AMCRAX_ASPEN_SOLVE_TIMEOUT_S", "180"))
PROGID = "Apwn.Document"

QUEUED, RUNNING, SUCCEEDED, FAILED, TIMEOUT = "queued", "running", "succeeded", "failed", "timeout"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- availability
def aspen_progid_registered() -> bool:
    try:
        import winreg
    except ImportError:
        return False
    for hive in (winreg.HKEY_CLASSES_ROOT,):
        try:
            winreg.CloseKey(winreg.OpenKey(hive, PROGID))
            return True
        except OSError:
            continue
    return False


def worker_module_present() -> bool:
    try:
        return importlib.util.find_spec("amcrax.aspen.worker") is not None
    except Exception:
        return False


def aspen_unavailable_reason() -> Optional[str]:
    if not aspen_progid_registered():
        return f"COM ProgID '{PROGID}' is not registered on this machine"
    if not worker_module_present():
        return "worker module amcrax.aspen.worker is not available"
    return None


def require_aspen() -> None:
    reason = aspen_unavailable_reason()
    if reason:
        raise ApiError(503, "aspen_unavailable", f"Aspen Plus engine unavailable: {reason}. "
                       "No fallback to the python engine is performed.", {"reason": reason})


# ---------------------------------------------------------------- aspen subprocess
class AspenJobError(Exception):
    def __init__(self, msg: str, state: str = FAILED):
        super().__init__(msg)
        self.state = state


def _kill_tree(proc) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, timeout=20)
        proc.kill()
    except Exception:  # noqa: BLE001
        try:
            proc.kill()
        except Exception:  # noqa: BLE001
            pass


ALLOWED_PROPERTY_METHODS = frozenset({"PENG-ROB", "RK-SOAVE", "RKS-BM", "PR-BM", "SRK", "IDEAL"})
_SOLVE_MARGIN_S = 60.0


def check_inputs(inputs: CaseInputs, engine: Optional[str] = None) -> CaseInputs:
    """Validate what is written into file names / the Aspen input file (422 on failure).
    For the aspen engine also apply the flowsheet's own feasibility check."""
    store.check_id(inputs.case_id)
    if inputs.property_method not in ALLOWED_PROPERTY_METHODS:
        raise ApiError(422, "invalid_property_method",
                       f"property_method '{inputs.property_method}' is not allowed",
                       {"allowed": sorted(ALLOWED_PROPERTY_METHODS)})
    if engine == "aspen":
        check_flowsheet(inputs)
    return inputs


def check_flowsheet(inputs: CaseInputs) -> None:
    try:
        from amcrax.aspen.inp_writer import validate_flowsheet_inputs
    except Exception:  # noqa: BLE001 - validator unavailable: the worker will still reject the case
        return
    try:
        validate_flowsheet_inputs(inputs)
    except ValueError as e:
        raise ApiError(422, "invalid_flowsheet_inputs", str(e), {"case_id": inputs.case_id})


def solve_timeout_for(timeout_s: Optional[float]) -> float:
    """Worker solve limit consistent with the request's wall clock (outer limit minus a margin)."""
    if timeout_s is None:
        return ASPEN_SOLVE_TIMEOUT_S
    return max(5.0, timeout_s - min(_SOLVE_MARGIN_S, 0.25 * timeout_s))


def failed_without_streams(res: SimulationResult) -> bool:
    return bool(res.status.has_errors) and not res.streams


def run_aspen_case(inputs: CaseInputs, timeout_s: Optional[float] = None) -> SimulationResult:
    solve_s = solve_timeout_for(timeout_s)
    timeout_s = ASPEN_TIMEOUT_S if timeout_s is None else timeout_s
    with tempfile.TemporaryDirectory(prefix="amcrax_job_") as td:
        fin, fout = os.path.join(td, "in.json"), os.path.join(td, "out.json")
        with open(fin, "w", encoding="utf-8") as f:
            f.write(inputs.model_dump_json())
        cmd = [sys.executable, "-m", "amcrax.aspen.worker", "--inputs", fin, "--output", fout,
               "--timeout", f"{solve_s:g}"]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except Exception as e:  # noqa: BLE001
            raise AspenJobError(f"could not start Aspen worker process: {type(e).__name__}: {e}")
        try:
            out, err = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            _kill_tree(proc)
            try:
                proc.communicate(timeout=10)
            except Exception:  # noqa: BLE001
                pass
            raise AspenJobError(f"Aspen worker exceeded the {timeout_s:g} s timeout and was killed", TIMEOUT)
        if proc.returncode != 0:
            tail = (err or out or "").strip()[-1500:]
            raise AspenJobError(f"Aspen worker exited with code {proc.returncode}: {tail or '(no output)'}")
        try:
            with open(fout, "r", encoding="utf-8") as f:
                res = SimulationResult.model_validate_json(f.read())
        except Exception as e:  # noqa: BLE001
            raise AspenJobError(f"Aspen worker output is missing or not a valid SimulationResult: {str(e)[:400]}")
        if res.source != DataSource.ASPEN:
            raise AspenJobError(f"Aspen worker returned a result with source '{res.source.value}'; refusing to treat it as an Aspen result")
        return res


# ---------------------------------------------------------------- job registry
class Job:
    def __init__(self, kind: str, engine: str, label: str):
        self.id = uuid.uuid4().hex[:12]
        self.kind, self.engine, self.label = kind, engine, label
        self.state, self.message = QUEUED, "queued"
        self.created_utc, self.started_utc, self.finished_utc = _now(), None, None
        self.queue_time_s: Optional[float] = None
        self.run_time_s: Optional[float] = None
        self.case_id: Optional[str] = None
        self.result: Any = None
        self.progress: Optional[dict] = None
        self._t_created = time.monotonic()
        self._t_started: Optional[float] = None

    def start(self):
        self._t_started = time.monotonic()
        self.queue_time_s = round(self._t_started - self._t_created, 3)
        self.started_utc, self.state, self.message = _now(), RUNNING, "running"
        self.persist()

    def finish(self, state: str, message: str):
        self.state, self.message, self.finished_utc = state, message, _now()
        if self._t_started is not None:
            self.run_time_s = round(time.monotonic() - self._t_started, 3)
        self.persist()

    def persist(self) -> None:
        """Write the job record to logs/jobs/<id>.json so it survives an API restart / auto-reload."""
        try:
            d = _jobs_dir()
            d.mkdir(parents=True, exist_ok=True)
            tmp = d / f"{self.id}.json.tmp"
            tmp.write_text(json.dumps(self.to_dict()), encoding="utf-8")
            os.replace(tmp, d / f"{self.id}.json")
        except Exception:  # noqa: BLE001
            log.debug("could not persist job %s", self.id, exc_info=True)

    def to_dict(self) -> dict:
        return jsonable({
            "job_id": self.id, "kind": self.kind, "engine": self.engine, "label": self.label,
            "state": self.state, "message": self.message, "created_utc": self.created_utc,
            "started_utc": self.started_utc, "finished_utc": self.finished_utc,
            "queue_time_s": self.queue_time_s, "run_time_s": self.run_time_s,
            "case_id": self.case_id, "progress": self.progress, "result": self.result,
        })


_JOBS: dict[str, Job] = {}
_JOBS_LOCK = threading.Lock()
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="amcrax-py")
_ASPEN_Q: "queue.Queue[tuple[Job, Callable[[Job], None]]]" = queue.Queue()
_aspen_thread: Optional[threading.Thread] = None
_aspen_thread_lock = threading.Lock()


def _jobs_dir():
    return paths.ROOT / "logs" / "jobs"


class _StoredJob:
    """Read-only view of a job record written by an earlier API process."""

    def __init__(self, d: dict):
        self._d = d
        self.id = d.get("job_id", "")
        self.created_utc = d.get("created_utc") or ""
        self.state = d.get("state")

    def to_dict(self) -> dict:
        return self._d


def _load_stored(job_id: str) -> Optional[_StoredJob]:
    if not job_id.isalnum():
        return None
    p = _jobs_dir() / f"{job_id}.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    if d.get("state") in (QUEUED, RUNNING):  # the owning API process is gone
        d["message"] = f"API process restarted while the job was {d['state']}; the job was abandoned and its result is lost"
        d["state"] = FAILED
    return _StoredJob(d)


def get_job(job_id: str):
    j = _JOBS.get(job_id) or _load_stored(job_id)
    if j is None:
        raise ApiError(404, "job_not_found", f"No job '{job_id}'", {"job_id": job_id})
    return j


def list_jobs() -> list[dict]:
    with _JOBS_LOCK:
        live = dict(_JOBS)
    for p in sorted(_jobs_dir().glob("*.json"))[-200:] if _jobs_dir().exists() else []:
        if p.stem not in live:
            s = _load_stored(p.stem)
            if s is not None:
                live[p.stem] = s
    return [j.to_dict() for j in sorted(live.values(), key=lambda j: j.created_utc, reverse=True)]


def _register(job: Job) -> Job:
    job.persist()
    with _JOBS_LOCK:
        _JOBS[job.id] = job
        if len(_JOBS) > 500:  # bounded memory: drop oldest finished
            for k in [k for k, v in _JOBS.items() if v.state in (SUCCEEDED, FAILED, TIMEOUT)][:100]:
                _JOBS.pop(k, None)
    return job


def _aspen_loop():
    while True:
        job, fn = _ASPEN_Q.get()
        _guarded(job, fn)
        _ASPEN_Q.task_done()


def _guarded(job: Job, fn: Callable[[Job], None]) -> None:
    job.start()
    try:
        fn(job)
    except AspenJobError as e:
        job.finish(e.state, str(e))
    except ApiError as e:
        job.finish(FAILED, f"{e.code}: {e.message}")
    except Exception as e:  # noqa: BLE001
        log.exception("job %s failed", job.id)
        job.finish(FAILED, f"{type(e).__name__}: {e}")


def _submit(job: Job, fn: Callable[[Job], None]) -> Job:
    _register(job)
    if job.engine == "aspen":
        global _aspen_thread
        with _aspen_thread_lock:
            if _aspen_thread is None or not _aspen_thread.is_alive():
                _aspen_thread = threading.Thread(target=_aspen_loop, name="amcrax-aspen", daemon=True)
                _aspen_thread.start()
        _ASPEN_Q.put((job, fn))
    else:
        _POOL.submit(_guarded, job, fn)
    return job


# ---------------------------------------------------------------- public submitters
def run_python_case(inputs: CaseInputs) -> SimulationResult:
    try:
        from amcrax.process_model import run_python_case as f
    except Exception as e:  # noqa: BLE001
        raise ApiError(503, "module_unavailable", "amcrax.process_model is not available yet",
                       {"module": "amcrax.process_model", "error": f"{type(e).__name__}: {e}"})
    return f(inputs)


def _require_process_model() -> None:
    try:
        import amcrax.process_model as pm  # noqa: F401
        if not hasattr(pm, "run_python_case"):
            raise ImportError("run_python_case not defined")
    except Exception as e:  # noqa: BLE001
        raise ApiError(503, "module_unavailable", "amcrax.process_model is not available yet",
                       {"module": "amcrax.process_model", "error": f"{type(e).__name__}: {e}"})


def submit_case(inputs: CaseInputs, engine: str, timeout_s: Optional[float] = None) -> Job:
    check_inputs(inputs, engine)
    if engine == "aspen":
        require_aspen()
    else:
        _require_process_model()
    job = Job("simulation", engine, inputs.case_id)

    def work(j: Job):
        res = run_aspen_case(inputs, timeout_s) if engine == "aspen" else run_python_case(inputs)
        if failed_without_streams(res):  # rejected / failed Aspen case: report, do not store as a case
            msgs = "; ".join(res.status.messages[:5]) or "no messages"
            j.finish(FAILED, f"{engine} run failed (no streams): {msgs}")
            return
        saved = store.save_new(res)
        j.case_id = saved.case_id
        ok = saved.status.converged
        j.finish(SUCCEEDED, "converged" if ok else "finished but NOT converged: " + "; ".join(saved.status.messages[:3]))

    return _submit(job, work)


def sens_case_id(base_id: str, i: int) -> str:
    """Point id derived from the (validated) base id; stays within the 64-character id limit."""
    return f"{base_id[:40]}_sens_{i}"


def sensitivity_row(variable: str, value: float, res: SimulationResult) -> dict:
    row = {variable: value, "converged": res.status.converged, "source": res.source.value}
    row.update({k: v for k, v in res.kpis.model_dump().items()})
    if failed_without_streams(res):
        row["converged"] = False
        row["error"] = ("; ".join(res.status.messages[:3]) or "run failed without streams")[:300]
    return row


def submit_sensitivity(variable: str, values: list[float], base: CaseInputs, engine: str) -> Job:
    check_inputs(base)
    if engine == "aspen":
        require_aspen()
    job = Job("sensitivity", engine, f"{variable} x{len(values)}")

    def work(j: Job):
        rows, errors = [], 0
        for i, v in enumerate(values):
            j.progress = {"done": i, "total": len(values)}
            inp = base.model_copy(update={variable: v, "case_id": sens_case_id(base.case_id, i)})
            try:
                inp = CaseInputs.model_validate(inp.model_dump())
                if engine == "aspen":
                    check_flowsheet(inp)  # infeasible point: reported per point, Aspen is not started
                res = run_aspen_case(inp) if engine == "aspen" else run_python_case(inp)
                row = sensitivity_row(variable, v, res)
                errors += "error" in row
                rows.append(row)
            except ApiError as e:
                errors += 1
                rows.append({variable: v, "converged": False, "error": e.message[:300]})
            except AspenJobError as e:
                if e.state == TIMEOUT:
                    j.result = {"variable": variable, "rows": rows}
                    raise
                errors += 1
                rows.append({variable: v, "converged": False, "error": str(e)[:300]})
            except Exception as e:  # noqa: BLE001
                errors += 1
                rows.append({variable: v, "converged": False, "error": f"{type(e).__name__}: {e}"[:300]})
        j.progress = {"done": len(values), "total": len(values)}
        j.result = {"variable": variable, "engine": engine, "rows": rows}
        j.finish(SUCCEEDED if errors < len(values) else FAILED, f"{len(values) - errors}/{len(values)} points succeeded")

    return _submit(job, work)
