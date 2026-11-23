"""Quantitative cause of the Aspen RPLUG 'above RGibbs equilibrium' failures (Phase 2, task K1 item 3).

For every stored standalone Aspen RPLUG case that has an RGibbs reference (results/research/aspen_kinetic/c[vs]_*.json)
this script computes, with the AmCraX Python thermodynamics (no Aspen run, no fitting):

* X_eq_ideal      ideal-gas equilibrium, Kp from the ln K fit actually entered in Aspen (aspen_kinetics_spec.json)
* X_eq_PR         Peng-Robinson fugacity equilibrium (amcrax.thermodynamics, k_ij = 0)
* K_phi           phi_N2^0.5 phi_H2^1.5 / phi_NH3 at the PR equilibrium composition
* Z               PR compressibility at the kinetic stopping state
* X_stop_kinetic  the state at which the Aspen LHHW driving force vanishes, given the concentration basis:
                    MOLARITY : C_i = y_i P / (Z R T)  ->  Q_y (P/P0) = Kp * Z     (Z from PENG-ROB, as Aspen does)
                    MOLEFRAC : term-2 constant contains P = 20 bar  ->  Q_y (P/P0) = Kp   (ideal gas)
                    PARTIALPRES (Kum): p_i = y_i P  ->  Q_y (P/P0) = Kp
  The thermodynamically consistent stopping state would be Q_y (P/P0) K_phi = Kp (= RGibbs with PENG-ROB).

Output: results/research/kinetics/equilibrium_consistency.json (+ .csv). Source type: python (analysis of stored
aspen results). Deterministic; run from the AmCraX root.
"""
from __future__ import annotations

import csv
import glob
import json
import math
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from scipy.optimize import brentq  # noqa: E402

from amcrax.thermodynamics import peng_robinson as pr  # noqa: E402
from amcrax.thermodynamics.equilibrium import equilibrium_constant, solve_equilibrium  # noqa: E402

SPEC = os.path.join(ROOT, "results", "research", "kinetics", "aspen_kinetics_spec.json")
OUT_DIR = os.path.join(ROOT, "results", "research", "kinetics")
TOL = 1e-4  # tolerance of the aspen_kinetic *_below_equilibrium items (unchanged)


def kp_fit(T_K: float, fit: dict) -> float:
    return math.exp(fit["A"] + fit["B"] / T_K + fit["C"] * math.log(T_K) + fit["D"] * T_K)


def _state(xi: float, feed: dict[str, float]) -> dict[str, float]:
    n = dict(feed)
    n["NH3"] = feed["NH3"] - xi
    n["N2"] = feed.get("N2", 0.0) + 0.5 * xi
    n["H2"] = feed.get("H2", 0.0) + 1.5 * xi
    return n


def _y(n):
    tot = sum(n.values())
    return {k: v / tot for k, v in n.items()}


def _qy(y):
    return y["N2"] ** 0.5 * y["H2"] ** 1.5 / y["NH3"]


def stop_state(T_K, P_bar, feed, Kp, basis):
    """Conversion of feed NH3 at which the Aspen driving force (for this concentration basis) vanishes."""
    def resid(xi):
        n = _state(xi, feed)
        y = _y(n)
        rhs = Kp
        if basis == "MOLARITY":
            rhs = Kp * pr.compressibility(y, T_K, P_bar)
        return math.log(_qy(y) * P_bar) - math.log(rhs)
    hi = feed["NH3"] * (1 - 1e-12)
    xi = brentq(resid, 1e-9 * feed["NH3"], hi, xtol=1e-14, rtol=1e-15, maxiter=500)
    n = _state(xi, feed)
    y = _y(n)
    return xi / feed["NH3"], y, pr.compressibility(y, T_K, P_bar)


def pr_equilibrium(T_K, P_bar, feed, Kp):
    def resid(xi):
        y = _y(_state(xi, feed))
        ph = pr.fugacity_coefficients(y, T_K, P_bar)
        return math.log(_qy(y) * P_bar) + 0.5 * math.log(ph["N2"]) + 1.5 * math.log(ph["H2"]) - math.log(ph["NH3"]) - math.log(Kp)
    xi = brentq(resid, 1e-9 * feed["NH3"], feed["NH3"] * (1 - 1e-12), xtol=1e-14, rtol=1e-15, maxiter=500)
    return xi / feed["NH3"], _y(_state(xi, feed))


def main() -> int:
    spec = json.load(open(SPEC, encoding="utf-8"))
    fit = spec["equilibrium_constant_fit"]
    basis_of = {}
    for c in spec["catalysts"]:
        if c.get("aspen_native"):
            cb = c["concentration_basis"].lower()
            basis_of[c["catalyst_id"]] = "PARTIALPRES" if "partial" in cb else "MOLARITY"
        else:
            basis_of[c["catalyst_id"]] = "MOLEFRAC"
    rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, "results", "research", "aspen_kinetic", "c[vs]_*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        a = d.get("aspen") or {}
        eq = a.get("equilibrium_reference")
        if not eq or d.get("run_status") != "ok":
            continue
        cid = d["kinetic_spec"]["catalyst_id"]
        T_K = a["product"]["T_C"] + 273.15
        P = a["product"]["P_bar"]
        if abs(a["feed"]["T_C"] - a["product"]["T_C"]) > 0.01 or d["inputs"]["reactor"]["thermal_mode"] != "isothermal":
            continue
        feed = {k: v for k, v in a["feed"]["flows_kmol_h"].items() if k in ("NH3", "H2", "N2") }
        Kp = kp_fit(T_K, fit)
        basis = basis_of[cid]
        X_stop, y_stop, Z_stop = stop_state(T_K, P, feed, Kp, basis)
        # amcrax.thermodynamics.solve_equilibrium(eos="pr") cannot be used on this feed: its upper bracket
        # (all products consumed by synthesis) yields -1e-16 mole fractions and peng_robinson raises (defect noted in
        # the hand-back). The same equations are solved here on the cracking extent: ln(Q_y P/P0) + ln K_phi = ln Kp,
        # with Kp from amcrax.thermodynamics (ideal: K_phi = 1).
        Kp_thermo = equilibrium_constant(T_K)
        X_ideal = stop_state(T_K, P, feed, Kp_thermo, "IDEAL")[0]
        X_pr, y_pr = pr_equilibrium(T_K, P, feed, Kp_thermo)
        ph = pr.fugacity_coefficients(y_pr, T_K, P)
        K_phi = ph["N2"] ** 0.5 * ph["H2"] ** 1.5 / ph["NH3"]
        # cross-check against the library solver on a pure-NH3 feed of 100 (works when the numbers are round)
        try:
            lib = solve_equilibrium(T_K, P, {"NH3": 100.0}, eos="pr").conversion
        except (ValueError, RuntimeError):
            lib = None
        X_rplug = a["conversion_of_reactor_inlet_NH3"]
        X_rg = eq["conversion_of_reactor_inlet_NH3"]
        excess = X_rplug - X_rg
        rows.append({
            "case_id": d["case_id"], "catalyst_id": cid, "concentration_basis": basis, "T_C": round(T_K - 273.15, 3),
            "P_bar": P, "W_kg": d["inputs"]["reactor"]["catalyst_mass_kg"],
            "X_rplug_aspen": X_rplug, "X_rgibbs_aspen": X_rg, "excess_aspen": excess,
            "fails_1e-4_check": excess > TOL,
            "X_eq_ideal_python": X_ideal, "X_eq_PR_python": X_pr, "X_eq_PR_library_pure_NH3": lib, "K_phi_PR": K_phi,
            "Z_PR_at_stop": Z_stop, "X_stop_kinetic_predicted": X_stop,
            "predicted_excess_stop_minus_PR": X_stop - X_pr,
            "python_PR_minus_aspen_rgibbs": X_pr - X_rg,
            "rplug_minus_predicted_stop": X_rplug - X_stop,
            "near_equilibrium": abs(X_rplug - X_stop) < 2e-4,
        })
    fails = [r for r in rows if r["fails_1e-4_check"]]
    near = [r for r in rows if r["near_equilibrium"]]
    summary = {
        "n_cases": len(rows), "n_failing_cases": len(fails),
        "failing_cases": [r["case_id"] for r in fails],
        "max_abs_python_PR_minus_aspen_rgibbs": max(abs(r["python_PR_minus_aspen_rgibbs"]) for r in rows),
        "near_equilibrium_cases": len(near),
        "max_abs_rplug_minus_predicted_stop_near_equilibrium": max(abs(r["rplug_minus_predicted_stop"]) for r in near) if near else None,
        "failing_cases_detail": [{k: r[k] for k in ("case_id", "concentration_basis", "T_C", "P_bar", "W_kg", "excess_aspen",
                                                      "predicted_excess_stop_minus_PR", "K_phi_PR", "Z_PR_at_stop",
                                                      "rplug_minus_predicted_stop")} for r in fails],
    }
    out = {
        "provenance": {
            "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "script": "scripts/research/kinetics_equilibrium_consistency.py",
            "source_type": "python (analysis of stored aspen results)",
            "inputs_summary": "results/research/aspen_kinetic/c[vs]_*.json (isothermal, with RGibbs reference); "
                              "results/research/kinetics/aspen_kinetics_spec.json (ln K fit entered in Aspen)",
            "model_versions": {"thermo": "amcrax.thermodynamics (NASA7/GRI-Mech 3.0; Peng-Robinson, k_ij = 0)"},
        },
        "method": __doc__.strip(),
        "tolerance_of_aspen_check": TOL,
        "summary": summary,
        "rows": rows,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "equilibrium_consistency.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    with open(os.path.join(OUT_DIR, "equilibrium_consistency.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
