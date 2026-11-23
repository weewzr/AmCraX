"""Summarise the catalyst-specific Aspen RPLUG runs (research expansion, workstream A part 2).

Usage (from the project root, after scripts/env.ps1, once the case lists of make_catalyst_study_cases.py have
been run with run_kinetic_cases.py)::

    python aspen/automation/summarise_catalyst_studies.py

Reads   results/research/aspen_kinetic/c*.json (cv_ validation, cs_ studies, ci_ integrated), the kinetics
        workstream's aspen_kinetics_spec.json and the stored RGibbs flowsheet sweeps in results/sensitivity
        (read only, not re-run).
Writes  results/research/aspen_kinetic/catalyst_standalone_runs.csv / .json   every standalone run
        results/research/aspen_kinetic/catalyst_mass_targets.json / .csv      W for 95/99 % of equilibrium
        results/research/aspen_kinetic/catalyst_integrated.csv                 integrated flowsheet KPIs
        results/research/aspen_kinetic/catalyst_comparison.json               summary table (source_type aspen)
        results/research/aspen_kinetic/aspen_kinetic_plotdata.csv              data behind the figures
        results/figures/research/aspen_kinetic_*.png
        results/research/validation/aspen_kinetic.json  (items with id prefix 'cat_' replaced; others kept)
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

IN = ROOT / "results" / "research" / "aspen_kinetic"
VAL = ROOT / "results" / "research" / "validation" / "aspen_kinetic.json"
SPEC = ROOT / "results" / "research" / "kinetics" / "aspen_kinetics_spec.json"
SENS = ROOT / "results" / "sensitivity"
NOW = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
SCRIPT = "aspen/automation/summarise_catalyst_studies.py"
X_TOL, REL_TOL, EQ_MARGIN = 0.005, 0.02, 1e-4
VM_STP = 22.414  # m3/kmol at 0 degC, 1 atm (assumption: GHSV reference state)
APPROX = {"ni_takahashi_microkinetic", "ru_takahashi_microkinetic"}
SHORT = {"ru_kum_temkin_pyzhev": "Ru/Al2O3 (Kum)", "nire_ceo2_5ni1ru_lucentini_lhhw": "5Ni1Ru/CeO2 (Lucentini)",
         "nire_ceo2_2p5ni0p5ru_lucentini_lhhw": "2.5Ni0.5Ru/CeO2 (Lucentini)",
         "ni_takahashi_microkinetic": "Ni/MgO (Takahashi, LHHW approx.)",
         "ru_takahashi_microkinetic": "Ru/MgO (Takahashi, LHHW approx.)"}
ORDER = list(SHORT)
ASSUMPTIONS = [
    {"name": "Catalyst operating temperature (part 2)", "value": "lowest T giving X = 0.95 with 100 kg catalyst per "
     "100 kmol/h NH3 at 20 bar, isothermal; rounded up to 1 degC", "unit": "degC", "source_type": "assumption",
     "source": "definition of this study; T from results/research/kinetics/study_temperature_for_target_conversion.json",
     "applicability_note": "99 % at 20 bar is equilibrium-limited below about 685 degC for every catalyst, so a 99 % "
     "target would not discriminate between catalysts."},
    {"name": "Takahashi Ni/MgO and Ru/MgO in Aspen", "value": "fitted LHHW approximation (best_native_approximation), "
     "mole-fraction basis, used only at 20 bar", "unit": "-", "source_type": "python",
     "source": "results/research/kinetics/aspen_kinetics_spec.json (kinetics workstream fit to the microkinetic law)",
     "applicability_note": "Not the published law; rate error RMS 12 %, max about 50 %. Integrated cases run the "
     "cracker at 20.2 bar (heater outlet), 1 % above the pressure in the fitted term-2 constant."},
    {"name": "H2 seed in isothermal catalyst runs", "value": "1e-6 of the NH3 pre-cracked (1e-3 in adiabatic runs, "
     "1e-4 kmol/h-scale H2SEED stream in integrated runs)", "unit": "-", "source_type": "assumption",
     "source": "numerical requirement (Kum rate singular at pH2 = 0); part 1 tests", "applicability_note":
     "Python comparison uses the same seeded feed."},
    {"name": "GHSV reference state", "value": "NH3 feed volume at 0 degC, 1 atm (22.414 m3/kmol) over the bed volume",
     "unit": "h-1", "source_type": "assumption", "source": "convention of this study", "applicability_note":
     "Bed volume = W/((1-eps) rho_p) with the bed properties of aspen_kinetics_spec.json."},
    {"name": "Adiabatic catalyst runs without pressure drop", "value": "inlet 650 degC, 20 bar, 100 kg, no Ergun",
     "unit": "-", "source_type": "assumption", "source": "choice of this study", "applicability_note":
     "The Lucentini particle size (0.1 mm lab powder) would give an unrealistic Ergun pressure drop."},
    {"name": "Effectiveness factor", "value": 1.0, "unit": "-", "source_type": "assumption",
     "source": "powder kinetics applied directly to the bed", "applicability_note":
     "Industrial pellets would need an effectiveness factor below 1; catalyst masses are lower bounds."},
]


def prov(inputs: str, source_type: str = "aspen") -> dict:
    return {"generated_utc": NOW, "script": SCRIPT, "source_type": source_type, "inputs_summary": inputs,
            "model_versions": {"aspen": "Aspen Plus V15 (PENG-ROB), RPLUG + RGIBBS reference",
                               "python": "amcrax.reactor.pfr.simulate_pfr",
                               "kinetics": "results/research/kinetics/aspen_kinetics_spec.json (version 2)"}}


def wcsv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def item(id_, desc, method, observed, expected, tol, unit, ok, files, ref):
    return {"id": id_, "description": desc, "method": method, "reference_source": ref, "observed": observed,
            "expected": expected, "tolerance": tol, "unit": unit,
            "status": ("pass" if ok else "fail") if ok is not None else "informational", "source_files": files,
            "provenance": prov("results/research/aspen_kinetic/c*.json", "aspen vs python")}


def in_range(v: dict, T_C: float, P: float) -> bool:
    TK = T_C + 273.15
    return (v["T_min_K"] - 1e-6 <= TK <= v["T_max_K"] + 1e-6) and (v["P_min_bar"] - 1e-3 <= P <= v["P_max_bar"] + 1e-3)


def load_runs(spec: dict) -> tuple[list[dict], list[dict], list[dict]]:
    std, integ, failed = [], [], []
    for f in sorted(IN.glob("c[vsi]_*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        rel = f.relative_to(ROOT).as_posix()
        inp = r["inputs"]["reactor"]
        cat = inp["catalyst_id"]
        if r.get("run_status") in ("failed", "error"):
            failed.append({"case_id": r["case_id"], "status": r.get("run_status"), "error": r.get("error"), "file": rel})
            continue
        a = r["aspen"]
        e = spec[cat]
        approx = inp["kinetic_form"] == "lhhw_approximation"
        rngok = (not approx) and in_range(e["validity"], inp["temperature_C"], inp["pressure_bar"])
        if r["configuration"] == "integrated":
            k = a["flowsheet_result"]["kpis"]
            integ.append({"case_id": r["case_id"], "catalyst_id": cat, "catalyst": SHORT[cat], "approximation": approx,
                          "T_C": inp["temperature_C"], "P_bar": inp["pressure_bar"], "W_kg": inp["catalyst_mass_kg"],
                          "heat_integration": r["inputs"]["flowsheet"].get("heat_integration"),
                          "converged": a["status"].get("converged"), "has_warnings": a["status"].get("has_warnings"),
                          "X_cracker": a["conversion_of_reactor_inlet_NH3"],
                          "cracker_outlet_P_bar": a["cracker_outlet"]["P_bar"], **k,
                          "within_fitted_range": rngok, "source_type": "aspen", "file": rel})
            continue
        rp, py = a["rplug"], (r.get("python_pfr") or {}).get("outlet", {})
        bulk = (1 - inp["bed_voidage"]) * inp["particle_density_kg_m3"]
        vbed = inp["catalyst_mass_kg"] / bulk
        n0 = sum(inp["feed_kmol_h"].values())
        duty = rp["duty"] if rp["duty_unit"] == "kW" else (rp["duty"] * 1000 if rp["duty_unit"] == "MW" else None)
        x = a["conversion_of_reactor_inlet_NH3"]
        xeq = a["equilibrium_reference"]["conversion_of_reactor_inlet_NH3"]
        row = {"case_id": r["case_id"], "group": r["case_id"].split("_")[0] + ("_" + r["case_id"].split("_")[1]
                                                                             if r["case_id"].startswith("cs_") else ""),
               "catalyst_id": cat, "catalyst": SHORT[cat], "kinetic_form": inp["kinetic_form"], "approximation": approx,
               "thermal_mode": inp["thermal_mode"], "T_in_C": inp["temperature_C"], "P_bar": inp["pressure_bar"],
               "W_kg": inp["catalyst_mass_kg"], "bed_volume_m3": vbed, "reactor_length_m": rp["reactor_length"],
               "GHSV_NH3_STP_h-1": n0 * VM_STP / vbed,
               "X_aspen": x, "X_eq_aspen_rgibbs": xeq, "fraction_of_equilibrium": x / xeq if xeq else None,
               "X_python": py.get("conversion"), "X_eq_python_ideal_gas": py.get("X_eq_outlet"),"dX_aspen_minus_python": (x - py["conversion"]) if py.get("conversion") is not None else None,
               "H2_out_kmol_h": a["product"]["flows_kmol_h"]["H2"],
               "H2_out_kg_h": a["product"]["flows_kmol_h"]["H2"] * 2.016,
               "duty_kW": duty, "python_heat_kW": py.get("heat_input_kW"),
               "T_out_C": a["product"]["T_C"], "P_out_bar": a["product"]["P_bar"],
               "residence_time_s": rp.get("residence_time_s"), "within_fitted_range": rngok,
               "run_status": r["run_status"], "source_type": "aspen", "file": rel}
        std.append(row)
    return std, integ, failed


def interp_w_for_fraction(pts: list[tuple[float, float]], f: float):
    pts = sorted(pts)
    for (w1, f1), (w2, f2) in zip(pts, pts[1:]):
        if (f1 - f) * (f2 - f) <= 0 and f1 != f2:
            lw = math.log(w1) + (f - f1) / (f2 - f1) * (math.log(w2) - math.log(w1))
            return math.exp(lw)
    return None


def stored_rgibbs(T: float, hi: bool) -> dict:
    """Linear interpolation of the stored Aspen RGibbs flowsheet temperature sweep (20 bar), read only."""
    f = SENS / ("aspen_temperature.csv" if hi else "aspen_no_hi_temperature.csv")
    rows = list(csv.DictReader(open(f, encoding="utf-8")))
    rows = [r for r in rows if float(r["reactor_pressure_bar"]) == 20.0]
    rows.sort(key=lambda r: float(r["reactor_temperature_C"]))
    keys = ("nh3_conversion", "h2_product_kg_h", "total_external_heating_kW", "recovered_heat_kW",
            "tailgas_combustion_heat_kW", "lhv_efficiency", "reactor_duty_kW")
    for a, b in zip(rows, rows[1:]):
        ta, tb = float(a["reactor_temperature_C"]), float(b["reactor_temperature_C"])
        if ta <= T <= tb:
            w = (T - ta) / (tb - ta)
            out = {k: float(a[k]) + w * (float(b[k]) - float(a[k])) for k in keys}
            out.update(source=f.relative_to(ROOT).as_posix(), source_type="aspen",
                       note=f"linear interpolation between stored RGibbs runs at {ta:g} and {tb:g} degC")
            return out
    return {}


def main() -> int:
    spec = {c["catalyst_id"]: c for c in json.loads(SPEC.read_text(encoding="utf-8"))["catalysts"]}
    std, integ, failed = load_runs(spec)
    wcsv(IN / "catalyst_standalone_runs.csv", std)
    (IN / "catalyst_standalone_runs.json").write_text(json.dumps(
        {"provenance": prov("results/research/aspen_kinetic/cv_*.json, cs_*.json"), "failed_runs": failed,
         "notes": ["X basis: NH3 at the RPLUG inlet (a 1e-6 fraction pre-cracked as H2 seed; 1e-3 in adiabatic runs)",
                   "X_python: amcrax.reactor.pfr at identical conditions; for Takahashi cases it is the exact "
                   "microkinetic law while Aspen runs the fitted LHHW approximation (valid at 20 bar only)",
                   "GHSV: NH3 feed at 0 degC, 1 atm over the bed volume W/((1-eps) rho_p) (assumption)",
                   "within_fitted_range false = extrapolation of the kinetic law (always false for approximations)"],
         "rows": std}, indent=2), encoding="utf-8")

    items: list[dict] = []
    # ---- 1. reference test points of the kinetics spec
    for r in [x for x in std if x["case_id"].startswith("cv_")]:
        cat = r["catalyst_id"]
        pts = [p for p in spec[cat]["reference_test_points"]
               if abs(p["T_C"] - r["T_in_C"]) < 1e-6 and abs(p["P_bar"] - r["P_bar"]) < 1e-6
               and abs(p["W_cat_kg"] - r["W_kg"]) < 1e-6]
        p = pts[0]
        lbl = f"{SHORT[cat]}, {r['T_in_C']:g} degC, {r['P_bar']:g} bar, {r['W_kg']:g} kg"
        if r["approximation"]:
            ref = p["X_native_approximation_python"]
            items.append(item(f"cat_{r['case_id']}_vs_spec", f"Aspen RPLUG (fitted LHHW approximation) vs Python "
                              f"evaluation of the same approximation ({lbl})", "|X_aspen - X_ref|", r["X_aspen"], ref,
                              X_TOL, "-", abs(r["X_aspen"] - ref) <= X_TOL, [r["file"], "results/research/kinetics/aspen_kinetics_spec.json"],
                              "python: X_native_approximation_python of the spec reference test point"))
            items.append(item(f"cat_{r['case_id']}_vs_exact_law", f"Aspen LHHW approximation vs exact Takahashi "
                              f"microkinetic law in Python ({lbl}); measures the approximation error, not Aspen",
                              "X_aspen - X_python_exact", r["X_aspen"], p["X_python"], None, "-", None,
                              [r["file"]], "python: X_python of the spec reference test point"))
        else:
            items.append(item(f"cat_{r['case_id']}_vs_spec", f"NH3 conversion Aspen RPLUG vs kinetics-spec "
                              f"reference test point ({lbl})", "|X_aspen - X_ref|", r["X_aspen"], p["X_python"], X_TOL,
                              "-", abs(r["X_aspen"] - p["X_python"]) <= X_TOL,
                              [r["file"], "results/research/kinetics/aspen_kinetics_spec.json"],
                              "python: X_python of the spec reference test point (feed 1e-4 kmol/h H2 seed)"))
            items.append(item(f"cat_{r['case_id']}_duty", f"Isothermal reactor duty Aspen vs Python PFR ({lbl})",
                              "relative difference", r["duty_kW"], r["python_heat_kW"], REL_TOL, "kW",
                              abs(r["duty_kW"] / r["python_heat_kW"] - 1) <= REL_TOL, [r["file"]],
                              "python model amcrax.reactor.pfr (ideal gas; Aspen PENG-ROB)"))
    # ---- 2. aggregated checks per catalyst over all standalone runs
    for cat in ORDER:
        rows = [x for x in std if x["catalyst_id"] == cat]
        if not rows:
            continue
        worst = max(rows, key=lambda x: x["X_aspen"] - x["X_eq_aspen_rgibbs"])
        items.append(item(f"cat_{cat}_below_equilibrium", f"{SHORT[cat]}: no RPLUG run above RGibbs equilibrium "
                          f"(same model, same feed), {len(rows)} runs", "max(X_rplug - X_rgibbs) <= 1e-4",
                          worst["X_aspen"] - worst["X_eq_aspen_rgibbs"], 0.0, EQ_MARGIN, "-",
                          worst["X_aspen"] - worst["X_eq_aspen_rgibbs"] <= EQ_MARGIN, [worst["file"]],
                          "aspen RGibbs block REQ in the same model"))
        if items[-1]["status"] == "fail":
            over = [x["case_id"] for x in rows if x["X_aspen"] - x["X_eq_aspen_rgibbs"] > EQ_MARGIN]
            items[-1]["note"] = (
                f"runs above the PENG-ROB RGibbs equilibrium by more than 1e-4: {over}. The LHHW reverse term uses "
                "the ideal-gas equilibrium constant of the kinetics spec (ln K fit) on a "
                + ("molarity" if spec[cat].get("concentration_basis", "").lower().startswith("molar") else "mole-fraction")
                + " basis (concentrations from PENG-ROB molar volumes in the molarity case), not fugacities, so the "
                "kinetic model equilibrates to a slightly different state than RGibbs (PENG-ROB fugacity based). The "
                "excess is largest at 40 bar. Not tuned; "
                "kept as a failure of this strict check. The Python PFR at the same conditions agrees within the "
                "conversion tolerance (item cat_<catalyst>_study_vs_python / cat_cv_*_vs_spec).")
        iso = [x for x in rows if x["thermal_mode"] == "isothermal" and x["X_python"] is not None]
        if iso:
            w = max(iso, key=lambda x: abs(x["dX_aspen_minus_python"]))
            approx = rows[0]["approximation"]
            items.append(item(f"cat_{cat}_study_vs_python", f"{SHORT[cat]}: largest |X_aspen - X_python| over "
                              f"{len(iso)} isothermal runs" + (" (Aspen runs the fitted approximation, Python the exact "
                                                               "law: informational)" if approx else ""),
                              "max |dX|", abs(w["dX_aspen_minus_python"]), 0.0, None if approx else X_TOL, "-",
                              None if approx else abs(w["dX_aspen_minus_python"]) <= X_TOL, [w["file"]],
                              "python model amcrax.reactor.pfr at identical conditions"))
        ad = [x for x in rows if x["thermal_mode"] == "adiabatic" and x["X_python"] is not None]
        for x in ad:
            items.append(item(f"cat_{x['case_id']}_adiabatic", f"{SHORT[cat]}: adiabatic RPLUG outlet temperature "
                              f"vs Python PFR (inlet {x['T_in_C']:g} degC, 20 bar, {x['W_kg']:g} kg)",
                              "|T_aspen - T_python|", x["T_out_C"], None, 2.0 if not x["approximation"] else None,
                              "degC", None, [x["file"]], "python model amcrax.reactor.pfr"))
    # fill adiabatic expected values from the per-case python block
    for it in items:
        if it["id"].endswith("_adiabatic"):
            r = json.loads((ROOT / it["source_files"][0]).read_text(encoding="utf-8"))
            tp = r["python_pfr"]["outlet"]["T_C"]
            it["expected"] = tp
            if it["tolerance"] is not None:
                it["status"] = "pass" if abs(it["observed"] - tp) <= it["tolerance"] else "fail"
    # ---- 3. catalyst mass for a fraction of equilibrium (20 bar)
    mrows = []
    for cat in ORDER:
        for T in (500, 600):
            for fr in (0.95, 0.99):
                ver = [x for x in std if x["catalyst_id"] == cat and x["case_id"].startswith(f"cs_M_")
                       and x["T_in_C"] == T and f"_f{str(fr).replace('.', 'p')}" in x["case_id"]]
                pts = [(x["W_kg"], x["fraction_of_equilibrium"]) for x in std if x["catalyst_id"] == cat
                       and x["thermal_mode"] == "isothermal" and x["P_bar"] == 20.0 and x["T_in_C"] == T]
                w_interp = interp_w_for_fraction(pts, fr) if T == 600 else None
                v = ver[0] if ver else None
                bulk = (1 - (0.36)) * spec[cat]["bed_properties"]["particle_density_kg_m3"]["value"]
                mrows.append({"catalyst_id": cat, "catalyst": SHORT[cat], "T_C": T, "P_bar": 20.0,
                              "fraction_target": fr, "W_python_kg": v["W_kg"] if v else None,
                              "fraction_aspen_at_W_python": v["fraction_of_equilibrium"] if v else None,
                              "X_aspen_at_W_python": v["X_aspen"] if v else None,
                              "W_aspen_interpolated_kg": w_interp,
                              "bed_volume_aspen_m3": (w_interp / bulk) if w_interp else ((v["W_kg"] / bulk) if v else None),
                              "within_fitted_range": v["within_fitted_range"] if v else None,
                              "approximation": cat in APPROX, "source_type": "aspen",
                              "file": v["file"] if v else None})
                if v and cat not in APPROX:
                    items.append(item(f"cat_{v['case_id']}_fraction", f"{SHORT[cat]}: Aspen fraction of equilibrium "
                                      f"at the Python-derived catalyst mass ({T} degC, 20 bar, target {fr})",
                                      "|f_aspen - f_target|", v["fraction_of_equilibrium"], fr, X_TOL, "-",
                                      abs(v["fraction_of_equilibrium"] - fr) <= X_TOL, [v["file"],
                                      "results/research/kinetics/study_mass_for_fraction_of_equilibrium.json"],
                                      "python: kinetics workstream study_mass_for_fraction_of_equilibrium"))
    wcsv(IN / "catalyst_mass_targets.csv", mrows)
    (IN / "catalyst_mass_targets.json").write_text(json.dumps({"provenance": prov(
        "cs_M_* runs (W from the Python study) and 600 degC W sweep (log-linear interpolation)"),
        "notes": ["W per 100 kmol/h NH3; bed volume with eps = 0.36"], "rows": mrows}, indent=2), encoding="utf-8")
    # ---- 4. operating point and integrated flowsheet
    comp = []
    for cat in ORDER:
        op = [x for x in std if x["catalyst_id"] == cat and x["case_id"].startswith("cs_OP_")]
        if not op:
            continue
        op = op[0]
        t600 = [x for x in std if x["catalyst_id"] == cat and x["case_id"].startswith("cs_T_") and x["T_in_C"] == 600]
        mt = {f"W_for_{int(m['fraction_target'] * 100)}pct_eq_600C_kg": m["W_aspen_interpolated_kg"]
              for m in mrows if m["catalyst_id"] == cat and m["T_C"] == 600}
        row = {"catalyst_id": cat, "catalyst": SHORT[cat], "approximation": op["approximation"],
               "operating_temperature_C": op["T_in_C"], "operating_temperature_source": "python (kinetics study), "
               "confirmed in Aspen standalone RPLUG", "P_bar": 20.0, "W_kg": op["W_kg"],
               "bed_volume_m3": op["bed_volume_m3"], "GHSV_NH3_STP_h-1": op["GHSV_NH3_STP_h-1"],
               "X_standalone_at_operating_T": op["X_aspen"], "X_eq_at_operating_T": op["X_eq_aspen_rgibbs"],
               "standalone_duty_kW": op["duty_kW"], "standalone_H2_kmol_h": op["H2_out_kmol_h"],
               "X_standalone_600C_W100": t600[0]["X_aspen"] if t600 else None, **mt,
               "within_fitted_range_at_operating_point": op["within_fitted_range"], "source_files": [op["file"]]}
        items.append(item(f"cat_{op['case_id']}_target", f"{SHORT[cat]}: Aspen conversion at the operating "
                          f"temperature {op['T_in_C']:g} degC (100 kg, 20 bar) vs target 0.95",
                          "|X_aspen - 0.95|", op["X_aspen"], 0.95, None if op["approximation"] else X_TOL, "-",
                          None if op["approximation"] else abs(op["X_aspen"] - 0.95) <= X_TOL, [op["file"]],
                          "definition of the operating temperature (python kinetics study)"))
        for hi in (True, False):
            ig = [x for x in integ if x["catalyst_id"] == cat and x["heat_integration"] == hi]
            tag = "hi" if hi else "nohi"
            if not ig:
                continue
            ig = ig[0]
            rg = stored_rgibbs(op["T_in_C"], hi)
            for k in ("X_cracker", "h2_product_kg_h", "total_external_heating_kW", "recovered_heat_kW",
                      "tailgas_combustion_heat_kW", "lhv_efficiency", "reactor_duty_kW",
                      "specific_heat_demand_kWh_per_kgH2", "converged"):
                row[f"integrated_{tag}_{k}"] = ig.get(k)
            row[f"rgibbs_same_T_{tag}"] = rg
            row["source_files"].append(ig["file"])
            items.append(item(f"cat_{ig['case_id']}_converged", f"{SHORT[cat]}: integrated flowsheet with RPLUG "
                              f"cracker converged (heat integration {'on' if hi else 'off'})", "Aspen run status",
                              ig["converged"], True, None, "-", bool(ig["converged"]), [ig["file"]], "Aspen Plus run status"))
            if rg:
                items.append(item(f"cat_{ig['case_id']}_below_rgibbs", f"{SHORT[cat]}: integrated RPLUG conversion "
                                  f"not above the stored RGibbs flowsheet at the same T (interpolated)",
                                  "X_rplug <= X_rgibbs + 1e-3 (interpolation margin)", ig["X_cracker"],
                                  rg["nh3_conversion"], 1e-3, "-", ig["X_cracker"] <= rg["nh3_conversion"] + 1e-3,
                                  [ig["file"], rg["source"]], "aspen RGibbs flowsheet sweep (stored)"))
        comp.append(row)
    base = {k: json.loads((ROOT / "results" / "simulations" / f"{k}.json").read_text(encoding="utf-8"))["kpis"]
            for k in ("baseline", "baseline_no_hi")}
    (IN / "catalyst_comparison.json").write_text(json.dumps({
        "provenance": prov("cs_OP_*, cs_T_*, cs_M_*, cs_W_* and ci_* runs; stored RGibbs sweeps for comparison"),
        "definition_operating_temperature": "lowest isothermal temperature at which 100 kg catalyst per 100 kmol/h NH3 "
            "reaches 95 % NH3 conversion at 20 bar (python kinetics study, rounded up to 1 degC; Aspen confirms). "
            "95 % is used because 99 % at 20 bar needs at least about 685 degC for any catalyst (equilibrium limit).",
        "notes": ["Takahashi Ni/MgO and Ru/MgO rows use a fitted LHHW approximation (python fit, valid at 20 bar only; "
                  "rate error RMS 12 %, max about 50 %) and are extrapolations from 1 atm data.",
                  "Every kinetic law is used outside its fitted pressure range at 20 bar (within_fitted_range false).",
                  "Integrated cases: the RPLUG cracker runs at the HEATER outlet pressure (20.2 bar) and the feed has "
                  "0.2 mol% H2O as the baseline flowsheet; standalone cases are pure NH3.",
                  "Effectiveness factor 1 (powder kinetics applied to an industrial bed)."],
        "rgibbs_baseline_600C": {"heat_integration": base["baseline"], "no_heat_integration": base["baseline_no_hi"],
                                 "source": "results/simulations/baseline*.json", "source_type": "aspen"},
        "rows": comp}, indent=2), encoding="utf-8")
    wcsv(IN / "catalyst_integrated.csv", integ)
    # ---- assumptions register: add/replace part-2 entries by name, keep the others
    ap = IN / "assumptions.json"
    reg = json.loads(ap.read_text(encoding="utf-8")) if ap.exists() else []
    names = {a["name"] for a in ASSUMPTIONS}
    ap.write_text(json.dumps([a for a in reg if a["name"] not in names] + ASSUMPTIONS, indent=2), encoding="utf-8")
    # ---- validation file: replace own items, keep the others
    old = json.loads(VAL.read_text(encoding="utf-8")) if VAL.exists() else []
    keep = [i for i in old if not str(i.get("id", "")).startswith("cat_")]
    VAL.write_text(json.dumps(keep + items, indent=2), encoding="utf-8")
    n = {s: sum(1 for i in items if i["status"] == s) for s in ("pass", "fail", "informational")}
    print("standalone", len(std), "integrated", len(integ), "failed", len(failed))
    print("validation (cat_)", n, [i["id"] for i in items if i["status"] == "fail"])
    figures(std, comp)
    return 0


def figures(std: list[dict], comp: list[dict]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from amcrax.plotstyle import PALETTE, add_provenance, apply_style, save

    apply_style()
    col = {c: PALETTE[i % len(PALETTE)] for i, c in enumerate(ORDER)}
    plot_rows = []

    def series(cat, pred, key):
        pts = sorted([x for x in std if x["catalyst_id"] == cat and pred(x)], key=lambda x: x[key])
        return pts

    def draw(ax, pts, key, ykey, cat, label=True):
        if not pts:
            return
        ls = "--" if cat in APPROX else "-"
        ax.plot([p[key] for p in pts], [p[ykey] for p in pts], ls, color=col[cat], label=SHORT[cat] if label else None)
        for p in pts:
            ax.plot(p[key], p[ykey], "o", color=col[cat], mfc=col[cat] if p["within_fitted_range"] else "white")

    # conversion vs T
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    for cat in ORDER:
        pts = series(cat, lambda x: x["case_id"].startswith("cs_T_"), "T_in_C")
        draw(ax, pts, "T_in_C", "X_aspen", cat)
        plot_rows += [{"figure": "conversion_vs_T", "catalyst_id": cat, "x": p["T_in_C"], "y": p["X_aspen"],
                       "X_eq": p["X_eq_aspen_rgibbs"], "within_fitted_range": p["within_fitted_range"],
                       "source_type": "aspen"} for p in pts]
    eq = series(ORDER[0], lambda x: x["case_id"].startswith("cs_T_"), "T_in_C")
    ax.plot([p["T_in_C"] for p in eq], [p["X_eq_aspen_rgibbs"] for p in eq], ":", color="black", label="RGibbs equilibrium")
    ax.set_xlabel("Reactor temperature (degC)")
    ax.set_ylabel("NH3 conversion (-)")
    ax.set_title("Aspen RPLUG: conversion vs temperature (20 bar, 100 kg, 100 kmol/h NH3)")
    ax.legend(loc="lower right")
    fig.subplots_adjust(bottom=0.18)
    add_provenance(fig, "isothermal RPLUG; open markers = extrapolated law; dashed = fitted LHHW approximation")
    save(fig, "research/aspen_kinetic_conversion_vs_T.png")
    # conversion vs P
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    for cat in ORDER:
        if cat in APPROX:
            continue
        pts = series(cat, lambda x: x["case_id"].startswith("cs_P_") or (x["case_id"].startswith("cs_T_")
                                                                         and x["T_in_C"] == 550), "P_bar")
        draw(ax, pts, "P_bar", "X_aspen", cat)
        plot_rows += [{"figure": "conversion_vs_P", "catalyst_id": cat, "x": p["P_bar"], "y": p["X_aspen"],
                       "X_eq": p["X_eq_aspen_rgibbs"], "within_fitted_range": p["within_fitted_range"],
                       "source_type": "aspen"} for p in pts]
    eq = series(ORDER[0], lambda x: x["case_id"].startswith("cs_P_") or (x["case_id"].startswith("cs_T_") and x["T_in_C"] == 550), "P_bar")
    ax.plot([p["P_bar"] for p in eq], [p["X_eq_aspen_rgibbs"] for p in eq], ":", color="black", label="RGibbs equilibrium")
    ax.set_xlabel("Pressure (bar)")
    ax.set_ylabel("NH3 conversion (-)")
    ax.set_title("Aspen RPLUG: conversion vs pressure (550 degC, 100 kg, 100 kmol/h NH3)")
    ax.legend(loc="lower left")
    fig.subplots_adjust(bottom=0.18)
    add_provenance(fig, "isothermal RPLUG; open markers = extrapolated law")
    save(fig, "research/aspen_kinetic_conversion_vs_P.png")
    # fraction of equilibrium vs W
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    for cat in ORDER:
        pts = series(cat, lambda x: x["thermal_mode"] == "isothermal" and x["P_bar"] == 20.0 and x["T_in_C"] == 600
                     and x["case_id"].startswith("cs_"), "W_kg")
        draw(ax, pts, "W_kg", "fraction_of_equilibrium", cat)
        plot_rows += [{"figure": "fraction_eq_vs_W", "catalyst_id": cat, "x": p["W_kg"], "y": p["fraction_of_equilibrium"],
                       "GHSV": p["GHSV_NH3_STP_h-1"], "tau_s": p["residence_time_s"],
                       "within_fitted_range": p["within_fitted_range"], "source_type": "aspen"} for p in pts]
    ax.set_xscale("log")
    ax.axhline(0.99, color="grey", lw=0.8, ls=":")
    ax.axhline(0.95, color="grey", lw=0.8, ls=":")
    ax.set_xlabel("Catalyst mass per 100 kmol/h NH3 (kg)")
    ax.set_ylabel("X / X_equilibrium (-)")
    ax.set_title("Aspen RPLUG: approach to equilibrium vs catalyst loading (600 degC, 20 bar)")
    ax.legend(loc="lower right")
    fig.subplots_adjust(bottom=0.18)
    add_provenance(fig, "isothermal RPLUG; open markers = extrapolated law")
    save(fig, "research/aspen_kinetic_approach_vs_loading.png")
    # operating point and integrated flowsheet
    if comp:
        fig, axs = plt.subplots(1, 2, figsize=(9.0, 4.0))
        tick = {"ru_kum_temkin_pyzhev": "Ru/Al2O3\n(Kum)", "nire_ceo2_5ni1ru_lucentini_lhhw": "5Ni1Ru/\nCeO2",
                "nire_ceo2_2p5ni0p5ru_lucentini_lhhw": "2.5Ni0.5Ru/\nCeO2",
                "ni_takahashi_microkinetic": "Ni/MgO\n(approx.)", "ru_takahashi_microkinetic": "Ru/MgO\n(approx.)"}
        names = [tick[c["catalyst_id"]] for c in comp]
        xs = range(len(comp))
        axs[0].bar(xs, [c["operating_temperature_C"] for c in comp], color=[col[c["catalyst_id"]] for c in comp])
        axs[0].set_xticks(list(xs), names, fontsize=6.5)
        axs[0].set_ylabel("Operating temperature (degC)")
        axs[0].set_title("T for 95 % conversion, 100 kg, 20 bar")
        axs[0].set_ylim(400, None)
        w = 0.38
        hi = [c.get("integrated_hi_total_external_heating_kW") or 0 for c in comp]
        no = [c.get("integrated_nohi_total_external_heating_kW") or 0 for c in comp]
        axs[1].bar([x - w / 2 for x in xs], hi, w, label="heat integration on")
        axs[1].bar([x + w / 2 for x in xs], no, w, label="heat integration off")
        axs[1].set_xticks(list(xs), names, fontsize=6.5)
        axs[1].set_ylabel("External heating (kW)")
        axs[1].set_title("Integrated flowsheet with RPLUG cracker")
        axs[1].legend(loc="lower right")
        for c in comp:
            plot_rows.append({"figure": "operating_point", "catalyst_id": c["catalyst_id"],
                              "x": c["operating_temperature_C"], "y": c.get("integrated_hi_total_external_heating_kW"),
                              "y2": c.get("integrated_nohi_total_external_heating_kW"),
                              "lhv_hi": c.get("integrated_hi_lhv_efficiency"),
                              "lhv_nohi": c.get("integrated_nohi_lhv_efficiency"), "source_type": "aspen"})
        fig.tight_layout()
        fig.subplots_adjust(bottom=0.2)
        add_provenance(fig, "Takahashi rows: fitted LHHW approximation; all laws extrapolated to 20 bar")
        save(fig, "research/aspen_kinetic_operating_point.png")
    wcsv(IN / "aspen_kinetic_plotdata.csv", plot_rows)


if __name__ == "__main__":
    sys.exit(main())
