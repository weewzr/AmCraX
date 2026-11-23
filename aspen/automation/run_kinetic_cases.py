"""Run catalyst-kinetic RPLUG cases in Aspen Plus V15 (research expansion, workstream A).

Usage (from the project root, after scripts/env.ps1)::

    python aspen/automation/run_kinetic_cases.py CASES.json [--force] [--no-bkp] [--no-python]
           [--study NAME]

CASES.json is a JSON list; each item has the fields of amcrax.aspen.kinetic.KineticReactorInputs plus
``configuration`` ("standalone" default, or "integrated") and, for integrated cases, ``flowsheet`` (a dict of
CaseInputs overrides, e.g. {"heat_integration": false}). Example item::

    {"case_id": "ru_kum_T450_P5_W20", "catalyst_id": "ru_kum_temkin_pyzhev", "temperature_C": 450,
     "pressure_bar": 5, "catalyst_mass_kg": 20, "n_tubes": 50, "tube_diameter_m": 0.126,
     "feed_kmol_h": {"NH3": 99.8, "H2O": 0.2}, "thermal_mode": "isothermal", "pressure_drop": false}

thermal_mode: isothermal | adiabatic | coolant (needs coolant_temperature_C and U_W_m2K).
Give exactly one of catalyst_mass_kg (total over all tubes; length derived) or length_m.

Outputs
    results/research/aspen_kinetic/<case_id>.json   per-case result with provenance (source_type aspen; the
                                                    optional python_pfr block is source_type python)
    results/research/aspen_kinetic/run_status.json  per-case status (ok | ok_with_warnings | error | failed)
    aspen/models/research/<case_id>.inp / .bkp      generated input and solved, sanitised backup
Resume: cases whose status is ok/ok_with_warnings and whose JSON exists are skipped unless --force.
Screenshots: afterwards run aspen/automation/capture_kinetic_screenshots.py CASE_ID ... (uses the saved .bkp).
Then: python aspen/automation/validate_kinetic_vs_python.py (Aspen vs Python PFR vs RGibbs).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
from pathlib import Path

from amcrax.aspen.kinetic import KineticCase, run_kinetic_cases
from amcrax.paths import ROOT

OUT = ROOT / "results" / "research" / "aspen_kinetic"
STATUS = OUT / "run_status.json"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def python_counterpart(case: KineticCase) -> dict:
    """Independent Python PFR (amcrax.reactor.pfr) at identical conditions (standalone cases only)."""
    from amcrax.reactor.pfr import simulate_pfr

    r = case.reactor
    mode = {"isothermal": "isothermal", "adiabatic": "adiabatic", "coolant": "external"}[r.thermal_mode]
    res = simulate_pfr(
        r.catalyst_id, r.catalyst_mass_total_kg, T_in_C=r.temperature_C, P_in_bar=r.pressure_bar,
        feed_kmol_h=r.seeded_feed(), mode=mode, T_wall_C=r.coolant_temperature_C, U_W_m2K=r.U_W_m2K,
        eps_b=r.bed_voidage, rho_particle_kg_m3=r.particle_density_kg_m3, dp_m=r.particle_diameter_m,
        tube_inner_diameter_m=r.tube_diameter_m, n_tubes=r.n_tubes, pressure_drop=r.pressure_drop,
        keq_basis="amcrax_thermo",
    )
    return {"source_type": "python", "model": "amcrax.reactor.pfr.simulate_pfr", "keq_basis": "amcrax_thermo",
            "outlet": res.outlet, "assumptions": res.assumptions,
            "profiles": {"W_kg": res.W_kg[::10], "conversion": res.conversion[::10], "T_K": res.T_K[::10],
                         "P_bar": res.P_bar[::10]}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cases")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-bkp", action="store_true")
    ap.add_argument("--no-python", action="store_true")
    ap.add_argument("--study", default="research_kinetic")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    raw = json.loads(Path(a.cases).read_text(encoding="utf-8"))
    cases = [KineticCase.from_json(d) for d in raw]
    OUT.mkdir(parents=True, exist_ok=True)
    status = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}
    todo = [c for c in cases if a.force or not (
        status.get(c.reactor.case_id, {}).get("status") in ("ok", "ok_with_warnings")
        and (OUT / f"{c.reactor.case_id}.json").exists())]
    print(f"{len(cases)} cases, {len(cases) - len(todo)} already done, {len(todo)} to run")
    if not todo:
        return 0
    hook = None

    def on_result(rec: dict, case: KineticCase) -> None:
        rec["inputs"] = case.model_dump()
        if case.configuration == "standalone" and rec["run_status"] != "failed" and not a.no_python:
            try:
                rec["python_pfr"] = python_counterpart(case)
            except Exception as exc:  # keep the Aspen result
                rec["python_pfr"] = {"error": str(exc)}
        rec["provenance"] = {
            "generated_utc": _now(), "script": "aspen/automation/run_kinetic_cases.py", "source_type": "aspen",
            "inputs_summary": f"{case.configuration} RPLUG, {case.reactor.catalyst_id}, "
                              f"{case.reactor.temperature_C} degC, {case.reactor.pressure_bar} bar, "
                              f"{case.reactor.catalyst_mass_total_kg:.4g} kg catalyst, {case.reactor.thermal_mode}",
            "model_versions": {"aspen": "Aspen Plus V15 (Apwn.Document.41.0)", "property_method": case.reactor.property_method,
                               "kinetics": rec.get("kinetic_spec", {}).get("source", "")},
        }
        (OUT / f"{case.reactor.case_id}.json").write_text(json.dumps(rec, indent=2, default=str), encoding="utf-8")
        status[case.reactor.case_id] = {"status": rec["run_status"], "utc": _now(), "message": rec.get("error")}
        STATUS.write_text(json.dumps(status, indent=2), encoding="utf-8")
        print(f"{case.reactor.case_id}: {rec['run_status']}")

    run_kinetic_cases(todo, study=a.study, save_models=not a.no_bkp, on_result=on_result, session_hook=hook)
    failed = [k for k, v in status.items() if v["status"] in ("failed", "error")]
    print("failed/error:", failed or "none")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
