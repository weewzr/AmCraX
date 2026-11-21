"""Build the AmCraX validation matrix from everything that exists right now.

    python scripts/build_validation_matrix.py [--skip-pytest]

Runs every check in :mod:`amcrax.validation` on the available Aspen Plus results, Python models,
literature benchmarks and test results. Items whose inputs do not exist yet are listed as
``not_run`` with the reason; re-run the script when more results land.

Outputs
  results/validation/validation_matrix.json
  results/validation/aspen_vs_python_flowsheet.csv
  results/validation/aspen_internal_consistency.csv
  results/validation/literature_benchmarks.csv
  results/validation/pytest_junit.xml            (unless --skip-pytest)
  docs/validation/validation_matrix.md
"""
from __future__ import annotations

import argparse
import csv
import glob
import importlib.util
import json
import math
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import yaml

from amcrax import paths
from amcrax.schemas import LHV_KJ_PER_MOL, MOLAR_MASS, CaseInputs, SimulationResult
from amcrax.validation import (FAIL, INFO, NOT_RUN, PASS, CheckResult, check_aspen_verification,
                               check_single_objective_feasibility, check_converged, check_economic_consistency,
                               check_nonnegative, check_optimisation_feasibility, check_reaction_stoichiometry,
                               check_unit_sanity, check_vant_hoff, check_vant_hoff_data, judge, simulation_closures)

ROOT = paths.ROOT
VAL = paths.RESULTS_VALIDATION
SENS = paths.RESULTS_SENSITIVITY
SIMS = paths.RESULTS_SIMULATIONS
DOC = paths.DOCS_DIR / "validation" / "validation_matrix.md"


def rel(p) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


MATRIX: list[dict] = []

# Distinct, documented root causes of failing items (attached to an item with add(..., cause=key)).
# The feed-section text is replaced by a quantitative version computed in section_flowsheet() (feed_section_text).
ROOT_CAUSES = {
    "feed_section_enthalpy": (
        "Different feed-section property models (model-form difference in both directions, not a data error): Aspen "
        "uses PENG-ROB for the liquid, the vaporisation and the NH3-H2O dew point; the Python model uses the reference "
        "EOS for ammonia (CoolProp, Gao et al. 2020) and an ideal-liquid (Raoult) dew point. The reference EOS is the "
        "more accurate model for pure-ammonia enthalpy; the dew point depends on the NH3-H2O VLE model and no reference "
        "mixture model was available to arbitrate. The quantitative split could not be computed in this run."),
    "kinetics_figure_predictions": (
        "Takahashi (2016) microkinetic predictions: with W/F inferred from a single anchor point per catalyst "
        "(catalyst mass not reported; assumption) the PFR under-predicts conversion by more than 0.05 at diluted NH3 "
        "(p_NH3 0.25-0.3 atm) and with H2 co-feed (Figs. 3b, 5a, 5b), while the pure-NH3 temperature series agree; "
        "figure readings are approximate. Systematic, not tuned (developer guide 4.4)."),
}

# Item families for the summary (first matching prefix wins; order matters).
FAMILIES = [("FS-PRIMARY-", "FS-PRIMARY"), ("FS-", "FS"), ("FEEDSEC-", "FEEDSEC"), ("PHYS-", "PHYS"),
            ("BAL-ASPEN-", "BAL-ASPEN"), ("BAL-PY-", "BAL-PY"),
            ("SENS-", "SENS"), ("STEMP-", "STEMP"), ("FEED-PROP", "FEED-PROP"), ("THERMO-", "THERMO"), ("EQ-", "EQ"),
            ("LIT-", "LIT"), ("KIN-", "KIN"), ("OPT-", "OPT"), ("ECON-", "ECON"), ("ENV-", "ENV"),
            ("PYTEST-", "PYTEST"), ("SECTION-", "SECTION")]


def family(id: str) -> str:
    return next((f for p, f in FAMILIES if id.startswith(p)), "other")


def add(cr: CheckResult, component: str, method: str, reference: str, expected: str, limitations: str = "",
        evidence=(), actual: str | None = None, status: str | None = None, cause: str | None = None):
    st = status or cr.status
    if st == PASS and (cr.value is None or cr.tolerance is None):
        st = INFO  # never pass without metric and tolerance
    if actual is None:
        if cr.value is None:
            actual = cr.detail
        else:
            actual = f"{cr.metric} = {cr.value:.4g}" + (f" ({cr.detail})" if cr.detail else "")
    MATRIX.append({
        "id": cr.id, "model_component": component, "validation_method": method, "reference": reference,
        "expected_behaviour": expected, "actual_result": actual,
        "metric": cr.metric, "value": cr.value, "tolerance": cr.tolerance, "status": st,
        "limitations": limitations, "evidence_files": [rel(e) for e in (list(evidence) + list(cr.evidence))],
        "family": family(cr.id), "root_cause": cause if st == FAIL else None,
    })


def nr(id, component, method, reference, expected, reason, evidence=()):
    add(CheckResult(id, id, NOT_RUN, detail=reason), component, method, reference, expected, evidence=evidence,
        actual=f"not run: {reason}")


def load_sim(p: Path) -> SimulationResult | None:
    try:
        return SimulationResult.model_validate_json(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_csv(p: Path) -> list[dict]:
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fnum(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def write_csv(p: Path, rows: list[dict]):
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols or ["empty"])
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.10g}" if isinstance(v, float) else v) for k, v in r.items()})


# =====================================================================================  1 equilibrium
def section_equilibrium():
    from amcrax.thermodynamics import (NU, equilibrium_constant, reaction_enthalpy_kJ_mol)

    comp = "thermodynamics (equilibrium)"
    add(check_reaction_stoichiometry(NU, "THERMO-STOICH"), comp, "element balance of NH3 <-> 0.5 N2 + 1.5 H2",
        "stoichiometry", "N and H conserved exactly")
    # NASA-7 polynomials switch range at 1000 K: a central difference straddling the junction measures the
    # (tiny) junction mismatch, not van't Hoff consistency -> test within ranges + junction continuity separately.
    add(check_vant_hoff(lambda T: math.log(equilibrium_constant(T)), reaction_enthalpy_kJ_mol,
                        [500 + 25 * i for i in range(29) if 500 + 25 * i != 1000], "THERMO-VANTHOFF", tol=1e-4),
        comp, "numerical d lnK/dT (h = 0.5 K) vs dH/(R T^2), 500-1200 K, inside each NASA-7 range",
        "van't Hoff equation (code self-consistency only)",
        "Python K(T) and dH(T) derive from the same NASA-7 data -> consistent to numerical precision",
        "INFORMATIONAL: a code self-consistency check, not a validation. For NASA-7 polynomials the Gibbs-Helmholtz "
        "relation holds exactly (h and s/g come from the same coefficients), so this item can only detect an "
        "implementation error in lnK or dH, never a data error; the metric is the central-difference truncation. "
        "T = 1000 K (polynomial junction) excluded here and tested by THERMO-NASA-JUNCTION",
        evidence=[ROOT / "backend/amcrax/thermodynamics/equilibrium.py"], status=INFO)
    from amcrax.thermodynamics import species_enthalpy_kJ_mol, species_gibbs_kJ_mol
    jumps = []
    for s in ("NH3", "H2", "N2", "H2O", "O2"):
        for f, q in ((species_gibbs_kJ_mol, "G"), (species_enthalpy_kJ_mol, "H")):
            jumps.append((abs(1000 * (f(s, 1000 + 1e-7) - f(s, 1000 - 1e-7))), f"{s}.{q}"))
    w = max(jumps)
    add(CheckResult("THERMO-NASA-JUNCTION", "", judge(w[0], 1.0), "max |jump| of G or H at the 1000 K NASA-7 junction (J/mol)",
                    w[0], 1.0, f"worst {w[1]}"), comp, "continuity of the two NASA-7 temperature ranges",
        "GRI-Mech 3.0 NASA-7 data", "continuous within data precision", "tolerance 1 J/mol = assumption")

    grid = VAL / "equilibrium_aspen_grid.csv"
    if not grid.exists():
        nr("EQ-ASPEN", comp, "Aspen RGibbs vs Python", "Aspen grid", "agreement", "equilibrium_aspen_grid.csv missing")
        return
    spec = importlib.util.spec_from_file_location("aed", ROOT / "scripts" / "analyse_equilibrium_discrepancy.py")
    aed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(aed)
    out, summ = aed.analyse()
    aed.write_csv(out)
    (VAL / "equilibrium_discrepancy_summary.json").write_text(json.dumps(summ, indent=2), encoding="utf-8")
    ev = [grid, VAL / "equilibrium_discrepancy.csv", VAL / "equilibrium_discrepancy_summary.json",
          paths.RESULTS_FIGURES / "validation_parity_by_method.png"]

    def mx(key, sub=out):
        v = [r for r in sub if key in r]
        r = max(v, key=lambda r: abs(r[key]))
        return abs(r[key]), r

    v, r = mx("dX_ideal_aspen_minus_python_pp")
    add(CheckResult("EQ-IDEAL", "", judge(v, 0.1), "max |X_Aspen,IDEAL - X_Python,ideal| (pp)", v, 0.1,
                    f"at {r['T_C']:g} C / {r['P_bar']:g} bar; mean {summ['mean_abs_dX_ideal_vs_ideal_pp']:.4f} pp; 84 points"),
        comp, "Aspen Plus V15 RGibbs (IDEAL) vs Python eos='ideal', 250-900 C x 1-40 bar, pure NH3",
        "Aspen Plus V15 (independent simulator)", "same ideal-gas equilibrium; differences only from pure-component data",
        "tolerance 0.1 pp = assumption (engineering agreement for equilibrium conversion)", ev)
    v, r = mx("dX_pr_aspen_minus_python_pp")
    add(CheckResult("EQ-PR", "", judge(v, 0.5), "max |X_Aspen,PENG-ROB - X_Python,pr| (pp)", v, 0.5,
                    f"at {r['T_C']:g} C / {r['P_bar']:g} bar; mean {summ['mean_abs_dX_pr_vs_pr_pp']:.4f} pp"),
        comp, "Aspen PENG-ROB vs Python Peng-Robinson (k_ij = 0)", "Aspen Plus V15",
        "agreement within EOS-parameter differences",
        "Aspen uses databank k_ij (PRKBV, EOS-LIT); Python k_ij = 0 and standard alpha; tolerance 0.5 pp = assumption. "
        "The k_ij values could not be read: the PRKBV-1 input form holds no user values (aspen_binary_parameters.json), "
        "Aspen retrieves EOS-LIT k_ij at run time, so the k_ij explanation of the residual gap is unverified; the "
        "k_ij sensitivity (EQ-KIJ-SENS) shows that single-pair k_ij values within +/-0.3 cannot close it",
        ev + [paths.RESULTS_FIGURES / "validation_eos_effect.png", VAL / "aspen_binary_parameters.json"])
    ks = summ.get("kij_sensitivity_250C_40bar") or {}
    if ks.get("pairs"):
        need = ", ".join(f"{k} {v['kij_needed_to_close_gap']:.2f}" if v["kij_needed_to_close_gap"] is not None
                         else f"{k} outside [-2, 3]" for k, v in ks["pairs"].items())
        slope = ", ".join(f"{k} {v['dX_dkij_pp_per_0p1']:+.4f}" for k, v in ks["pairs"].items())
        add(CheckResult("EQ-KIJ-SENS", "", INFO, "k_ij (one pair, others 0) needed to close the PR-vs-PR gap at "
                        "250 C / 40 bar", None, None,
                        f"gap Aspen - Python (k_ij = 0) {ks['gap_kij0_aspen_minus_python_pp']:+.3f} pp; k_ij needed: "
                        f"{need}; dX per 0.1 in k_ij (pp): {slope}; all three pairs at the same k_ij within +/-0.3 "
                        f"close at most {ks['max_gap_reduction_within_range_pp']:.3f} pp"),
            comp, "SENSITIVITY of Python PR equilibrium to k_ij (scripts/analyse_equilibrium_discrepancy.py), not a "
                  "calibration", "Aspen Plus V15 PENG-ROB grid point", "shows whether plausible k_ij can explain the gap",
            "INFORMATIONAL and used nowhere: every AmCraX model keeps k_ij = 0. The range is illustrative (no sourced "
            "k_ij in research/; Aspen's values unreadable). Result: the needed single-pair values are far outside any "
            "physical range, so binary parameters alone are an unlikely explanation of the residual PR gap",
            ev, status=INFO)
    v, r = mx("dX_aspenPR_minus_pythonIdeal_pp")
    add(CheckResult("EQ-MIXED", "", INFO, "max |X_Aspen,PENG-ROB - X_Python,ideal| (pp)", v, None,
                    f"at {r['T_C']:g} C / {r['P_bar']:g} bar = the fugacity (EOS) effect itself, not a data error"),
        comp, "cross-method comparison reported by validate_equilibrium.py", "Aspen Plus V15",
        "differs by the non-ideality of the gas at low T / high P", "not a like-for-like comparison", ev)
    resolved = [r for r in out if "dG_offset_aspen_minus_python_J_mol" in r and r["X_aspen_ideal"] < 0.999]
    v, r = mx("dG_offset_aspen_minus_python_J_mol", resolved)
    add(CheckResult("EQ-DG-ASPEN", "", judge(v, 50.0), "max |dG offset| Aspen IDEAL - Python (J/mol NH3)", v, 50.0,
                    f"at {r['T_C']:g} C; spread over P at fixed T {summ['dG_offset_max_spread_over_P_at_fixed_T_J_mol']:.2g} J/mol"),
        comp, "back-calculated Kp from Aspen IDEAL compositions vs Python K(T)", "Aspen Plus V15 pure-component data",
        "small, pressure-independent offset (thermochemical data)",
        "points with X > 0.999 excluded (y_NH3 poorly resolved); tolerance 50 J/mol = assumption",
        ev + [paths.RESULTS_FIGURES / "validation_lnK_offset.png"])
    jv = [r for r in out if "dG_offset_janaf_minus_python_J_mol" in r]
    v, r = mx("dG_offset_janaf_minus_python_J_mol", jv)
    add(CheckResult("EQ-DG-JANAF", "", judge(v, 50.0), "max |dG_rxn JANAF - Python| (J/mol NH3)", v, 50.0,
                    f"at {r['T_C']:g} C; Aspen-JANAF mean {summ['dG_offset_aspen_minus_janaf_J_mol']['mean']:.1f} J/mol"),
        comp, "Python dG_rxn(T) vs NIST-JANAF dGf(NH3) (cubic spline of 100 K table)", "NIST-JANAF 4th ed. (Chase 1998)",
        "agreement within tabulation precision", "JANAF tabulated to 1 J/mol; spline interpolation", ev)
    v, r = mx("dH_janaf_minus_python_kJ_mol", jv)
    add(CheckResult("EQ-DH-JANAF", "", judge(v, 0.1), "max |dH_rxn JANAF - Python| (kJ/mol)", v, 0.1,
                    f"at {r['T_C']:g} C"), comp, "Python reaction enthalpy vs NIST-JANAF -dHf(NH3)",
        "NIST-JANAF 4th ed.", "agreement", "tolerance 0.1 kJ/mol = assumption", ev)
    v, r = mx("dH_aspen_minus_python_kJ_mol")
    anomalies = summ.get("aspen_ideal_duty_anomalies", [])
    add(CheckResult("EQ-DH-ASPEN", "", judge(v, 0.1), "max |dH_rxn Aspen IDEAL (duty/X) - Python| (kJ/mol)", v, 0.1,
                    f"at {r['T_C']:g} C / {r['P_bar']:g} bar; median {summ['dH_aspen_minus_python_median_kJ_mol']:.3f} kJ/mol; "
                    f"anomalous Aspen points: {anomalies}"),
        comp, "Aspen IDEAL isothermal duty / conversion vs Python dH_rxn(T)", "Aspen Plus V15",
        "duty/X equals dH_rxn(T) for an ideal gas at every pressure",
        "resolved defect: the first grid had one IDEAL point (600 C, 30 bar) carrying the previous point's duty "
        "(-1.24 kJ/mol). Cause: asynchronous engine run (Run2(1) + IsRunning polling) read in a no-reinitialisation "
        "sweep while results were loading. Fixed in the automation (synchronous Run2(), re-initialisation at every "
        "point, repeatability and pressure-independence guards in run_equilibrium_grid.py); grid regenerated. "
        "Flowsheet runs always re-initialised and were not affected", ev)
    # stale-value guard on the stored grid: for an ideal gas duty/X must not depend on pressure at fixed T
    by_t: dict[float, list[float]] = {}
    for g in read_csv(grid):
        if g.get("property_method") == "IDEAL" and fnum(g.get("nh3_conversion")):
            by_t.setdefault(fnum(g["T_C"]), []).append(fnum(g["heat_duty_kJ_per_mol_NH3_fed"]) / fnum(g["nh3_conversion"]))
    if by_t:
        spread, tw = max((max(v) - min(v), t) for t, v in by_t.items())
        add(CheckResult("EQ-GRID-STALE", "", judge(spread, 1e-3), "max spread over P of Aspen IDEAL duty/X at fixed T (kJ/mol)",
                        spread, 1e-3, f"{sum(len(v) for v in by_t.values())} IDEAL points, {len(by_t)} temperatures; "
                        f"worst at {tw:g} C"),
            "Aspen Plus RGibbs (IDEAL) / automation", "physical stale-result guard on the stored grid",
            "ideal-gas thermodynamics (reaction enthalpy independent of P)", "spread at numerical precision",
            "same criterion (1e-3 kJ/mol) as the guard in aspen/automation/run_equilibrium_grid.py; repeatability of "
            "independent sessions is checked there at run time (not re-checkable from the CSV)",
            [grid, ROOT / "aspen/automation/run_equilibrium_grid.py", ROOT / "backend/amcrax/aspen/session.py"])
    v, r = mx("dX_ideal_residual_after_dlnK_pp")
    dg_max = summ.get("dG_offset_max_abs_resolved_J_mol")
    add(CheckResult("EQ-AMPLIFY", "", INFO, "max |dX_observed - (dX/dlnK) dlnK| (pp)", v, None,
                    f"dX/dlnK ranges {summ['dXdlnK_range'][0]:.2e}-{summ['dXdlnK_range'][1]:.3f}; the Aspen IDEAL - "
                    f"Python conversion difference is equivalent to a standard-Gibbs-energy offset of at most "
                    f"{dg_max:.1f} J/mol NH3 (resolved points, X < 0.999)"),
        comp, "first-order sensitivity dX/dlnK = X(1-X^2)/2 applied to the lnK back-calculated from Aspen's y",
        "analytic derivative (restatement, not an independent reference)",
        "expresses the ideal-gas conversion difference as an equivalent standard-Gibbs-energy offset",
        "INFORMATIONAL: circular by construction - the lnK back-calculated from Aspen's equilibrium composition "
        "reproduces Aspen's conversion exactly, so the residual is only the second-order Taylor term of the "
        "linearisation; it re-expresses the deviation (as a dG offset, see EQ-DG-ASPEN), it does not explain or "
        "validate it", ev, status=INFO)
    # van't Hoff on the Aspen IDEAL data (40 bar: lowest conversion, best-resolved y_NH3)
    sub = sorted([r for r in out if r["P_bar"] == max(x["P_bar"] for x in out) and "lnK_aspen_ideal" in r
                  and abs(r.get("dH_aspen_minus_python_kJ_mol", 0)) < 0.2], key=lambda r: r["T_K"])
    if len(sub) > 3:
        cr = check_vant_hoff_data([r["T_K"] for r in sub], [r["lnK_aspen_ideal"] for r in sub],
                                  [r["dH_rxn_aspen_ideal_kJ_mol"] for r in sub], "EQ-VANTHOFF-ASPEN", tol=0.01)
        add(cr, "Aspen Plus RGibbs (IDEAL)", "integral van't Hoff test on Aspen lnK (from y) and duty/X, 40 bar",
            "van't Hoff equation", "Aspen K(T) and duty consistent",
            "50 K spacing, dH taken linear between nodes (curvature error included); tolerance 1 % = assumption", ev)


# =====================================================================================  2 flowsheet
KEY_KPIS = ("nh3_conversion", "h2_product_kmol_h", "reactor_duty_kW", "vaporiser_duty_kW", "preheat_duty_kW",
            "recovered_heat_kW", "total_external_heating_kW", "cooling_duty_kW", "tailgas_lhv_kW",
            "tailgas_combustion_heat_kW", "pump_power_kW", "lhv_efficiency")


def section_flowsheet():
    from amcrax.process_model import compare_results, run_python_case

    comp = "process model (flowsheet)"
    aspen_files = []
    for p in sorted(SIMS.glob("*.json")):
        if p.name.startswith(("python_", "heat_integration_")):
            continue
        r = load_sim(p)
        if r is not None and r.source.value == "aspen_plus_v15":
            aspen_files.append((p, r))
    if not aspen_files:
        nr("FS", comp, "Aspen vs Python flowsheet", "Aspen", "agreement", "no Aspen simulation JSON found")
        return
    rows = []
    for p, ra in aspen_files:
        for eos in ("ideal", "pr"):
            try:
                rp = run_python_case(ra.inputs, eos=eos)
            except Exception as e:  # noqa: BLE001
                nr(f"FS-{ra.case_id}-{eos}", comp, "run_python_case with Aspen inputs", "Aspen", "agreement",
                   f"Python model failed: {e}", [p])
                continue
            cmp = compare_results(ra, rp)
            for c in cmp:
                rows.append({"case_id": ra.case_id, "python_eos": eos, "quantity": c["quantity"], "aspen": c["a"],
                             "python": c["b"], "abs_diff": c["abs_diff"], "rel_diff": c["rel_diff"]})
            if eos == "pr":
                _fs_primary(ra, p, {c["quantity"]: c for c in cmp}, comp)
            if eos != "ideal":
                continue
            kp = {c["quantity"][4:]: c for c in cmp if c["quantity"].startswith("kpi.")}
            devs = [(k, kp[k]["rel_diff"]) for k in KEY_KPIS if k in kp and kp[k]["rel_diff"] is not None]
            if not devs:
                continue
            # conversion judged in absolute terms
            dX = kp.get("nh3_conversion", {}).get("abs_diff")
            k_w, v_w = max(devs, key=lambda t: abs(t[1]))
            top = sorted(devs, key=lambda t: -abs(t[1]))[:4]
            add(CheckResult(f"FS-{ra.case_id}", "", judge(v_w, 0.02),
                            "max |relative deviation| over key KPIs (Python - Aspen)/Aspen", abs(v_w), 0.02,
                            f"worst {k_w}; top: " + ", ".join(f"{k} {100*v:+.2f}%" for k, v in top)
                            + (f"; conversion {100*dX:+.3f} pp" if dX is not None else "")),
                comp, f"amcrax.process_model.compare: Aspen {ra.case_id} vs run_python_case(same inputs, eos=ideal)",
                "Aspen Plus V15 (PENG-ROB)", "agreement of duties, flows and KPIs within 2 %",
                "the two models use different feed-section property models (Aspen PENG-ROB; Python reference EOS for "
                "ammonia + ideal-liquid Raoult dew point), so this item measures a model-form difference in both "
                "directions (see FEEDSEC-ANALYSIS for the split at identical states); gas section ideal gas in this "
                "eos=ideal comparison; no PSA duty in Python; tolerance 2 % = assumption, kept. The independent "
                "reaction-section quantities are judged separately in FS-PRIMARY-<case>",
                [p, VAL / "aspen_vs_python_flowsheet.csv"], cause="feed_section_enthalpy")
    write_csv(VAL / "aspen_vs_python_flowsheet.csv", rows)
    _feed_section(aspen_files, comp)


def _feed_section(aspen_files, comp: str):
    """C1: neutral, quantitative statement of the feed-section property-model difference (baseline states)."""
    from amcrax.process_model import run_python_case
    from amcrax.validation import physics

    base = next((ra for p, ra in aspen_files if ra.case_id == "baseline"), None)
    if base is None:
        nr("FEEDSEC-ANALYSIS", comp, "feed-section analysis", "Aspen baseline", "-", "baseline.json missing")
        return
    path = VAL / "feed_section_analysis.json"
    d = physics.feed_section_analysis(base, run_python_case(base.inputs, eos="pr"))
    path.write_text(json.dumps(d, indent=2), encoding="utf-8")
    va, hr, dw, sp = (d["vaporiser_at_aspen_states"], d["nh3_residual_enthalpy_S2_kJ_mol"], d["dew_point"],
                      d.get("fehe_gap_split_kW", {}))
    text = (
        "Different feed-section property models (a model-form difference in both directions, not a data error). "
        "Aspen uses PENG-ROB for the liquid, the vaporisation and the NH3-H2O dew point; the Python model uses the "
        "reference EOS for ammonia (CoolProp, Gao et al. 2020) and an ideal-liquid (Raoult) dew point. At identical "
        f"states (Aspen baseline S1 -> S2) the Aspen vaporiser duty is {100 * va['aspen_minus_reference_rel']:+.1f} % "
        f"relative to the reference EOS ({va['aspen_peng_rob_kW']:.2f} vs {va['reference_eos_kW']:.1f} kW); the NH3 "
        f"vapour residual enthalpy at S2 is {hr['peng_robinson_kij0']:.3f} kJ/mol with PR (k_ij = 0) against "
        f"{hr['reference_eos']:.3f} kJ/mol with the reference EOS, which is the more accurate model for pure-ammonia "
        f"enthalpy. The vaporiser outlet temperature is set by the 0.2 mol% water and the VLE model: at "
        f"{d['P2_bar']:g} bar the dew point is {dw['pure_NH3_saturation_reference_C']:.1f} C for pure NH3, "
        f"{dw['peng_robinson_kij_NH3_H2O_+0.00_C']:.1f} C with PR k_ij = 0, {dw['raoult_ideal_liquid_C']:.1f} C with "
        f"Raoult, {dw['peng_robinson_kij_NH3_H2O_-0.25_C']:.1f} C with PR k_ij(NH3-H2O) = -0.25 and "
        f"{dw['aspen_peng_rob_C (S2 - 10 K superheat)']:.1f} C in Aspen; no reference NH3-H2O mixture model was "
        "available to arbitrate.")
    if sp:
        text += (f" Of the {sp['gap_python_minus_aspen_kW']:.1f} kW baseline FEHE gap (Python {sp['python_kW']:.1f}, "
                 f"Aspen {sp['aspen_kW']:.1f} kW) {sp['a_inlet_temperature_dew_point']:.1f} kW come from the inlet "
                 f"temperature (dew point), {sp['b_PR_vs_reference_residual_at_S2']:.1f} kW from the PR vs reference "
                 f"residual enthalpy at S2, {sp['c_reference_vs_PR_residual_at_S3']:.1f} kW from the residual at S3 "
                 f"and {sp['d_remainder_ideal_gas_cp_and_PR_constants']:+.1f} kW remain (ideal-gas cp sources, PR "
                 "constants).")
    text += (" The FS-<case> items therefore measure this model-form difference; they keep their 2 % tolerance and "
             "fail.")
    ROOT_CAUSES["feed_section_enthalpy"] = text
    add(CheckResult("FEEDSEC-ANALYSIS", "", INFO, "Aspen - reference-EOS vaporiser duty at identical states (relative)",
                    va["aspen_minus_reference_rel"], None, text),
        comp, "vaporiser duty, NH3 residual enthalpy, dew points (PR with two k_ij, Raoult, Aspen) and FEHE gap split "
              "at the Aspen baseline states (amcrax.validation.physics.feed_section_analysis)",
        "CoolProp reference EOS for NH3 (Gao 2020); Peng-Robinson; Raoult; Aspen Plus V15",
        "quantifies the model-form difference; no model is adjusted",
        "INFORMATIONAL: no reference NH3-H2O VLE model is available, so the dew-point difference cannot be judged; "
        "the PR terms use the AmCraX PR implementation (CoolProp constants) as a stand-in for Aspen PENG-ROB "
        "(its databank constants and k_ij could not be read)", [path, SIMS / "baseline.json"], status=INFO,
        actual=text)


# FS-PRIMARY: the INDEPENDENT reaction-section comparisons (do not depend on the feed-section property model).
# H2 product flow, purity, overall yield, tail-gas flow / LHV and flame temperature are functions of the conversion
# and of the fixed PSA split fractions (inputs), so they are reported as derived quantities and are not judged.
FS_PRIMARY_REL_TOL = 0.01    # relative, reactor duty - assumption
FS_PRIMARY_ABS_TOL = 0.005   # absolute, conversion and cracked-gas mole fractions = EQ-PR tolerance (0.5 pp)
FS_PRIMARY_REL = {"kpi.reactor_duty_kW": "reactor duty"}
FS_PRIMARY_ABS = {"kpi.nh3_conversion": "NH3 conversion", "stream.S5.mole_frac.NH3": "cracked-gas y_NH3",
                  "stream.S5.mole_frac.H2": "cracked-gas y_H2", "stream.S5.mole_frac.N2": "cracked-gas y_N2"}
FS_DERIVED_REL = {"kpi.h2_product_kmol_h": "H2 product flow", "kpi.h2_yield_overall": "overall H2 yield",
                  "stream.TAILGAS.mole_flow_kmol_h": "tail-gas flow", "kpi.tailgas_lhv_kW": "tail-gas LHV",
                  "block.BURNER.outlet_temperature_C": "flame temperature (K)"}
FS_DERIVED_ABS = {"kpi.h2_purity_mole_frac": "H2 purity"}


def _devs(cq: dict, rel: dict, abs_: dict, missing: list) -> list:
    out = []
    for q, lab in rel.items():
        c = cq.get(q)
        a, b = (fnum(c["a"]), fnum(c["b"])) if c else (None, None)
        if a is None or b is None or a == 0:
            missing.append(lab)
            continue
        if q.endswith("temperature_C"):
            a, b = a + 273.15, b + 273.15
        r = (b - a) / abs(a)
        out.append((abs(r) / FS_PRIMARY_REL_TOL, lab, f"{100 * r:+.3f}%"))
    for q, lab in abs_.items():
        c = cq.get(q)
        a, b = (fnum(c["a"]), fnum(c["b"])) if c else (None, None)
        if a is None or b is None:
            missing.append(lab)
            continue
        out.append((abs(b - a) / FS_PRIMARY_ABS_TOL, lab, f"{100 * (b - a):+.4f} pp"))
    return out


def _fs_primary(ra, p, cq: dict, comp: str):
    missing: list[str] = []
    devs = _devs(cq, FS_PRIMARY_REL, FS_PRIMARY_ABS, missing)
    derived = _devs(cq, FS_DERIVED_REL, FS_DERIVED_ABS, [])
    if not devs:
        nr(f"FS-PRIMARY-{ra.case_id}", comp, "Aspen vs Python independent reaction-section quantities", "Aspen",
           "agreement", "no comparable quantities", [p])
        return
    w = max(devs)
    imp = 1.0 - ra.kpis.h2_purity_mole_frac if ra.kpis.h2_purity_mole_frac is not None else None
    add(CheckResult(f"FS-PRIMARY-{ra.case_id}", "", judge(w[0], 1.0),
                    "max normalised deviation over the independent quantities (|rel|/0.01 for the reactor duty; "
                    "|abs|/0.005 for conversion and cracked-gas mole fractions)",
                    w[0], 1.0, f"worst {w[1]} {w[2]}; independent: " + ", ".join(f"{t[1]} {t[2]}" for t in devs)
                    + "; derived, not independent (functions of conversion and the fixed PSA split, reported only): "
                    + ", ".join(f"{t[1]} {t[2]}" for t in derived)
                    + (f"; not available: {', '.join(missing)}" if missing else "")),
        comp, f"Aspen {ra.case_id} vs run_python_case(same inputs, eos=pr): judged on NH3 conversion, cracked-gas "
        "mole fractions and reactor duty only",
        "Aspen Plus V15 (PENG-ROB)", "the independent reaction-section quantities agree",
        "H2 product flow, purity, overall yield, tail-gas flow and LHV and flame temperature follow from the conversion "
        "and the PSA split fractions (psa_h2_recovery, psa_n2_slip: inputs) and are listed as derived, not independent; "
        "H2 purity is set by the assumed PSA split, it is not predicted"
        + (f" (total impurity {100 * imp:.3f} mol%, so a 0.5 pp purity tolerance would be "
           f"{0.005 / imp:.0f} x the impurity and meaningless)" if imp else "")
        + ". Separate family from FS-<case> (2 % test on all key KPIs incl. feed-section duties); Python eos=pr is "
        "the like-for-like counterpart of Aspen PENG-ROB; tolerances 1 % relative and 0.5 pp absolute (= EQ-PR) are "
        "assumptions", [p, VAL / "aspen_vs_python_flowsheet.csv"])


# =====================================================================================  3 Aspen internal
def section_aspen_internal():
    comp = "Aspen Plus flowsheet (internal consistency)"
    rows_out = []
    # 3a simulations json: closures, nonnegativity, units, converged
    for p in sorted(SIMS.glob("*.json")):
        if p.name.startswith("heat_integration_"):
            continue
        r = load_sim(p)
        if r is None:
            continue
        src = r.source.value
        tag = ("ASPEN" if src == "aspen_plus_v15" else "PY") + f"-{p.stem}"
        crs = simulation_closures(r, f"BAL-{tag}") + [check_nonnegative(r, f"NONNEG-{tag}"),
                                                       check_unit_sanity(r, f"UNITS-{tag}"),
                                                       check_converged(r, f"CONV-{tag}")]
        aspen = src == "aspen_plus_v15"
        # Python model: every block duty is H_out - H_in by construction, so its energy closure cannot fail; it is
        # reported (informational) but not judged. Aspen: all closures are judged (they fail if extraction is wrong).
        judged = [c for c in crs if aspen or not c.id.endswith(".energy")]
        info = [c for c in crs if c not in judged]
        worst = [c for c in judged if c.status == FAIL]
        vals = [abs(c.value) for c in judged if c.value is not None and c.id.startswith("BAL")]

        def lab(c):
            return c.id.split('.')[-1] if '.' in c.id else c.id.split('-')[0]
        summary = "; ".join(f"{lab(c)}: {c.status}" + (f" ({c.value:.2e})" if c.value is not None else "")
                            for c in judged)
        if info:
            summary += "; " + "; ".join(f"{lab(c)}: informational, zero by construction"
                                        + (f" ({c.value:.2e})" if c.value is not None else "") for c in info)
        for c in crs:
            rows_out.append({"source_file": rel(p), "check": c.id, "status": c.status if c in judged else INFO,
                             "metric": c.metric, "value": c.value, "tolerance": c.tolerance, "detail": c.detail})
        st = FAIL if worst else (PASS if all(c.status == PASS for c in judged) else NOT_RUN)
        add(CheckResult(f"BAL-{tag}", "", st,
                        "max |relative closure| (mass, N/H/O" + (", energy)" if aspen else "); energy not judged"),
                        max(vals) if vals else None, 1e-4, summary),
            "Aspen Plus flowsheet" if aspen else "process model (flowsheet)",
            "extraction consistency (stream and block mapping, units and signs): plant-boundary mass/element closure "
            "(FEED+AIR -> H2PROD+STACK)" + (", energy closure" if aspen else "") + ", non-negative flows, "
            "fraction/unit sanity, converged flag", src,
            "closures < 1e-6 (mass, elements)" + (", < 1e-4 (energy)" if aspen else "") + "; all flows >= 0; converged",
            ("verifies that the extracted streams and block duties are mapped, converted and signed consistently "
             "(the closures fail if they are not); it is not a test of the physics, because Aspen closes its own "
             "balances. Energy closure from balances.energy_closure_rel (amcrax.kpis)") if aspen else
            ("bookkeeping check of the Python result; the energy closure is zero by construction (each block duty is "
             "H_out - H_in) and is therefore informational, not judged"), [p])
    # 3b sensitivity CSVs
    studies = sorted(SENS.glob("aspen_*.csv"))
    expected = ["temperature", "pressure", "tp_map", "feed_rate", "feed_water", "psa_recovery", "fehe_approach",
                "no_hi_temperature"]
    have = {p.stem[len("aspen_"):] for p in studies}
    for s in expected:
        if s not in have:
            nr(f"SENS-{s}", comp, "balance closures of every Aspen sensitivity run", "Aspen Plus V15",
               "all runs converged, closures small", f"results/sensitivity/aspen_{s}.csv not present yet")
    for p in studies:
        if p.stem.startswith("aspen_native"):
            continue
        rows = read_csv(p)
        if not rows or "mass_closure_rel" not in rows[0]:
            continue
        m = [abs(fnum(r["mass_closure_rel"])) for r in rows if fnum(r.get("mass_closure_rel")) is not None]
        e = [abs(fnum(r["energy_closure_rel"])) for r in rows if fnum(r.get("energy_closure_rel")) is not None]
        nconv = sum(1 for r in rows if str(r.get("converged")).lower() not in ("true", "1"))
        neg = [k for r in rows for k in ("nh3_conversion", "h2_product_kmol_h", "tailgas_kmol_h")
               if fnum(r.get(k)) is not None and fnum(r[k]) < 0]
        tag = p.stem[len("aspen_"):]
        # a closure value is required for EVERY row: an empty/partial column must not pass vacuously
        complete = len(m) == len(rows) and len(e) == len(rows)
        worst = max(max(m, default=0) / 1e-6, max(e, default=0) / 1e-4) if complete else float("inf")
        ok = (nconv == 0 and not neg and complete and worst <= 1)
        add(CheckResult(f"SENS-{tag}", "", PASS if ok else FAIL,
                        "max(|mass closure|/1e-6, |energy closure|/1e-4) (normalised)", worst, 1.0,
                        f"{len(rows)} runs; max |mass| {max(m, default=float('nan')):.2e}, max |energy| "
                        f"{max(e, default=float('nan')):.2e}; not converged {nconv}; negative flows {len(neg)}"),
            comp, f"extraction consistency (stream and block mapping, units and signs): closures and convergence of "
                  f"every run in {p.name}", "Aspen Plus V15",
            "all runs converged, mass closure < 1e-6, energy closure < 1e-4, flows >= 0",
            "closures as exported by the coordinator (computed by amcrax.kpis from Aspen streams); they verify the "
            "extraction and bookkeeping, not the physics (Aspen closes its own balances)", [p])
        for r in rows:
            rows_out.append({"source_file": rel(p), "check": f"run {r.get('case_id')}", "status": "",
                             "metric": "mass/energy closure", "value": fnum(r.get("mass_closure_rel")),
                             "tolerance": fnum(r.get("energy_closure_rel")), "detail": f"converged={r.get('converged')}"})
    # 3c native STEMP vs COM temperature study
    for base, study in (("baseline", "temperature"), ("baseline_no_hi", "no_hi_temperature")):
        nat = SENS / f"aspen_native_STEMP_{base}.csv"
        com = SENS / f"aspen_{study}.csv"
        if not (nat.exists() and com.exists()):
            nr(f"STEMP-{base}", comp, "native Sensitivity STEMP vs COM temperature study", "Aspen Plus V15",
               "identical results at identical T", f"missing {nat.name if not nat.exists() else com.name}")
            continue
        b = load_sim(SIMS / f"{base}.json")
        ref_in = b.inputs if b else CaseInputs()
        crows = [r for r in read_csv(com)
                 if all(abs((fnum(r.get(k)) or 0) - getattr(ref_in, k)) < 1e-9 for k in
                        ("reactor_pressure_bar", "psa_h2_recovery", "fehe_hot_end_approach_K", "feed_total_kmol_h"))
                 and str(r.get("heat_integration")).lower() == str(ref_in.heat_integration).lower()]
        pairs = []
        mp = {"nh3_conversion": "nh3_conversion", "h2_product_kmol_h": "h2_product_kmol_h",
              "cracker_duty_kW": "reactor_duty_kW", "heater_duty_kW": "preheat_duty_kW"}
        for rn in read_csv(nat):
            T = fnum(rn["reactor_temperature_C"])
            m = [r for r in crows if abs(fnum(r["reactor_temperature_C"]) - T) < 1e-6]
            if not m:
                continue
            for kn, kc in mp.items():
                a, c = fnum(rn[kn]), fnum(m[0][kc])
                if a is not None and c is not None:
                    pairs.append((T, kn, a, c, (c - a) / abs(a) if a else 0.0))
        if not pairs:
            nr(f"STEMP-{base}", comp, "native STEMP vs COM study", "Aspen", "identical", "no common temperatures", [nat, com])
            continue
        w = max(pairs, key=lambda t: abs(t[4]))
        add(CheckResult(f"STEMP-{base}", "", judge(w[4], 1e-4), "max relative deviation native vs COM", abs(w[4]), 1e-4,
                        f"{len({t[0] for t in pairs})} common temperatures, {len(pairs)} values; worst {w[1]} at {w[0]:g} C"),
            comp, "Aspen native Sensitivity block STEMP vs COM-driven temperature study (same T points)",
            "Aspen Plus V15 (two independent drivers)", "identical within convergence tolerance",
            "tolerance 1e-4 = Aspen default flowsheet convergence tolerance order", [nat, com])
    # 3d feed-rate proportionality
    fr = SENS / "aspen_feed_rate.csv"
    if fr.exists():
        rows = [r for r in read_csv(fr) if str(r.get("converged")).lower() in ("true", "1")]
        ext = ("h2_product_kmol_h", "reactor_duty_kW", "vaporiser_duty_kW", "total_external_heating_kW", "tailgas_lhv_kW")
        worst, where, evaluated = 0.0, "", 0
        for k in ext:
            spec = [fnum(r[k]) / fnum(r["feed_total_kmol_h"]) for r in rows if fnum(r.get(k)) is not None]
            if len(spec) > 1:
                evaluated += 1
                mean = sum(spec) / len(spec)
                d = max(abs(s - mean) / abs(mean) for s in spec) if mean else 0.0
                if d > worst:
                    worst, where = d, k
        xs = [x for x in (fnum(r.get("nh3_conversion")) for r in rows) if x is not None]
        dX = max(xs) - min(xs) if xs else float("nan")
        if len(rows) < 2 or evaluated == 0:
            # nothing to compare: a proportionality check on fewer than two runs must not pass vacuously
            nr("FEED-PROP", comp, "feed-rate proportionality", "scaling law", "linear scaling",
               f"fewer than two converged runs with data in aspen_feed_rate.csv ({len(rows)} converged rows)", [fr])
        else:
            add(CheckResult("FEED-PROP", "", judge(worst, 1e-3), "max relative deviation of (extensive / feed) from mean",
                            worst, 1e-3, f"{len(rows)} runs; worst {where}; conversion spread {dX:.2e}"),
                comp, "extensive outputs proportional to feed rate (intensive specs fixed)", "scaling law",
                "specific duties and yields independent of feed rate", "pump efficiency fixed; tolerance 1e-3 = assumption", [fr])
    else:
        nr("FEED-PROP", comp, "feed-rate proportionality", "scaling law", "linear scaling", "aspen_feed_rate.csv not present yet")
    write_csv(VAL / "aspen_internal_consistency.csv", rows_out)


# =====================================================================================  3e independent physics
# Tolerances (assumptions, fixed before the comparison; justification in the item text):
PHYS_FLAME_TOL_K = 2.0        # flame temperature, complete combustion
PHYS_FLUEHX_TOL_REL = 0.005   # FLUEHX duty
PHYS_PUMP_TOL_REL = 0.01      # pump brake power
PHYS_UA_TOL_REL = 1e-4        # HeatX UA vs Q/LMTD


def section_independent_physics():
    """Recompute selected Aspen block outputs from Aspen inlet states with independent property sources."""
    from amcrax.validation import physics as ph

    comp = "Aspen Plus flowsheet (independent physics)"
    cases = []
    for p in sorted(SIMS.glob("*.json")):
        r = load_sim(p)
        if r is not None and r.source.value == "aspen_plus_v15":
            cases.append((p, r))
    if not cases:
        for i in ("PHYS-FLAME", "PHYS-FLUEHX", "PHYS-PUMP", "PHYS-FEHE-UA"):
            nr(i, comp, "independent recalculation", "-", "-", "no Aspen simulation JSON found")
        return
    rows, fl, fx, pu, ua = [], [], [], [], []
    for p, r in cases:
        f = ph.flame_temperature_cantera(r)
        q = ph.fluehx_duty_cantera(r)
        w = ph.pump_power_hand(r)
        u = ph.fehe_ua_lmtd(r)
        fl.append((abs(f["dT_complete_minus_aspen_K"]), r.case_id, f))
        fx.append((abs(q["rel_dev"]), r.case_id, q))
        pu.append((abs(w["rel_dev"]), r.case_id, w))
        if u is not None:
            ua.append((abs(u["rel_dev"]), r.case_id, u))
        rows.append({"case_id": r.case_id, "source_file": rel(p),
                     "flame_T_aspen_C": f["T_aspen_C"], "flame_T_cantera_complete_C": f["T_complete_C"],
                     "flame_T_cantera_HP_equilibrium_C": f["T_equilibrium_C"],
                     "dT_complete_minus_aspen_K": f["dT_complete_minus_aspen_K"],
                     "dT_equilibrium_minus_complete_K": f["dT_equilibrium_minus_complete_K"],
                     "product_flow_dev_vs_aspen_flue_kmol_h": f["max_abs_product_flow_dev_vs_aspen_flue_kmol_h"],
                     "fluehx_Q_aspen_kW": q["Q_aspen_kW"], "fluehx_Q_cantera_kW": q["Q_cantera_kW"],
                     "fluehx_rel_dev": q["rel_dev"], "pump_W_aspen_kW": w["W_aspen_kW"],
                     "pump_W_hand_kW": w["W_hand_kW"], "pump_rel_dev": w["rel_dev"],
                     "fehe_UA_aspen_kW_K": u["UA_aspen_kW_K"] if u else None,
                     "fehe_UA_Q_over_LMTD_kW_K": u["UA_Q_over_LMTD_kW_K"] if u else None,
                     "fehe_UA_rel_dev": u["rel_dev"] if u else None})
    out = VAL / "independent_physics_checks.csv"
    write_csv(out, rows)
    ev = [out, ROOT / "backend/amcrax/validation/physics.py"]
    n = len(cases)
    w = max(fl)
    b = next((t[2] for t in fl if t[1] == "baseline"), w[2])
    add(CheckResult("PHYS-FLAME", "", judge(w[0], PHYS_FLAME_TOL_K),
                    "max |T_ad,Cantera - T_ad,Aspen| over stored Aspen cases (K)", w[0], PHYS_FLAME_TOL_K,
                    f"{n} cases; worst {w[1]} ({w[2]['T_complete_C']:.2f} vs {w[2]['T_aspen_C']:.2f} C); baseline "
                    f"{b['T_complete_C']:.2f} vs {b['T_aspen_C']:.2f} C; Cantera products from the Aspen TAILGAS+AIR "
                    f"by stoichiometry agree with the Aspen FLUE flows to "
                    f"{max(r['product_flow_dev_vs_aspen_flue_kmol_h'] for r in rows):.1e} kmol/h"),
        comp, "adiabatic COMPLETE-combustion temperature of the Aspen TAILGAS + AIR streams (Aspen T, P, flows), "
              "Cantera ideal gas with GRI-Mech 3.0 thermo, products fixed to H2O/N2/O2 (Aspen RStoic basis)",
        "Cantera 3 (GRI-Mech 3.0 NASA polynomials) - independent of Aspen's databank",
        "agreement within the spread of evaluated ideal-gas data",
        "the value is the complete-combustion flame temperature (no dissociation, as the Aspen RStoic burner); "
        "see PHYS-FLAME-DISSOC for the equilibrium value. Tolerance 2 K (assumption): GRI-Mech 3.0 enthalpies of "
        "N2/O2 agree with NIST-JANAF within 0.02 kJ/mol and of H2O within 0.15 kJ/mol up to 1800 K, i.e. about "
        "0.1 % of the sensible enthalpy rise of the flue gas, which is 1-1.5 K at 1350-1550 C; 2 K allows for that "
        "spread between Aspen's and GRI's data", ev)
    eqd = [t[2]["dT_equilibrium_minus_complete_K"] for t in fl]
    add(CheckResult("PHYS-FLAME-DISSOC", "", INFO, "T_ad(HP equilibrium) - T_ad(complete), baseline (K)",
                    b["dT_equilibrium_minus_complete_K"], None,
                    f"range over {n} cases {min(eqd):.2f} to {max(eqd):.2f} K; main equilibrium minor species at the "
                    "baseline (mole fraction): " + ", ".join(f"{k} {v:.1e}" for k, v in
                                                            list(b["equilibrium_minor_species_mole_frac"].items())[:4])),
        comp, "Cantera equilibrate('HP') with the full GRI-Mech 3.0 species set (OH, H, O, NO, ...) from the same "
              "reactant enthalpy", "Cantera 3 (GRI-Mech 3.0)",
        "dissociation lowers the flame temperature slightly", "INFORMATIONAL: neither Aspen nor the Python model "
        "includes dissociation or NO formation; the flame temperatures of the matrix are complete-combustion values",
        ev, status=INFO)
    w = max(fx)
    add(CheckResult("PHYS-FLUEHX", "", judge(w[0], PHYS_FLUEHX_TOL_REL),
                    "max |Q_Cantera - Q_Aspen| / |Q_Aspen| for FLUEHX over stored Aspen cases", w[0], PHYS_FLUEHX_TOL_REL,
                    f"{n} cases; worst {w[1]} ({w[2]['Q_cantera_kW']:.2f} vs {w[2]['Q_aspen_kW']:.2f} kW)"),
        comp, "FLUEHX duty = n_flue (h(T_stack) - h(T_flue)) with the Aspen FLUE composition and temperatures, "
              "Cantera ideal gas (GRI-Mech 3.0)", "Cantera 3 (GRI-Mech 3.0)",
        "agreement within the spread of evaluated ideal-gas data",
        "tolerance 0.5 % (assumption) = about 5 x the GRI-Mech vs NIST-JANAF enthalpy spread of the flue-gas species "
        "(about 0.1 % of the sensible enthalpy); flue gas at 1.1-1.2 bar treated as ideal gas", ev)
    w = max(pu)
    add(CheckResult("PHYS-PUMP", "", judge(w[0], PHYS_PUMP_TOL_REL),
                    "max |W_hand - W_Aspen| / W_Aspen for the PUMP brake power over stored Aspen cases", w[0],
                    PHYS_PUMP_TOL_REL,
                    f"{n} cases; worst {w[1]} ({w[2]['W_hand_kW']:.4f} vs {w[2]['W_aspen_kW']:.4f} kW); "
                    f"v_L = {w[2]['v_L_m3_mol'] * 1e6:.3f} cm3/mol, efficiency {w[2]['efficiency']}"),
        comp, "hand calculation W = n v_L (P_S1 - P_FEED) / eta: incompressible liquid, v_L of NH3 from the CoolProp "
              "reference EOS at the Aspen FEED state, eta = 0.75 (the Aspen input)",
        "CoolProp reference EOS for NH3 (Gao 2020)", "agreement within the liquid-volume uncertainty",
        "tolerance 1 % (assumption): typical accuracy of the liquid-volume correlations used by simulators "
        "(Rackett-type, about 1 %), larger than the neglected effects (0.2 mol% water in the volume, compressibility "
        "over the pressure rise, each < 0.2 %)", ev)
    if ua:
        w = max(ua)
        add(CheckResult("PHYS-FEHE-UA", "", judge(w[0], PHYS_UA_TOL_REL),
                        "max |UA_Aspen - Q/LMTD| / (Q/LMTD) over stored Aspen cases with FEHE", w[0], PHYS_UA_TOL_REL,
                        f"{len(ua)} cases; worst {w[1]}; with the thermochemical calorie (4.184 J) the deviation would "
                        f"be {w[2]['rel_dev_if_thermochemical_cal']:.1e}, so Aspen's 'cal' here is the International "
                        "Table calorie (4.1868 J)"),
            comp, "Aspen HeatX UA (cal/sec-K, converted with 4.1868 J/cal) against Q / LMTD computed from the four "
                  "terminal temperatures (counter-current, F = 1)", "counter-current LMTD relation",
            "UA = Q / LMTD (shortcut HeatX, LMTD correction factor 1)",
            "consistency of the Aspen HeatX shortcut output (duty, terminal temperatures, UA) and of the unit "
            "conversion; it is not a heat-transfer validation (no film coefficients are involved). Tolerance 1e-4 "
            "(assumption) = order of the Aspen convergence tolerance", ev)
    else:
        nr("PHYS-FEHE-UA", comp, "HeatX UA vs Q/LMTD", "LMTD relation", "-", "no Aspen case with a FEHE UA value")


# =====================================================================================  4 literature
def _X(T_C, P, eos="ideal"):
    from amcrax.thermodynamics import solve_equilibrium
    return 100 * solve_equilibrium(T_C + 273.15, P, {"NH3": 1.0}, eos=eos).conversion


def section_literature():
    from amcrax.thermodynamics import (equilibrium_constant, reaction_enthalpy_kJ_mol, reaction_gibbs_kJ_mol,
                                       species_enthalpy_kJ_mol)
    from scipy.optimize import brentq

    comp = "literature benchmarks"
    ypath = ROOT / "research" / "model_parameters.yaml"
    if not ypath.exists():
        nr("LIT", comp, "literature", "model_parameters.yaml", "", "research/model_parameters.yaml missing")
        return
    mp = yaml.safe_load(ypath.read_text(encoding="utf-8"))
    th = mp.get("thermodynamics", {})
    lit_rows = []

    def record(id, quantity, conditions, lit_value, unit, citekey, page, amcrax_value, tol, status=None, note="",
               relative=False):
        dev = None if (amcrax_value is None or lit_value is None) else amcrax_value - lit_value
        if status is None:
            status = judge(dev, tol)
        lit_rows.append({"id": id, "quantity": quantity, "conditions": conditions, "literature_value": lit_value,
                         "unit": unit, "citekey": citekey, "page": page, "amcrax_value": amcrax_value,
                         "deviation": dev, "tolerance": tol, "status": status, "note": note})
        return dev, status

    # reaction enthalpy at 298.15 K
    dH298 = reaction_enthalpy_kJ_mol(298.15)
    devs = []
    for i, e in enumerate(th.get("reaction_enthalpy_kJ_per_mol_NH3", [])):
        d, s = record(f"LIT-DH-{i}", "dH_rxn 298 K", "298.15 K, per mol NH3", float(e["value"]), "kJ/mol",
                      e["citekey"], e.get("page"), dH298, 0.5, note=e.get("note", ""))
        devs.append((abs(d), e["citekey"], s))
    if devs:
        w = max(devs)
        nf = sum(1 for d in devs if d[2] == FAIL)
        add(CheckResult("LIT-DH298", "", PASS if nf == 0 else FAIL, "max |dH_AmCraX - dH_lit| (kJ/mol)", w[0], 0.5,
                        f"AmCraX {dH298:.3f} kJ/mol vs {len(devs)} printed values ({nf} outside tolerance; worst {w[1]})"),
            comp, "reaction enthalpy at 298.15 K vs values printed in the papers", "; ".join(sorted({d[1] for d in devs})),
            "within rounding of printed values", "printed values rounded to 0.1-0.01 kJ/mol and from various data "
            "editions; tolerance 0.5 kJ/mol = assumption", [ypath, VAL / "literature_benchmarks.csv"])

    eb = th.get("equilibrium_conversion_benchmarks", {})
    ce = eb.get("cechetto_aspen_v11", {})
    pts = []
    for key, P in (("p_1bar", 1.0), ("p_4bar", 4.0), ("p_5bar", 5.0)):
        blk = ce.get(key)
        if blk:
            for T, X in zip(blk["T_C"], blk["X_pct"]):
                xa_i, xa_p = _X(T, P), _X(T, P, "pr")
                d, s = record(f"LIT-CECH-{P:g}-{T}", "equilibrium conversion", f"pure NH3, {T} C, {P:g} bar", X, "%",
                              "cechetto2023membrane", 9, xa_i, 0.3, note=f"Table 3; Aspen V11 RGibbs; AmCraX PR {xa_p:.2f}")
                pts.append((abs(d), T, P, s))
    if pts:
        w = max(pts)
        nf = sum(1 for p in pts if p[3] == FAIL)
        add(CheckResult("LIT-CECHETTO-T3", "", PASS if nf == 0 else FAIL, "max |X_AmCraX,ideal - X_lit| (pp)", w[0], 0.3,
                        f"{len(pts)} points at 1/4/5 bar, worst {w[1]} C/{w[2]:g} bar; {nf} outside tolerance"),
            comp, "equilibrium conversion of pure NH3 vs tabulated Aspen V11 RGibbs values",
            "cechetto2023membrane p. 9, Table 3", "agreement within printed precision (0.1 %)",
            "property method of the paper not stated; values printed to 0.1 %; tolerance 0.3 pp = assumption",
            [ypath, VAL / "literature_benchmarks.csv"])
    # statements
    x400 = _X(400, 1.0)
    x500_20 = _X(500, 20.0)
    for id, cond, val, lim in (("LIT-CECH-S1", ">99 % at 1 bar above 400 C (checked at 400 C)", x400, 99.0),
                               ("LIT-CECH-S2", ">95 % at 1-20 bar above 500 C (checked at 500 C, 20 bar)", x500_20, 95.0)):
        record(id, "equilibrium statement", cond, lim, "% (lower bound)", "cechetto2023membrane", 3, val, 0.0,
               status=PASS if val > lim else FAIL)
        add(CheckResult(id, "", PASS if val > lim else FAIL, "margin X_AmCraX - bound (pp)", val - lim, 0.0,
                        f"AmCraX {val:.2f} %"), comp, f"qualitative statement: {cond}", "cechetto2023membrane p. 3, Fig. 2",
            "statement holds", "bound check (pass if margin > 0)", [VAL / "literature_benchmarks.csv"])
    # figure readings (approximate): 3 pp tolerance
    fig_pts = []
    f2 = ce.get("fig2_200C_approx")
    if f2:
        for P, X in zip(f2["p_bar"], f2["X_pct"]):
            d, s = record(f"LIT-CECH-F2-{P}", "equilibrium conversion (figure reading)", f"200 C, {P} bar", X, "%",
                          "cechetto2023membrane", 3, _X(200, P), 3.0, note="read from figure")
            fig_pts.append((abs(d), "cechetto Fig.2", 200, P, s))
    xu = eb.get("xu_fig4a_approx", {})
    for key, P in (("p_0p1MPa", 1.0), ("p_3MPa", 30.0)):
        blk = xu.get(key)
        if blk:
            for T, X in zip(blk["T_C"], blk["X_pct"]):
                d, s = record(f"LIT-XU-{P:g}-{T}", "equilibrium conversion (figure reading)", f"{T} C, {P:g} bar", X, "%",
                              "xu2025review", "5-6", _X(T, P), 3.0, note="Fig. 4(a), read from figure")
                fig_pts.append((abs(d), "xu Fig.4a", T, P, s))
    if fig_pts:
        w = max(fig_pts)
        nf = sum(1 for p in fig_pts if p[4] == FAIL)
        add(CheckResult("LIT-FIGREAD", "", PASS if nf == 0 else FAIL, "max |X_AmCraX - X_figure| (pp)", w[0], 3.0,
                        f"{len(fig_pts)} points; worst {w[1]} {w[2]} C/{w[3]:g} bar; {nf} outside tolerance"),
            comp, "equilibrium conversion vs values read from published figures",
            "cechetto2023membrane Fig. 2 p. 3; xu2025review Fig. 4(a) p. 5-6",
            "agreement within figure-reading uncertainty", "values read from figures (approximate); tolerance 3 pp = "
            "assumption; 100-200 C lies below the AmCraX operating range", [VAL / "literature_benchmarks.csv"])
    # not comparable / flagged
    hh = eb.get("hansen_hsc_quoted")
    if hh:
        for T, X in zip(hh["T_C"], hh["X_pct"]):
            record(f"LIT-HANSEN-{T}", "equilibrium conversion", f"{T} C, pressure not stated", X, "%", "hansen2024hysys", 2,
                   None, None, status="not_comparable", note=f"pressure not stated; AmCraX at 1 bar would be {_X(T, 1.0):.2f}")
        add(CheckResult("LIT-HANSEN", "", INFO, "not comparable", None, None,
                        "pressure not stated in the source -> not comparable (AmCraX 1 bar values listed in CSV for context)"),
            comp, "HSC Chemistry equilibrium conversions quoted by Hansen", "hansen2024hysys p. 2, Table 1",
            "-", "under-specified conditions", [VAL / "literature_benchmarks.csv"], status=INFO)
    for nb in eb.get("not_valid_benchmark", []):
        record(f"LIT-INVALID-{nb['citekey']}", "equilibrium conversion", "500 C, 30 bar", 96.4, "%", nb["citekey"], 19,
               _X(500, 30.0), None, status="not_comparable", note=nb["reason"])
    for ck, desc in (("hansen2024hysys", "Gibbs cracker 437 C conversion 99.42 % (pressure not stated)"),
                     ("farokhi2025costoptimization", "Gibbs cracker conversion 98.15 % (T, P not stated in benchmark)"),
                     ("kum2026heatintegrated", "cracker duty 79.25 kJ/mol NH3 (fired kinetic reactor incl. preheat; "
                                               "boundary differs from AmCraX isothermal RGibbs)")):
        record(f"LIT-NC-{ck}", "process result", desc, None, "", ck, "", None, None, status="not_comparable",
               note="conditions under-specified for a like-for-like comparison")
    add(CheckResult("LIT-PROCESS", "", INFO, "not comparable", None, None,
                    "Hansen 437 C Gibbs conversion, Farokhi Gibbs conversion and Kum cracker duty lack the pressure or "
                    "reactor boundary needed for a like-for-like run; listed as not comparable in literature_benchmarks.csv"),
        comp, "process-paper simulation results at their stated conditions", "hansen2024hysys; farokhi2025costoptimization; "
        "kum2026heatintegrated", "-", "under-specified conditions", [VAL / "literature_benchmarks.csv"], status=INFO)
    # dG = 0 temperature (Maccarrone: ~450 K)
    T0 = brentq(lambda T: reaction_gibbs_kJ_mol(T), 350, 600)
    record("LIT-MACC-T0", "T at which dG_rxn = 0", "1 bar standard state", 450.0, "K", "maccarrone2025comprehensive", 4,
           T0, 15.0, note="read from Fig. 1b text (rounded)")
    add(CheckResult("LIT-MACC-T0", "", judge(T0 - 450.0, 15.0), "T(dG=0)_AmCraX - 450 K (K)", T0 - 450.0, 15.0,
                    f"AmCraX T(dG=0) = {T0:.1f} K"), comp, "temperature where decomposition becomes spontaneous",
        "maccarrone2025comprehensive p. 4, Fig. 1b", "~450 K", "literature value is a rounded statement; "
        "tolerance 15 K = assumption", [VAL / "literature_benchmarks.csv"])
    # Kum dGr correlation (per 2 mol NH3, J)
    kc = []
    for T in (623.15, 773.15, 873.15):
        lit = (95117 - 193.67 * T - 0.035293 * T ** 2 + 9.22e-6 * T ** 3) / 1000.0
        am = 2 * reaction_gibbs_kJ_mol(T)
        d, s = record(f"LIT-KUM-DG-{T:g}", "dG_rxn per 2 mol NH3", f"{T} K", lit, "kJ", "kum2026heatintegrated", 4,
                      am, 1.0, note="Eq. 4 correlation (basis per 2 mol NH3 verified by research agent)")
        kc.append((abs(d), T))
    w = max(kc)
    add(CheckResult("LIT-KUM-DG", "", judge(w[0], 1.0), "max |dG_AmCraX - dG_Kum Eq.4| (kJ per 2 mol NH3)", w[0], 1.0,
                    f"worst at {w[1]} K"), comp, "Gibbs energy correlation of the reaction",
        "kum2026heatintegrated p. 4, Eq. 4", "agreement of correlation", "correlation fitted by the authors; "
        "tolerance 1 kJ = assumption", [VAL / "literature_benchmarks.csv"])
    # Maccarrone Kp correlations (amcrax_check_values): informational
    kpc = th.get("kp_correlations", {}).get("amcrax_check_values")
    if kpc:
        for eq in ("eq3", "eq4", "eq5"):
            for T, K in zip(kpc["T_K"], kpc[eq]):
                record(f"LIT-MACC-{eq}-{T}", "Kp (per mol NH3)", f"{T} K", K, "-", "maccarrone2025comprehensive", 4,
                       equilibrium_constant(T), None, status=INFO,
                       note="misprinted correlation, corrected reading by extraction agent; informational")
        worst = max(abs(equilibrium_constant(T) / K - 1) for eq in ("eq3", "eq4", "eq5")
                    for T, K in zip(kpc["T_K"], kpc[eq]))
        add(CheckResult("LIT-MACC-KP", "", INFO, "max |K_AmCraX/K_corr - 1|", worst, None,
                        "corrected readings of misprinted correlations (Eqs. 3-5); not judged"),
            comp, "Kp correlations quoted in review", "maccarrone2025comprehensive p. 4, Eqs. 3-5", "-",
            "correlations misprinted in source; corrected readings are interpretations", [VAL / "literature_benchmarks.csv"],
            status=INFO)
    # LHV / stoichiometric constants
    oth = th.get("other", {})
    dHc = (0.5 * species_enthalpy_kJ_mol("N2", 298.15) + 1.5 * species_enthalpy_kJ_mol("H2O", 298.15)
           - species_enthalpy_kJ_mol("NH3", 298.15) - 0.75 * species_enthalpy_kJ_mol("O2", 298.15))
    consts = [("LIT-NH3-COMB", "NH3 combustion enthalpy to H2O(g)", -317.0, dHc, 1.0, "kJ/mol", "xu2025review", 6),
              ("LIT-LHV-H2", "LHV of H2", 120.0, LHV_KJ_PER_MOL["H2"] / MOLAR_MASS["H2"], 0.5, "MJ/kg", "xu2025review", 4),
              ("LIT-NH3-PER-H2", "theoretical NH3 per kg H2", 5.632, MOLAR_MASS["NH3"] / (1.5 * MOLAR_MASS["H2"]), 0.005,
               "kg/kg", "cho2026nickel", 10),
              ("LIT-H-CONTENT", "H content of NH3", 17.8, 100 * 1.5 * MOLAR_MASS["H2"] / MOLAR_MASS["NH3"], 0.1, "wt%",
               "xu2025review", 3)]
    for id, q, lv, av, tol, unit, ck, pg in consts:
        d, s = record(id, q, "standard", lv, unit, ck, pg, av, tol)
        add(CheckResult(id, "", s, f"AmCraX - literature ({unit})", d, tol, f"AmCraX {av:.4f} vs {lv}"),
            "thermodynamics / constants", q, f"{ck} p. {pg}", "agreement within rounding of printed value",
            "printed value rounded; tolerance = assumption", [VAL / "literature_benchmarks.csv"])
    write_csv(VAL / "literature_benchmarks.csv", lit_rows)


# =====================================================================================  5 tests + other modules
def section_pytest(skip: bool):
    junit = VAL / "pytest_junit.xml"
    if not skip:
        subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", f"--junitxml={junit}", "-p", "no:cacheprovider"],
                       cwd=ROOT, capture_output=True, text=True, timeout=1500)
    if not junit.exists():
        nr("PYTEST", "test suite", "pytest", "tests/", "all tests pass", "pytest_junit.xml not produced")
        return
    tree = ET.parse(junit)
    per: dict[str, dict] = {}
    for tc in tree.iter("testcase"):
        f = (tc.get("classname") or "").split(".")
        key = next((x for x in f if x.startswith("test_")), f[0] if f else "?") + ".py"
        d = per.setdefault(key, {"n": 0, "fail": 0, "skip": 0, "names": []})
        d["n"] += 1
        if tc.find("failure") is not None or tc.find("error") is not None:
            d["fail"] += 1
            d["names"].append(tc.get("name"))
        elif tc.find("skipped") is not None:
            d["skip"] += 1
    for key, d in sorted(per.items()):
        st = PASS if d["fail"] == 0 and d["n"] > d["skip"] else (FAIL if d["fail"] else INFO)
        add(CheckResult(f"PYTEST-{key[:-3]}", "", st, "failed + errored tests", float(d["fail"]), 0.0,
                        f"{d['n']} tests, {d['fail']} failed/errored, {d['skip']} skipped"
                        + (f"; failing: {', '.join(d['names'][:6])}" if d["names"] else "")),
            key[5:-3], "pytest unit/integration tests", f"tests/{key}", "all tests pass", "",
            [junit, ROOT / "tests" / key])


def section_optional():
    # kinetics validation
    kv = VAL / "kinetics_validation.csv"
    if kv.exists():
        rows = read_csv(kv)
        cols = rows[0].keys() if rows else []
        stcol = next((c for c in cols if c.lower() in ("status", "pass", "ok")), None)
        if "deviation" in cols and "basis" in cols:
            groups = {
                "KIN-TABLE2": ([r for r in rows if r["dataset"].endswith(":Table2")], 0.10, PASS,
                               "rate constants from Table 1 Arrhenius parameters vs Table 2 values at 773.15 K",
                               "takahashi2016kinetic p. 5, Table 2",
                               "tolerance 10 % as recorded in research/model_parameters.yaml (Table 1 rounding)"),
                "KIN-NI-PRED": ([r for r in rows if r["dataset"].startswith("takahashi_ni") and "ANCHOR" not in r["basis"]],
                                0.05, PASS, "Ni/MgO microkinetic PFR conversion vs published curves (Figs. 3, 5)",
                                "takahashi2016kinetic Figs. 3a/3b/5a (read from figures)",
                                "W/F inferred from one anchor point (assumption); figure readings approximate (+/-2 points); "
                                "tolerance 0.05 absolute = assumption"),
                "KIN-RU-PRED": ([r for r in rows if r["dataset"].startswith("takahashi_ru") and "ANCHOR" not in r["basis"]],
                                0.05, PASS, "Ru/MgO microkinetic PFR conversion vs published curves (Figs. 4, 5)",
                                "takahashi2016kinetic Figs. 4a/4b/5b (read from figures)",
                                "W/F inferred from one anchor point (assumption); figure readings approximate; "
                                "tolerance 0.05 absolute = assumption"),
                "KIN-DICARLO": ([r for r in rows if r["dataset"].startswith("dicarlo")], 0.01, INFO,
                                "Temkin-Pyzhev Ru/Al2O3 rate law in PFR vs measured conversion",
                                "maccarrone2025comprehensive Table 2 (Di Carlo 2014)",
                                "rate law fitted to these data (not independent) and near equilibrium -> informational"),
            }
            for gid, (sub, tol, mode, method, ref, lim) in groups.items():
                if not sub:
                    continue
                d = [(abs(fnum(r["deviation"])), r["condition"]) for r in sub if fnum(r["deviation"]) is not None]
                w = max(d)
                nf = sum(1 for x in d if x[0] > tol)
                unit = sub[0]["deviation_unit"]
                st = (PASS if nf == 0 else FAIL) if mode == PASS else INFO
                add(CheckResult(gid, "", st, f"max |deviation| ({unit})", w[0], tol,
                                f"{len(d)} points, {nf} outside tolerance; worst: {w[1]}"),
                    "kinetics", method, ref, "model reproduces literature within tolerance", lim, [kv], status=st,
                    cause="kinetics_figure_predictions" if gid in ("KIN-NI-PRED", "KIN-RU-PRED") else None)
        elif stcol:
            nf = sum(1 for r in rows if str(r[stcol]).lower() in ("fail", "false", "0"))
            add(CheckResult("KIN-VAL", "", PASS if nf == 0 else FAIL, "rows failing own tolerance", float(nf), 0.0,
                            f"{len(rows)} rows; column '{stcol}'"), "kinetics", "rate-law reproduction of published values",
                "see kinetics_validation.csv", "all rows within stated tolerance", "tolerances set by the kinetics agent", [kv])
        else:
            add(CheckResult("KIN-VAL", "", INFO, "rows", float(len(rows)), None, f"columns {list(cols)}"), "kinetics",
                "kinetics validation table", "kinetics_validation.csv", "-", "no status column to judge", [kv], status=INFO)
    else:
        nr("KIN-VAL", "kinetics", "rate-law reproduction of published values", "takahashi2016kinetic",
           "reproduces published rates", "results/validation/kinetics_validation.csv not present yet")
    # optimisation Aspen verification
    ov = paths.RESULTS_OPTIMISATION / "aspen_verification.json"
    if ov.exists():
        try:
            d = json.loads(ov.read_text(encoding="utf-8"))
            cr = check_aspen_verification(d, "OPT-ASPEN")
            add(cr, "optimisation", "optimisation candidates (Python model) re-solved in Aspen Plus V15; judged by the "
                "criterion stated in the file: Aspen converged AND every primary metric within tolerance_relative",
                "Aspen Plus V15", f"criterion: {d.get('criterion', '-')}",
                f"tolerance {d.get('tolerance_relative')} relative (file's stated tolerance; assumption). This item "
                "previously took the maximum over every numeric field incl. secondary metrics; it now reads the file "
                "by its own documented criterion - a correction of how the check reads the file, not a relaxed "
                "tolerance. Secondary metrics (individual duties such as FEHE, minor cost items such as cooling "
                "water) deviate by up to the value quoted in the result, for the feed-section enthalpy reason of "
                "FS-<case>; they are reported, not judged", [ov, paths.RESULTS_OPTIMISATION / "aspen_verification.csv"])
        except Exception as e:  # noqa: BLE001
            nr("OPT-ASPEN", "optimisation", "Aspen verification", "Aspen", "-", f"unreadable: {e}", [ov])
    else:
        nr("OPT-ASPEN", "optimisation", "Aspen re-run of the surrogate optimum", "Aspen Plus V15",
           "optimum confirmed by Aspen", "results/optimisation/aspen_verification.json not present yet")
    # optimisation feasibility hook on any optimum file
    so = paths.RESULTS_OPTIMISATION / "single_objective.json"
    found = False
    if so.exists():
        d = json.loads(so.read_text(encoding="utf-8"))
        if isinstance(d, dict) and d.get("results"):
            add(check_single_objective_feasibility(d, "OPT-FEAS"), "optimisation",
                "each reported single-objective optimum: decision variables inside their stated bounds, constraints "
                "g >= 0 satisfied when flagged feasible, at_bound flags consistent with the optimum values",
                "results/optimisation/single_objective.json (constraint convention 'g >= 0 satisfied')",
                "feasible optima; infeasible results labelled as such",
                "tolerance 1e-6 in the constraint's own units (numerical solver tolerance; assumption); at_bound "
                "consistency within 1e-6 x variable range; Python process model, not Aspen", [so])
            found = True
    opt_files = sorted(p for p in paths.RESULTS_OPTIMISATION.glob("*.json") if p.name != "single_objective.json")
    for p in opt_files:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(d, dict):
            continue
        x = d.get("optimum_inputs") or d.get("best_inputs") or (d.get("optimum") or {}).get("inputs")
        if isinstance(x, dict):
            b = {}
            for k, f in CaseInputs.model_fields.items():
                lo = hi = None
                for m in f.metadata:
                    for attr in ("ge", "gt"):
                        if getattr(m, attr, None) is not None:
                            lo = getattr(m, attr)
                    for attr in ("le", "lt"):
                        if getattr(m, attr, None) is not None:
                            hi = getattr(m, attr)
                if k in x and lo is not None and hi is not None:
                    b[k] = (lo, hi)
            add(check_optimisation_feasibility({k: float(v) for k, v in x.items() if isinstance(v, (int, float))}, b,
                                               id=f"OPT-FEAS-{p.stem}"), "optimisation", "optimum inside CaseInputs bounds",
                "amcrax.schemas.CaseInputs", "feasible", "only variable bounds checked", [p])
            found = True
    if not found:
        nr("OPT-FEAS", "optimisation", "optimum feasibility (bounds/constraints)", "CaseInputs bounds", "feasible",
           "no optimisation result with optimum inputs found in results/optimisation/")
    # economics hook
    base = load_sim(SIMS / "baseline.json")
    try:
        import amcrax.economics as eco  # noqa: F401
        fn = getattr(eco, "compute_lcoh", None)
        EA = getattr(eco, "EconomicAssumptions", None)
        if fn is None or EA is None or base is None:
            raise ImportError("compute_lcoh/EconomicAssumptions not exported yet")
        res = fn(base, EA())
        dd = res.model_dump() if hasattr(res, "model_dump") else dict(res)
        total = next((v for k, v in dd.items() if "lcoh" in k.lower() and isinstance(v, (int, float))), None)
        compd = next((v for k, v in dd.items() if isinstance(v, dict) and k.lower() in
                      ("breakdown", "components", "lcoh_breakdown", "breakdown_usd_per_kg")), None)
        if total is not None and compd:
            add(check_economic_consistency({k: float(v) for k, v in compd.items() if isinstance(v, (int, float))},
                                           float(total), "ECON-SUM", tol=1e-6), "economics",
                "LCOH components sum to total (Aspen baseline, default assumptions)", "arithmetic identity",
                "sum = total", "", [ROOT / "backend/amcrax/economics"])
        else:
            add(CheckResult("ECON-SUM", "", INFO, "", None, None, f"LCOH result fields {list(dd)[:12]}; no breakdown "
                            "dict recognised"), "economics", "LCOH components sum to total", "arithmetic identity", "-",
                "format not recognised", [], status=INFO)
        if total is not None:
            ok = 0 < float(total) < 50
            add(CheckResult("ECON-RANGE", "", PASS if ok else FAIL, "LCOH sanity bound (0, 50) USD/kg", float(total), 50.0,
                            f"LCOH {float(total):.3f}"), "economics", "LCOH in plausible range",
                "cho2026nickel reports 5.29-5.44 USD/kg (different plant)", "0 < LCOH < 50 USD/kg",
                "coarse sanity bound only (assumption)", [])
    except Exception as e:  # noqa: BLE001
        nr("ECON-SUM", "economics", "LCOH component consistency", "arithmetic identity", "sum = total",
           f"amcrax.economics not usable yet: {type(e).__name__}: {e}")
    # stored economics / environmental outputs (results/simulations/economics_*.json, environmental_*.json)
    for p in sorted(SIMS.glob("economics_*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        bd, tot = d.get("breakdown_USD_per_kg"), d.get("lcoh_USD_per_kg")
        if isinstance(bd, dict) and isinstance(tot, (int, float)):
            add(check_economic_consistency({k: float(v) for k, v in bd.items()}, float(tot), f"ECON-SUM-{p.stem}"),
                "economics", "LCOH breakdown sums to LCOH (stored result)", "arithmetic identity", "sum = total", "", [p])
        fl, fe = d.get("stoichiometric_floor_kg_nh3_per_kg_h2"), d.get("kg_nh3_feed_per_kg_h2")
        if isinstance(fl, (int, float)) and isinstance(fe, (int, float)):
            add(CheckResult(f"ECON-STOICH-{p.stem}", "", PASS if fe >= fl else FAIL,
                            "kg NH3 fed per kg H2 minus stoichiometric floor", fe - fl, 0.0,
                            f"{fe:.4f} vs floor {fl:.4f} kg/kg"), "economics", "NH3 consumption above stoichiometric minimum",
                "stoichiometry (5.632 kg/kg)", ">= floor", "bound check (pass if margin >= 0)", [p])
    for p in sorted(SIMS.glob("environmental_*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        worst, neg, n = 0.0, 0, 0
        for sc in (d.get("scenarios") or {}).values():
            bd, tot = sc.get("breakdown_kgCO2e_per_kgH2"), sc.get("total_kgCO2e_per_kgH2")
            if isinstance(bd, dict) and isinstance(tot, (int, float)):
                n += 1
                s = sum(float(v) for v in bd.values())
                worst = max(worst, abs(s - tot) / max(abs(tot), 1e-12))
                neg += sum(1 for v in bd.values() if float(v) < 0) + (tot < 0)
        if n:
            add(CheckResult(f"ENV-SUM-{p.stem}", "", PASS if (worst <= 1e-6 and neg == 0) else FAIL,
                            "max relative |sum(breakdown) - total|", worst, 1e-6,
                            f"{n} scenarios; negative contributions {neg}"), "environmental",
                "carbon-intensity breakdown sums to total, all contributions >= 0", "arithmetic identity",
                "sum = total", "simplified activity x factor accounting (not an LCA)", [p])
    try:
        import amcrax.environmental as env
        fn = getattr(env, "carbon_intensity")
        res = fn(base, "grey/natural_gas")
        dd = res.model_dump() if hasattr(res, "model_dump") else dict(res)
        tot = next((v for k, v in dd.items() if "total" in k.lower() and isinstance(v, (int, float))), None)
        add(CheckResult("ENV-CI", "", INFO if tot is None else (PASS if tot >= 0 else FAIL), "carbon intensity >= 0",
                        tot, 0.0 if tot is not None else None, f"fields {list(dd)[:10]}"), "environmental",
            "carbon intensity non-negative (grey NH3)", "physical bound", ">= 0", "", [])
    except Exception as e:  # noqa: BLE001
        nr("ENV-CI", "environmental", "carbon-intensity sanity", "physical bound", ">= 0",
           f"amcrax.environmental not usable yet: {type(e).__name__}: {e}")


# =====================================================================================  output
def write_outputs():
    counts = {s: sum(1 for m in MATRIX if m["status"] == s) for s in (PASS, FAIL, NOT_RUN, INFO)}
    fams: dict[str, dict] = {}
    for m in MATRIX:
        f = fams.setdefault(m["family"], {"n_items": 0, PASS: 0, FAIL: 0, NOT_RUN: 0, INFO: 0})
        f["n_items"] += 1
        f[m["status"]] += 1
    causes = []
    for key, desc in ROOT_CAUSES.items():
        ids = [m["id"] for m in MATRIX if m["status"] == FAIL and m["root_cause"] == key]
        if ids:
            causes.append({"cause": key, "description": desc, "n_items": len(ids), "items": ids})
    unassigned = [m["id"] for m in MATRIX if m["status"] == FAIL and m["root_cause"] not in ROOT_CAUSES]
    if unassigned:
        causes.append({"cause": "unassigned", "description": "failing items without a documented root cause - investigate",
                       "n_items": len(unassigned), "items": unassigned})
    doc = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "generator": "scripts/build_validation_matrix.py",
           "summary": {"n_items": len(MATRIX), **counts, "by_family": fams, "failure_root_causes": causes,
                       "failing_ids": [m["id"] for m in MATRIX if m["status"] == FAIL],
                       "not_run_ids": [m["id"] for m in MATRIX if m["status"] == NOT_RUN]},
           "items": MATRIX}
    (VAL / "validation_matrix.json").write_text(json.dumps(doc, indent=2, default=str), encoding="utf-8")
    DOC.parent.mkdir(parents=True, exist_ok=True)

    def esc(s):
        return str(s if s is not None else "").replace("|", "\\|").replace("\n", " ")

    def fmt(v):
        return "" if v is None else (f"{v:.4g}" if isinstance(v, float) else str(v))
    L = ["# AmCraX validation matrix", "",
         f"Generated {doc['generated_utc']} by `scripts/build_validation_matrix.py` (do not edit by hand; "
         "re-run the script). Machine-readable copy: `results/validation/validation_matrix.json`.", "",
         f"**Summary:** {len(MATRIX)} items - pass {counts[PASS]}, fail {counts[FAIL]}, not run {counts[NOT_RUN]}, "
         f"informational {counts[INFO]}.", "",
         "Status rules: `pass` only with a computed metric and an explicit tolerance; `fail` items are kept and "
         "reported; `not_run` means the input does not exist yet; `informational` means no tolerance applies "
         "(e.g. under-specified literature conditions). Tolerances marked *assumption* are engineering choices, "
         "stated before comparison. See `docs/validation/discrepancy_analysis.md` for the equilibrium investigation.", ""]
    L += ["**Counts by family:**", "", "| Family | Items | pass | fail | not run | informational |", "|---|---|---|---|---|---|"]
    for f, c in fams.items():
        L.append(f"| {f} | {c['n_items']} | {c[PASS]} | {c[FAIL]} | {c[NOT_RUN]} | {c[INFO]} |")
    L.append("")
    if counts[FAIL]:
        L += ["**Failing items by root cause** (each distinct cause listed once):", ""]
        for c in causes:
            L += [f"* **{c['cause']}** ({c['n_items']} items): {esc(c['description'])} Items: "
                  + ", ".join(f"`{i}`" for i in c["items"])]
        L.append("")
    L += ["| ID | Component | Method | Reference | Expected | Actual result | Metric | Value | Tol. | Status | Limitations | Evidence |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in MATRIX:
        L.append("| " + " | ".join(esc(x) for x in (m["id"], m["model_component"], m["validation_method"], m["reference"],
                                                      m["expected_behaviour"], m["actual_result"], m["metric"],
                                                      fmt(m["value"]), fmt(m["tolerance"]), f"**{m['status']}**",
                                                      m["limitations"], ", ".join(f"`{e}`" for e in m["evidence_files"])))
                 + " |")
    DOC.write_text("\n".join(L) + "\n", encoding="utf-8")
    return counts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-pytest", action="store_true", help="reuse an existing pytest_junit.xml")
    a = ap.parse_args(argv)
    for name, fn in (("equilibrium", section_equilibrium), ("flowsheet", section_flowsheet),
                     ("aspen_internal", section_aspen_internal), ("independent_physics", section_independent_physics),
                     ("literature", section_literature),
                     ("optional", section_optional), ("pytest", lambda: section_pytest(a.skip_pytest))):
        try:
            fn()
        except Exception as e:  # noqa: BLE001  - a crashing section must show up, not vanish
            import traceback
            traceback.print_exc()
            add(CheckResult(f"SECTION-{name}", "", FAIL, "section crashed", None, None, f"{type(e).__name__}: {e}"),
                "validation pipeline", f"section {name}", "-", "runs", "", [], status=FAIL,
                actual=f"section crashed: {type(e).__name__}: {e}")
    counts = write_outputs()
    print(json.dumps(counts))
    for m in MATRIX:
        if m["status"] == FAIL:
            print(f"  FAIL {m['id']}: {m['actual_result'][:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
