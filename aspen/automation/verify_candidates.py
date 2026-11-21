"""Verify optimisation candidates in the actual Aspen Plus V15 model (P2.5 / P3.5).

The optimiser works on the fast independent Python process model. Every optimum it reports must be
confirmed by the principal simulator before it is presented as a result. This script

1. reads ``results/optimisation/candidates_for_aspen.json``
   (list of ``{"id", "label", "inputs": <CaseInputs fields>, ...}``),
2. solves each candidate in Aspen Plus (stored as ``results/simulations/opt_<id>.json``),
3. evaluates the same metrics on the Aspen result and on the Python result
   (``amcrax.optimisation.evaluate_result`` - LCOH, carbon intensity, efficiency ...),
4. writes ``results/optimisation/aspen_verification.json`` and ``.csv`` with the deviations and a
   pass/fail flag per candidate (convergence + relative tolerance on each metric).

Usage:  python aspen/automation/verify_candidates.py [--tolerance 0.03]
"""
from __future__ import annotations

import csv
import json
import logging
import sys
from datetime import datetime, timezone

from amcrax.aspen.runner import run_cases, save_result
from amcrax.paths import RESULTS_OPTIMISATION, RESULTS_SIMULATIONS, ensure_dirs
from amcrax.schemas import CaseInputs, SimulationResult

KPI_FIELDS = (
    "nh3_conversion", "h2_product_kg_h", "h2_purity_mole_frac", "total_external_heating_kW",
    "recovered_heat_kW", "net_fuel_heat_deficit_kW", "specific_heat_demand_kWh_per_kgH2", "lhv_efficiency",
)

#: Metrics that are optimisation objectives or directly determine them. A candidate is VERIFIED
#: when Aspen converges and each of these agrees with the Python surrogate within the tolerance.
#: All other metrics (individual duties, minor cost items) are reported as secondary deviations:
#: they carry the documented model-form differences of the feed section (vaporiser dew point,
#: liquid-ammonia enthalpy; see docs/validation/discrepancy_analysis.md) and do not decide a ranking.
PRIMARY_METRICS = (
    "nh3_conversion", "h2_product_kg_h", "h2_yield_overall", "h2_purity_mole_frac", "lhv_efficiency",
    "total_external_heating_kW", "specific_heat_demand_kWh_per_kgH2",
    "lcoh_USD_per_kg", "carbon_intensity_kgCO2e_per_kgH2", "nh3_feed_kg_per_kgH2", "nh3_total_kg_per_kgH2",
)


def _metrics(result) -> dict:
    """KPIs plus the optimisation metrics (LCOH, carbon intensity ...) of a SimulationResult."""
    out = {k: getattr(result.kpis, k) for k in KPI_FIELDS}
    try:
        from amcrax.optimisation import evaluate_result

        out.update({k: v for k, v in evaluate_result(result).items() if isinstance(v, (int, float))})
    except Exception as exc:  # the comparison of raw KPIs is still valid without the optimisation module
        out["_evaluate_result_error"] = str(exc)  # type: ignore[assignment]
    return out


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    ensure_dirs()
    tol = 0.02
    if "--tolerance" in sys.argv:
        tol = float(sys.argv[sys.argv.index("--tolerance") + 1])
    reuse = "--reuse" in sys.argv  # reuse stored Aspen results whose inputs are identical
    src = RESULTS_OPTIMISATION / "candidates_for_aspen.json"
    if not src.exists():
        print(f"{src} not found - run the optimisation first")
        return 2
    candidates = json.loads(src.read_text(encoding="utf-8"))
    if isinstance(candidates, dict):
        candidates = candidates.get("candidates", [])

    from amcrax.process_model import run_python_case

    cases = [CaseInputs(**{**c["inputs"], "case_id": f"opt_{c['id']}"}) for c in candidates]
    order = sorted(range(len(cases)), key=lambda i: (cases[i].heat_integration, cases[i].reactor_pressure_bar,
                                                      cases[i].burner_excess_air))
    aspen_results = {}
    todo = []
    for i in order:
        stored = RESULTS_SIMULATIONS / f"{cases[i].case_id}.json"
        if reuse and stored.exists():
            try:
                r = SimulationResult.model_validate_json(stored.read_text(encoding="utf-8"))
                if r.status.converged and r.inputs == cases[i] and r.source.value == "aspen_plus_v15":
                    aspen_results[r.case_id] = r
                    continue
            except Exception:
                pass
        todo.append(cases[i])
    if todo:
        for r in run_cases(todo, study="optimisation"):
            save_result(r)
            aspen_results[r.case_id] = r

    rows, report = [], []
    for cand, inputs in zip(candidates, cases):
        a = aspen_results[inputs.case_id]
        entry = {"id": cand["id"], "label": cand.get("label", ""), "case_id": inputs.case_id,
                 "inputs": inputs.model_dump(), "aspen_converged": a.status.converged,
                 "aspen_messages": [m for m in a.status.messages if "error" in m.lower() or "warning" in m.lower()]}
        if not a.status.converged:
            entry.update({"status": "fail", "reason": "Aspen Plus did not converge"})
            report.append(entry)
            continue
        p = run_python_case(inputs.model_copy(update={"case_id": inputs.case_id + "_py"}))
        ma, mp = _metrics(a), _metrics(p)
        deviations = {}
        worst_primary, worst_primary_key = 0.0, None
        worst_secondary, worst_secondary_key = 0.0, None
        for key in sorted(set(ma) & set(mp)):
            va, vp = ma[key], mp[key]
            if not isinstance(va, (int, float)) or not isinstance(vp, (int, float)):
                continue
            rel = (vp - va) / abs(va) if abs(va) > 1e-12 else None
            primary = key in PRIMARY_METRICS
            deviations[key] = {"aspen": va, "python": vp, "python_minus_aspen": vp - va, "relative": rel,
                               "class": "primary" if primary else "secondary"}
            rows.append({"candidate": cand["id"], "metric": key, "class": "primary" if primary else "secondary",
                         "aspen": va, "python": vp, "python_minus_aspen": vp - va, "relative": rel})
            if rel is None:
                continue
            if primary and abs(rel) > worst_primary:
                worst_primary, worst_primary_key = abs(rel), key
            if not primary and abs(rel) > worst_secondary:
                worst_secondary, worst_secondary_key = abs(rel), key
        # coverage: every primary metric must be present with a finite relative deviation
        missing = [m for m in PRIMARY_METRICS
                   if m not in deviations or deviations[m]["relative"] is None
                   or deviations[m]["relative"] != deviations[m]["relative"]]
        if missing or "_evaluate_result_error" in ma or "_evaluate_result_error" in mp:
            entry.update({"metrics": deviations, "status": "fail", "tolerance": tol,
                          "reason": "primary metrics missing or not comparable: " + ", ".join(missing)
                                    + (f"; evaluate_result error: {ma.get('_evaluate_result_error') or mp.get('_evaluate_result_error')}"
                                       if ("_evaluate_result_error" in ma or "_evaluate_result_error" in mp) else "")})
            report.append(entry)
            print(f"{cand['id']:14s} FAIL - {entry['reason']}")
            continue
        entry.update({
            "metrics": deviations,
            "max_relative_deviation_primary": worst_primary,
            "max_relative_deviation_primary_metric": worst_primary_key,
            "max_relative_deviation_secondary": worst_secondary,
            "max_relative_deviation_secondary_metric": worst_secondary_key,
            "tolerance": tol,
            "status": "pass" if worst_primary <= tol else "fail",
            "aspen_mass_closure_rel": a.balances.mass_closure_rel,
            "aspen_energy_closure_rel": a.balances.energy_closure_rel,
        })
        report.append(entry)
        print(f"{cand['id']:14s} converged={a.status.converged}  primary max |rel| = {worst_primary:.4f} ({worst_primary_key})"
              f"  secondary max |rel| = {worst_secondary:.4f} ({worst_secondary_key})  -> {entry['status']}")

    out = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "description": "Optimisation candidates found on the Python process model, re-solved in Aspen Plus V15.",
        "tolerance_relative": tol,
        "criterion": "pass = Aspen Plus converged AND every primary metric agrees with the Python surrogate within "
                     "the tolerance. Secondary metrics (individual duties, minor cost items) are reported, not judged.",
        "primary_metrics": list(PRIMARY_METRICS),
        "candidates": report,
    }
    (RESULTS_OPTIMISATION / "aspen_verification.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    with open(RESULTS_OPTIMISATION / "aspen_verification.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["candidate", "metric", "class", "aspen", "python", "python_minus_aspen", "relative"])
        w.writeheader()
        w.writerows(rows)
    return 0 if all(e["status"] == "pass" for e in report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
