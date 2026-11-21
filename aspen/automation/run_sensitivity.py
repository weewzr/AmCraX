"""Automated Aspen Plus sensitivity studies on the full AmCraX flowsheet (P1.4).

Every row of every CSV is an actual Aspen Plus V15 run driven through COM. One CSV per study:

    results/sensitivity/aspen_<study>.csv

Studies: temperature, pressure, tp_map, feed_rate, feed_water, psa_recovery, fehe_approach, no_hi_temperature

Usage:  python aspen/automation/run_sensitivity.py [study ...]     (default: all)
"""
from __future__ import annotations

import csv
import logging
import sys
import time

from amcrax.aspen.runner import run_cases
from amcrax.paths import RESULTS_SENSITIVITY, ensure_dirs
from amcrax.schemas import CaseInputs, KPIs, SimulationResult

BASE = CaseInputs()


def _case(study: str, i: int, **kw) -> CaseInputs:
    return BASE.model_copy(update={"case_id": f"{study}_{i:03d}", **kw})


def build_studies() -> dict[str, list[CaseInputs]]:
    st: dict[str, list[CaseInputs]] = {}
    st["temperature"] = [_case("temperature", i, reactor_temperature_C=float(t)) for i, t in enumerate(range(400, 801, 25))]
    st["pressure"] = [_case("pressure", i, reactor_pressure_bar=p) for i, p in enumerate([5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0])]
    tp = []
    for p in (5.0, 10.0, 20.0, 30.0, 40.0):  # grouped by pressure: one model load per pressure level
        for t in range(450, 751, 50):
            tp.append(_case("tp_map", len(tp), reactor_pressure_bar=p, reactor_temperature_C=float(t)))
    st["tp_map"] = tp
    st["feed_rate"] = [_case("feed_rate", i, feed_total_kmol_h=f) for i, f in enumerate([25.0, 50.0, 100.0, 150.0, 200.0])]
    st["feed_water"] = [_case("feed_water", i, feed_h2o_mole_frac=x) for i, x in enumerate([0.0, 0.002, 0.005, 0.01, 0.02])]
    st["psa_recovery"] = [_case("psa_recovery", i, psa_h2_recovery=r) for i, r in enumerate([0.70, 0.75, 0.80, 0.85, 0.90, 0.95])]
    st["fehe_approach"] = [_case("fehe_approach", i, fehe_hot_end_approach_K=a) for i, a in enumerate([20.0, 30.0, 50.0, 75.0, 100.0, 150.0])]
    st["no_hi_temperature"] = [
        _case("no_hi_temperature", i, heat_integration=False, reactor_temperature_C=float(t))
        for i, t in enumerate(range(400, 801, 50))
    ]
    return st


INPUT_COLS = list(CaseInputs.model_fields.keys())
KPI_COLS = list(KPIs.model_fields.keys())
EXTRA_COLS = [
    "y_NH3_cracked", "y_H2_cracked", "y_N2_cracked", "fehe_hot_outlet_C", "flame_temperature_C",
    "tailgas_kmol_h", "mass_closure_rel", "energy_closure_rel", "converged", "has_warnings",
    "engine_time_s", "source", "messages",
]


def row_of(r: SimulationResult) -> dict:
    row = {**r.inputs.model_dump(), **r.kpis.model_dump()}
    s5 = r.streams.get("S5")
    for c in ("NH3", "H2", "N2"):
        row[f"y_{c}_cracked"] = s5.mole_frac.get(c) if s5 else None
    row["fehe_hot_outlet_C"] = r.streams["S6"].temperature_C if "S6" in r.streams else None
    row["flame_temperature_C"] = r.streams["FLUE"].temperature_C if "FLUE" in r.streams else None
    row["tailgas_kmol_h"] = r.streams["TAILGAS"].mole_flow_kmol_h if "TAILGAS" in r.streams else None
    row["mass_closure_rel"] = r.balances.mass_closure_rel
    row["energy_closure_rel"] = r.balances.energy_closure_rel
    row["converged"] = r.status.converged
    row["has_warnings"] = r.status.has_warnings
    row["engine_time_s"] = r.status.engine_time_s
    row["source"] = r.source.value
    row["messages"] = " | ".join(m for m in r.status.messages if "BINARY PARAMETERS" not in m and "EOS DATABANK" not in m
                                 and "INFORMATION" not in m and "Input Translation" not in m)
    return row


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    ensure_dirs()
    studies = build_studies()
    wanted = [a for a in sys.argv[1:] if not a.startswith("-")] or list(studies)
    failures = 0
    for name in wanted:
        cases = studies[name]
        t0 = time.time()
        results = run_cases(cases, study=f"sens_{name}")
        out = RESULTS_SENSITIVITY / f"aspen_{name}.csv"
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=INPUT_COLS + KPI_COLS + EXTRA_COLS)
            w.writeheader()
            for r in results:
                w.writerow(row_of(r))
        bad = [r.case_id for r in results if not r.status.converged]
        warn = [r.case_id for r in results if r.status.has_warnings]
        failures += len(bad)
        print(f"{name:20s} {len(results):3d} runs in {time.time() - t0:6.1f} s -> {out.name}"
              f"   failed: {bad or 'none'}   warnings: {warn or 'none'}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
