"""Live smoke sweep of the running API (default http://127.0.0.1:8000).

Every GET endpoint of /openapi.json that needs no body is called (path parameters filled with case_id=baseline or a
real name taken from the listing endpoints), then a fixed set of POST requests with minimal valid bodies.
Prints a table (method, path, status, ms). Exit code 1 on any 5xx or connection failure; a 404 is accepted only for
the optional files listed in OPTIONAL_404 and is marked "ok(404 optional)".

Usage: python scripts/smoke_api.py [base_url]
No Aspen run is started (simulation/sensitivity use engine python).
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
CASE = "baseline"
OPTIONAL_404 = ("/api/economics/price-curve", "/api/scenarios/comparison", "/api/validation", "/api/validation/summary",
                "/api/references", "/api/traceability", "/api/flowsheet", "/api/heat-integration/")
rows: list[tuple[str, str, int, float, str]] = []


def call(method: str, path: str, body=None, timeout: float = 120.0):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"})
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status, raw = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    except Exception as e:  # noqa: BLE001
        status, raw = 599, str(e).encode()
    ms = (time.perf_counter() - t) * 1000
    note = ""
    if status == 404 and any(path.startswith(p) for p in OPTIONAL_404):
        note = "ok(404 optional)"
    elif status >= 500:
        note = "FAIL"
    elif status >= 400:
        note = "CLIENT-ERR"
    rows.append((method, path, status, ms, note))
    try:
        return status, json.loads(raw)
    except Exception:  # noqa: BLE001
        return status, None


def main() -> int:
    st, spec = call("GET", "/openapi.json")
    if st != 200 or not spec:
        print(f"cannot read {BASE}/openapi.json (status {st})")
        return 1
    # real names for path parameters
    _, ds = call("GET", "/api/data/optimisation")
    _, dsens = call("GET", "/api/data/sensitivity")
    _, dan = call("GET", "/api/data/analysis")
    _, jobs = call("GET", "/api/jobs")
    _, reps = call("GET", "/api/reports")
    subs = {"case_id": CASE, "id": CASE, "category": "optimisation",
            "name": ((ds or {}).get("items") or [{"file": "pareto.json"}])[0]["file"]}
    for p, item in (("/api/data/sensitivity/{name}", ((dsens or {}).get("items") or [None])[0]),
                    ("/api/data/analysis/{name}", ((dan or {}).get("items") or [None])[0])):
        pass
    done = set()
    for path in sorted(spec["paths"]):
        ops = spec["paths"][path]
        if "get" not in ops:
            continue
        params = ops["get"].get("parameters", [])
        if any(p["in"] == "query" and p.get("required") for p in params):
            req_q = {p["name"]: p for p in params if p["in"] == "query" and p.get("required")}
            q = []
            for n in req_q:
                if n in ("case_id",):
                    q.append(f"case_id={CASE}")
                elif n == "catalyst_id":
                    q.append("catalyst_id=ru_kum_temkin_pyzhev")
                elif n == "case_ids":
                    q.append(f"case_ids={CASE},scn_low_temperature")
                else:
                    q.append(f"{n}=1")
            query = "?" + "&".join(q)
            if path == "/api/reactor/catalyst-mass":
                query += "&target=0.9&n_tubes=40"
        else:
            query = ""
        url = path
        if "{" in path:
            if path.startswith("/api/jobs/"):
                jl = (jobs or {}).get("jobs") or []
                if not jl:
                    continue
                url = path.replace("{job_id}", jl[0]["job_id"])
            elif path == "/files/{key}":
                rl = (reps or {}).get("reports") or []
                if not rl:
                    continue
                url = path.replace("{key}", rl[0]["key"])
            elif path.startswith("/api/data/{category}"):
                continue  # covered below with real files
            elif path == "/api/sensitivity/datasets/{name}":
                items = (dsens or {}).get("items") or []
                if not items:
                    continue
                url = path.replace("{name}", items[0]["name"])
            elif path == "/figures/{file}":
                continue
            else:
                url = path
                for k, v in subs.items():
                    url = url.replace("{" + k + "}", str(v))
                if "{" in url:
                    continue
                if path == "/api/export/{case_id}":
                    query = "?format=json"
        if path == "/api/cases/{case_id}" or path.startswith("/api/export"):
            pass
        call("GET", url + query)
        done.add(url)
    # data endpoints with real names
    for cat, listing in (("optimisation", ds), ("sensitivity", dsens), ("analysis", dan)):
        items = (listing or {}).get("items") or []
        call("GET", f"/api/data/{cat}")
        for it in items[:3] + [i for i in items if i["file"].startswith("pareto")]:
            call("GET", f"/api/data/{cat}/{it['file']}")
        if cat == "optimisation":
            call("GET", "/api/data/optimisation/pareto")  # bare stem -> JSON preferred
    call("GET", "/api/data/validation")
    call("GET", f"/api/economics/price-curve?case_id={CASE}&target_lcoh=4")

    posts = [
        ("/api/economics/lcoh", {"case_id": CASE}),
        ("/api/economics/sensitivity", {"case_id": CASE}),
        ("/api/environment/carbon-intensity", {"case_id": CASE, "scenario": "grey"}),
        ("/api/separation/compare", {"case_id": CASE}),
        ("/api/separation/psa", {"feed_kmol_h": {"H2": 150.0, "N2": 50.0}, "feed_pressure_bar": 20.0}),
        ("/api/separation/membrane", {"feed_kmol_h": {"H2": 150.0, "N2": 50.0}, "feed_pressure_bar": 20.0, "target_recovery": 0.8}),
        ("/api/reactor/pfr", {"catalyst_id": "ru_kum_temkin_pyzhev", "W_kg": 50.0, "n_tubes": 40}),
        ("/api/scenarios/compare", {"case_ids": [CASE, "scn_low_temperature"], "engine": "python"}),
        ("/api/scenarios/analyse", {"scenario_ids": ["baseline", "scn_low_temperature"]}),
        ("/api/optimisation/run", {"objective": "min_lcoh", "method": "grid"}),
        ("/api/simulation/run", {"inputs": {"case_id": "smoke_py_case", "reactor_temperature_C": 600.0}, "engine": "python"}),
        ("/api/sensitivity/run", {"variable": "reactor_temperature_C", "values": [550, 600, 650], "engine": "python"}),
    ]
    for path, body in posts:
        st, j = call("POST", path, body)
        if path == "/api/simulation/run" and st == 202 and j:
            for _ in range(60):
                time.sleep(0.5)
                s2, jj = call("GET", f"/api/jobs/{j['job_id']}")
                if s2 == 200 and jj and jj.get("state") in ("succeeded", "failed", "timeout"):
                    break
    call("DELETE", "/api/cases/smoke_py_case")

    w = max(len(r[1]) for r in rows)
    print(f"{'method':7} {'path':{w}} {'status':>6} {'ms':>8}  note")
    for m, p, s, ms, n in rows:
        print(f"{m:7} {p:{w}} {s:>6} {ms:8.0f}  {n}")
    bad = [r for r in rows if r[2] >= 500]
    errs = [r for r in rows if 400 <= r[2] < 500 and not r[4].startswith("ok")]
    print(f"\n{len(rows)} requests, {len(bad)} with 5xx, {len(errs)} unexpected 4xx")
    for r in errs:
        print("  4xx:", r[0], r[1], r[2])
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
