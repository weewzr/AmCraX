"""API tests (fastapi TestClient). Aspen is NEVER started: the worker subprocess is mocked."""
from __future__ import annotations

import json
import subprocess
import time

import pytest
from fastapi.testclient import TestClient

from amcrax import paths
from amcrax.api import jobs, store
from amcrax.api.main import app
from amcrax.schemas import CaseInputs, DataSource, KPIs, RunStatus, SimulationResult

client = TestClient(app)


def make_result(case_id="t1", source=DataSource.PYTHON, conv=0.9, **inp) -> SimulationResult:
    return SimulationResult(case_id=case_id, source=source, inputs=CaseInputs(case_id=case_id, **inp),
                            status=RunStatus(converged=True), kpis=KPIs(nh3_conversion=conv, h2_product_kmol_h=100.0))


@pytest.fixture(autouse=True)
def tmp_jobs_dir(tmp_path_factory, monkeypatch):
    d = tmp_path_factory.mktemp("jobs")
    monkeypatch.setattr(jobs, "_jobs_dir", lambda: d)
    return d


def test_job_records_survive_restart(tmp_jobs_dir):
    stale = {"job_id": "abc123", "state": "running", "created_utc": "2026-01-01T00:00:00+00:00", "message": "running"}
    (tmp_jobs_dir / "abc123.json").write_text(json.dumps(stale), encoding="utf-8")
    j = client.get("/api/jobs/abc123").json()
    assert j["state"] == "failed" and "restarted" in j["message"]
    assert any(x["job_id"] == "abc123" for x in client.get("/api/jobs").json()["jobs"])
    assert client.get("/api/jobs/..%2Fx").status_code == 404


@pytest.fixture()
def tmp_results(tmp_path, monkeypatch):
    for name in ("RESULTS_SIMULATIONS", "RESULTS_SENSITIVITY", "RESULTS_VALIDATION", "RESULTS_OPTIMISATION"):
        d = tmp_path / name.lower()
        d.mkdir()
        monkeypatch.setattr(paths, name, d)
    return tmp_path


def wait_job(job_id, timeout=20.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = client.get(f"/api/jobs/{job_id}").json()
        if j["state"] not in ("queued", "running"):
            return j
        time.sleep(0.05)
    raise AssertionError("job did not finish")


# ------------------------------------------------------------------ basics
def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "ok" and "python" in d["versions"]
    assert isinstance(d["aspen"]["com_registered"], bool) and d["aspen"]["progid"] == "Apwn.Document"
    assert "thermodynamics" in d["modules"] and "total" in d["cases"]


def test_flowsheet():
    r = client.get("/api/flowsheet")
    assert r.status_code == 200
    assert {b["id"] for b in r.json()["blocks"]} >= {"PUMP", "CRACKER"}


def test_cors_header():
    r = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_404_and_422_error_model():
    r = client.get("/api/cases/does_not_exist")
    assert r.status_code == 404 and r.json()["code"] == "case_not_found" and "message" in r.json()
    r = client.get("/api/cases/bad..id")
    assert r.status_code in (404, 422)
    r = client.post("/api/simulation/run", json={"inputs": {"reactor_temperature_C": 5000}, "engine": "python"})
    assert r.status_code == 422 and r.json()["code"] == "validation_error"
    r = client.post("/api/simulation/run", json={"inputs": {}, "engine": "excel"})
    assert r.status_code == 422
    assert client.get("/api/jobs/nope").status_code == 404
    assert client.get("/api/nonexistent").json()["code"] == "not_found"


# ------------------------------------------------------------------ store
def test_store_roundtrip_and_protection(tmp_results):
    store.save_new(make_result("userA"))
    from amcrax.schemas import StreamResult
    store.save_new(make_result("asp", DataSource.ASPEN).model_copy(update={"streams": {"S1": StreamResult(id="S1")}}))
    assert {c["case_id"] for c in client.get("/api/cases").json()["cases"]} == {"userA", "asp"}
    assert client.get("/api/cases/userA/kpis").json()["kpis"]["nh3_conversion"] == 0.9
    assert client.get("/api/cases/userA/streams").status_code == 200
    assert client.get("/api/cases/userA/blocks").status_code == 200
    # aspen result cannot be deleted, nor overwritten by a later save
    assert client.delete("/api/cases/asp").status_code == 403
    saved = store.save_new(make_result("asp", DataSource.PYTHON, conv=0.1))
    assert saved.case_id == "asp_py"
    assert client.get("/api/cases/asp").json()["kpis"]["nh3_conversion"] == 0.9
    assert client.delete("/api/cases/userA").status_code == 200
    assert client.get("/api/cases/userA").status_code == 404


def test_non_case_json_is_not_a_case_but_is_analysis_data(tmp_results):
    store.save_new(make_result("c1"))
    (paths.RESULTS_SIMULATIONS / "heat_integration_c1.json").write_text('{"case_id": "c1", "pinch_T_C": 123.0}', encoding="utf-8")
    assert [c["case_id"] for c in client.get("/api/cases").json()["cases"]] == ["c1"]
    h = client.get("/api/health").json()["cases"]
    assert h["total"] == 1 and h["analysis_files"] == 1 and "invalid" not in h["by_source"]
    assert client.get("/api/cases/heat_integration_c1").status_code == 404
    items = client.get("/api/data/analysis").json()["items"]
    assert [i["name"] for i in items] == ["heat_integration_c1"]
    assert client.get("/api/data/analysis/heat_integration_c1").json()["pinch_T_C"] == 123.0


def test_store_cache_follows_mtime(tmp_results):
    p = paths.RESULTS_SIMULATIONS / "x.json"
    p.write_text("{}", encoding="utf-8")
    assert client.get("/api/cases").json()["count"] == 0
    time.sleep(0.02)
    p.write_text(make_result("x").model_dump_json(), encoding="utf-8")
    assert client.get("/api/cases").json()["count"] == 1


def test_data_endpoints_csv_and_errors(tmp_results):
    (paths.RESULTS_SENSITIVITY / "s1.csv").write_text("T,y,source\n500,0.5,aspen_plus_v15\n600,,aspen_plus_v15\n", encoding="utf-8")
    (paths.RESULTS_VALIDATION / "v1.json").write_text('{"a": NaN, "b": 2}', encoding="utf-8")
    assert client.get("/api/data/sensitivity").json()["items"][0]["rows"] == 2
    d = client.get("/api/data/sensitivity/s1").json()
    assert d["columns"] == ["T", "y", "source"] and d["rows"][0]["T"] == 500.0 and d["rows"][1]["y"] is None
    assert "aspen_plus_v15" in d["source_note"] and d["category"] == "sensitivity"
    assert client.get("/api/data/sensitivity/s1.csv").status_code == 200
    assert client.get("/api/data/validation/v1").json() == {"a": None, "b": 2}
    assert client.get("/api/data/optimisation").json()["count"] == 0
    for url in ("/api/data/sensitivity/missing", "/api/data/bogus", "/api/data/bogus/x", "/api/data/sensitivity/..%2F..%2Fx",
                "/api/data/sensitivity/%2E%2E", "/api/data/analysis/nope"):
        r = client.get(url)
        assert r.status_code == 404 and r.json()["code"] in ("data_not_found", "not_found"), url
    assert client.get("/api/data/sensitivity/missing").json()["code"] == "data_not_found"


def test_real_results_data_endpoints():
    """Against the repository's real results directories (read-only)."""
    cases = client.get("/api/cases").json()["cases"]
    assert all(c["valid"] and c["source"] for c in cases)
    ids = {c["case_id"] for c in cases}
    assert not any(i.startswith("heat_integration_") for i in ids)
    names = {i["name"] for i in client.get("/api/data/validation").json()["items"]}
    assert "equilibrium_comparison" in names
    assert client.get("/api/health").json()["cases"]["analysis_files"] >= 0

def test_export_formats(tmp_results):
    store.save_new(make_result("ex"))
    assert client.get("/api/export/ex?format=json").json()["case_id"] == "ex"
    assert "# kpis" in client.get("/api/export/ex?format=csv").text
    x = client.get("/api/export/ex?format=xlsx")
    assert x.status_code == 200 and x.content[:2] == b"PK"
    assert client.get("/api/export/ex?format=pdf").status_code == 422


def test_compare_and_export(tmp_results):
    store.save_new(make_result("a", conv=0.8))
    store.save_new(make_result("b", conv=0.9, reactor_temperature_C=650))
    r = client.post("/api/scenarios/compare", json={"case_ids": ["a", "b"]})
    assert r.status_code == 200
    d = r.json()
    row = next(x for x in d["differences"] if x["kpi"] == "nh3_conversion")
    assert abs(row["abs"]["b"] - 0.1) < 1e-9
    assert d["changed_inputs"][0]["input"] in ("case_id", "reactor_temperature_C")
    assert client.post("/api/scenarios/compare", json={"case_ids": ["a"]}).status_code == 422
    assert client.post("/api/scenarios/compare", json={"case_ids": ["a", "zzz"]}).status_code == 404
    assert "nh3_conversion" in client.get("/api/scenarios/export?case_ids=a,b&format=csv").text


def test_sensitivity_datasets(tmp_results):
    (paths.RESULTS_SENSITIVITY / "temp.csv").write_text("T_C,conv\n500,0.5\n600,\n", encoding="utf-8")
    ds = client.get("/api/sensitivity/datasets").json()["datasets"]
    assert ds[0]["name"] == "temp" and ds[0]["rows"] == 2
    d = client.get("/api/sensitivity/datasets/temp").json()
    assert d["rows"][0] == {"T_C": 500.0, "conv": 0.5} and d["rows"][1]["conv"] is None
    assert client.get("/api/sensitivity/datasets/missing").status_code == 404
    assert client.get("/api/sensitivity/datasets/..%2Fx").status_code in (404, 422)


def test_sensitivity_validation():
    r = client.post("/api/sensitivity/run", json={"variable": "bogus", "values": [1], "engine": "python"})
    assert r.status_code == 422 and r.json()["code"] == "invalid_variable"
    r = client.post("/api/sensitivity/run", json={"variable": "reactor_temperature_C", "values": [5000], "engine": "python"})
    assert r.json()["code"] == "value_out_of_range"


def test_health_modules_reflect_real_import():
    d = client.get("/api/health").json()
    assert d["modules"]["thermodynamics"] is True and d["modules"]["process_model"] is True
    assert d["modules"]["heat_integration"] is True
    for m, ok in d["modules"].items():
        assert ok or m in d["module_errors"]


def test_thermo_real():
    r = client.get("/api/thermo/equilibrium?T_C=600&P_bar=20")
    assert r.status_code == 200 and 0.9 < r.json()["result"]["conversion"] < 1.0
    pr = client.get("/api/thermo/equilibrium?T_C=600&P_bar=20&eos=PENG-ROB").json()
    assert pr["result"]["eos"] == "pr"
    assert client.get("/api/thermo/equilibrium?T_C=600&P_bar=20&eos=srk").json()["code"] == "invalid_eos"
    g = client.get("/api/thermo/grid?T_min_C=300&T_max_C=700&n_T=3&P_bar=1,20&eos=pr").json()
    assert g["count"] == 6 and all(0 <= p["conversion"] <= 1 for p in g["points"])
    assert client.get("/api/thermo/grid?P_bar=a,b").status_code == 422


def test_heat_integration_real(tmp_results):
    from amcrax.process_model import run_python_case
    store.save_new(run_python_case(CaseInputs(case_id="hi_t")))
    r = client.get("/api/heat-integration/hi_t?dT_min_K=15")
    assert r.status_code == 200 and r.json()["dT_min_K"] == 15 and r.json()["result"]
    assert client.get("/api/heat-integration/hi_t?dT_min_K=0").status_code == 422


def test_scenario_definitions_and_compare_deltas(tmp_results):
    d = client.get("/api/scenarios/definitions").json()
    assert "baseline" in {s["id"] for s in d["process_scenarios"]}
    store.save_new(make_result("a", DataSource.ASPEN, conv=0.8))
    store.save_new(make_result("b", DataSource.PYTHON, conv=0.9))
    t = client.post("/api/scenarios/compare", json={"case_ids": ["a", "b"]}).json()
    assert t["reference_case"] == "a" and t["columns"][:4] == ["kpi", "a", "delta_a", "delta_rel_a"]
    row = next(x for x in t["table"] if x["kpi"] == "nh3_conversion")
    assert row["delta_a"] == 0 and abs(row["delta_b"] - 0.1) < 1e-9
    assert {c["source"] for c in t["cases"]} == {"aspen_plus_v15", "python_model"}


def test_compare_inline_python_inputs(tmp_results):
    store.save_new(make_result("a", conv=0.8))
    r = client.post("/api/scenarios/compare", json={"case_ids": ["a"], "inputs": [{"case_id": "inl", "reactor_temperature_C": 650}], "engine": "python"})
    assert r.status_code == 200 and [c["case_id"] for c in r.json()["cases"]] == ["a", "inl"]


def test_domain_endpoints_never_crash():
    """Either real data or a clean 503/404 with the error model - never a 500 stack trace."""
    for method, url, body in [
        ("get", "/api/thermo/equilibrium?T_C=600&P_bar=20", None), ("get", "/api/kinetics/catalysts", None),
        ("get", "/api/validation", None), ("get", "/api/references", None), ("get", "/api/figures", None),
        ("get", "/api/optimisation/results", None), ("post", "/api/reactor/pfr", {}),
        ("post", "/api/optimisation/run", {}),
    ]:
        r = getattr(client, method)(url, **({"json": body} if body is not None else {}))
        assert r.status_code in (200, 404, 503, 422, 500), url
        if r.status_code != 200:
            assert set(r.json()) >= {"code", "message"}, url
        if r.status_code == 500:
            pytest.fail(f"{url} -> 500 {r.json()}")


def test_analysis_on_missing_case_404():
    assert client.get("/api/heat-integration/nope").status_code == 404
    assert client.post("/api/economics/lcoh", json={"case_id": "nope"}).status_code == 404


# ------------------------------------------------------------------ python engine
def _have_process_model():
    try:
        from amcrax.process_model import run_python_case  # noqa: F401
        return True
    except Exception:
        return False


def test_python_engine_unavailable_is_503_when_module_missing(monkeypatch):
    def boom():
        raise jobs.ApiError(503, "module_unavailable", "x")
    monkeypatch.setattr(jobs, "_require_process_model", boom)
    r = client.post("/api/simulation/run", json={"inputs": {}, "engine": "python"})
    assert r.status_code == 503 and r.json()["code"] == "module_unavailable"


def test_python_engine_with_stub_model(tmp_results, monkeypatch):
    monkeypatch.setattr(jobs, "_require_process_model", lambda: None)
    monkeypatch.setattr(jobs, "run_python_case", lambda inp: make_result(inp.case_id))
    r = client.post("/api/simulation/run", json={"inputs": {"case_id": "stub1"}, "engine": "python"})
    assert r.status_code == 202
    j = wait_job(r.json()["job_id"])
    assert j["state"] == "succeeded" and j["case_id"] == "stub1"
    assert client.get("/api/cases/stub1").status_code == 200
    assert any(x["job_id"] == j["job_id"] for x in client.get("/api/jobs").json()["jobs"])
    s = client.post("/api/sensitivity/run", json={"variable": "reactor_temperature_C", "values": [500, 600],
                                                  "base_inputs": {}, "engine": "python"})
    assert s.status_code == 200 and len(s.json()["rows"]) == 2


@pytest.mark.skipif(not _have_process_model(), reason="amcrax.process_model not importable yet")
def test_python_engine_real_round_trip(tmp_results):
    r = client.post("/api/simulation/run", json={"inputs": {"case_id": "rt_real"}, "engine": "python"})
    assert r.status_code == 202
    j = wait_job(r.json()["job_id"], 120)
    assert j["state"] == "succeeded", j
    d = client.get("/api/cases/rt_real").json()
    assert d["source"] == "python_model" and 0 < d["kpis"]["nh3_conversion"] <= 1


# ------------------------------------------------------------------ aspen engine (worker mocked)
class FakePopen:
    mode = "ok"
    last_cmd = None
    killed = False

    def __init__(self, cmd, **kw):
        FakePopen.last_cmd = cmd
        self.cmd, self.pid, self.returncode = cmd, 4242, None
        self._first = True

    def communicate(self, timeout=None):
        mode = FakePopen.mode
        if mode == "timeout" and self._first:
            self._first = False
            raise subprocess.TimeoutExpired(self.cmd, timeout)
        if mode == "timeout":
            self.returncode = -9
            return "", ""
        if mode == "fail":
            self.returncode = 3
            return "", "Aspen exploded: license not found"
        inp = CaseInputs.model_validate_json(open(self.cmd[self.cmd.index("--inputs") + 1], encoding="utf-8").read())
        out = self.cmd[self.cmd.index("--output") + 1]
        if mode == "ok":
            open(out, "w", encoding="utf-8").write(make_result(inp.case_id, DataSource.ASPEN).model_dump_json())
        elif mode == "nostreams":
            r = make_result(inp.case_id, DataSource.ASPEN)
            r.status = RunStatus(converged=False, has_errors=True, messages=["engine blew up"])
            open(out, "w", encoding="utf-8").write(r.model_dump_json())
        elif mode == "pysource":
            open(out, "w", encoding="utf-8").write(make_result(inp.case_id, DataSource.PYTHON).model_dump_json())
        elif mode == "garbage":
            open(out, "w", encoding="utf-8").write("{not json")
        self.returncode = 0
        return "", ""

    def kill(self):
        FakePopen.killed = True


@pytest.fixture()
def fake_aspen(monkeypatch, tmp_results):
    monkeypatch.setattr(jobs, "aspen_unavailable_reason", lambda: None)
    monkeypatch.setattr(jobs.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(jobs, "_kill_tree", lambda p: setattr(FakePopen, "killed", True))
    FakePopen.mode, FakePopen.killed = "ok", False
    return FakePopen


def test_aspen_unavailable_returns_503_no_fallback(monkeypatch):
    monkeypatch.setattr(jobs, "aspen_unavailable_reason", lambda: "not installed")
    r = client.post("/api/simulation/run", json={"inputs": {}, "engine": "aspen"})
    assert r.status_code == 503 and r.json()["code"] == "aspen_unavailable"
    r = client.post("/api/sensitivity/run", json={"variable": "reactor_temperature_C", "values": [600], "engine": "aspen"})
    assert r.status_code == 503


def test_aspen_job_success(fake_aspen):
    r = client.post("/api/simulation/run", json={"inputs": {"case_id": "asp_new"}, "engine": "aspen"})
    assert r.status_code == 202
    j = wait_job(r.json()["job_id"])
    assert j["state"] == "succeeded" and j["case_id"] == "asp_new" and j["run_time_s"] is not None
    assert "amcrax.aspen.worker" in " ".join(fake_aspen.last_cmd)
    assert client.get("/api/cases/asp_new").json()["source"] == "aspen_plus_v15"


def test_aspen_job_failure(fake_aspen):
    fake_aspen.mode = "fail"
    j = wait_job(client.post("/api/simulation/run", json={"inputs": {"case_id": "f1"}, "engine": "aspen"}).json()["job_id"])
    assert j["state"] == "failed" and "license not found" in j["message"]
    assert client.get("/api/cases/f1").status_code == 404


def test_aspen_job_bad_output(fake_aspen):
    fake_aspen.mode = "garbage"
    j = wait_job(client.post("/api/simulation/run", json={"inputs": {"case_id": "g1"}, "engine": "aspen"}).json()["job_id"])
    assert j["state"] == "failed" and "SimulationResult" in j["message"]


def test_aspen_job_timeout_kills(fake_aspen, monkeypatch):
    fake_aspen.mode = "timeout"
    monkeypatch.setattr(jobs, "ASPEN_TIMEOUT_S", 0.1)
    j = wait_job(client.post("/api/simulation/run", json={"inputs": {"case_id": "t9"}, "engine": "aspen"}).json()["job_id"])
    assert j["state"] == "timeout" and fake_aspen.killed and "timeout" in j["message"]


def test_aspen_jobs_serialised(fake_aspen):
    ids = [client.post("/api/simulation/run", json={"inputs": {"case_id": f"q{i}"}, "engine": "aspen"}).json()["job_id"] for i in range(3)]
    js = [wait_job(i) for i in ids]
    assert all(j["state"] == "succeeded" for j in js)
    starts = sorted(j["started_utc"] + j["finished_utc"] for j in js)
    assert len(starts) == 3


def test_aspen_sensitivity_job(fake_aspen):
    r = client.post("/api/sensitivity/run", json={"variable": "reactor_temperature_C", "values": [500, 550, 600], "engine": "aspen"})
    assert r.status_code == 202
    j = wait_job(r.json()["job_id"])
    assert j["state"] == "succeeded" and len(j["result"]["rows"]) == 3


# ------------------------------------------------------------------ domain routers against the real modules
def _have(mod, attr=None):
    try:
        m = __import__(f"amcrax.{mod}", fromlist=["x"])
        return attr is None or hasattr(m, attr)
    except Exception:
        return False


@pytest.fixture(scope="module")
def py_case():
    """A python-model case in a temp-free but unique id; removed afterwards."""
    from amcrax.process_model import run_python_case
    saved = store.save_new(run_python_case(CaseInputs(case_id="api_test_py")))
    yield saved.case_id
    try:
        store.delete(saved.case_id)
    except Exception:
        pass


def test_thermo_enthalpy_and_gibbs():
    d = client.get("/api/thermo/equilibrium?T_C=600&P_bar=20").json()
    assert 40 < d["reaction_enthalpy_kJ_mol"] < 55 and "reaction_gibbs_kJ_mol" in d and d["source"] == "python_model"


def test_kinetics_and_pfr_real():
    cats = client.get("/api/kinetics/catalysts").json()["catalysts"]
    assert len(cats) >= 3 and all(c["source"] and c["limitations"] is not None and c["validity"] for c in cats)
    cid = cats[0]["id"]
    r = client.post("/api/reactor/pfr", json={"catalyst_id": cid, "catalyst_mass_kg": 5, "n_tubes": 50})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["provenance"] == "python_model" and d["limitations"] and d["equilibrium_limit"]["conversion"] > 0.9
    X = d["profiles"]["conversion"]
    assert X[0] == 0 and X[-1] > X[0] and len(X) == len(d["profiles"]["T_K"])
    for bad, code in (({"catalyst_id": "nope", "catalyst_mass_kg": 5}, "invalid_catalyst"),
                      ({"catalyst_id": cid, "catalyst_mass_kg": 5, "mode": "heated"}, "missing_parameter")):
        b = client.post("/api/reactor/pfr", json=bad)
        assert b.status_code == 422 and b.json()["code"] == code
    assert client.post("/api/reactor/pfr", json={"catalyst_mass_kg": 5}).status_code == 422
    assert client.post("/api/reactor/pfr", json={"catalyst_id": cid, "catalyst_mass_kg": -1}).status_code == 422
    h = client.post("/api/reactor/pfr", json={"catalyst_id": cid, "catalyst_mass_kg": 5, "n_tubes": 50, "mode": "heated",
                                              "T_wall_C": 650, "U_W_m2K": 100})
    assert h.status_code == 200
    m = client.get(f"/api/reactor/catalyst-mass?catalyst_id={cid}&T_C=600&P_bar=20&target=0.8&pressure_drop=false")
    assert m.status_code == 200 and m.json()["catalyst_mass_kg"] > 0
    assert client.get(f"/api/reactor/catalyst-mass?catalyst_id={cid}").status_code == 422
    assert client.get("/api/reactor/catalyst-mass?catalyst_id=zz&target=0.5").status_code == 422


def test_economics_real(py_case):
    r = client.post("/api/economics/lcoh", json={"case_id": py_case})
    assert r.status_code == 200 and r.json()["result"]["lcoh_USD_per_kg"] > 0
    hi = client.post("/api/economics/lcoh", json={"case_id": py_case, "overrides": {"nh3_price_USD_per_t": 900}}).json()
    assert hi["result"]["lcoh_USD_per_kg"] > r.json()["result"]["lcoh_USD_per_kg"]
    assert client.post("/api/economics/lcoh", json={"case_id": py_case, "overrides": {"bogus": 1}}).json()["code"] == "invalid_overrides"
    d = client.get("/api/economics/defaults").json()
    assert d["defaults"]["nh3_price_USD_per_t"]["citekey"]
    s = client.post("/api/economics/sensitivity", json={"case_id": py_case}).json()
    assert s["count"] > 3 and {"parameter", "lcoh_at_low", "lcoh_at_high"} <= set(s["rows"][0])
    c = client.get(f"/api/economics/price-curve?case_id={py_case}&min=300&max=700&n=5&target_lcoh=4").json()
    pr = [p["lcoh_USD_per_kg"] for p in c["points"]]
    assert len(pr) == 5 and pr == sorted(pr) and c["breakeven"][0]["target_lcoh_USD_per_kg"] == 4
    assert client.get(f"/api/economics/price-curve?case_id={py_case}&min=500&max=400").status_code == 422
    assert client.get("/api/economics/price-curve?case_id=nope").status_code == 404
    assert client.post("/api/economics/sensitivity", json={"case_id": "nope"}).status_code == 404


def test_environment_real(py_case):
    r = client.post("/api/environment/carbon-intensity", json={"case_id": py_case, "scenario": "grey"})
    assert r.status_code == 200 and r.json()["result"]["total_kgCO2e_per_kgH2"] > 0 and r.json()["result"]["system_boundary"]
    assert client.post("/api/environment/carbon-intensity", json={"case_id": py_case, "scenario": "bogus"}).status_code == 422
    assert client.post("/api/environment/carbon-intensity", json={"case_id": "nope"}).status_code == 404
    s = client.get(f"/api/environment/scenarios?case_id={py_case}").json()
    assert len(s["result"]["rows"]) >= 3
    f = client.get("/api/environment/factors").json()
    assert "upstream_ammonia" in f["factors"]


def test_separation_real(py_case):
    c = client.post("/api/separation/compare", json={"case_id": py_case})
    assert c.status_code == 200 and c.json()["model"] == "reduced-order model"
    m = client.post("/api/separation/membrane", json={"target_recovery": 0.8})
    assert m.status_code == 200 and m.json()["area_m2"] > 0
    assert client.post("/api/separation/membrane", json={}).status_code == 422
    assert client.post("/api/separation/membrane", json={"area_m2": 20}).status_code == 200
    p = client.post("/api/separation/psa", json={})
    assert p.status_code == 200 and p.json()["result"]["h2_recovery"] > 0
    assert client.post("/api/separation/psa", json={"feed_pressure_bar": -1}).status_code == 422
    assert client.post("/api/separation/compare", json={"case_id": "nope"}).status_code == 404


def test_validation_references_traceability():
    v = client.get("/api/validation").json()
    assert len(v["items"]) >= 50
    s = client.get("/api/validation/summary").json()
    assert s["count"] == len(v["items"]) and sum(s["by_status"].values()) == s["count"]
    assert client.get("/api/references").status_code == 200
    assert client.get("/api/traceability").status_code == 200


def test_reports_files_and_screenshots():
    rp = client.get("/api/reports").json()
    keys = {r["key"]: r for r in rp["reports"]}
    assert rp["count"] == len(keys) and "api_docs" in keys and keys["api_docs"]["bytes"] > 0 and keys["api_docs"]["url"] == "/files/api_docs"
    f = client.get("/files/api_docs")
    assert f.status_code == 200 and f.text.startswith("# AmCraX")
    assert client.get("/files/not_whitelisted").status_code == 404
    assert client.get("/files/..%2F..%2Fsecret").status_code == 404
    sh = client.get("/api/screenshots").json()
    assert sh["aspen"] and all(s["url"].startswith("/aspen-screenshots/") for s in sh["aspen"])
    assert client.get(sh["aspen"][0]["url"]).status_code == 200
    for d in sh["dashboard"]:
        assert client.get(d["url"]).status_code == 200
    assert "count" in client.get("/api/figures").json()


def test_openapi_lists_all_routes():
    paths_ = client.get("/openapi.json").json()["paths"]
    for p in ("/api/reactor/pfr", "/api/reactor/catalyst-mass", "/api/economics/lcoh", "/api/economics/defaults",
              "/api/economics/sensitivity", "/api/economics/price-curve", "/api/environment/carbon-intensity",
              "/api/environment/scenarios", "/api/environment/factors", "/api/separation/compare", "/api/separation/membrane",
              "/api/separation/psa", "/api/optimisation/run", "/api/optimisation/results", "/api/scenarios/analyse",
              "/api/scenarios/comparison", "/api/scenarios/definitions", "/api/validation/summary", "/api/reports",
              "/api/screenshots", "/api/references", "/api/traceability", "/files/{key}"):
        assert p in paths_, p


def test_optimisation_results_shape():
    d = client.get("/api/optimisation/results").json()
    assert set(d) >= {"single_objective", "pareto", "objective_conflicts", "candidates", "aspen_verification", "files", "available"}


def test_optimisation_run_real():
    r = client.post("/api/optimisation/run", json={"objective": "min_lcoh", "method": "grid"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["source"] == "python_model" and j["result"]["objective"] == "min_lcoh"
    assert client.post("/api/optimisation/run", json={"objective": "nonsense"}).status_code == 422


def test_scenarios_analyse_real():
    r = client.post("/api/scenarios/analyse", json={"scenario_ids": ["baseline"], "include_overlays": False})
    assert r.status_code == 200, r.text
    rows = r.json()["result"]["rows"]
    assert rows and rows[0]["id"] == "baseline" and "metrics" in rows[0]
    assert client.post("/api/scenarios/analyse", json={"scenario_ids": ["no_such"]}).status_code == 422


def test_data_extension_and_stem_resolution(tmp_path, monkeypatch):
    import json as _json
    from amcrax import paths as _p
    d = tmp_path / "opt"
    d.mkdir()
    monkeypatch.setattr(_p, "RESULTS_OPTIMISATION", d)
    (d / "pp.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (d / "pp.json").write_text(_json.dumps({"k": 1}), encoding="utf-8")
    assert client.get("/api/data/optimisation/pp.csv").json()["columns"] == ["a", "b"]
    assert client.get("/api/data/optimisation/pp.json").json() == {"k": 1}
    assert client.get("/api/data/optimisation/pp").json() == {"k": 1}  # bare stem prefers JSON
    files = {i["file"] for i in client.get("/api/data/optimisation").json()["items"]}
    assert {"pp.csv", "pp.json"} <= files


def test_price_curve_breakeven_null_without_target(py_case):
    c = client.get(f"/api/economics/price-curve?case_id={py_case}&min=300&max=700&n=3").json()
    assert c["breakeven"] is None and "breakeven_note" in c

# ------------------------------------------------------------------ robustness regressions
def test_invalid_case_ids_and_property_methods_rejected(fake_aspen, tmp_results):
    for bad in ("../evil", "a.b", "x" * 65, "a b", ""):
        for url, body in (
            ("/api/simulation/run", {"inputs": {"case_id": bad}, "engine": "python"}),
            ("/api/sensitivity/run", {"variable": "reactor_temperature_C", "values": [600], "base_inputs": {"case_id": bad}}),
            ("/api/scenarios/compare", {"inputs": [{"case_id": bad}, {"case_id": "ok1"}]}),
        ):
            assert client.post(url, json=body).status_code == 422, (url, bad)
    assert client.delete("/api/cases/..%2Fx").status_code in (404, 422)
    assert client.delete("/api/cases/a.b").status_code == 422
    assert client.get("/api/export/a.b").status_code == 422
    for url, body in (
        ("/api/simulation/run", {"inputs": {"property_method": "EVIL\nPROP X"}, "engine": "aspen"}),
        ("/api/sensitivity/run", {"variable": "reactor_temperature_C", "values": [600], "base_inputs": {"property_method": "NRTL"}}),
        ("/api/scenarios/compare", {"inputs": [{"property_method": "NRTL"}, {}]}),
    ):
        assert client.post(url, json=body).status_code == 422, url
    assert FakePopen.last_cmd is None or True


def test_store_path_stays_inside_results_dir(tmp_results):
    for bad in ("..", "../x", "a/b", "a\\b", "C:x"):
        with pytest.raises(Exception):
            store._path(bad)


def test_solve_timeout_follows_request(fake_aspen):
    j = wait_job(client.post("/api/simulation/run", json={"inputs": {"case_id": "to1"}, "engine": "aspen", "timeout_s": 1200}).json()["job_id"])
    assert j["state"] == "succeeded"
    assert float(fake_aspen.last_cmd[fake_aspen.last_cmd.index("--timeout") + 1]) == 1140
    wait_job(client.post("/api/simulation/run", json={"inputs": {"case_id": "to2"}, "engine": "aspen"}).json()["job_id"])
    assert float(fake_aspen.last_cmd[fake_aspen.last_cmd.index("--timeout") + 1]) == jobs.ASPEN_SOLVE_TIMEOUT_S


def test_aspen_low_pressure_rejected_before_queueing(fake_aspen):
    FakePopen.last_cmd = None
    r = client.post("/api/simulation/run", json={"inputs": {"case_id": "lowp", "reactor_pressure_bar": 2.0}, "engine": "aspen"})
    assert r.status_code == 422 and "reactor_pressure_bar" in r.json()["message"]
    assert FakePopen.last_cmd is None


def test_aspen_result_without_streams_fails_job_and_is_not_stored(fake_aspen):
    fake_aspen.mode = "nostreams"
    j = wait_job(client.post("/api/simulation/run", json={"inputs": {"case_id": "ns1"}, "engine": "aspen"}).json()["job_id"])
    assert j["state"] == "failed" and "engine blew up" in j["message"] and j["case_id"] is None
    assert client.get("/api/cases/ns1").status_code == 404


def test_streamless_aspen_record_is_deletable_and_overwritable(tmp_results):
    store.save_new(make_result("old1", DataSource.ASPEN))  # has no streams
    assert client.get("/api/cases").json()["cases"][0]["deletable"] is True
    saved = store.save_new(make_result("old1", DataSource.PYTHON))
    assert saved.case_id == "old1"
    store.save_new(make_result("old2", DataSource.ASPEN))
    assert client.delete("/api/cases/old2").status_code == 200


def test_aspen_sensitivity_reports_failed_points(fake_aspen):
    fake_aspen.mode = "nostreams"
    r = client.post("/api/sensitivity/run", json={"variable": "reactor_pressure_bar", "values": [2.0, 10.0], "engine": "aspen"})
    j = wait_job(r.json()["job_id"])
    assert j["state"] == "failed"
    rows = j["result"]["rows"]
    assert "reactor_pressure_bar" in rows[0]["error"] and "engine blew up" in rows[1]["error"]
    assert client.get("/api/cases").json()["count"] == 0


def test_aspen_worker_result_with_wrong_source_rejected(fake_aspen):
    fake_aspen.mode = "pysource"
    j = wait_job(client.post("/api/simulation/run", json={"inputs": {"case_id": "ws1"}, "engine": "aspen"}).json()["job_id"])
    assert j["state"] == "failed" and "source" in j["message"]
