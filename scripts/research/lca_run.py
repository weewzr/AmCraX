"""Scenario-based LCA of imported ammonia in Singapore (workstream U). Deterministic; re-run:
   python scripts/research/lca_run.py
Writes results/research/lca/*, results/research/validation/lca.json, results/figures/research/lca_*.png,
research/reference_additions/enduse_lca.json (shared with enduse_run.py, which merges its own entries).
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from amcrax.enduse import (breakeven_ef, carbon_intensity, hydrogen_activity, load_cracker, power_activity)  # noqa: E402
from amcrax.environmental import carbon_intensity as old_ci, reference_lines  # noqa: E402
from amcrax.environmental import lca  # noqa: E402
from amcrax.enduse import pathways as pw  # noqa: E402
from amcrax.enduse import params as P  # noqa: E402
from amcrax.plotstyle import C_AMBER, C_GREY, C_H2, C_HEAT, C_N2, C_NH3, C_PRIMARY, apply_style, plt  # noqa: E402

OUT = ROOT / "results" / "research" / "lca"
FIG = ROOT / "results" / "figures" / "research"
VAL = ROOT / "results" / "research" / "validation"
SCRIPT = "scripts/research/lca_run.py"
D0 = 5000.0
ROUTES = ["green", "green_lee", "blue", "blue_v2", "blue_param", "grey", "coal"]


def prov(source_type: str, summary: str) -> dict:
    return {"generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "script": SCRIPT,
            "source_type": source_type, "inputs_summary": summary,
            "model_versions": {"amcrax.environmental.lca": "1", "aspen_inputs": "stored results/simulations/baseline.json (Aspen Plus V15)"}}


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=float), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def foot(fig, text="AmCraX workstream U | emission factors: results/research/lca/assumptions.json | cracker activity: stored Aspen Plus V15 baseline | turbine efficiency: literature-calibrated (Ahmad 2025)"):
    fig.text(0.01, 0.005, text, fontsize=6.0, color=C_GREY, ha="left", va="bottom")


def main() -> None:
    apply_style()
    h2 = hydrogen_activity("baseline", "h2_industrial", "industrial H2 (99.9 %)", "")
    pw_direct = power_activity("direct")
    pw_part40 = power_activity("partial_exhaust", 0.4)
    pw_pur = power_activity("full_purified")
    ccgt = lca.ccgt_ci_kg_per_MWh()
    smr_u, smr_c = lca.smr_h2_ci(False), lca.smr_h2_ci(True)
    grid_mwh = lca.f("grid_ef_singapore_2024") * 1000.0

    # ---- 1 routes -------------------------------------------------------------------------------------
    routes = []
    for r in ROUTES:
        s = lca.route_spec(r)
        row = {"route": r, "label": s.label, "gate_kgCO2e_per_kgNH3": s.ef, "range_low": s.low, "range_high": s.high,
               "delivered_5000km": lca.delivered_nh3_ef(s.ef, D0), "source_type": s.source_type}
        for nm, a in (("H2_kgCO2e_per_kg", h2), ("direct_NH3_CCGT_kgCO2e_per_MWh", pw_direct),
                      ("cracked_purified_H2_CCGT_kgCO2e_per_MWh", pw_pur)):
            b = carbon_intensity(a, s.ef, D0)
            row[nm] = b["total"]
            if nm == "H2_kgCO2e_per_kg":
                row["H2_breakdown"] = b
            if nm == "direct_NH3_CCGT_kgCO2e_per_MWh":
                row["MWh_breakdown"] = b
        row["H2_low_high"] = [carbon_intensity(h2, s.low, D0)["total"], carbon_intensity(h2, s.high, D0)["total"]]
        row["MWh_low_high"] = [carbon_intensity(pw_direct, s.low, D0)["total"], carbon_intensity(pw_direct, s.high, D0)["total"]]
        routes.append(row)

    # ---- 2 alternatives and break-evens --------------------------------------------------------------
    alts = {
        "ccgt_ng_kgCO2e_per_MWh": {"central": ccgt, "low_eff_0.50": lca.ccgt_ci_kg_per_MWh(0.50), "high_eff_0.60": lca.ccgt_ci_kg_per_MWh(0.60),
                                    **{f"leak_{x}": lca.ccgt_ci_kg_per_MWh(leak_frac=x) for x in lca.f("ng_upstream_leak_scenarios")},
                                    "source_type": "literature combustion factor + assumption efficiency"},
        "grid_average_kgCO2e_per_MWh": {"central": grid_mwh, "source_type": "literature (EMA 2024)"},
        "smr_h2_unabated_kgCO2e_per_kgH2": {"central": smr_u, "range": lca.f("smr_h2_unabated"), "source_type": "literature"},
        "smr_h2_ccs_kgCO2e_per_kgH2": {"central": smr_c, "range": lca.f("smr_h2_ccs"), "upper_sensitivity": lca.f("smr_h2_ccs_high"),
                                       "source_type": "literature (low confidence)"},
    }
    be = []
    for dist in (2000.0, D0, 12000.0):
        for name, a, cmp_name, cmp_ci in (
            ("industrial H2 vs SMR unabated", h2, "smr_unabated", smr_u),
            ("industrial H2 vs SMR + CCS", h2, "smr_ccs", smr_c),
            ("direct NH3 CCGT vs NG CCGT", pw_direct, "ccgt_ng", ccgt),
            ("direct NH3 CCGT vs NG CCGT (leak 1.5 %)", pw_direct, "ccgt_ng_leak", lca.ccgt_ci_kg_per_MWh(leak_frac=0.015)),
            ("direct NH3 CCGT vs grid average", pw_direct, "grid", grid_mwh),
            ("partial crack 40 vol% H2 vs NG CCGT", pw_part40, "ccgt_ng", ccgt),
            ("cracked + purified H2 CCGT vs NG CCGT", pw_pur, "ccgt_ng", ccgt),
            ("cracked + purified H2 CCGT vs grid average", pw_pur, "grid", grid_mwh),
        ):
            be.append({"comparison": name, "distance_km": dist, "alternative_CI": cmp_ci,
                       "breakeven_NH3_gate_EF_kgCO2e_per_kgNH3": breakeven_ef(a, cmp_ci, dist),
                       "note": "NH3 gate EF at or below this value cuts emissions versus the alternative (negative = never, even at zero upstream)"})
    be_blue = {"blue_v1": lca.blue_nh3_ef(1, 0), "blue_v2": lca.blue_nh3_ef(1, 1), "blue_param": lca.route_spec("blue_param").ef}

    # ---- 3 distance scenarios ------------------------------------------------------------------------
    dist_rows = []
    for d in (0.0, 2000.0, 5000.0, 8000.0, 12000.0):
        for r in ("green", "blue", "grey"):
            ef = lca.route_spec(r).ef
            dist_rows.append({"distance_km": d, "route": r, "shipping_kgCO2e_per_kgNH3": lca.ship_kg_per_kg_nh3(d),
                              "H2_kgCO2e_per_kg": carbon_intensity(h2, ef, d)["total"],
                              "direct_NH3_CCGT_kgCO2e_per_MWh": carbon_intensity(pw_direct, ef, d)["total"]})

    # ---- 4 OAT and Monte Carlo (blue, direct NH3 CCGT and industrial H2) ------------------------------
    def blue_power_margin(capture=0.95, leak=0.015, dist=D0, elec_scale=1.0, cc_eff=0.55, cc_leak=0.0):
        ef = lca.blue_nh3_ef(capture, 0.0, leak)
        a = pw_direct
        n = a.nh3_kg / elec_scale
        t = carbon_intensity(a, ef, dist)["total"] / a.nh3_kg * n
        return lca.ccgt_ci_kg_per_MWh(cc_eff, cc_leak) - t

    base_margin = blue_power_margin()
    oat_defs = {
        "process CO2 capture 0.90-1.00": ("capture", 0.90, 1.00),
        "extra upstream CH4 leakage 0.2-3.0 %": ("leak", 0.002, 0.03),
        "sea distance 2000-12000 km": ("dist", 2000.0, 12000.0),
        "turbine electricity per kg NH3 +/-6 % (about +/-3 pts)": ("elec_scale", 0.94, 1.06),
        "CCGT efficiency 0.50-0.60": ("cc_eff", 0.50, 0.60),
        "CCGT upstream CH4 leakage 0-3 %": ("cc_leak", 0.0, 0.03),
    }
    oat = []
    for label, (k, lo, hi) in oat_defs.items():
        oat.append({"parameter": label, "margin_at_low": blue_power_margin(**{k: lo}), "margin_at_high": blue_power_margin(**{k: hi})})
    rng = np.random.default_rng(20261123)
    N = 20000
    cap = rng.uniform(0.9, 1.0, N)
    lk = rng.uniform(0.002, 0.03, N)
    dist = rng.uniform(2000, 12000, N)
    es = rng.uniform(0.94, 1.06, N)
    ce = rng.uniform(0.50, 0.60, N)
    cl = rng.uniform(0.0, 0.03, N)
    marg = np.array([blue_power_margin(cap[i], lk[i], dist[i], es[i], ce[i], cl[i]) for i in range(N)])
    smr_u_s = rng.uniform(*lca.f("smr_h2_unabated"), N)
    smr_c_s = rng.uniform(lca.f("smr_h2_ccs")[0], lca.f("smr_h2_ccs_high"), N)
    h2_blue = np.array([carbon_intensity(h2, lca.blue_nh3_ef(cap[i], 0.0, lk[i]), dist[i])["total"] for i in range(N)])
    mc = {
        "n": N, "seed": 20261123, "distributions": "uniform over the stated ranges; ranges are sourced or flagged scenario bounds (see assumptions.json)",
        "blue_direct_NH3_power": {"CI_kgCO2e_per_MWh_p5_p50_p95": list(np.percentile(
            [carbon_intensity(pw_direct, lca.blue_nh3_ef(cap[i], 0, lk[i]), dist[i])["total"] / es[i] for i in range(0, N, 10)], [5, 50, 95])),
            "P_cuts_emissions_vs_NG_CCGT": float((marg > 0).mean())},
        "blue_industrial_H2": {"CI_kgCO2e_per_kgH2_p5_p50_p95": list(np.percentile(h2_blue, [5, 50, 95])),
                               "P_below_SMR_unabated": float((h2_blue < smr_u_s).mean()),
                               "P_below_SMR_CCS": float((h2_blue < smr_c_s).mean())},
    }

    result = {"provenance": prov("python+literature", "route factors lca.FACTORS; cracker activities from stored Aspen baseline; comparators literature"),
              "method": "Scenario-based cradle-to-gate-of-use GHG assessment; GWP100 AR6; NOx reported separately, never added to CO2e",
              "system_boundary": "upstream NH3 (well-to-plant-gate) + sea shipping + optional boil-off (default 0, unsourced) + process electricity + direct N2O; excludes plant construction, catalyst, H2 compression/delivery, NG supply chain of the comparators except via a leakage parameter",
              "distance_km_baseline": D0, "functional_units": {"hydrogen": "1 kg H2 at the PSA outlet (99.96 mol%) at the cracker", "electricity": "1 MWh net electricity"},
              "activity_per_FU": {"H2": {"nh3_kg": h2.nh3_kg, "efficiency_LHV": h2.efficiency}, "direct_NH3_CCGT": {"nh3_kg": pw_direct.nh3_kg, "efficiency_LHV": pw_direct.efficiency}},
              "routes": routes, "alternatives": alts, "breakeven": be, "blue_ef_reproduction": be_blue,
              "distance_scenarios": dist_rows, "sensitivity_oat_blue_direct_power": {"base_margin_kgCO2e_per_MWh(CCGT minus NH3)": base_margin, "rows": oat},
              "monte_carlo": mc,
              "n2o_nox": {**lca.n2o_noX_per_MWh(), "note": "SIMULATED exhaust ppmv (Ahmad 2025, VNH3), converted with Ahmad's gas flow per MWh; NO is a local pollutant reported separately; N2O is included in CO2e (it is ~0.2 kg CO2e/MWh, negligible)"},
              "carbon_tax_sg": {"rate_SGD_per_t": lca.f("carbon_tax_sg_2026"), "direct_in_scope_kgCO2e_per_MWh_direct_NH3": pw_direct.n2o_kgCO2e,
                                "SGD_per_MWh": pw_direct.n2o_kgCO2e / 1000.0 * lca.f("carbon_tax_sg_2026"),
                                "note": "Only direct in-scope emissions (N2O at the turbine); CO2e upstream and shipping are outside Singapore's tax base. Reported in SGD here; results/research/enduse converts it with the FX in data/singapore.yaml (secondary_web)."},
              "limitations": ["Coal-based NH3 factor is low confidence (abstract-level).", "Blue-NH3 leakage and capture are scenario parameters, not measured values.",
                              "Boil-off and terminal losses excluded (no sourced value).", "Green NH3 central value includes embedded renewable-asset emissions from the IEA range; Lee's boundary gives zero.",
                              "Distances are scenario values, not sourced route lengths.", "NOx and N2O are simulated values from one paper."]}
    dump(OUT / "lca_results.json", result)
    write_csv(OUT / "lca_routes.csv", [{k: v for k, v in r.items() if not isinstance(v, (dict, list))} for r in routes])
    write_csv(OUT / "lca_breakeven.csv", be)
    write_csv(OUT / "lca_distance.csv", dist_rows)
    write_csv(OUT / "lca_sensitivity_oat.csv", oat)

    # ---- assumptions register ------------------------------------------------------------------------
    reg = [{"name": k, "value": v["value"], "unit": v["unit"], "source_type": v["source_type"], "source": v["source"],
            "access_date": lca.ACCESS if "http" in v["source"] or "extract" in v["source"] or "accessed" in v["source"] else "n/a (paper or standard)",
            "applicability_note": v["note"]} for k, v in lca.FACTORS.items()]
    reg += [{"name": "eta_direct_ahmad", "value": P.ETA_DIRECT_AHMAD, "unit": "-", "source_type": "literature", "source": "Ahmad 2025 Table 6 Case 2a (LHV 18.8 MJ/kg basis)", "access_date": "n/a", "applicability_note": "Literature-calibrated scenario input, not an Aspen result."},
            {"name": "eta_full_crack_ahmad", "value": P.ETA_FULL_CRACK_AHMAD, "unit": "-", "source_type": "literature", "source": "Ahmad 2025 p. 15 (alpha = 0, about 54 %)", "access_date": "n/a", "applicability_note": "Exhaust-heated cracker, PR 8; value read from text, approximate."},
            {"name": "eta_gt_gas", "value": P.ETA_GT_GAS, "unit": "-", "source_type": "assumption", "source": "electricity per kg NH3 of Ahmad Case 2a re-expressed on the AmCraX LHV basis (18.6 MJ/kg)", "access_date": "n/a", "applicability_note": "Applied to every gaseous fuel in the fired and purified variants."}]
    dump(OUT / "assumptions.json", reg)

    # ---- validation ----------------------------------------------------------------------------------
    cr = load_cracker("baseline")
    items = []

    def add(id_, desc, method, ref, obs, exp, tol, unit, status, files):
        items.append({"id": id_, "description": desc, "method": method, "reference_source": ref, "observed": obs, "expected": exp,
                      "tolerance": tol, "unit": unit, "status": status, "source_files": files})
    sf = ["backend/amcrax/environmental/lca.py", "results/research/lca/lca_results.json"]
    for nm, got, exp in (("v1", lca.blue_nh3_ef(1, 0), 1.16), ("v2", lca.blue_nh3_ef(1, 1), 0.77)):
        add(f"LCA-blue-{nm}", f"Blue NH3 function reproduces Lee et al. version {nm[1]}", "blue_nh3_ef with the published capture streams", "Lee 2022 p. 13",
            got, exp, 1e-9, "kg CO2e/kg NH3", "pass" if abs(got - exp) < 1e-9 else "fail", sf)
    env_res = pw.load_result("baseline")
    for route, key in (("grey", "grey"), ("blue", "blue"), ("green", "green_lee")):
        old = old_ci(env_res, f"{route}/self_firing").total_kgCO2e_per_kgH2
        new = carbon_intensity(h2, lca.route_spec(key).ef if route != "green" else 0.0, D0)["total"]
        add(f"LCA-baseline-{route}", f"Existing baseline carbon intensity ({route}, self-firing) reproduced by the new LCA with old settings",
            "new enduse.carbon_intensity (NH3 factor, 5000 km, GLEC factor, grid 0.402, no N2O) vs amcrax.environmental.carbon_intensity; stored baseline.json",
            "results/simulations/environmental_baseline.json logic", new, old, 1e-6, "kg CO2e/kg H2", "pass" if abs(new - old) < 1e-6 * max(1, old) else "fail",
            ["backend/amcrax/environmental/__init__.py", "results/simulations/baseline.json"])
    # sum of parts
    b = routes[2]["H2_breakdown"]
    ssum = b["upstream_ammonia"] + b["shipping"] + b["electricity"] + b["direct_n2o"]
    add("LCA-sum", "Breakdown components sum to the total", "arithmetic", "internal", ssum, b["total"], 1e-9, "kg CO2e/kg H2", "pass" if abs(ssum - b["total"]) < 1e-9 else "fail", sf)
    add("LCA-nh3-per-h2", "NH3 per kg H2 (feed + heat NH3) consistent with stored Aspen feed/product",
        "nh3_feed/h2 x (1 + heat deficit/LHV NH3)", "results/simulations/baseline.json", h2.nh3_kg,
        cr.nh3_kg_h / cr.h2_product_kg_h * (1 + cr.deficit_MJ_per_kg_nh3 / P.LHV_NH3_MJ_KG), 1e-9, "kg NH3/kg H2", "pass", ["results/simulations/baseline.json"])
    add("LCA-ccgt-vs-grid", "Computed NG CCGT intensity (eff 0.55) versus the EMA grid average 2024", "IPCC factor / assumed efficiency vs EMA GEF",
        "EMA Singapore Energy Statistics 2024", ccgt, grid_mwh, None, "kg CO2/MWh", "informational", sf)
    for rl in reference_lines():
        add(f"LCA-ref-{rl.label[:8].strip().replace(' ', '_')}", f"Industrial H2 from blue NH3 (Lee v1, 5000 km) against yardstick: {rl.label}", "comparison", rl.source,
            routes[2]["H2_kgCO2e_per_kg"], rl.value_kgCO2e_per_kgH2, None, "kg CO2e/kg H2", "informational", sf)
    add("LCA-smr", "Cracked blue-NH3 H2 against SMR with CCS (3.5) and unabated SMR (11)", "comparison", "IEA GHR 2024; Frontiers 2024 (low confidence)",
        routes[2]["H2_kgCO2e_per_kg"], [smr_c, smr_u], None, "kg CO2e/kg H2", "informational", sf)
    dump(VAL / "lca.json", items)

    # ---- figures -------------------------------------------------------------------------------------
    names = ["green", "blue", "blue_v2", "blue_param", "grey", "coal"]
    sel = [r for r in routes if r["route"] in names]
    parts = (("upstream_ammonia", "upstream NH3", C_NH3), ("shipping", "shipping", C_N2), ("electricity", "pump electricity", C_AMBER))
    fig, ax = plt.subplots(figsize=(7.4, 4.3))
    x = np.arange(len(sel))
    bot = np.zeros(len(sel))
    for key, lab, col in parts:
        v = np.array([r["H2_breakdown"][key] for r in sel])
        ax.bar(x, v, 0.6, bottom=bot, label=lab, color=col)
        bot += v
    for i, r in enumerate(sel):
        lo, hi = r["H2_low_high"]
        ax.plot([i, i], [lo, hi], color="k", lw=1)
        ax.text(i, hi + 0.3, f"{r['H2_kgCO2e_per_kg']:.1f}", ha="center", fontsize=7.5)
    ax.axhline(smr_u, color=C_HEAT, ls="--", lw=1)
    ax.text(len(sel) - 0.5, smr_u + 0.3, "SMR unabated (IEA 10-12)", ha="right", fontsize=7, color=C_HEAT)
    ax.axhline(smr_c, color=C_PRIMARY, ls="--", lw=1)
    ax.text(len(sel) - 0.5, smr_c + 0.3, "SMR + CCS (3.4-3.6, low confidence)", ha="right", fontsize=7, color=C_PRIMARY)
    ax.set_xticks(x, [r["route"].replace("_", " ") for r in sel])
    ax.set_ylabel("kg CO$_2$e / kg H$_2$ (cracker outlet, 99.96 mol%)")
    ax.set_title("Imported-ammonia hydrogen: GHG intensity by ammonia route (5000 km; bars = sourced range)")
    ax.legend(loc="upper left")
    foot(fig)
    fig.savefig(FIG / "lca_h2_by_route.png", dpi=300, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.4, 4.3))
    bot = np.zeros(len(sel))
    for key, lab, col in (("upstream_ammonia", "upstream NH3", C_NH3), ("shipping", "shipping", C_N2), ("direct_n2o", "N2O", C_HEAT)):
        v = np.array([r["MWh_breakdown"][key] for r in sel])
        ax.bar(x, v, 0.6, bottom=bot, label=lab, color=col)
        bot += v
    ax.axhline(ccgt, color=C_PRIMARY, ls="--", lw=1)
    ax.text(len(sel) - 0.5, ccgt + 15, f"NG CCGT {ccgt:.0f} (eff 0.55, assumption)", ha="right", fontsize=7, color=C_PRIMARY)
    ax.axhline(grid_mwh, color=C_GREY, ls="--", lw=1)
    ax.text(len(sel) - 0.5, grid_mwh + 15, f"grid average 2024 {grid_mwh:.0f} (EMA)", ha="right", fontsize=7, color=C_GREY)
    for i, r in enumerate(sel):
        ax.text(i, r["direct_NH3_CCGT_kgCO2e_per_MWh"] + 15, f"{r['direct_NH3_CCGT_kgCO2e_per_MWh']:.0f}", ha="center", fontsize=7.5)
    ax.set_xticks(x, [r["route"].replace("_", " ") for r in sel])
    ax.set_ylabel("kg CO$_2$e / MWh")
    ax.set_title("Direct NH3 combined cycle: GHG intensity by ammonia route (5000 km)")
    ax.legend(loc="upper left")
    foot(fig)
    fig.savefig(FIG / "lca_power_by_route.png", dpi=300, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    oo = sorted(oat, key=lambda o: abs(o["margin_at_high"] - o["margin_at_low"]))
    for i, o in enumerate(oo):
        ax.barh(i, o["margin_at_high"] - base_margin, left=base_margin, color=C_PRIMARY, alpha=0.8)
        ax.barh(i, o["margin_at_low"] - base_margin, left=base_margin, color=C_HEAT, alpha=0.8)
    ax.axvline(base_margin, color="k", lw=1)
    ax.axvline(0, color=C_GREY, ls="--", lw=1)
    ax.set_yticks(range(len(oo)), [o["parameter"] for o in oo], fontsize=7.5)
    ax.set_xlabel("NG CCGT minus blue-NH3 direct power, kg CO$_2$e / MWh (positive = ammonia cuts emissions)")
    ax.set_title("One-at-a-time sensitivity, blue NH3 (95 % capture, 1.5 % leakage) at base")
    foot(fig)
    fig.savefig(FIG / "lca_sensitivity_blue_power.png", dpi=300, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)

    efs = np.linspace(0, 3, 61)
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    ax.plot(efs, [carbon_intensity(pw_direct, e, D0)["total"] for e in efs], color=C_NH3, label="direct NH3 CCGT")
    ax.plot(efs, [carbon_intensity(pw_pur, e, D0)["total"] for e in efs], color=C_H2, label="cracked + PSA H$_2$ CCGT (fired)")
    ax.axhline(ccgt, color=C_PRIMARY, ls="--", label="NG CCGT (0.55)")
    ax.axhline(grid_mwh, color=C_GREY, ls="--", label="grid average 2024")
    for nm, v in (("green", lca.route_spec("green").ef), ("blue v1", be_blue["blue_v1"]), ("grey", lca.route_spec("grey").ef)):
        ax.axvline(v, color=C_AMBER, lw=0.8, alpha=0.7)
        ax.text(v, ax.get_ylim()[1] * 0.97, nm, rotation=90, fontsize=7, va="top", ha="right")
    ax.set_xlabel("ammonia carbon intensity at producer gate, kg CO$_2$e / kg NH$_3$")
    ax.set_ylabel("kg CO$_2$e / MWh")
    ax.set_title("Break-even ammonia carbon intensity for power (5000 km)")
    ax.legend(loc="upper left")
    foot(fig)
    fig.savefig(FIG / "lca_breakeven_power.png", dpi=300, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    print("lca done", {r["route"]: round(r["H2_kgCO2e_per_kg"], 2) for r in routes}, round(ccgt, 1))
    print({b_["comparison"] + "@" + str(b_["distance_km"]): round(b_["breakeven_NH3_gate_EF_kgCO2e_per_kgNH3"], 3) for b_ in be if b_["distance_km"] == D0})
    print(mc)


if __name__ == "__main__":
    main()
