"""Re-derivation of the two Takahashi prediction failures KIN-NI-PRED / KIN-RU-PRED (Phase 2, task K1 item 4).

Independent re-implementation of takahashi2016kinetic Eqs. 5-19 (coverage QSS + isothermal PFR over catalyst mass,
1 atm, mole-fraction basis, total flow fixed by the space velocity), written here without amcrax.reactor, to check:

  A. implementation: the same Table 1 parameters give the same predictions as the stored validation
     (results/validation/kinetics_validation.csv) -> no hidden unit/basis error in amcrax.kinetics/amcrax.reactor;
  B. basis alternatives that the paper leaves open, each evaluated with ONE anchor point (as Phase 1):
       B1 SV defined on the NH3 flow instead of the total flow (diluted runs then have a larger total flow);
       B2 the rate constants of Table 2 (500 degC, printed by the paper) instead of Table 1 evaluated at 773.15 K
          (Table 1 reproduces Table 2 only to 2-7 %); Ni only, because all Ni dilution/H2 series are at 500 degC;
       B3 temperature conversion T = T_C + 273 instead of 273.15.
No parameter is fitted. The anchor (Fig. 3a / 4a lowest temperature) fixes the unreported W/F only.
Output: results/research/kinetics/takahashi_rederivation.json. Deterministic; run from the AmCraX root.
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "backend"))

import yaml  # noqa: E402
from scipy.integrate import solve_ivp  # noqa: E402
from scipy.optimize import brentq  # noqa: E402

REG = yaml.safe_load(open(os.path.join(ROOT, "backend", "amcrax", "data", "kinetics.yaml"), encoding="utf-8"))
R = 8.314
TOL = 0.05


def consts_table1(cid: str, T_K: float) -> dict[str, float]:
    p = {k: float(v["value"]) for k, v in REG["catalysts"][cid]["parameters"].items()}
    RT = R * T_K
    k1 = p["A1"]
    K1 = p["A5"] * math.exp(-p["Ea5"] * 1e3 / RT)
    k4 = p["A4"] * math.exp(-p["Ea4"] * 1e3 / RT)
    K4 = p["A6"] * math.exp(-p["Ea4"] * 1e3 / RT)
    return {"k1": k1, "km1": k1 / K1, "k2": p["A2"] * math.exp(-p["Ea2"] * 1e3 / RT),
            "k3": p["A3"] * math.exp(-p["Ea3"] * 1e3 / RT), "k4": k4, "km4": k4 / K4}


def consts_table2(cid: str) -> dict[str, float]:
    r = REG["catalysts"][cid]["reference_values_773K"]
    k1 = float(REG["catalysts"][cid]["parameters"]["A1"]["value"])
    return {"k1": k1, "km1": r["k_minus1"], "k2": r["k2"], "k3": r["k3"], "k4": r["k4"], "km4": r["k_minus4"]}


def rate(c: dict[str, float], y_nh3: float, y_h2: float) -> float:
    """r2 [mol s-1 g-1] from Eqs. 5-14 (QSS), site balance solved for ln(theta_s)."""
    if y_nh3 <= 0:
        return 0.0

    def parts(ths):
        a = c["k1"] * y_nh3 * ths / (c["km1"] + c["k2"] * ths ** 3)
        r2 = c["k2"] * a * ths ** 3
        return a, math.sqrt(r2 / (2 * c["k3"])), math.sqrt((1.5 * r2 + c["km4"] * max(y_h2, 0) * ths ** 2) / c["k4"]), r2

    u = brentq(lambda u: math.exp(u) + sum(parts(math.exp(u))[:3]) - 1.0, -300.0, 0.0, xtol=1e-14, rtol=1e-13)
    return parts(math.exp(u))[3]


def pfr(c, y_feed: dict[str, float], m_over_F: float) -> float:
    """Isothermal PFR over m [g] per total feed flow F0 [mol/s]; returns NH3 conversion (Eqs. 15-19)."""
    n0 = {k: y_feed.get(k, 0.0) for k in ("NH3", "H2", "N2", "Ar")}

    def f(_m, x):
        nh3 = max(n0["NH3"] * (1 - x[0]), 0.0)
        ext = n0["NH3"] * x[0]
        h2 = n0["H2"] + 1.5 * ext
        tot = 1.0 + ext
        return [rate(c, nh3 / tot, h2 / tot) / n0["NH3"]]

    s = solve_ivp(f, (0.0, m_over_F), [0.0], method="LSODA", rtol=1e-9, atol=1e-12)
    return float(s.y[0, -1])


def points(cid: str):
    V = REG["validation"]
    sets = {"ni_takahashi_microkinetic": ["takahashi_ni_fig3a", "takahashi_ni_fig3b", "takahashi_ni_fig5a"],
            "ru_takahashi_microkinetic": ["takahashi_ru_fig4a", "takahashi_ru_fig4b", "takahashi_ru_fig5b"]}[cid]
    out = []
    for ds in sets:
        d = V[ds]
        if "P_atm" in d:
            out += [(ds, T, {"NH3": 1.0}, X / 100) for T, X in zip(d["T_C"], d["X_pct"])]
        elif "p_H2_atm" in d:
            out += [(ds, d["T_C"], {"NH3": d["p_NH3_atm"], "H2": h, "Ar": 1 - d["p_NH3_atm"] - h}, X / 100)
                    for h, X in zip(d["p_H2_atm"], d["X_pct"])]
        else:
            out += [(ds, d["T_C"], {"NH3": p, "Ar": 1 - p}, X / 100) for p, X in zip(d["p_NH3_atm"], d["X_pct"])]
    return out


def evaluate(cid: str, variant: str) -> dict:
    t0 = 273.0 if variant == "B3_T_plus_273" else 273.15
    pts = points(cid)
    anchor = pts[0]

    def consts(T_C):
        if variant == "B2_table2_constants":
            if abs(T_C - 500.0) > 1e-9:
                return None
            return consts_table2(cid)
        return consts_table1(cid, T_C + t0)

    def mF(y):  # total-flow scale factor: SV on total flow (default) or on NH3 flow (B1)
        return 1.0 / y["NH3"] if variant == "B1_SV_on_NH3_flow" else 1.0

    ca = consts(anchor[1])
    if ca is None:
        anchor = next(p for p in pts if abs(p[1] - 500.0) < 1e-9 and p[2] == {"NH3": 1.0})
        ca = consts(anchor[1])
    wf = brentq(lambda w: pfr(ca, anchor[2], w) - anchor[3], 1e-6, 1e5, xtol=1e-12, rtol=1e-10)
    rows = []
    for ds, T, y, X in pts:
        c = consts(T)
        if c is None:
            continue
        Xm = pfr(c, y, wf / mF(y))
        rows.append({"dataset": ds, "T_C": T, "feed_y": y, "X_literature": X, "X_model": Xm, "deviation": Xm - X,
                     "anchor": (ds, T, y) == anchor[:3]})
    pred = [r for r in rows if not r["anchor"]]
    worst = max(pred, key=lambda r: abs(r["deviation"]))
    return {"variant": variant, "anchor": {"dataset": anchor[0], "T_C": anchor[1], "X": anchor[3]},
            "inferred_m_over_F_total_g_s_per_mol": wf, "n_predictions": len(pred),
            "max_abs_deviation": abs(worst["deviation"]), "worst_point": worst,
            "n_outside_0.05": sum(abs(r["deviation"]) > TOL for r in pred),
            "rms_deviation": math.sqrt(sum(r["deviation"] ** 2 for r in pred) / len(pred)), "rows": rows}


def main() -> int:
    stored = {}
    with open(os.path.join(ROOT, "results", "validation", "kinetics_validation.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["dataset"].startswith("takahashi_") and "Table2" not in r["dataset"]:
                stored.setdefault(r["catalyst"], []).append(float(r["model"]))
    res = {}
    for cid in ("ni_takahashi_microkinetic", "ru_takahashi_microkinetic"):
        variants = ["A_as_implemented", "B1_SV_on_NH3_flow", "B3_T_plus_273"]
        if cid.startswith("ni_"):
            variants.insert(2, "B2_table2_constants")
        res[cid] = {v: evaluate(cid, v) for v in variants}
        a = res[cid]["A_as_implemented"]["rows"]
        res[cid]["A_reproduces_stored_validation_max_abs_diff"] = max(
            abs(r["X_model"] - s) for r, s in zip(a, stored[cid]))
    out = {
        "provenance": {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "script": "scripts/research/kinetics_takahashi_rederivation.py",
                       "source_type": "python (independent re-implementation; literature data read from figures)",
                       "inputs_summary": "backend/amcrax/data/kinetics.yaml (Table 1, Table 2, validation sets); "
                                         "results/validation/kinetics_validation.csv (stored Phase 1 predictions)",
                       "model_versions": {"python": "scipy LSODA, brentq"}},
        "method": __doc__.strip(), "tolerance": TOL,
        "results": res,
    }
    with open(os.path.join(ROOT, "results", "research", "kinetics", "takahashi_rederivation.json"), "w",
              encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    for cid, r in res.items():
        print(cid, "reproduces stored:", r["A_reproduces_stored_validation_max_abs_diff"])
        for v, e in r.items():
            if isinstance(e, dict):
                w = e["worst_point"]
                print(f"  {v}: max|dX|={e['max_abs_deviation']:.4f} n>0.05={e['n_outside_0.05']} rms={e['rms_deviation']:.4f} "
                      f"worst {w['dataset']} T={w['T_C']} y={w['feed_y']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
