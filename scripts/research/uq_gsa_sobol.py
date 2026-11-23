"""Task U1 / T1: Sobol global sensitivity analysis of amcrax.economics.singapore.evaluate (unified reference scenario).

Deterministic (seed 20261123); run from the project root:  python scripts/research/uq_gsa_sobol.py
Writes results/research/uq/gsa_sobol.json/.csv, gsa_cost_decomposition.json/.csv, checks_t1.json and
results/figures/research/uq_gsa_sobol.png.
Estimators: Saltelli et al. (2010) first order, Jansen (1999) total effect; grouped indices swap all columns of a group.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.optimize import brentq
from scipy.stats import lognorm, triang

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from amcrax.economics.lcoh import EconomicAssumptions  # noqa: E402
from amcrax.economics.reference import load_reference_scenario, provenance_stamp  # noqa: E402
from amcrax.economics.singapore import evaluate, extract_summary, load_singapore_data  # noqa: E402
from amcrax.uq import LABEL, SEED  # noqa: E402
from amcrax.uq.sobol import (ab_matrix, bootstrap_ci, indices_from_outputs, ishigami, ishigami_analytic,  # noqa: E402
                             sobol_base)

OUT = ROOT / "results" / "research" / "uq"
FIG = ROOT / "results" / "figures" / "research"
SCRIPT = "scripts/research/uq_gsa_sobol.py"
REF = load_reference_scenario()
SD = load_singapore_data()
N = 2 ** 13
N_BOOT = 1000
OUTPUTS = ("lcoh_USD_per_kg", "rec_USD_per_kg", "npv_USD")
SCEN = ("grey", "blue", "green_current", "green_2030")
TORN = json.loads((ROOT / "results/research/singapore/tornado.json").read_text(encoding="utf-8"))
TB = {b["parameter"]: b for b in TORN["bars"]}


def tb_range(key):
    b = TB[key]
    return tuple(sorted((float(b["low_input"]), float(b["high_input"]))))


CAT_PRICE = EconomicAssumptions().resolved_catalyst_price_USD_per_kg()
CAPX_LO, CAPX_HI = tb_range("capex_multiplier")
LIFE_LO, LIFE_HI = tb_range("catalyst_lifetime_yr")
PSA_LO, PSA_HI = tb_range("psa_recovery")
CT_LO, CT_HI = tb_range("carbon_tax_SGD_per_t")
INPUTS = ["nh3_price_USD_per_t", "electricity_price_USD_per_kWh", "capex_multiplier", "capex_scaling_exponent",
          "catalyst_price_USD_per_kg", "catalyst_lifetime_yr", "discount_rate", "operating_hours_h_per_yr", "plant_life_yr",
          "psa_recovery"]
GROUPS = {"feed": ["nh3_price_USD_per_t"],
          "capital": ["capex_multiplier", "capex_scaling_exponent", "discount_rate", "plant_life_yr"],
          "operation": ["operating_hours_h_per_yr", "electricity_price_USD_per_kWh", "psa_recovery"],
          "catalyst": ["catalyst_price_USD_per_kg", "catalyst_lifetime_yr"]}


def tri_ppf(u, lo, mode, hi):
    return triang.ppf(u, (mode - lo) / (hi - lo), loc=lo, scale=hi - lo)


def lognormal_sigma():
    """sigma of a median-1 lognormal with the same 5-95 % width as triangular(0.5, 1, 1.5)."""
    w = tri_ppf(0.95, CAPX_LO, 1.0, CAPX_HI) - tri_ppf(0.05, CAPX_LO, 1.0, CAPX_HI)
    return brentq(lambda s: math.exp(1.6448536269514722 * s) - math.exp(-1.6448536269514722 * s) - w, 1e-6, 3.0), w


SIG_LN, W_TRI = lognormal_sigma()


def dists(scen, capex_shape="triangular", dummy=False):
    d = SD["nh3_price_scenarios_USD_per_t"][scen]
    lo, md, hi = float(d["low"]), float(REF.nh3_prices_USD_per_t[scen]), float(d["high"])
    e, x, dr, oh, pl = (REF.sens(k) for k in ("electricity_USD_per_kWh", "capex_scaling_exponent", "discount_rate",
                                              "operating_hours_h_per_yr", "plant_life_yr"))
    capx = ((lambda u: tri_ppf(u, CAPX_LO, 1.0, CAPX_HI)), f"triangular({CAPX_LO:g}, 1, {CAPX_HI:g}) Cho 2026 Table 8")
    if capex_shape == "lognormal":
        capx = ((lambda u: lognorm.ppf(u, SIG_LN, scale=1.0)),
                f"lognormal(median 1, sigma {SIG_LN:.4f}; same 5-95 % width {W_TRI:.4f} as the triangular) "
                "assumption: right-skewed CAPEX, shape after Stewart and Shirvan 2023, no chemical-plant data")
    D = [((lambda u: tri_ppf(u, lo, md, hi)), f"triangular({lo:g}, {md:g}, {hi:g}) data/singapore.yaml range, reference-scenario base"),
         ((lambda u: e[0] + u * (e[1] - e[0])), f"uniform({e[0]:g}, {e[1]:g}) REF.sens electricity_USD_per_kWh"),
         capx,
         ((lambda u: x[0] + u * (x[1] - x[0])), f"uniform({x[0]:g}, {x[1]:g}) REF.sens capex_scaling_exponent"),
         ((lambda u: tri_ppf(u, 0.5 * CAT_PRICE, CAT_PRICE, 2 * CAT_PRICE)), f"triangular(0.5x, 1x, 2x of {CAT_PRICE:g}) Cho 2026 Table 8"),
         ((lambda u: LIFE_LO + u * (LIFE_HI - LIFE_LO)), f"uniform({LIFE_LO:g}, {LIFE_HI:g}) Cho 2026 Table 8"),
         ((lambda u: dr[0] + u * (dr[1] - dr[0])), f"uniform({dr[0]:g}, {dr[1]:g}) REF.sens discount_rate"),
         ((lambda u: oh[0] + u * (oh[1] - oh[0])), f"uniform({oh[0]:g}, {oh[1]:g}) REF.sens operating_hours_h_per_yr"),
         ((lambda u: pl[0] + u * (pl[1] - pl[0])), f"uniform({pl[0]:g}, {pl[1]:g}) REF.sens plant_life_yr (NPV: int(round) step)"),
         ((lambda u: PSA_LO + u * (PSA_HI - PSA_LO)), f"uniform({PSA_LO:g}, {PSA_HI:g}) Cho 2026 0.756; AmCraX tornado bound 0.95")]
    names = list(INPUTS)
    if dummy:
        D.append(((lambda u: CT_LO + u * (CT_HI - CT_LO)), f"uniform({CT_LO:g}, {CT_HI:g}) tornado range (dummy: ammonia heat, no direct CO2)"))
        names.append("carbon_tax_SGD_per_t")
    return D, names


def to_x(U, D):
    return np.column_stack([D[i][0](np.clip(U[:, i], 1e-12, 1 - 1e-12)) for i in range(len(D))])


def model(X, names, S):
    out = np.empty((X.shape[0], len(OUTPUTS)))
    for r in range(X.shape[0]):
        ov = {k: float(v) for k, v in zip(names, X[r]) if k != "nh3_price_USD_per_t"}
        e = evaluate(S, float(X[r, 0]), ov)
        out[r] = [e[k] for k in OUTPUTS]
    return out


def analyse(S, scen, capex_shape="triangular", dummy=False):
    D, names = dists(scen, capex_shape, dummy)
    d = len(D)
    A, B = sobol_base(N, d, SEED)
    sets = [[i] for i in range(d)] + [[names.index(k) for k in g] for g in GROUPS.values()]
    set_names = names + [f"group:{g}" for g in GROUPS]
    fA, fB = model(to_x(A, D), names, S), model(to_x(B, D), names, S)
    fAB = np.stack([model(to_x(ab_matrix(A, B, s), D), names, S) for s in sets])
    res = {"distributions": {n: D[i][1] for i, n in enumerate(names)}, "N": N, "seed": SEED, "d": d,
           "n_evaluations": N * (d + 2 + len(GROUPS)), "outputs": {}}
    for j, o in enumerate(OUTPUTS):
        Sx, STx, V = indices_from_outputs(fA[:, j], fB[:, j], fAB[:, :, j])
        ciS, ciT = bootstrap_ci(fA[:, j], fB[:, j], fAB[:, :, j], N_BOOT, SEED)
        conv = {}
        for m in (11, 12, 13):
            n = 2 ** m
            s_, t_, _ = indices_from_outputs(fA[:n, j], fB[:n, j], fAB[:, :n, j])
            conv[f"N={n}"] = {"S1": dict(zip(set_names[:d], s_[:d].tolist())), "ST": dict(zip(set_names[:d], t_[:d].tolist()))}
        res["outputs"][o] = {
            "V": V, "mean": float(np.concatenate([fA[:, j], fB[:, j]]).mean()),
            "sd": float(np.concatenate([fA[:, j], fB[:, j]]).std(ddof=1)),
            "p5": float(np.percentile(np.concatenate([fA[:, j], fB[:, j]]), 5)),
            "p95": float(np.percentile(np.concatenate([fA[:, j], fB[:, j]]), 95)),
            "indices": {n: {"S1": float(Sx[i]), "S1_ci": ciS[i].tolist(), "ST": float(STx[i]), "ST_ci": ciT[i].tolist()}
                        for i, n in enumerate(set_names[:d])},
            "groups": {set_names[d + g]: {"S1": float(Sx[d + g]), "S1_ci": ciS[d + g].tolist(), "ST": float(STx[d + g]),
                                          "ST_ci": ciT[d + g].tolist(), "members": list(GROUPS[set_names[d + g][6:]])}
                       for g in range(len(GROUPS))},
            "convergence": conv}
    # mean with the two inputs that the Monte Carlo of results/research/singapore does not vary held at their base
    if o and not dummy and capex_shape == "triangular":
        X = to_x(A, D)
        keep = [i for i, n in enumerate(names) if n not in ("psa_recovery", "capex_scaling_exponent")]
        vals = []
        for r in range(N):
            ov = {names[i]: float(X[r, i]) for i in keep if names[i] != "nh3_price_USD_per_t"}
            vals.append(evaluate(S, float(X[r, 0]), ov)["lcoh_USD_per_kg"])
        res["lcoh_mean_mc_comparable"] = float(np.mean(vals))
    return res


def ranking(ix, key="ST"):
    return [k for k, _ in sorted(ix.items(), key=lambda kv: -kv[1][key])]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    S = {"heat_integration_on": extract_summary(json.loads((ROOT / "results/simulations/baseline.json").read_text(encoding="utf-8"))),
         "heat_integration_off": extract_summary(json.loads((ROOT / "results/simulations/baseline_no_hi.json").read_text(encoding="utf-8")))}
    checks = []
    # ---------------- estimator checks
    A, B = sobol_base(N, 3, SEED)
    to = lambda U: -math.pi + 2 * math.pi * U  # noqa: E731
    fA, fB = ishigami(to(A)), ishigami(to(B))
    fAB = np.stack([ishigami(to(ab_matrix(A, B, [i]))) for i in range(3)])
    s_, t_, _ = indices_from_outputs(fA, fB, fAB)
    an = ishigami_analytic()
    err = max(max(abs(a - b) for a, b in zip(s_, an["S"])), max(abs(a - b) for a, b in zip(t_, an["ST"])))
    checks.append({"id": "T1-ISHIGAMI", "evidence_kind": "numerical_verification",
                   "description": "Ishigami (a=7, b=0.1) indices at N=2^13 against the analytic values within 0.02 absolute",
                   "estimated": {"S1": s_.tolist(), "ST": t_.tolist()}, "analytic": an, "max_abs_error": float(err), "tolerance": 0.02,
                   "analytic_source": "closed-form variances as given in OpenTURNS use-case documentation (Ishigami function) and "
                                      "Marrel et al. (2009), Reliab. Eng. Syst. Saf. 94, 742-751 (S1 = 0.3139, 0.4424, 0); checked 23 Nov 2026",
                   "status": "pass" if err <= 0.02 else "fail"})
    c = np.array([1.0, 2.0, 3.0, 4.0])
    A, B = sobol_base(N, 4, SEED)
    lin = lambda X: X @ c  # noqa: E731
    fAB = np.stack([lin(ab_matrix(A, B, [i])) for i in range(4)])
    s_, t_, _ = indices_from_outputs(lin(A), lin(B), fAB)
    an = c ** 2 / np.sum(c ** 2)
    err = float(max(np.max(np.abs(s_ - an)), np.max(np.abs(t_ - an))))
    checks.append({"id": "T1-LINEAR", "evidence_kind": "numerical_verification",
                   "description": "linear additive f = sum c_i x_i, x_i ~ U(0,1), c = 1..4: S_i = ST_i = c_i^2/sum c^2 within 0.01",
                   "estimated": {"S1": s_.tolist(), "ST": t_.tolist()}, "analytic": an.tolist(), "max_abs_error": err, "tolerance": 0.01,
                   "status": "pass" if err <= 0.01 else "fail"})
    # ---------------- real model
    cases = {}
    for hi, s in S.items():
        for sc in SCEN:
            cases[f"{sc}|{hi}"] = analyse(s, sc)
            cases[f"{sc}|{hi}|capex_lognormal"] = analyse(s, sc, "lognormal")
            print("done", sc, hi, flush=True)
    dummy = analyse(S["heat_integration_on"], "grey", dummy=True)
    mc = json.loads((ROOT / "results/research/singapore/monte_carlo.json").read_text(encoding="utf-8"))
    same_ref = mc.get("provenance", {}).get("reference_scenario", {}).get("sha256") == provenance_stamp()["sha256"]
    for key, cs in cases.items():
        if key.endswith("capex_lognormal"):
            continue
        for o in OUTPUTS:
            ix = cs["outputs"][o]["indices"]
            ssum = sum(v["S1"] for v in ix.values())
            okT = all(v["ST"] >= v["S1"] - 0.02 for v in ix.values())
            checks.append({"id": f"T1-SUM-{key}-{o}", "evidence_kind": "numerical_verification", "description": "sum S_i <= 1.05 and ST_i >= S_i - 0.02",
                           "sum_S1": ssum, "status": "pass" if ssum <= 1.05 and okT else "fail"})
            c11, c12, c13 = (cs["outputs"][o]["convergence"][f"N={2**m}"]["ST"] for m in (11, 12, 13))
            r12 = sorted(c12, key=lambda k: -c12[k])[:3]
            r13 = sorted(c13, key=lambda k: -c13[k])[:3]
            checks.append({"id": f"T1-CONV-{key}-{o}", "evidence_kind": "numerical_verification",
                           "description": "top-3 ranking by ST identical at N = 2^12 and 2^13", "top3_N4096": r12, "top3_N8192": r13,
                           "status": "pass" if r12 == r13 else "fail"})
    for o in OUTPUTS:
        v = dummy["outputs"][o]["indices"]["carbon_tax_SGD_per_t"]
        checks.append({"id": f"T1-DUMMY-{o}", "evidence_kind": "numerical_verification",
                       "description": "carbon tax (ignored by evaluate for ammonia-fired heat) as a dummy input: |S|, |ST| < 0.01",
                       "S1": v["S1"], "ST": v["ST"], "status": "pass" if abs(v["S1"]) < 0.01 and abs(v["ST"]) < 0.01 else "fail"})
    for sc in SCEN:
        m_sob = cases[f"{sc}|heat_integration_on"]["lcoh_mean_mc_comparable"]
        m_mc = mc["results"][sc]["lcoh_mean"]
        rel = abs(m_sob / m_mc - 1)
        checks.append({"id": f"T1-MCMEAN-{sc}", "evidence_kind": "numerical_verification",
                       "description": "mean LCOH (Sobol base sample, PSA recovery and CAPEX exponent at base as in the Monte Carlo) within 1 % of monte_carlo.json lcoh_mean",
                       "sobol_mean": m_sob, "monte_carlo_mean": m_mc, "rel_diff": rel, "same_reference_scenario": same_ref,
                       "status": ("pass" if rel <= 0.01 else "fail") if same_ref else "informational"})
    # ranking change under the lognormal CAPEX
    rank_change = {}
    for hi in S:
        for sc in SCEN:
            a = ranking(cases[f"{sc}|{hi}"]["outputs"]["lcoh_USD_per_kg"]["indices"])
            b = ranking(cases[f"{sc}|{hi}|capex_lognormal"]["outputs"]["lcoh_USD_per_kg"]["indices"])
            rank_change[f"{sc}|{hi}"] = {"triangular_rank_ST": a, "lognormal_rank_ST": b, "top3_changed": a[:3] != b[:3]}
    tornado = {b["parameter"]: {"swing_USD_per_kg": b["swing"], "low_input": b["low_input"], "high_input": b["high_input"]} for b in TORN["bars"]}
    prov = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "script": SCRIPT, "source_type": "python",
            "inputs_summary": "amcrax.economics.singapore.evaluate (default capex_mode reference) on results/simulations/baseline.json and baseline_no_hi.json; "
                              "ranges from the reference scenario (REF.sens), data/singapore.yaml NH3 ranges, and results/research/singapore/tornado.json bounds",
            "reference_scenario": provenance_stamp()}
    doc = {"provenance": prov, "evidence_kind": "numerical_verification", "analysis_kind": "global_sensitivity", "label": LABEL,
           "method": "Saltelli et al. (2010) first order, Jansen (1999) total effect; scrambled Sobol base sample (scipy.stats.qmc, seed 20261123), "
                     "N = 8192, bootstrap 95 % CI with 1000 row resamples; grouped indices swap all columns of a group",
           "notes": ["Carbon tax omitted from the inputs: ammonia-fired heat has no direct CO2 so evaluate ignores it (index exactly 0); "
                     "tested as a dummy input (checks T1-DUMMY-*). No natural-gas heat case exists in the reference scenario.",
                     "plant_life_yr enters NPV through int(round(...)) only: its NPV index reflects a step function.",
                     "Heat integration and capacity are design choices, reported as separate cases (capacity scale 1).",
                     "NH3 price drives both the feed and the ammonia-fuelled heat; it is one input, so the feed group includes heat-fuel cost.",
                     "NH3 low/high from data/singapore.yaml nh3_price_scenarios_USD_per_t (the reference scenario holds the base values only); same as monte_carlo.json."],
           "groups": GROUPS, "inputs": INPUTS, "cases": cases, "dummy_run_grey_HIon": dummy,
           "capex_lognormal_ranking_change": rank_change, "tornado_swing_grey_HIon": tornado}
    (OUT / "gsa_sobol.json").write_text(json.dumps(doc, indent=1, default=float), encoding="utf-8")
    with open(OUT / "gsa_sobol.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["case", "output", "input_or_group", "S1", "S1_lo", "S1_hi", "ST", "ST_lo", "ST_hi", "tornado_swing_USD_per_kg"])
        for key, cs in cases.items():
            for o in OUTPUTS:
                for n, v in {**cs["outputs"][o]["indices"], **cs["outputs"][o]["groups"]}.items():
                    w.writerow([key, o, n, v["S1"], *v["S1_ci"], v["ST"], *v["ST_ci"], tornado.get(n, {}).get("swing_USD_per_kg", "")])
    # ---------------- deterministic cost decomposition (accounting, not sensitivity)
    cfr = REF.raw["capex"]
    osbl = cfr["osbl_frac_isbl"]["value"]
    engc = cfr["engineering_frac_isbl_osbl"]["value"] + cfr["contingency_frac_isbl_osbl"]["value"]
    dec, rows = {}, []
    for hi, s in S.items():
        for sc in SCEN:
            e = evaluate(s, sc)
            cap = e["capex"]
            isbl = cap["isbl_USD"]
            it = sum(isbl.values())
            block = {"OSBL": it * osbl, "engineering_and_contingency": it * (1 + osbl) * engc}
            dec[f"{sc}|{hi}"] = {"lcoh_USD_per_kg": e["lcoh_USD_per_kg"], "lcoh_SGD_per_kg": e["lcoh_SGD_per_kg"],
                                 "breakdown_USD_per_kg": e["breakdown_USD_per_kg"], "breakdown_SGD_per_kg": e["breakdown_SGD_per_kg"],
                                 "breakdown_share": {k: v / e["lcoh_USD_per_kg"] for k, v in e["breakdown_USD_per_kg"].items()},
                                 "capex_isbl_by_item_USD": isbl, "capex_indirect_block_USD": block,
                                 "capex_total_USD": cap["total_capex_USD"], "capex_total_SGD": e["capex_total_SGD"],
                                 "indirect_share_of_tci": sum(block.values()) / cap["total_capex_USD"]}
            for k, v in e["breakdown_USD_per_kg"].items():
                rows.append([sc, hi, "lcoh_breakdown", k, v, v * REF.fx_SGD_per_USD, v / e["lcoh_USD_per_kg"]])
            for k, v in {**isbl, **block}.items():
                rows.append([sc, hi, "capex", k, v, v * REF.fx_SGD_per_USD, v / cap["total_capex_USD"]])
    (OUT / "gsa_cost_decomposition.json").write_text(json.dumps({"provenance": prov, "evidence_kind": "numerical_verification",
        "analysis_kind": "cost_accounting", "label": "Deterministic cost accounting at the base point (not a sensitivity analysis). " + LABEL,
        "fractions": {"osbl_frac_isbl": osbl, "engineering_plus_contingency_frac_isbl_osbl": engc}, "fx_SGD_per_USD": REF.fx_SGD_per_USD,
        "cases": dec}, indent=1, default=float), encoding="utf-8")
    with open(OUT / "gsa_cost_decomposition.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["scenario", "heat_integration", "kind", "item", "USD", "SGD", "share"])
        w.writerows(rows)
    (OUT / "checks_t1.json").write_text(json.dumps(checks, indent=1, default=float), encoding="utf-8")
    # ---------------- figure (grey, HI on)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ix = cases["grey|heat_integration_on"]["outputs"]["lcoh_USD_per_kg"]
    allx = {**ix["indices"], **ix["groups"]}
    order = sorted(allx, key=lambda k: allx[k]["ST"])
    fig, ax = plt.subplots(figsize=(8, 5.5))
    y = np.arange(len(order))
    for off, key, col in ((-0.2, "S1", "#2a6f97"), (0.2, "ST", "#e07a5f")):
        v = np.array([allx[k][key] for k in order])
        ci = np.array([allx[k][key + "_ci"] for k in order])
        ax.barh(y + off, v, height=0.38, color=col, label=key, xerr=np.abs(np.vstack([v - ci[:, 0], ci[:, 1] - v])), capsize=2)
    ax.set_yticks(y)
    ax.set_yticklabels(order, fontsize=7)
    ax.set_xlabel("Sobol index of LCOH (95 % bootstrap CI)")
    ax.set_title("Global sensitivity of LCOH, grey scenario, heat integration on (N = 8192)", fontsize=9)
    ax.legend(fontsize=8)
    fig.text(0.01, 0.005, "Source: python (amcrax.economics.singapore, reference scenario) on the stored Aspen Plus V15 baseline;\n"
             "uncertainty of a model given its stated input ranges, not experimental validation. S1 CIs are wide (estimator variance), ST CIs narrow.",
             fontsize=6, color="#555")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(FIG / "uq_gsa_sobol.png", dpi=150)
    plt.close(fig)
    print(json.dumps([c for c in checks if c["status"] == "fail"], indent=1, default=float)[:3000])


if __name__ == "__main__":
    main()

