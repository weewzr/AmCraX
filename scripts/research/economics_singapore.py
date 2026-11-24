"""Workstream E: Singapore techno-economics. Deterministic; run from the project root:
    python scripts/research/economics_singapore.py
Writes results/research/singapore/*, results/figures/research/singapore_*.png,
results/research/validation/economics.json, research/reference_additions/economics.json.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from amcrax.economics import compute_lcoh  # noqa: E402
from amcrax.economics.singapore import (SCENARIOS, breakeven_nh3_price, default_electricity_USD_per_kWh, evaluate,  # noqa: E402
                                        extract_summary, load_singapore_data)
from amcrax.economics.reference import load_reference_scenario, provenance_stamp  # noqa: E402
from amcrax.schemas import SimulationResult  # noqa: E402

OUT = ROOT / "results" / "research" / "singapore"
FIG = ROOT / "results" / "figures" / "research"
VAL = ROOT / "results" / "research" / "validation"
for d in (OUT, FIG, VAL):
    d.mkdir(parents=True, exist_ok=True)

SCRIPT = "scripts/research/economics_singapore.py"
SD = load_singapore_data()
REF = load_reference_scenario()   # Phase 2 unified reference scenario: all cost inputs and sensitivity ranges
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")
PROV = {"generated_utc": NOW, "script": SCRIPT, "source_type": "python",
        "inputs_summary": "Aspen Plus V15 stored baseline results (results/simulations/baseline.json, baseline_no_hi.json) "
                          "costed by amcrax.economics.singapore; prices from backend/amcrax/data/singapore.yaml (scenarios)",
        "reference_scenario": provenance_stamp(),
        "model_versions": {"economics_module": "amcrax.economics.singapore/2 (reference scenario)", "data_schema": SD["schema"],
                           "cost_basis": REF.raw["price_year_label"], "capex_method": REF.capex_method}}
FOOT = "Source: python (amcrax.economics.singapore) on Aspen Plus V15 baseline; ammonia prices are scenarios, not Singapore transaction prices; mixed 2024-2026 USD; CAPEX cho2026_itemised_v1 (reference scenario)"

HI = json.loads((ROOT / "results/simulations/baseline.json").read_text(encoding="utf-8"))
NOHI = json.loads((ROOT / "results/simulations/baseline_no_hi.json").read_text(encoding="utf-8"))
S_HI, S_NOHI = extract_summary(HI), extract_summary(NOHI)
H2B = {k: v["value"] for k, v in SD["h2_price_benchmarks_USD_per_kg"].items() if isinstance(v, dict) and "value" in v}
ELEC_LO, ELEC_HI = REF.sens("electricity_USD_per_kWh")
DR_LO, DR_HI = REF.sens("discount_rate")
PL_LO, PL_HI = REF.sens("plant_life_yr")
OH_LO, OH_HI = REF.sens("operating_hours_h_per_yr")
EX_LO, EX_HI = REF.sens("capex_scaling_exponent")
FX = REF.fx_SGD_per_USD


def wj(name, obj):
    obj = {"provenance": PROV, **obj}
    (OUT / name).write_text(json.dumps(obj, indent=2, default=float), encoding="utf-8")


def wcsv(name, rows, header):
    with open(OUT / name, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def foot(fig):
    fig.text(0.01, 0.005, FOOT, fontsize=6.5, color="#555")


# ------------------------------------------------------------------ 1. scenarios x heat integration
rows, scen = [], {}
for hi_name, s in (("heat_integration_on", S_HI), ("heat_integration_off", S_NOHI)):
    for sc in SCENARIOS:
        e = evaluate(s, sc)
        scen[f"{sc}|{hi_name}"] = e
        rows.append([sc, hi_name, e["nh3_price_USD_per_t"], e["lcoh_USD_per_kg"], e["rec_USD_per_kg"],
                     *[e["breakdown_USD_per_kg"][k] for k in e["breakdown_USD_per_kg"]], e["npv_USD"], e["irr"], e["payback_yr"]])
bk = list(scen["grey|heat_integration_on"]["breakdown_USD_per_kg"])
wcsv("scenario_breakdown.csv", rows, ["scenario", "heat_integration", "nh3_USD_per_t", "lcoh", "rec", *bk, "npv_USD_at_ne_asia_smr", "irr", "payback_yr"])
wj("scenario_results.json", {"description": "LCOH, REC and breakdown for grey/blue/green ammonia price scenarios, heat integration on and off. "
    "Ammonia prices are scenarios (data/singapore.yaml), not Singapore transaction prices. NPV/IRR/payback at the NE Asia SMR benchmark 3.06 USD/kg H2 (Argus, 6 Jan 2026).",
    "results": {k: {kk: v[kk] for kk in ("scenario", "nh3_price_USD_per_t", "lcoh_USD_per_kg", "rec_USD_per_kg", "breakdown_USD_per_kg",
                    "purification_memo_USD_per_kg", "npv_USD", "irr", "payback_yr", "kg_nh3_feed_per_kg_h2", "kg_nh3_fuel_per_kg_h2",
                    "catalyst_mass_kg", "direct_emissions_tCO2e_per_yr", "carbon_tax_liable", "annual_H2_kg" if False else "annual_h2_kg")} |
                {"capex_total_USD": v["capex"]["total_capex_USD"], "capex_total_SGD": v["capex_total_SGD"],
                 "lcoh_SGD_per_kg": v["lcoh_SGD_per_kg"], "rec_SGD_per_kg": v["rec_SGD_per_kg"],
                 "breakdown_SGD_per_kg": v["breakdown_SGD_per_kg"], "npv_SGD": v["npv_SGD"], "fx_SGD_per_USD": FX,
                 "capex_by_item_USD": v["capex"]["tci_by_item_USD"], "capex_method": v["capex"]["method"]} for k, v in scen.items()},
    "phase1_equipment_basis_lcoh_USD_per_kg": {k: evaluate(s_, sc, {"capex_mode": "equipment"})["lcoh_USD_per_kg"]
                                                for k, s_, sc in [(f"{sc}|{h}", S_HI if h == "heat_integration_on" else S_NOHI, sc)
                                                                  for h in ("heat_integration_on", "heat_integration_off") for sc in SCENARIOS]},
    "note_phase2": "Phase 2: CAPEX method cho2026_itemised_v1 of the unified reference scenario (data/reference_scenario.yaml). "
                   "The Phase 1 equipment-basis values are kept under phase1_equipment_basis_lcoh_USD_per_kg for traceability (superseded)."})

# ------------------------------------------------------------------ 2. tornado (grey base, heat integration on)
base = evaluate(S_HI, "grey")["lcoh_USD_per_kg"]
torn_specs = [
    ("NH3 price 300-610 USD/t (Cho Table 8)", "nh3_price_USD_per_t", 300, 610, S_HI),
    ("CAPEX multiplier 0.5-1.5 (Cho Table 8)", "capex_multiplier", 0.5, 1.5, S_HI),
    ("Catalyst price 0.5x-2x (Cho Table 8)", "catalyst_price_USD_per_kg", 16.7, 66.8, S_HI),
    ("Catalyst lifetime 4-1 yr (Cho Table 8)", "catalyst_lifetime_yr", 4.0, 1.0, S_HI),
    (f"Electricity {ELEC_LO:.3f}-{ELEC_HI:.3f} USD/kWh (Cho; SP Group Q4 2026)", "electricity_price_USD_per_kWh", ELEC_LO, ELEC_HI, S_HI),
    ("Carbon tax 0-80 SGD/t (ammonia heat: no direct CO2)", "carbon_tax_SGD_per_t", 0.0, 80.0, S_HI),
    ("Capacity x0.25-x4 (feed 25-400 kmol/h)", "capacity_scale", 4.0, 0.25, S_HI),
    ("PSA recovery 0.95-0.756 (Cho 0.756; AmCraX 0.85)", "psa_recovery", 0.95, 0.756, S_HI),
    (f"Capacity factor {OH_LO:g}-{OH_HI:g} h/yr", "operating_hours_h_per_yr", OH_HI, OH_LO, S_HI),
    (f"Discount rate {DR_LO:g}-{DR_HI:g}", "discount_rate", DR_LO, DR_HI, S_HI),
    (f"Plant life {PL_HI:g}-{PL_LO:g} yr", "plant_life_yr", PL_HI, PL_LO, S_HI),
    (f"Capacity exponent {EX_LO:g}-{EX_HI:g} (six-tenths rule; Chopra Eq. 5)", "capex_scaling_exponent", EX_LO, EX_HI, S_HI),
]
bars = []
for label, key, lo, hi, s in torn_specs:
    el, eh = evaluate(s, "grey", {key: lo})["lcoh_USD_per_kg"], evaluate(s, "grey", {key: hi})["lcoh_USD_per_kg"]
    bars.append({"parameter": key, "label": label, "low_input": lo, "high_input": hi, "lcoh_at_low_input": el, "lcoh_at_high_input": eh,
                 "swing": abs(eh - el)})
hi_off = evaluate(S_NOHI, "grey")["lcoh_USD_per_kg"]
bars.append({"parameter": "heat_integration", "label": "Heat integration on vs off", "low_input": "on", "high_input": "off",
             "lcoh_at_low_input": base, "lcoh_at_high_input": hi_off, "swing": abs(hi_off - base)})
bars.sort(key=lambda b: -b["swing"])
wj("tornado.json", {"basis": "grey scenario (450 USD/t), heat integration on, reference-scenario CAPEX (cho2026_itemised_v1)", "lcoh_base_USD_per_kg": base,
                    "bars": bars, "note": "capacity bars hold labour fixed (labour_scales_with_capacity False)."})
wcsv("tornado.csv", [[b["label"], b["lcoh_at_low_input"], b["lcoh_at_high_input"], b["swing"]] for b in bars], ["parameter", "lcoh_low", "lcoh_high", "swing"])
fig, ax = plt.subplots(figsize=(9, 5.5))
for i, b in enumerate(reversed(bars)):
    lo, hi = sorted((b["lcoh_at_low_input"], b["lcoh_at_high_input"]))
    ax.barh(i, hi - lo, left=lo, color="#2a6f97")
    ax.text(hi + 0.01, i, f"{lo:.2f} - {hi:.2f}", va="center", fontsize=7)
ax.set_yticks(range(len(bars)))
ax.set_yticklabels([b["label"] for b in reversed(bars)], fontsize=7)
ax.axvline(base, color="k", lw=0.8)
ax.set_xlabel("LCOH (USD/kg H2)")
ax.set_title(f"One-at-a-time sensitivity, grey NH3 450 USD/t (base {base:.2f} USD/kg)", fontsize=10)
foot(fig)
fig.tight_layout(rect=(0, 0.02, 1, 1))
fig.savefig(FIG / "singapore_tornado.png", dpi=150)
plt.close(fig)

# ------------------------------------------------------------------ 3. breakdown figure
fig, ax = plt.subplots(figsize=(9, 5))
labels, keys = [], []
for sc in SCENARIOS:
    for hn in ("heat_integration_on", "heat_integration_off"):
        keys.append(f"{sc}|{hn}")
        labels.append(f"{sc}\n{'HI' if hn.endswith('on') else 'no HI'}")
cols = ["#2a6f97", "#61a5c2", "#89c2d9", "#a9d6e5", "#e07a5f", "#f2cc8f", "#81b29a", "#6d597a"]
bottom = np.zeros(len(keys))
for c, k in zip(cols, bk):
    v = np.array([scen[kk]["breakdown_USD_per_kg"][k] for kk in keys])
    ax.bar(range(len(keys)), v, bottom=bottom, label=k, color=c)
    bottom += v
ax.set_xticks(range(len(keys)))
ax.set_xticklabels(labels, fontsize=7)
ax.set_ylabel("USD/kg H2")
ax.set_title("LCOH breakdown by ammonia price scenario", fontsize=10)
ax.legend(fontsize=7, ncol=2)
foot(fig)
fig.tight_layout(rect=(0, 0.02, 1, 1))
fig.savefig(FIG / "singapore_cost_breakdown.png", dpi=150)
plt.close(fig)

# ------------------------------------------------------------------ 4. break-even NH3 price vs H2 benchmarks
be = {}
for hn, s in (("heat_integration_on", S_HI), ("heat_integration_off", S_NOHI)):
    be[hn] = {name: {"h2_price_USD_per_kg": v, "breakeven_nh3_USD_per_t": breakeven_nh3_price(s, v),
                     "source": SD["h2_price_benchmarks_USD_per_kg"][name]["source"]} for name, v in H2B.items()}
wj("breakeven_ammonia_price.json", {"description": "NH3 price (USD/t) at which LCOH equals each hydrogen benchmark; null means the benchmark is "
    "below the zero-ammonia-price conversion cost, i.e. unreachable. Benchmarks differ in basis; none is a Singapore transaction price.",
    "results": be, "nh3_scenarios_USD_per_t": {k: SD["nh3_price_scenarios_USD_per_t"][k]["value"] for k in SCENARIOS}})
prices = np.linspace(0, 1200, 61)
fig, ax = plt.subplots(figsize=(8, 5))
for hn, s, st in (("heat_integration_on", S_HI, "-"), ("heat_integration_off", S_NOHI, "--")):
    ax.plot(prices, [evaluate(s, p)["lcoh_USD_per_kg"] for p in prices], st, color="#2a6f97", label=f"LCOH ({hn.replace('_', ' ')})")
for (name, v), c in zip(H2B.items(), ["#81b29a", "#e07a5f", "#f2cc8f", "#6d597a"]):
    ax.axhline(v, color=c, lw=1, ls=":")
    ax.text(1195, v + 0.1, name.replace("_", " "), fontsize=6.5, ha="right", color=c)
for sc in SCENARIOS:
    ax.axvline(SD["nh3_price_scenarios_USD_per_t"][sc]["value"], color="#aaa", lw=0.6)
    ax.text(SD["nh3_price_scenarios_USD_per_t"][sc]["value"], 0.2, sc, rotation=90, fontsize=6.5, va="bottom")
ax.set_xlabel("Delivered NH3 price scenario (USD/t)")
ax.set_ylabel("LCOH (USD/kg H2)")
ax.set_title("Break-even ammonia price against hydrogen benchmark prices", fontsize=10)
ax.legend(fontsize=7, loc="upper left")
foot(fig)
fig.tight_layout(rect=(0, 0.02, 1, 1))
fig.savefig(FIG / "singapore_breakeven.png", dpi=150)
plt.close(fig)

# ------------------------------------------------------------------ 5. heatmaps and capacity curve
nh3p = np.linspace(300, 1100, 17)
tax = np.linspace(0, 80, 17)
Z_gas = np.array([[evaluate(S_HI, p, {"heat_fuel": "natural_gas", "carbon_tax_SGD_per_t": t, "apply_threshold": False})["lcoh_USD_per_kg"]
                   for p in nh3p] for t in tax])
Z_nh3 = np.array([[evaluate(S_HI, p, {"carbon_tax_SGD_per_t": t})["lcoh_USD_per_kg"] for p in nh3p] for t in tax])
scales = np.array([0.25, 0.5, 1, 2, 4, 5, 10, 20])
Z_cap = np.array([[evaluate(S_HI, p, {"capacity_scale": c})["lcoh_USD_per_kg"] for p in nh3p] for c in scales])
wcsv("heatmap_nh3_price_x_carbon_tax_nh3_heat.csv", [[t, *Z_nh3[i]] for i, t in enumerate(tax)], ["carbon_tax_SGD_per_t", *[f"nh3_{p:.0f}" for p in nh3p]])
wcsv("heatmap_nh3_price_x_carbon_tax_gas_heat_hypothetical.csv", [[t, *Z_gas[i]] for i, t in enumerate(tax)], ["carbon_tax_SGD_per_t", *[f"nh3_{p:.0f}" for p in nh3p]])
wcsv("heatmap_nh3_price_x_capacity.csv", [[100 * c, *Z_cap[i]] for i, c in enumerate(scales)], ["nh3_feed_kmol_h", *[f"nh3_{p:.0f}" for p in nh3p]])


def heat(Z, xs, ys, xl, yl, title, name, ytick_fmt="{:.0f}"):
    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(Z, origin="lower", aspect="auto", cmap="viridis",
                   extent=(xs[0], xs[-1], 0, len(ys) - 1) if False else None)
    ax.set_xticks(range(0, len(xs), 2))
    ax.set_xticklabels([f"{x:.0f}" for x in xs[::2]], fontsize=7)
    ax.set_yticks(range(len(ys)))
    ax.set_yticklabels([ytick_fmt.format(y) for y in ys], fontsize=7)
    for i in range(Z.shape[0]):
        for j in range(0, Z.shape[1], 4):
            ax.text(j, i, f"{Z[i, j]:.1f}", ha="center", va="center", fontsize=6, color="w")
    ax.set_xlabel(xl)
    ax.set_ylabel(yl)
    ax.set_title(title, fontsize=9)
    fig.colorbar(im, label="LCOH (USD/kg H2)")
    foot(fig)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(FIG / name, dpi=150)
    plt.close(fig)


heat(Z_gas, nh3p, tax, "Delivered NH3 price scenario (USD/t)", "Carbon tax (SGD/tCO2e)",
     "HYPOTHETICAL: gas-fired heat, facility liable (25,000 t threshold ignored)", "singapore_heatmap_nh3_price_carbon_tax.png")
heat(Z_cap, nh3p, 100 * scales, "Delivered NH3 price scenario (USD/t)", "NH3 feed (kmol/h)",
     "LCOH vs NH3 price and plant capacity (labour fixed, exponent 0.8)", "singapore_heatmap_nh3_price_capacity.png")
cap_rows = []
for c in [0.25, 0.5, 1, 2, 5, 10]:
    e = evaluate(S_HI, "grey", {"capacity_scale": c})
    cap_rows.append([100 * c, e["h2_product_kg_h"] * 24 / 1000.0, e["lcoh_USD_per_kg"], e["rec_USD_per_kg"], e["capex"]["total_capex_USD"]])
wcsv("cost_vs_capacity.csv", cap_rows, ["nh3_feed_kmol_h", "h2_t_per_day", "lcoh", "rec", "capex_USD"])
fig, ax = plt.subplots(figsize=(7, 4.5))
cs = np.logspace(np.log10(0.1), np.log10(20), 25)
ax.plot(100 * cs, [evaluate(S_HI, "grey", {"capacity_scale": c})["rec_USD_per_kg"] for c in cs], label="REC, fixed labour")
ax.plot(100 * cs, [evaluate(S_HI, "grey", {"capacity_scale": c, "labour_scales_with_capacity": True})["rec_USD_per_kg"] for c in cs], "--", label="REC, labour scales with capacity")
ax.set_xscale("log")
ax.set_xlabel("NH3 feed (kmol/h)")
ax.set_ylabel("Reconversion cost (USD/kg H2)")
ax.set_title("Cost vs capacity (grey scenario)", fontsize=10)
ax.legend(fontsize=7)
foot(fig)
fig.tight_layout(rect=(0, 0.02, 1, 1))
fig.savefig(FIG / "singapore_cost_vs_capacity.png", dpi=150)
plt.close(fig)

# ------------------------------------------------------------------ 6. Monte Carlo
SEED, N = 20261123, 5000
rng = np.random.default_rng(SEED)
mc = {}
DIST = {"nh3_price_USD_per_t": "triangular(low, base, high) of the scenario range, data/singapore.yaml",
        "electricity_price_USD_per_kWh": f"uniform({ELEC_LO}, {ELEC_HI:.4f})",
        "catalyst_price_USD_per_kg": "triangular(0.5x, 1x, 2x of 33.4) Cho Table 8",
        "catalyst_lifetime_yr": "uniform(1, 4) Cho Table 8", "capex_multiplier": "triangular(0.5, 1, 1.5) Cho Table 8",
        "discount_rate": f"uniform({DR_LO}, {DR_HI})", "operating_hours_h_per_yr": f"uniform({OH_LO}, {OH_HI})",
        "plant_life_yr": f"uniform({PL_LO}, {PL_HI})"}
draws = {"elec": rng.uniform(ELEC_LO, ELEC_HI, N), "cat": rng.triangular(16.7, 33.4, 66.8, N), "life": rng.uniform(1, 4, N),
         "capx": rng.triangular(0.5, 1.0, 1.5, N), "dr": rng.uniform(DR_LO, DR_HI, N), "oh": rng.uniform(OH_LO, OH_HI, N),
         "pl": rng.uniform(PL_LO, PL_HI, N)}
u_nh3 = rng.random(N)
for sc in ("grey", "blue", "green_current", "green_2030"):
    d = SD["nh3_price_scenarios_USD_per_t"][sc]
    lo, md, hi = d["low"], d["value"], d["high"]
    fc = (md - lo) / (hi - lo)
    pr = np.where(u_nh3 < fc, lo + np.sqrt(u_nh3 * (hi - lo) * (md - lo)), hi - np.sqrt((1 - u_nh3) * (hi - lo) * (hi - md)))
    L, R = [], []
    for i in range(N):
        e = evaluate(S_HI, float(pr[i]), {"electricity_price_USD_per_kWh": draws["elec"][i], "catalyst_price_USD_per_kg": draws["cat"][i],
                                          "catalyst_lifetime_yr": draws["life"][i], "capex_multiplier": draws["capx"][i],
                                          "discount_rate": draws["dr"][i], "operating_hours_h_per_yr": draws["oh"][i],
                                          "plant_life_yr": draws["pl"][i]})
        L.append(e["lcoh_USD_per_kg"]); R.append(e["rec_USD_per_kg"])
    L, R = np.array(L), np.array(R)
    mc[sc] = {"lcoh_p5": float(np.percentile(L, 5)), "lcoh_p50": float(np.percentile(L, 50)), "lcoh_p95": float(np.percentile(L, 95)),
              "lcoh_mean": float(L.mean()), "rec_p5": float(np.percentile(R, 5)), "rec_p50": float(np.percentile(R, 50)),
              "rec_p95": float(np.percentile(R, 95)), "n": N, "seed": SEED}
    mc[sc]["_samples_lcoh"] = L
wj("monte_carlo.json", {"description": "Monte Carlo on the grey/blue/green scenarios, heat integration on, independent draws.", "seed": SEED,
                        "n_samples": N, "distributions": DIST,
                        "results": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in mc.items()}})
fig, ax = plt.subplots(figsize=(8, 4.5))
for sc, c in zip(mc, ["#2a6f97", "#61a5c2", "#e07a5f", "#81b29a"]):
    ax.hist(mc[sc]["_samples_lcoh"], bins=50, alpha=0.6, label=sc, color=c)
ax.set_xlabel("LCOH (USD/kg H2)")
ax.set_ylabel("Samples")
ax.set_title(f"Monte Carlo (n={N}, seed {SEED})", fontsize=10)
ax.legend(fontsize=7)
foot(fig)
fig.tight_layout(rect=(0, 0.02, 1, 1))
fig.savefig(FIG / "singapore_monte_carlo.png", dpi=150)
plt.close(fig)
wcsv("monte_carlo_samples_grey.csv", [[x] for x in mc["grey"]["_samples_lcoh"]], ["lcoh_USD_per_kg"])

# ------------------------------------------------------------------ 7. assumptions register
asm = []


def A(name, value, unit, st, src, note):
    asm.append({"name": name, "value": value, "unit": unit, "source_type": st, "source": src, "applicability_note": note})


A("currency_and_basis", SD["base_year_label"], "-", "assumption", "singapore.yaml header", "no escalation applied (conflicting CEPCI in library)")
A("fx_SGD_per_USD", FX, "SGD/USD", "derived", REF.raw["currency"]["fx_SGD_per_USD"]["source"], f"rate date {REF.fx_date}; reference scenario (supersedes 1.290, ADB)")
A("carbon_tax_2026", 45, "SGD/tCO2e", "literature", SD["carbon_tax"]["url"], "official NEA; applies to direct emissions of facilities >= 25,000 tCO2e/yr")
A("carbon_tax_threshold", 25000, "tCO2e/yr", "literature", SD["carbon_tax"]["url"], "facility-level; gas-fired heat of the baseline gives about 1.3 kt: below threshold")
A("N2O_treatment", "not quantified", "-", "assumption", "NEA: N2O is a covered gas", "no primary-source N2O factor for NH3 combustion; user may supply n2o_tCO2e_per_yr")
A("electricity_price", REF.electricity_USD_per_kWh, "USD/kWh", "derived", "reference scenario: USEP 2025 mean + network + fees (EMA, SP Group) / FX", "derived, not an industrial contract price; <0.1 % of LCOH")
A("capex_method", REF.capex_method, "-", "literature", REF.raw["capex"]["method"]["source"], "reference scenario; Phase 1 Farokhi 'equipment' method superseded")
for sc in SCENARIOS:
    d = SD["nh3_price_scenarios_USD_per_t"][sc]
    A(f"nh3_price_{sc}", d["value"], "USD/t NH3", d["source_type"] if d["source_type"] != "literature" else "literature", d["source"], "SCENARIO (delivered, international); not a Singapore transaction price")
for k, v in H2B.items():
    A(f"h2_price_benchmark_{k}", v, "USD/kg H2", "literature", SD["h2_price_benchmarks_USD_per_kg"][k]["source"], "secondary web value; basis differs by source")
c = SD["capex_equipment"]
A("pec_reference", c["pec_reference_kUSD"]["value"], "kUSD at 500 kmol/h NH3", "literature", c["pec_reference_kUSD"]["source"], "cost year not stated; kUSD inferred")
A("tci_over_pec", c["tci_over_pec"]["value"], "-", "literature", c["tci_over_pec"]["source"], "derived from Table 5")
A("scaling_exponent", c["scaling_exponent"]["value"], "-", "literature", c["scaling_exponent"]["source"], "0.7451 (Ahmad) as sensitivity")
A("singapore_location_factor", 1.0, "-", "assumption", c["singapore_location_factor"]["source"], "no source; CAPEX multiplier +-50 % (Cho Table 8) used for sensitivity")
A("catalyst", "Ni 33.4 / Ru 542 USD/kg; life 2 yr; 9000 mL NH3/(g h)", "-", "literature", "Cho 2026 Tables 3-4 (via economics.yaml)", "mass sized from space velocity, not from the PFR kinetics (results/research/kinetics not present)")
A("fixed_opex", "maintenance 3 %, insurance 1.5 % of CAPEX; labour 109,756 USD/yr; overhead 25 %; G&A 6 %", "-", "literature", "Chopra 2026 Table 2; Cho 2026 Table 4 (economics.yaml)", "labour is an Indian small-plant basis, not Singapore")
A("discount_rate_and_life", f"{REF.discount_rate:g}, {REF.plant_life_yr:g} yr", "-", "literature", "Kum 2026 Table 5 (also Farokhi, Chopra, Ahmad)", "no Singapore WACC sourced; Cho 8.5 % in sensitivity")
A("heat_fuel", "supplementary NH3, 100 % LHV efficiency", "-", "assumption", "economics.yaml", "gas-fired variant uses Kum fired-heat price 4.25 USD/GJ and IPCC 56.1 kg CO2/GJ; no Singapore gas price retrieved")
A("landed_cost", None, "-", "assumption", "-", "not computed: no sourced transport/distribution cost")
wj_obj = asm
(OUT / "assumptions.json").write_text(json.dumps(wj_obj, indent=2, default=float), encoding="utf-8")

# ------------------------------------------------------------------ 8. validation and benchmarks
_LEG = REF.reproduction("legacy_v1")
legacy = evaluate(S_HI, _LEG["nh3_price_USD_per_t"], {"capex_mode": "legacy", "electricity_price_USD_per_kWh": _LEG["electricity_price_USD_per_kWh"]})
eq_p1 = evaluate(S_HI, "grey", {"capex_mode": "equipment"})
old = compute_lcoh(SimulationResult.model_validate(HI))
stored = json.loads((ROOT / "results/simulations/economics_baseline.json").read_text(encoding="utf-8"))
g = scen["grey|heat_integration_on"]
items = []


def V(id_, desc, method, ref, obs, exp, tol, unit, status, files):
    items.append({"id": id_, "description": desc, "method": method, "reference_source": ref, "observed": obs, "expected": exp,
                  "tolerance": tol, "unit": unit, "status": status, "source_files": files,
                  # E08-E13 compare with published numbers; the others are numerical checks of the Python code
                  "evidence_kind": "literature_comparison" if id_ in ("E08", "E09", "E10", "E11", "E12", "E13") else "numerical_verification"})


V("E01", "Reproduction of the stored LCOH with the old settings (legacy capex, 450 USD/t, 0.084 USD/kWh)", "evaluate(capex_mode=legacy) vs results/simulations/economics_baseline.json",
  "python (existing amcrax.economics.lcoh)", legacy["lcoh_USD_per_kg"], stored["lcoh_USD_per_kg"], 1e-9, "USD/kg H2",
  "pass" if abs(legacy["lcoh_USD_per_kg"] - stored["lcoh_USD_per_kg"]) < 1e-9 else "fail", ["results/simulations/economics_baseline.json"])
V("E02", "Reproduction vs compute_lcoh on the same result", "direct comparison", "python", legacy["lcoh_USD_per_kg"], old.lcoh_USD_per_kg, 1e-9, "USD/kg H2",
  "pass" if abs(legacy["lcoh_USD_per_kg"] - old.lcoh_USD_per_kg) < 1e-9 else "fail", [])
V("E03", "Cost-share closure: breakdown sums to LCOH (grey, HI on)", "sum(breakdown) - lcoh", "internal", sum(g["breakdown_USD_per_kg"].values()), g["lcoh_USD_per_kg"], 1e-12, "USD/kg H2",
  "pass" if abs(sum(g["breakdown_USD_per_kg"].values()) - g["lcoh_USD_per_kg"]) < 1e-12 else "fail", ["results/research/singapore/scenario_results.json"])
tot = sum(g["annual_USD_per_yr"].values()) / g["annual_h2_kg"]
V("E04", "Unit consistency: total annual cost / annual H2 equals LCOH", "sum(annual USD/yr)/annual kg", "internal", tot, g["lcoh_USD_per_kg"], 1e-9, "USD/kg H2",
  "pass" if abs(tot - g["lcoh_USD_per_kg"]) < 1e-9 else "fail", [])
V("E05", "REC = LCOH - feed cost", "rec - (lcoh - feed)", "Cho 2026 Eq. 23", g["rec_USD_per_kg"], g["lcoh_USD_per_kg"] - g["breakdown_USD_per_kg"]["ammonia_feed"], 1e-12, "USD/kg H2",
  "pass", [])
be_ref = breakeven_nh3_price(S_HI, 5.0)
V("E06", "Break-even price returns the target LCOH", "evaluate at break-even price", "internal", evaluate(S_HI, be_ref)["lcoh_USD_per_kg"], 5.0, 1e-9, "USD/kg H2",
  "pass" if abs(evaluate(S_HI, be_ref)["lcoh_USD_per_kg"] - 5.0) < 1e-9 else "fail", ["results/research/singapore/breakeven_ammonia_price.json"])
V("E07", "Feed-NH3 per kg H2 at or above the stoichiometric floor 5.632 (kg/kg)", "kg_nh3_feed_per_kg_h2", "stoichiometry", g["kg_nh3_feed_per_kg_h2"], 5.632, 0.0, "kg NH3/kg H2",
  "pass" if g["kg_nh3_feed_per_kg_h2"] >= 5.632 else "fail", [])
cho_ni, cho_ru = 1.995, 1.856
V("E08", "REC vs Cho 2026 Ni (1.995 USD/kg, Fig. 8d): different boundary (no 180 bar compression, TSA, NOx; 251 vs about 100 kg/h)", "informational comparison",
  "Cho 2026 p. 13 Fig. 8(d)", g["rec_USD_per_kg"], cho_ni, None, "USD/kg H2", "informational", [])
V("E09", "Cho Ru REC 7.0 % lower than Ni check: (1.995-1.856)/1.995", "arithmetic on the notes", "Cho 2026 notes", (cho_ni - cho_ru) / cho_ni, 0.07, 0.005, "fraction",
  "informational", ["research/notes/cho2026nickel.md"])  # arithmetic on Cho's own numbers: consistency, not validation
V("E10", "LCOH (legacy capex) vs Cho Ni total 5.439 USD/kg at 450 USD/t", "informational comparison", "Cho 2026 Fig. 8(d)", legacy["lcoh_USD_per_kg"], 5.439, None, "USD/kg H2", "informational", [])
V("E11", "Reference-scenario LCOH (cho2026_itemised_v1) vs Cho Ni total 5.439 USD/kg", "informational comparison", "Cho 2026 Fig. 8(d)", g["lcoh_USD_per_kg"], 5.439, None, "USD/kg H2", "informational", [])
V("E12", "Halim 2025 LCOH 10.1 (blue) / 15.1 (green) USD/kg for a 60.1 MW plant", "not compared: only the abstract was retrievable; PDF absent from research/papers",
  "Halim, Zain & Khoo 2025 (brief values, unverified)", None, None, None, "USD/kg H2", "informational", [])
c25 = evaluate(S_HI, "grey", {"capacity_scale": 0.25})["lcoh_USD_per_kg"]
c10 = evaluate(S_HI, "grey", {"capacity_scale": 10})["lcoh_USD_per_kg"]
V("E13", "Scale effect 25 -> 1000 kmol/h: LCOH ratio vs Deka 2025 (5.21 -> 3.58, ratio 1.455; value from the brief, source not in library)",
  "evaluate at 25 and 1000 kmol/h", "Deka 2025 (unverified)", c25 / c10, 5.21 / 3.58, None, "ratio", "informational", ["results/research/singapore/cost_vs_capacity.csv"])
V("E14", "Carbon tax 0 for ammonia-fuelled heat (no direct CO2)", "carbon tax breakdown", "NEA Scope 1 rule", g["breakdown_USD_per_kg"]["carbon_tax"], 0.0, 0.0, "USD/kg H2",
  "pass" if g["breakdown_USD_per_kg"]["carbon_tax"] == 0 else "fail", [])
gas = evaluate(S_HI, "grey", {"heat_fuel": "natural_gas"})
V("E15", "Gas-fired heat of the baseline is below the 25,000 t threshold (no tax liability)", "direct emissions", "NEA threshold", gas["direct_emissions_tCO2e_per_yr"], 25000, None, "tCO2e/yr",
  "pass" if not gas["carbon_tax_liable"] else "fail", [])
(VAL / "economics.json").write_text(json.dumps({"provenance": PROV, "items": items}, indent=2, default=float), encoding="utf-8")

wj("benchmarks.json", {"comparisons": [
    {"item": "Cho 2026 REC Ni / Ru (Fig. 8d)", "literature_USD_per_kg": [cho_ni, cho_ru], "amcrax_equipment_rec": eq_p1["rec_USD_per_kg"], "amcrax_legacy_rec": legacy["rec_USD_per_kg"],
     "amcrax_reference_rec": g["rec_USD_per_kg"],
     "explanation": "Cho includes 180 bar product compression (about 137 kW at 99 kg/h), TSA, NOx SCR, OSBL/engineering/contingency and a 97 % conversion optimisation at about 100 kg H2/h; AmCraX baseline has none of these, runs at 251 kg H2/h, and its equipment-level CAPEX is a feed-scaled screening estimate. The gap is a boundary difference, not a validation failure or success."},
    {"item": "Halim 2025", "status": "numeric values not verified (abstract only)", "qualitative": "direct ammonia use preferred economically over cracking for power (abstract)"},
    {"item": "Deka 2025 scale effect", "status": "values from the brief; paper not in library", "amcrax_ratio_25_to_1000_kmol_h": c25 / c10, "literature_ratio": 5.21 / 3.58}]})

# ------------------------------------------------------------------ 9. references
refs = [
 {"citekey": "nea_carbon_tax", "apa7": "National Environment Agency. (n.d.). Carbon tax. Government of Singapore. https://www.nea.gov.sg/OUR-SERVICES/CLIMATE-CHANGE-ENERGY-EFFICIENCY/CLIMATE-CHANGE/CARBON-TAX", "doi": None, "url": "https://www.nea.gov.sg/OUR-SERVICES/CLIMATE-CHANGE-ENERGY-EFFICIENCY/CLIMATE-CHANGE/CARBON-TAX", "access_date": "2026-11-23", "taken_from_it": "Rates 5/25/45 SGD/tCO2e, 50-80 by 2030 target, 25,000 tCO2e threshold, seven covered gases incl. N2O, direct facility-level scope"},
 {"citekey": "spgroup_tariff_2026q4", "apa7": "SP Group. (2026). Electricity tariff information, 1 October to 31 December 2026. https://www.spgroup.com.sg/our-services/utilities/tariff-information", "doi": None, "url": "https://www.spgroup.com.sg/our-services/utilities/tariff-information", "access_date": "2026-11-23", "taken_from_it": "Regulated tariff components (energy 22.18, network 6.10, MSS 0.23, PSO 0.08; total 28.59 cents/kWh before GST)"},
 {"citekey": "ema_usep", "apa7": "Energy Market Authority. (2026). Average monthly Uniform Singapore Energy Price. https://ema.gov.sg/resources/statistics/average-monthly-uniform-singapore-energy-price", "doi": None, "url": "https://ema.gov.sg/resources/statistics/average-monthly-uniform-singapore-energy-price", "access_date": "2026-11-23", "taken_from_it": "2025 monthly USEP (via search-result summary; table not opened directly)"},
 {"citekey": "mpa_ema_ammonia_2025", "apa7": "Maritime and Port Authority of Singapore. (2025). Consortium appointed for next phase of study on low- or zero-carbon ammonia power generation and bunkering solution. https://www.mpa.gov.sg/media-centre/details/consortium-appointed-for-next-phase-of-study-on-low--or-zero-carbon-ammonia-power-generation-and-bunkering-solution", "doi": None, "url": "https://www.mpa.gov.sg/media-centre/details/consortium-appointed-for-next-phase-of-study-on-low--or-zero-carbon-ammonia-power-generation-and-bunkering-solution", "access_date": "2026-11-23", "taken_from_it": "Keppel-led FEED appointment 3 Oct 2025; 55-65 MW direct combustion; >= 0.1 Mt/yr bunkering (search-result summary)"},
 {"citekey": "mti_hydrogen_strategy", "apa7": "Ministry of Trade and Industry. (2022). Singapore's National Hydrogen Strategy. https://www.mti.gov.sg/-/media/MTI/HPO/Singapore-Hydrogen-Strategy/ebrochure_HPO_Oct_26.pdf", "doi": None, "url": "https://www.mti.gov.sg/-/media/MTI/HPO/Singapore-Hydrogen-Strategy/ebrochure_HPO_Oct_26.pdf", "access_date": "2026-11-23", "taken_from_it": "Policy context only (brochure not read in full)"},
 {"citekey": "halim2025ammonia", "apa7": "Halim, I., Zain, N. S., & Khoo, H. H. (2025). Assessing the feasibility of ammonia utilization for power generation: A techno-economic-environmental study. Applied Energy, 386, 125581. https://doi.org/10.1016/j.apenergy.2025.125581", "doi": "10.1016/j.apenergy.2025.125581", "url": "https://doi.org/10.1016/j.apenergy.2025.125581", "access_date": "2026-11-23", "taken_from_it": "Abstract only: direct NH3 use preferred over cracking for power; numeric values not verified. Bibliographic data (authors Iskandar Halim, Nur Sara Zain, Hsien H. Khoo; vol. 386, 125581) confirmed through Crossref and IDEAS/RePEc by the independent review."},
 {"citekey": "sp_blue_ammonia_2025", "apa7": "S&P Global Commodity Insights. (2025, August 21). Global blue ammonia prices rise in July, tracking tighter conventional markets. https://www.spglobal.com/energy/en/news-research/latest-news/energy-transition/082125-global-blue-ammonia-prices-rise-in-july-tracking-tighter-conventional-markets", "doi": None, "url": "https://www.spglobal.com/energy/en/news-research/latest-news/energy-transition/082125-global-blue-ammonia-prices-rise-in-july-tracking-tighter-conventional-markets", "access_date": "2026-11-23", "taken_from_it": "Blue ammonia 400 (Far East Asia) and 574 USD/mt (NW Europe); page returned HTTP 403, values from search-result text"},
 {"citekey": "sp_singapore_h2_2025", "apa7": "S&P Global Commodity Insights. (2025, May 7). Power generation firms face high hydrogen costs in Singapore. https://spglobal.com/commodity-insights/en/news-research/latest-news/energy-transition/050725-power-generation-firms-face-high-hydrogen-costs-in-singapore", "doi": None, "url": "https://spglobal.com/commodity-insights/en/news-research/latest-news/energy-transition/050725-power-generation-firms-face-high-hydrogen-costs-in-singapore", "access_date": "2026-11-23", "taken_from_it": "Singapore low-carbon hydrogen willingness to pay about 3 USD/kg; offers about 10 USD/kg FOB Malaysia (search-result text; article not fetched)"},
 {"citekey": "argus_h2_markers", "apa7": "Argus Media. (2026). Argus Hydrogen and Future Fuels, sample report (regional hydrogen cost markers). https://view.argusmedia.com/rs/584-BUW-606/images/POW-Sample-Report-20260106-Hydrogen.pdf?version=0", "doi": None, "url": "https://view.argusmedia.com/rs/584-BUW-606/images/POW-Sample-Report-20260106-Hydrogen.pdf?version=0", "access_date": "2026-11-23", "taken_from_it": "Issue 26-01, 6 Jan 2026, p. 2 regional hydrogen cost markers: Northeast Asia SMR 3.06 USD/kg incl. capex (2.09 excl. capex); read from the PDF text (corrected by the independent review; the earlier 4.68 is not in this document)"},
 {"citekey": "ace_h2_delivered", "apa7": "ASEAN Centre for Energy. (n.d.). Hydrogen delivered-cost estimate for East Asia. https://accept.aseanenergy.org/?p=24333", "doi": None, "url": "https://accept.aseanenergy.org/?p=24333", "access_date": "2026-11-23", "taken_from_it": "Delivered cost to East Asia 5-7 USD/kg blue, 9-11 USD/kg green (search-result text; exact title and year to be checked)"},
 {"citekey": "eu2018_2066_annex6", "apa7": "European Commission. (2018). Commission Implementing Regulation (EU) 2018/2066, Annex VI (reference values of emission factors, IPCC 2006 Guidelines). https://www.legislation.gov.uk/eur/2018/2066/annex/VI/data.pdf", "doi": None, "url": "https://www.legislation.gov.uk/eur/2018/2066/annex/VI/data.pdf", "access_date": "2026-11-23", "taken_from_it": "Natural gas 56.1 t CO2/TJ (IPCC 2006 default)"},
 {"citekey": "adb_fx", "apa7": "Asian Development Bank. (2026). Asia Bonds Online: Singapore economy, exchange rate. https://asianbondsonline.adb.org/economy/?economy=SG&page=9", "doi": None, "url": "https://asianbondsonline.adb.org/economy/?economy=SG&page=9", "access_date": "2026-11-23", "taken_from_it": "1.290 SGD per USD (recorded as 18 Nov 2026; the page showed 1.290 at the close of 20 Nov 2026 when re-checked by the independent review)"},
]
(ROOT / "research" / "reference_additions").mkdir(exist_ok=True)
(ROOT / "research" / "reference_additions" / "economics.json").write_text(json.dumps(refs, indent=2), encoding="utf-8")
print("done", {k: v["lcoh_USD_per_kg"] for k, v in scen.items()})
print("validation", [(i["id"], i["status"]) for i in items])
