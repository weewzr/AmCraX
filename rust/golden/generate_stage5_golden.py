"""Generate the stage 5 golden reference tables (catalyst studies, end use, LCA, optimisation, MCMC calibration).

Produced ONCE by the Python reference (the ``amcrax`` package of this repository, imported from ``backend/``) with the
project venv and committed; never regenerated from Rust. Run from the repository root, naming the tables to (re)write:

    python rust/golden/generate_stage5_golden.py catalyst

Conventions are those of ``generate_stage4_golden.py`` (repr floats, "nan"/"inf" strings, errors as
{"error": class, "message": ...}); the CoolProp calls made by the new flowsheet and heat-integration states are recorded
the same way and written to ``coolprop_states.json`` (merged over every table generated in the same invocation).
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("gen4", HERE / "generate_stage4_golden.py")
G4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G4)  # imports amcrax from this repository and checks it

REPO = G4.REPO
OUT = HERE / "stage5"
GENERATOR = "rust/golden/generate_stage5_golden.py"
META = dict(G4.META, generator=GENERATOR)
enc, err, call, load = G4.enc, G4.err, G4.call, G4.load


def manifest() -> dict:
    p = OUT / "MANIFEST.json"
    if p.exists():
        m = json.loads(p.read_text(encoding="utf-8"))
        m["meta"] = META
        return m
    return {"meta": META, "files": {}}


MANIFEST = manifest()


def write_table(name: str, body: dict, n_cases: int) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    text = json.dumps(enc({"meta": dict(META, table=name), **body}), separators=(",", ":"), allow_nan=False) + "\n"
    data = text.encode("utf-8")
    (OUT / f"{name}.json").write_bytes(data)
    MANIFEST["files"][f"{name}.json"] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                                         "cases": n_cases}
    print(f"wrote rust/golden/stage5/{name}.json ({len(data)} bytes, {n_cases} cases)")


def save_manifest() -> None:
    (OUT / "MANIFEST.json").write_bytes((json.dumps(MANIFEST, indent=1, sort_keys=True) + "\n").encode("utf-8"))


def max_rel_flat(stored: dict, new: dict, keys) -> float:
    worst = 0.0
    for k in keys:
        a, b = stored.get(k), new.get(k)
        try:
            a, b = float(a), float(b)
        except (TypeError, ValueError):
            continue
        if a != b:
            worst = max(worst, abs(a - b) / max(abs(a), 1e-300))
    return worst


# ===================================================================================== catalyst studies
def catalyst() -> None:
    from amcrax.research import catalyst_comparison as cc
    from amcrax.schemas import SimulationResult

    T_GRID = [float(t) for t in range(470, 761, 5)]
    BASE = dict(P_bar=20.0, X=0.95, dT=20.0, psa=0.85, feff=cc.FURNACE_EFFICIENCY, scenario="grey")
    ASPEN_CASES = {"ru_kum_temkin_pyzhev": "kum_T499", "nire_ceo2_5ni1ru_lucentini_lhhw": "luc5_T572",
                   "nire_ceo2_2p5ni0p5ru_lucentini_lhhw": "luc25_T576", "ni_takahashi_microkinetic": "tni_T594",
                   "ru_takahashi_microkinetic": "tru_T522"}
    catalysts = {cid: {k: c[k] for k in ("label", "family", "short", "eps_b", "rho_particle", "price", "price_key")}
                 for cid, c in cc.CATALYSTS.items()}
    curves, optima, designs, flows = [], [], [], []
    for hi in (True, False):
        for cid in cc.CATALYSTS:
            c = cc.lcoh_curve(cid, T_GRID, P_bar=20.0, X=0.95, hi=hi, dT=20.0, psa=0.85, feff=BASE["feff"],
                              scenario="grey")
            curves.append({"catalyst_id": cid, "heat_integration": hi, "T_grid": T_GRID, "rows": c})
            oc = cc.optimum(c)
            grid = [oc["T_C"] + k for k in range(-5, 6)]
            loc = cc.lcoh_curve(cid, grid, P_bar=20.0, X=0.95, hi=hi, dT=20.0, psa=0.85, feff=BASE["feff"],
                                scenario="grey")
            o = cc.optimum(loc)
            optima.append({"catalyst_id": cid, "heat_integration": hi, "coarse": oc, "refine_grid": grid,
                           "refined_rows": loc, "refined": o})
            d = cc.design_point(cid, o["T_C"], 20.0, 0.95, heat_integration=hi, W_kg=o["W_kg"])
            designs.append({"kind": "python_optimum", "catalyst_id": cid, "heat_integration": hi, "T_C": o["T_C"],
                            "P_bar": 20.0, "X": 0.95, "W_kg": o["W_kg"], "result_file": None, "out": d})
            flows.append({"T_C": o["T_C"], "P_bar": 20.0, "X": 0.95, "heat_integration": hi,
                          "result": G4.dump_result(cc.kinetic_flowsheet(o["T_C"], 20.0, 0.95, hi))})
    ni_curve = next(c for c in curves if c["catalyst_id"] == cc.REFERENCE_NI and c["heat_integration"])["rows"]
    for Tn in (700.0, 735.0):
        cN = [r for r in ni_curve if abs(r["T_C"] - Tn) < 1e-9][0]
        designs.append({"kind": "fixed_ni", "catalyst_id": cc.REFERENCE_NI, "heat_integration": True, "T_C": Tn,
                        "P_bar": 20.0, "X": 0.95, "W_kg": cN["W_kg"], "result_file": None,
                        "out": cc.design_point(cc.REFERENCE_NI, Tn, 20.0, 0.95, W_kg=cN["W_kg"])})
    pinch = []
    for cid, tag in ASPEN_CASES.items():
        for hi in (True, False):
            fn = f"results/research/aspen_kinetic/ci_{tag}_P20_W100_{'hi' if hi else 'nohi'}.json"
            res = SimulationResult.model_validate(load(fn)["aspen"]["flowsheet_result"])
            T, X = res.inputs.reactor_temperature_C, res.kpis.nh3_conversion
            d = cc.design_point(cid, T, 20.0, round(X, 6), heat_integration=hi, W_kg=100.0, result=res)
            designs.append({"kind": "aspen", "catalyst_id": cid, "heat_integration": hi, "T_C": T, "P_bar": 20.0,
                            "X": round(X, 6), "W_kg": 100.0, "result_file": fn, "out": d})
            py = cc.design_point(cid, T, 20.0, X, heat_integration=hi, W_kg=100.0)
            designs.append({"kind": "python_same_T_X", "catalyst_id": cid, "heat_integration": hi, "T_C": T,
                            "P_bar": 20.0, "X": X, "W_kg": 100.0, "result_file": None, "out": py})
            for dT in (10.0, 20.0, 30.0, 40.0, 50.0):
                pinch.append({"result_file": fn, "dT_min_K": dT, "out": cc.heat_accounting(res, dT)})
    base = SimulationResult.model_validate(load("results/simulations/baseline.json"))
    for dT in (10.0, 20.0, 30.0, 40.0, 50.0):
        pinch.append({"result_file": "results/simulations/baseline.json", "dT_min_K": dT,
                      "out": cc.heat_accounting(base, dT)})
    masses = []
    for cid in cc.CATALYSTS:
        for (T, P, X) in ((480.0, 20.0, 0.95), (600.0, 20.0, 0.95), (650.0, 10.0, 0.9), (700.0, 30.0, 0.99),
                          (450.0, 20.0, 0.95), (550.0, 5.0, 0.97)):
            masses.append({"catalyst_id": cid, "T_C": T, "P_bar": P, "X": X, "W_kg": cc.required_mass_kg(cid, T, P, X),
                           "X_eq": cc.eq_conversion(T, P)})
    # stored-result reproduction flags (the Rust verifier compares with the stored files itself)
    stored = []
    rows_csv = list(csv.DictReader(open(REPO / "results/research/catalyst_comparison/catalyst_design_curves.csv",
                                        encoding="utf-8")))
    new_rows = [dict(catalyst_id=c["catalyst_id"], heat_integration=str(c["heat_integration"]), **r)
                for c in curves for r in c["rows"]]
    keys = [k for k in rows_csv[0] if k not in ("catalyst_id", "heat_integration", "source_type")]
    dev = max((max_rel_flat(a, b, keys) for a, b in zip(rows_csv, new_rows)), default=0.0)
    stored.append({"file": "results/research/catalyst_comparison/catalyst_design_curves.csv", "rows": len(rows_csv),
                   "new_rows": len(new_rows), "python_max_rel_dev": dev,
                   "same_keys": all(a["catalyst_id"] == b["catalyst_id"] and a["heat_integration"] == b["heat_integration"]
                                    for a, b in zip(rows_csv, new_rows))})
    srows = load("results/research/catalyst_comparison/catalyst_comparison.json")["rows"]
    matched, worst = 0, 0.0
    for s in srows:
        for d in designs:
            if d["kind"] in ("python_optimum", "aspen", "fixed_ni") and d["catalyst_id"] == s["catalyst_id"] \
                    and d["heat_integration"] == s["heat_integration"] and d["T_C"] == s["T_C"] \
                    and (s.get("source_type") == "aspen") == (d["kind"] == "aspen"):
                matched += 1
                worst = max(worst, max_rel_flat(s, d["out"], [k for k in s if not isinstance(s[k], (dict, list))]))
    stored.append({"file": "results/research/catalyst_comparison/catalyst_comparison.json", "rows": len(srows),
                   "matched_rows": matched, "python_max_rel_dev": worst})
    body = {"catalysts": catalysts, "T_grid": T_GRID, "curves": curves, "optima": optima, "designs": designs,
            "pinch_dT": pinch, "masses": masses, "flowsheets": flows, "stored": stored,
            "constants": {"FURNACE_EFFICIENCY": cc.FURNACE_EFFICIENCY, "THERMAL_LOSS_FRACTION": cc.THERMAL_LOSS_FRACTION,
                          "CATALYST_LIFETIME_YR": cc.CATALYST_LIFETIME_YR, "FEED_NH3_KMOL_H": cc.FEED_NH3_KMOL_H,
                          "LCA_DISTANCE_KM": cc.LCA_DISTANCE_KM}}
    write_table("catalyst", body, sum(len(c["rows"]) for c in curves) + len(designs) + len(pinch) + len(masses))
    print("stored:", json.dumps(stored))


TABLES = {"catalyst": catalyst}


def main() -> None:
    names = sys.argv[1:] or list(TABLES)
    G4.install_recorder()
    try:
        for n in names:
            TABLES[n]()
    finally:
        G4.remove_recorder()
    prev = OUT / "coolprop_states.json"
    if prev.exists():  # keep the states recorded by tables generated in earlier invocations
        for r in json.loads(prev.read_text(encoding="utf-8"))["states"]:
            k = (r["fluid"], r["out"], r["in"], r["phase"], float(r["a"]), float(r["b"]))
            G4.STATES.setdefault(k, r)
    recs = sorted(G4.STATES.values(), key=lambda r: (r["fluid"], r["out"], r["in"], r["phase"], r["b"], r["a"]))
    write_table("coolprop_states", {
        "columns": "as rust/golden/stage4/coolprop_states.json",
        "recorded_from": "the tables of this generator run: " + ", ".join(names),
        "states": recs}, len(recs))
    save_manifest()


if __name__ == "__main__":
    main()
