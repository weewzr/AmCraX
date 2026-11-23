"""Compare the Aspen Plus kinetic RPLUG results with the independent Python PFR and with RGibbs equilibrium.

Reads results/research/aspen_kinetic/<case_id>.json (written by run_kinetic_cases.py, which also stores the
Python PFR at identical conditions under ``python_pfr``) and writes results/research/validation/aspen_kinetic.json
plus results/research/aspen_kinetic/aspen_vs_python.csv.

Tolerances (fixed before the comparison; not tuned):
* conversion: 0.005 absolute. Aspen evaluates Keq from its own Gibbs energies and the PENG-ROB property method;
  the Python model uses NASA7 ideal-gas data; both integrate the same rate law.
* isothermal duty and residence time: 2 % relative (PENG-ROB vs ideal-gas enthalpy and density).
* non-isothermal outlet temperature: 2 K.
* kinetic conversion must not exceed the RGibbs conversion at the same T, P, feed (+1e-4 numerical margin).

Usage:  python aspen/automation/validate_kinetic_vs_python.py
"""
from __future__ import annotations

import csv
import datetime as dt
import json

from amcrax.paths import ROOT

IN = ROOT / "results" / "research" / "aspen_kinetic"
OUT = ROOT / "results" / "research" / "validation" / "aspen_kinetic.json"
X_TOL, REL_TOL, T_TOL, EQ_MARGIN = 0.005, 0.02, 2.0, 1e-4


def _item(id_, desc, method, observed, expected, tol, unit, ok, files, ref="python model amcrax.reactor.pfr"):
    return {"id": id_, "description": desc, "method": method, "reference_source": ref, "observed": observed,
            "expected": expected, "tolerance": tol, "unit": unit,
            "status": ("pass" if ok else "fail") if ok is not None else "informational", "source_files": files}


def main() -> int:
    items, rows = [], []
    for f in sorted(IN.glob("k*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        cid, files = r["case_id"], [f.relative_to(ROOT).as_posix()]
        if r.get("run_status") in ("failed", "error"):
            items.append(_item(f"{cid}_run", f"Aspen run status of {cid}", "COM run status", r.get("run_status"),
                               "ok", None, "-", False, files, ref="Aspen Plus run status"))
            continue
        a = r["aspen"]
        inp = r["inputs"]["reactor"]
        mode = inp["thermal_mode"]
        if r["configuration"] == "integrated":
            base = json.loads((ROOT / "results" / "simulations" / "baseline.json").read_text(encoding="utf-8"))
            x_eq = base["kpis"]["nh3_conversion"]
            xa = a["conversion_of_reactor_inlet_NH3"]
            same = inp["temperature_C"] == base["inputs"]["reactor_temperature_C"] and \
                inp["pressure_bar"] == base["inputs"]["reactor_pressure_bar"]
            items.append(_item(f"{cid}_below_rgibbs", "Integrated flowsheet: RPLUG CRACKER conversion not above the "
                               "stored RGibbs baseline conversion at the same T, P", "X_rplug <= X_rgibbs + 1e-4",
                               xa, x_eq, EQ_MARGIN, "-", (xa <= x_eq + EQ_MARGIN) if same else None,
                               files + ["results/simulations/baseline.json"], ref="aspen RGibbs baseline (stored)"))
            fr = a.get("flowsheet_result", {})
            items.append(_item(f"{cid}_flowsheet_status", "Integrated flowsheet with RPLUG CRACKER solved",
                               "Aspen run status", a["status"], "converged", None, "-",
                               bool(a["status"].get("converged")), files, ref="Aspen Plus run status"))
            if fr:
                items.append(_item(f"{cid}_reactor_duty", "Integrated RPLUG CRACKER duty vs RGibbs baseline duty",
                                   "informational comparison", fr["kpis"].get("reactor_duty_kW"),
                                   base["kpis"]["reactor_duty_kW"], None, "kW", None,
                                   files + ["results/simulations/baseline.json"], ref="aspen RGibbs baseline (stored)"))
            continue
        py = r["python_pfr"]["outlet"]
        xa, xp = a["conversion_of_reactor_inlet_NH3"], py["conversion"]
        xeq = a["equilibrium_reference"]["conversion_of_reactor_inlet_NH3"]
        rp = a["rplug"]
        lbl = f"{inp['temperature_C']:g} degC, {inp['pressure_bar']:g} bar, {r['inputs']['reactor']['catalyst_mass_kg']:g} kg, {mode}"
        items.append(_item(f"{cid}_conversion", f"NH3 conversion Aspen RPLUG vs Python PFR ({lbl})",
                           "|X_aspen - X_python|", xa, xp, X_TOL, "-", abs(xa - xp) <= X_TOL, files))
        items.append(_item(f"{cid}_below_equilibrium", f"Kinetic conversion not above RGibbs equilibrium ({lbl})",
                           "X_rplug <= X_rgibbs + 1e-4 (same run, same feed)", xa, xeq, EQ_MARGIN, "-",
                           xa <= xeq + EQ_MARGIN, files, ref="aspen RGibbs block REQ in the same model"))
        if mode == "isothermal":
            items.append(_item(f"{cid}_duty", f"Isothermal reactor duty ({lbl})", "relative difference",
                               rp["duty"], py["heat_input_kW"], REL_TOL, "kW",
                               abs(rp["duty"] / py["heat_input_kW"] - 1) <= REL_TOL, files))
        else:
            items.append(_item(f"{cid}_T_out", f"Outlet temperature ({lbl})", "|T_aspen - T_python|",
                               a["product"]["T_C"], py["T_C"], T_TOL, "degC",
                               abs(a["product"]["T_C"] - py["T_C"]) <= T_TOL, files))
        items.append(_item(f"{cid}_residence_time", f"Gas residence time in the bed ({lbl})", "relative difference",
                           rp.get("residence_time_s"), py["residence_time_s"], REL_TOL, "s",
                           abs(rp["residence_time_s"] / py["residence_time_s"] - 1) <= REL_TOL, files))
        if inp["pressure_drop"]:
            items.append(_item(f"{cid}_pressure_drop", f"Ergun pressure drop ({lbl})", "informational",
                               inp["pressure_bar"] - a["product"]["P_bar"], py["pressure_drop_bar"], None, "bar",
                               None, files))
        rows.append({"case_id": cid, "T_C": inp["temperature_C"], "P_bar": inp["pressure_bar"],
                     "W_kg": inp["catalyst_mass_kg"], "mode": mode, "X_aspen": xa, "X_python": xp, "dX": xa - xp,
                     "X_eq_aspen_rgibbs": xeq, "X_eq_python": py["X_eq_outlet"], "duty_aspen_kW": rp["duty"],
                     "heat_python_kW": py["heat_input_kW"], "T_out_aspen_C": a["product"]["T_C"],
                     "T_out_python_C": py["T_C"], "tau_aspen_s": rp.get("residence_time_s"),
                     "tau_python_s": py["residence_time_s"]})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = {"provenance": {"generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                          "script": "aspen/automation/validate_kinetic_vs_python.py", "source_type": "aspen vs python",
                          "inputs_summary": "results/research/aspen_kinetic/k*.json",
                          "model_versions": {"aspen": "Aspen Plus V15", "python": "amcrax.reactor.pfr"}},
           }
    for it in items:  # the shared convention asks for a plain list of items; provenance travels with each item
        it["provenance"] = doc["provenance"]
    OUT.write_text(json.dumps(items, indent=2), encoding="utf-8")
    # Phase 2 (task K1): evidence_kind on every item + k1p2_ items. NOTE: this script rewrites the whole file
    # (pre-existing behaviour); run summarise_catalyst_studies.py afterwards to restore the cat_ items.
    import importlib.util
    _sp = importlib.util.spec_from_file_location(
        "kinetics_phase2_validation", ROOT / "scripts" / "research" / "kinetics_phase2_validation.py")
    _m = importlib.util.module_from_spec(_sp)
    _sp.loader.exec_module(_m)
    _m.apply(("aspen_kinetic",))
    if rows:
        with open(IN / "aspen_vs_python.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    n = {s: sum(1 for i in items if i["status"] == s) for s in ("pass", "fail", "informational")}
    print(n, [i["id"] for i in items if i["status"] == "fail"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
