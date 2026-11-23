"""Kinetic validity classification at the AmCraX operating conditions (Phase 2, task K1 item 1).

Every catalyst rate law in backend/amcrax/data/kinetics.yaml and every catalyst named by the author is given exactly
one class at the AmCraX conditions (20 bar; study temperatures 450-700 degC; operating points 499-594 degC):

  validated_at_relevant_conditions  a comparison with published data PASSED at >= 15 bar inside the AmCraX T window
  validated_against_literature      a comparison with published data PASSED, but not at the relevant pressure;
                                    the 20 bar use is still a pressure extrapolation
  extrapolated                      used outside its fitted range and no passing comparison with published data
  unmodelled                        no usable published rate law (nothing is simulated)

The class is decided by the rule in classify() from the machine-readable fields below, not by hand. Evidence kinds are
named as in the Phase 2 brief (numerical_verification, python_vs_aspen, literature_comparison); AmCraX has no
experimental validation. A literature comparison against the law's own fitting data is flagged
`comparison_uses_fitting_data` (a consistency check, not independent validation).
Outputs: results/research/kinetics/validity_classification.json and .csv. Deterministic; run from the AmCraX root.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "backend"))

import yaml  # noqa: E402

OUT = os.path.join(ROOT, "results", "research", "kinetics")
CLASSES = ["validated_at_relevant_conditions", "validated_against_literature", "extrapolated", "unmodelled"]
AMCRAX = {"P_bar": 20.0, "T_C_studies": [450.0, 700.0], "T_C_operating_points": [499.0, 594.0],
          "note": "standalone and integrated studies at 20 bar (pressure studies 1.013-40 bar); operating points = "
                  "lowest T for 95 % conversion with 100 kg catalyst per 100 kmol/h NH3 (results/research/aspen_kinetic/"
                  "catalyst_comparison.json)"}
RELEVANT_P_MIN_BAR = 15.0

REG = yaml.safe_load(open(os.path.join(ROOT, "backend", "amcrax", "data", "kinetics.yaml"), encoding="utf-8"))


def _cat(cid):
    return {**REG["catalysts"], **(REG.get("research_catalysts") or {})}[cid]


def _rng(cid):
    v = _cat(cid)["validity"]
    return {"T_K": [v["T_min_K"], v["T_max_K"]], "T_C": [round(v["T_min_K"] - 273.15, 2), round(v["T_max_K"] - 273.15, 2)],
            "P_bar": [v["P_min_bar"], v["P_max_bar"]]}


LAWS = [
    {
        "catalyst": "Ni/MgO", "catalyst_id": "ni_takahashi_microkinetic", "citekey": "takahashi2016kinetic",
        "law_form": "microkinetic, 4 lumped elementary steps, QSS coverages (Eqs. 5-14); mole-fraction basis p_i/p_total",
        "fitted_range_basis": "fit 350-450 degC (<20 % conversion), extrapolation tests by the authors 500-650 degC; all 1 atm",
        "experimental": {"T_C": [350, 650], "P_bar": [1.01325, 1.01325], "feed": "NH3 0.1-1.0 atm in Ar; H2 co-feed 0-0.7 atm at p_NH3 0.3 atm",
                         "space_velocity": "SV 15000-30000 h-1 (fit), 2000-20000 h-1 (tests); basis of SV and catalyst mass not reported",
                         "conversion_range": [0.0, 1.0], "conversion_note": "fit <20 %; tests 20-100 %"},
        "h2_inhibition": "fitted (H2 re-adsorption step 4, k-4 = k4/K4; Fig. 5 data)",
        "reversibility": "not in the published law (steps 2, 3 irreversible); AmCraX approach factor (1 - Q/Kp) is an assumption",
        "literature_comparisons": [
            {"id": "EXISTING-KIN-NI-PRED", "status": "fail", "observed": 0.1096, "tolerance": 0.05, "P_bar": 1.01325,
             "T_C": [500, 650], "comparison_uses_fitting_data": False,
             "what": "PFR conversion vs Figs. 3a/3b/5a (read from figures; W/F from one anchor point)"}],
        "numerical_checks": ["EXISTING-KIN-TABLE2 pass (Table 1 vs Table 2 at 773 K, 6.8 % < 10 %)",
                             "KINR-ASPENAPPROX-ni pass (fitted Aspen LHHW approximation vs exact law, 0.034 < 0.05)"],
        "aspen_representation": "fitted LHHW approximation (python fit, mole-fraction basis, 20 bar only); not native",
    },
    {
        "catalyst": "Ru/MgO", "catalyst_id": "ru_takahashi_microkinetic", "citekey": "takahashi2016kinetic",
        "law_form": "microkinetic, as Ni/MgO with Ru parameters (Table 1); mole-fraction basis",
        "fitted_range_basis": "fit 300-400 degC (<20 % conversion), tests 450-550 degC; all 1 atm",
        "experimental": {"T_C": [300, 550], "P_bar": [1.01325, 1.01325], "feed": "NH3 0.1-1.0 atm in Ar; H2 co-feed 0-0.7 atm at p_NH3 0.3 atm",
                         "space_velocity": "SV 15000-30000 h-1 (fit), 2000-20000 h-1 (tests); basis and catalyst mass not reported",
                         "conversion_range": [0.0, 1.0], "conversion_note": "fit <20 %; tests 16-100 %"},
        "h2_inhibition": "fitted (step 4 reversible)",
        "reversibility": "not in the published law; AmCraX approach factor is an assumption",
        "literature_comparisons": [
            {"id": "EXISTING-KIN-RU-PRED", "status": "fail", "observed": 0.1113, "tolerance": 0.05, "P_bar": 1.01325,
             "T_C": [450, 550], "comparison_uses_fitting_data": False,
             "what": "PFR conversion vs Figs. 4a/4b/5b (read from figures; W/F from one anchor point)"}],
        "numerical_checks": ["EXISTING-KIN-TABLE2 pass", "KINR-ASPENAPPROX-ru pass (0.019 < 0.05)"],
        "aspen_representation": "fitted LHHW approximation (python fit, mole-fraction basis, 20 bar only); not native",
    },
    {
        "catalyst": "Ru/Al2O3", "catalyst_id": "ru_kum_temkin_pyzhev", "citekey": "kum2026heatintegrated",
        "law_form": "Temkin-Pyzhev, reversible: r = k [(pNH3^2/pH2^3)^0.27 - pN2/Keq^2 (pH2^3/pNH3^2)^0.73], p in bar",
        "fitted_range_basis": "Kum et al. fit to 36 points of Di Carlo et al. 2014 (commercial 8 wt% Ru/Al2O3), 623-723 K, 1-10 bar",
        "experimental": {"T_C": [350, 450], "P_bar": [1.0, 10.0], "feed": "pure NH3 (Di Carlo 2014)",
                         "space_velocity": "GHSV 300-2400 h-1", "conversion_range": None,
                         "conversion_note": "not tabulated in the AmCraX notes for the fitting set"},
        "h2_inhibition": "fitted through the Temkin-Pyzhev H2 order (-3 beta = -0.81)",
        "reversibility": "in the published law (Keq basis ambiguous; AmCraX reading documented as an assumption)",
        "literature_comparisons": [
            {"id": "EXISTING-KIN-DICARLO", "status": "pass_informational", "observed": 0.0039, "tolerance": 0.01,
             "P_bar": 10.0, "P_bar_range": [1.0, 10.0], "T_C": [500, 500], "comparison_uses_fitting_data": True,
             "what": "PFR vs Di Carlo conversions at 500 degC, 1/5/10 bar (Maccarrone 2025 Table 2); stored as informational because the law was fitted to Di Carlo data"}],
        "numerical_checks": ["KINR-ASPENFORM-ru_kum pass (Aspen form vs Python, 5.8e-4 relative)"],
        "aspen_representation": "native LHHW, partial-pressure basis (exact up to the ln Kp fit)",
    },
    {
        "catalyst": "5Ni1Ru/CeO2", "catalyst_id": "nire_ceo2_5ni1ru_lucentini_lhhw", "citekey": "lucentini2021nirukinetic",
        "law_form": "LHHW, RDS first dehydrogenation: r = k K1 C_NH3/(1 + K1 C_NH3 + sqrt(C_H2/K4))^2, C in mol/m3 (ideal gas)",
        "fitted_range_basis": "350-600 degC, 1 atm, powder 0.1 mm in SiC",
        "experimental": {"T_C": [350, 600], "P_bar": [1.01325, 1.01325], "feed": "NH3 10-100 % in Ar; H2 co-feed 0-67.5 %, N2 co-feed 0-67.5 % at 10 % NH3",
                         "space_velocity": "F/W 15-45 L g-1 h-1 (GHSV 3660-7320 h-1)", "conversion_range": [0.365, 0.996],
                         "conversion_note": "Table 1 points 400/450/500 degC (36.5/86.1/99.6 %); full fitting set wider"},
        "h2_inhibition": "fitted (sqrt(C_H2/K4) adsorption term, H2 co-feed series)",
        "reversibility": "not in the published law; AmCraX approach factor (1 - Q/Kp) is an assumption",
        "literature_comparisons": [
            {"id": "KINR-LUC-5Ni1Ru_CeO2", "status": "pass", "observed": 0.0394, "tolerance": 0.05, "P_bar": 1.01325,
             "T_C": [400, 500], "comparison_uses_fitting_data": True, "what": "PFR vs Table 1 conversions"}],
        "numerical_checks": ["KINR-ASPENFORM pass (6.2e-4 relative)", "Aspen vs Python cv/cs points pass"],
        "aspen_representation": "native LHHW; molarity basis in Phase 1 runs, exact partial-pressure basis added in Phase 2 (task K1 item 3)",
    },
    {
        "catalyst": "2.5Ni0.5Ru/CeO2", "catalyst_id": "nire_ceo2_2p5ni0p5ru_lucentini_lhhw", "citekey": "lucentini2021nirukinetic",
        "law_form": "LHHW as 5Ni1Ru/CeO2 with Table 3 parameters",
        "fitted_range_basis": "350-600 degC, 1 atm",
        "experimental": {"T_C": [350, 600], "P_bar": [1.01325, 1.01325], "feed": "as 5Ni1Ru/CeO2",
                         "space_velocity": "F/W 15-45 L g-1 h-1", "conversion_range": [0.497, 0.992],
                         "conversion_note": "Table 1 points 400/450/500 degC (49.7/88.7/99.2 %)"},
        "h2_inhibition": "fitted", "reversibility": "not in the published law; AmCraX approach factor is an assumption",
        "literature_comparisons": [
            {"id": "KINR-LUC-2p5Ni0p5Ru_CeO2", "status": "pass", "observed": 0.0246, "tolerance": 0.05, "P_bar": 1.01325,
             "T_C": [400, 500], "comparison_uses_fitting_data": True, "what": "PFR vs Table 1 conversions"}],
        "numerical_checks": ["KINR-ASPENFORM pass (6.2e-4 relative)", "Aspen vs Python cv/cs points pass"],
        "aspen_representation": "native LHHW; molarity basis in Phase 1 runs, exact partial-pressure basis added in Phase 2",
    },
]

UNMODELLED = [
    {"catalyst": "Ni/CeO2", "catalyst_id": None, "citekey": "lucentini2019ceo2",
     "reason": "lucentini2019ceo2 gives conversion curves and TOFs only (63 % at 450 degC, 1 atm, GHSV 3067 h-1, Ar:NH3 1.3:1); "
               "no rate equation, Ea, orders or pre-exponential factor. Phase 2 search found no complete published law for Ni/CeO2.",
     "experimental": {"T_C": [350, 600], "P_bar": [1.01325, 1.01325], "feed": "Ar:NH3 1.3:1", "space_velocity": "GHSV 3067 h-1, F/W 13.8 L h-1 g-1",
                      "conversion_range": None, "conversion_note": "63 % at 450 degC (text)"}},
    {"catalyst": "Ru/CeO2", "catalyst_id": None, "citekey": "lucentini2019ceo2",
     "reason": "as Ni/CeO2 (98 % at 450 degC in the same paper; no rate law). Phase 2 search found no complete published law.",
     "experimental": {"T_C": [350, 600], "P_bar": [1.01325, 1.01325], "feed": "Ar:NH3 1.3:1", "space_velocity": "GHSV 3067 h-1",
                      "conversion_range": None, "conversion_note": "98 % at 450 degC (text)"}},
    {"catalyst": "Ru-K/CaO", "catalyst_id": None, "citekey": "sayas2020rukcao",
     "reason": "full text and SI not obtainable by automated access (HTTP 403 / connection closed, 23 Nov 2026, Phase 1 and Phase 2); "
               "the abstract gives conditions (1-40 bar, 250-550 degC, WHSV 9000-30000 mL g-1 h-1) but no pre-exponential factor; "
               "no parameter is estimated.",
     "experimental": {"T_C": [250, 550], "P_bar": [1.0, 40.0], "feed": "not verified", "space_velocity": "WHSV 9000-30000 mL g-1 h-1 (abstract)",
                      "conversion_range": None, "conversion_note": "about 80 % at 550 degC, 40 bar (abstract; conditions not verified)"}},
]


def classify(law: dict) -> tuple[str, str]:
    passed = [c for c in law["literature_comparisons"] if c["status"] in ("pass", "pass_informational")]
    lo, hi = AMCRAX["T_C_operating_points"]
    rel = [c for c in passed if max(c.get("P_bar_range", [c["P_bar"]])) >= RELEVANT_P_MIN_BAR
           and c["T_C"][1] >= lo and c["T_C"][0] <= hi]
    if rel:
        return "validated_at_relevant_conditions", "passed comparison at >= 15 bar in the operating window"
    if passed:
        pmax = max(max(c.get("P_bar_range", [c["P_bar"]])) for c in passed)
        return ("validated_against_literature",
                f"passed comparison with published data only up to {pmax:g} bar (" +
                ", ".join(c["id"] for c in passed) + "); 20 bar use is a pressure extrapolation" +
                ("; the comparison uses the law's own fitting data (consistency check)" if all(
                    c["comparison_uses_fitting_data"] for c in passed) else ""))
    failed = [c["id"] + f" fail {c['observed']} > {c['tolerance']}" for c in law["literature_comparisons"]]
    return "extrapolated", "no passing comparison with published data (" + "; ".join(failed) + "); fitted at 1 atm"


def main() -> int:
    rows = []
    for law in LAWS:
        cls, why = classify(law)
        rng = _rng(law["catalyst_id"])
        p20_out = not (rng["P_bar"][0] <= AMCRAX["P_bar"] <= rng["P_bar"][1])
        t_out = [t for t in (AMCRAX["T_C_studies"] + AMCRAX["T_C_operating_points"])
                 if not (rng["T_C"][0] <= t <= rng["T_C"][1])]
        rows.append({**law, "class": cls, "class_evidence": why,
                     "fitted_range": rng, "domain_warning": {
                         "pressure_extrapolated_at_20_bar": p20_out,
                         "temperatures_outside_fitted_range_C": sorted(set(t_out)),
                         "rule": "warn when P_bar outside fitted_range.P_bar or T_C outside fitted_range.T_C"},
                     "evidence_kinds_available": sorted({"literature_comparison"} | {"numerical_verification"} |
                                                        ({"python_vs_aspen"} if "ASPEN" in " ".join(law["numerical_checks"]).upper() else set())),
                     "experimental_validation": False})
    for u in UNMODELLED:
        rows.append({**u, "class": "unmodelled", "class_evidence": u["reason"], "fitted_range": None,
                     "domain_warning": {"pressure_extrapolated_at_20_bar": None, "temperatures_outside_fitted_range_C": None,
                                        "rule": "no model: nothing to evaluate"},
                     "evidence_kinds_available": [], "experimental_validation": False})
    for r in rows:
        assert r["class"] in CLASSES
    counts = {c: sum(r["class"] == c for r in rows) for c in CLASSES}
    out = {
        "provenance": {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "script": "scripts/research/kinetics_validity_classification.py",
                       "source_type": "literature (ranges) + classification rule (this script)",
                       "inputs_summary": "backend/amcrax/data/kinetics.yaml validity fields; research/notes/*; "
                                         "results/research/validation/kinetics.json statuses",
                       "model_versions": {"kinetics_registry": "backend/amcrax/data/kinetics.yaml"}},
        "classes": CLASSES, "rule": classify.__doc__ or __doc__.strip().split("\n\n")[1],
        "amcrax_conditions": AMCRAX, "relevant_pressure_min_bar": RELEVANT_P_MIN_BAR,
        "counts": counts,
        "statement": "No AmCraX kinetic law is validated at 20 bar. Every kinetic result at 20 bar is a pressure "
                     "extrapolation; Takahashi laws are additionally unvalidated at 1 atm (failed figure predictions).",
        "laws": rows,
    }
    with open(os.path.join(OUT, "validity_classification.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    cols = ["catalyst", "catalyst_id", "citekey", "class", "fitted_T_C_min", "fitted_T_C_max", "fitted_P_bar_min",
            "fitted_P_bar_max", "pressure_extrapolated_at_20_bar", "h2_inhibition", "reversibility", "class_evidence"]
    with open(os.path.join(OUT, "validity_classification.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            fr = r["fitted_range"] or {"T_C": [None, None], "P_bar": [None, None]}
            w.writerow({"catalyst": r["catalyst"], "catalyst_id": r["catalyst_id"], "citekey": r["citekey"],
                        "class": r["class"], "fitted_T_C_min": fr["T_C"][0], "fitted_T_C_max": fr["T_C"][1],
                        "fitted_P_bar_min": fr["P_bar"][0], "fitted_P_bar_max": fr["P_bar"][1],
                        "pressure_extrapolated_at_20_bar": r["domain_warning"]["pressure_extrapolated_at_20_bar"],
                        "h2_inhibition": r.get("h2_inhibition", ""), "reversibility": r.get("reversibility", ""),
                        "class_evidence": r["class_evidence"]})
    for r in rows:
        print(f"{r['catalyst']:16s} {r['class']}")
    print(counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
