"""Phase 2 (task K1) validation items and evidence kinds for results/research/validation/{kinetics,aspen_kinetic}.json.

* Gives EVERY item in both files an ``evidence_kind`` (numerical_verification | python_vs_aspen |
  literature_comparison). AmCraX has no experimental validation, so that kind is never assigned.
* Appends the Phase 2 items (id prefix ``K1P2-`` in kinetics.json, ``k1p2_`` in aspen_kinetic.json); existing items,
  statuses and tolerances are not changed. Idempotent: earlier Phase 2 items are replaced on each run.
* Called at the end of scripts/research/kinetics_validation.py and aspen/automation/summarise_catalyst_studies.py,
  so a regeneration of either file keeps the evidence kinds and the Phase 2 items. Run from the AmCraX root.
"""
from __future__ import annotations

import glob
import json
import os
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
VAL = os.path.join(ROOT, "results", "research", "validation")
KIN = os.path.join(ROOT, "results", "research", "kinetics")
AK = os.path.join(ROOT, "results", "research", "aspen_kinetic")
EQ_MARGIN, X_TOL = 1e-4, 0.005          # same tolerances as aspen/automation/summarise_catalyst_studies.py
EVIDENCE_KINDS = ("numerical_verification", "python_vs_aspen", "literature_comparison")
LUC = {"nire_ceo2_5ni1ru_lucentini_lhhw": "5Ni1Ru/CeO2 (Lucentini)",
       "nire_ceo2_2p5ni0p5ru_lucentini_lhhw": "2.5Ni0.5Ru/CeO2 (Lucentini)"}


def _prov(inputs: str, source_type: str) -> dict:
    return {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "script": "scripts/research/kinetics_phase2_validation.py", "source_type": source_type,
            "inputs_summary": inputs, "model_versions": {"aspen": "Aspen Plus V15 (PENG-ROB)",
                                                          "python": "amcrax.reactor.pfr / amcrax.thermodynamics"}}


def evidence_kind_kinetics(it: dict) -> str:
    i = it["id"]
    if i.startswith(("KINR-ASPENFORM", "KINR-ASPENAPPROX", "EXISTING-KIN-TABLE2")) or i.startswith("K1P2-TAKAHASHI-REIMPL"):
        return "numerical_verification"
    return "literature_comparison"


def evidence_kind_aspen(it: dict) -> str:
    ref = str(it.get("reference_source", "")).lower()
    if "python" in ref:
        return "python_vs_aspen"
    return "numerical_verification"   # Aspen against Aspen (RGibbs in the same model, stored RGibbs flowsheet, run status)


# ------------------------------------------------------------------------------------------------- kinetics.json
def kinetics_items() -> list[dict]:
    items = []
    p = os.path.join(KIN, "takahashi_rederivation.json")
    if os.path.exists(p):
        d = json.load(open(p, encoding="utf-8"))
        for cid, tag, old in (("ni_takahashi_microkinetic", "NI", 0.1096), ("ru_takahashi_microkinetic", "RU", 0.1113)):
            r = d["results"][cid]
            diff = r["A_reproduces_stored_validation_max_abs_diff"]
            items.append({"id": f"K1P2-TAKAHASHI-REIMPL-{tag}", "description": f"independent re-implementation of "
                          f"takahashi2016kinetic Eqs. 5-19 ({cid}) reproduces the stored Phase 1 predictions",
                          "method": "QSS coverages + isothermal PFR written without amcrax.reactor; Table 1 parameters; "
                                    "same anchor point; max |X_reimpl - X_stored| over all figure points",
                          "reference_source": "results/validation/kinetics_validation.csv (stored model column)",
                          "observed": diff, "expected": 0.0, "tolerance": 1e-6, "unit": "conversion (fraction)",
                          "status": "pass" if diff <= 1e-6 else "fail",
                          "source_files": ["results/research/kinetics/takahashi_rederivation.json"],
                          "note": "no implementation error in units (mol/(g s) -> x1000), basis (mole fractions p_i/p_total "
                                  "at 1 atm) or reactor equations: the failure of EXISTING-KIN-%s-PRED is not an "
                                  "AmCraX coding error" % tag,
                          "provenance": _prov("results/research/kinetics/takahashi_rederivation.json", "python")})
            var = {v: {"max_abs_deviation": e["max_abs_deviation"], "n_outside_0.05": e["n_outside_0.05"],
                       "rms": e["rms_deviation"]} for v, e in r.items() if isinstance(e, dict)}
            items.append({"id": f"K1P2-TAKAHASHI-BASIS-{tag}", "description": "the basis choices the paper leaves open "
                          "(SV on total vs NH3 flow; Table 1 vs Table 2 constants; T+273 vs T+273.15) do not remove the "
                          f"prediction failure ({cid})",
                          "method": "same re-implementation, one anchor point per variant, no fitting",
                          "reference_source": "takahashi2016kinetic Figs. 3-5 (read from figures, +/-2 pp)",
                          "observed": min(v["max_abs_deviation"] for v in var.values()), "expected": None,
                          "tolerance": 0.05, "unit": "max |deviation| (absolute conversion), best variant",
                          "status": "informational", "variants": var,
                          "source_files": ["results/research/kinetics/takahashi_rederivation.json"],
                          "note": f"original failure value {old} is unchanged (KIN-{tag}-PRED stays fail). Cause: a real "
                                  "limit of the published law as reproducible from the paper (catalyst mass not reported, "
                                  "W/F inferred from one anchor; dilution and H2 co-feed series under-predicted by up to "
                                  "0.11 even with the paper's own Table 2 constants)",
                          "provenance": _prov("results/research/kinetics/takahashi_rederivation.json", "python")})
    p = os.path.join(KIN, "validity_classification.json")
    if os.path.exists(p):
        d = json.load(open(p, encoding="utf-8"))
        items.append({"id": "K1P2-VALIDITY-CLASSIFICATION", "description": "kinetic validity class at 20 bar for every "
                      "registry law and every catalyst named by the author",
                      "method": "rule in scripts/research/kinetics_validity_classification.py applied to fitted ranges "
                                "and check statuses", "reference_source": "kinetics.yaml validity; research/notes",
                      "observed": d["counts"], "expected": None, "tolerance": None, "unit": "count per class",
                      "status": "informational", "source_files": ["results/research/kinetics/validity_classification.json"],
                      "note": d["statement"],
                      "provenance": _prov("results/research/kinetics/validity_classification.json", "literature")})
    items.append({"id": "K1P2-SEARCH-MISSING-KINETICS", "description": "Phase 2 search for complete published rate laws: "
                  "Ni/CeO2, Ru/CeO2, Ru-K/CaO (Sayas 2020 and follow-ups), any law fitted at 5-40 bar",
                  "method": "web search and publisher/repository fetch, 23 November 2026",
                  "reference_source": "research/reference_additions/phase2_kinetics.json",
                  "observed": "no usable complete law found", "expected": None, "tolerance": None, "unit": "-",
                  "status": "informational", "source_files": ["research/notes/phase2_kinetics_search.md"],
                  "note": "Sayas 2020 publisher HTML/PDF HTTP 403, SI connection closed; no parameter was estimated. Update 24 Nov 2026: "
                          "the Sayas main text was read from a copy supplied by the user; it has no rate constant (supplementary "
                          "information only, not obtained), so still no usable complete law"})
    # addendum of 24 November 2026: Sayas et al. 2020 measured conversions (not used by any model) and the cross-catalyst caution
    p = os.path.join(KIN, "validity_classification.json")
    if os.path.exists(p):
        d = json.load(open(p, encoding="utf-8"))
        sp, cx = d.get("literature_comparison_points_sayas2020"), d.get("cross_catalyst_context_sayas2020")
        if sp:
            items.append({"id": "K1P2-SAYAS-POINTS", "description": "Sayas et al. 2020: 15 measured conversions of 3%Ru10%K/CaO at 10, "
                          "20 and 40 bar, 350-550 degC, stored as literature comparison points; NOT used by any model, fit or rule",
                          "method": "figure reading of Fig. 4A (+/-2 points); pure NH3, 30 N mL/min over 200 mg ('N mL' reference "
                                    "state not defined, about 9 % in F)",
                          "reference_source": "sayas2020rukcao p. 5032 Fig. 4A", "observed": sp["n_points"], "expected": 15,
                          "tolerance": None, "unit": "points", "status": "informational",
                          "source_files": ["results/research/kinetics/validity_classification.json", "research/data/sayas2020_extract.json"],
                          "note": "Ru-K/CaO stays unmodelled; these points cannot test any AmCraX law (no Ru-K/CaO law exists)",
                          "provenance": _prov("results/research/kinetics/validity_classification.json", "literature")})
        if cx:
            h = cx["headline_20bar_500C"]
            items.append({"id": "K1P2-SAYAS-RUAL2O3-CONTEXT", "description": "caution, cross-catalyst context comparison (not a test of "
                          "the law): the AmCraX Ru/Al2O3 law (fitted at 1-10 bar) at the Sayas conditions with equal ruthenium per "
                          "mol NH3, against the measured Ru-K/CaO conversion at 20 bar and 500 degC",
                          "method": "isothermal PFR with ru_kum_temkin_pyzhev at W(Ru/Al2O3) giving the Sayas g Ru h/mol NH3, both "
                                    "flow reference states (0 and 25 degC)", "reference_source": "sayas2020rukcao Fig. 4A",
                          "observed": h["X_RuAl2O3_law_equal_Ru"], "expected": h["X_measured_RuK_CaO"], "tolerance": None,
                          "unit": "conversion (fraction)", "status": "informational",
                          "source_files": ["results/research/kinetics/validity_classification.json"],
                          "note": "different catalysts (support, K promoter, dispersion); the pressure-extrapolated Ru/Al2O3 law converts "
                                  "far more per gram of Ru than this measured Ru catalyst at 20 bar, a reason to keep the Ru/Al2O3 20 bar "
                                  "results labelled as extrapolation; not evidence under the verdict rules",
                          "provenance": _prov("results/research/kinetics/validity_classification.json", "python")})
    return items


# --------------------------------------------------------------------------------------------- aspen_kinetic.json
def aspen_items() -> list[dict]:
    items = []
    runs = {}
    for f in sorted(glob.glob(os.path.join(AK, "cpp_*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        if d.get("run_status") not in ("ok", "ok_with_warnings"):
            continue
        a = d["aspen"]
        eq = a.get("equilibrium_reference")
        if not eq:
            continue
        runs.setdefault(d["inputs"]["reactor"]["catalyst_id"], []).append({
            "file": os.path.relpath(f, ROOT).replace("\\", "/"), "case_id": d["case_id"],
            "iso": d["inputs"]["reactor"]["thermal_mode"] == "isothermal",
            "X": a["conversion_of_reactor_inlet_NH3"], "Xeq": eq["conversion_of_reactor_inlet_NH3"],
            "Xpy": (d.get("python_pfr") or {}).get("outlet", {}).get("conversion")})
    for cid, lbl in LUC.items():
        rs = runs.get(cid) or []
        if not rs:
            continue
        w = max(rs, key=lambda r: r["X"] - r["Xeq"])
        exc = w["X"] - w["Xeq"]
        over = [r["case_id"] for r in rs if r["X"] - r["Xeq"] > EQ_MARGIN]
        items.append({"id": f"k1p2_{cid}_below_equilibrium_partialpres", "description": f"{lbl}, exact partial-pressure "
                      f"form (Phase 2): no RPLUG run above RGibbs equilibrium (same model, same feed), {len(rs)} runs",
                      "method": "max(X_rplug - X_rgibbs) <= 1e-4 (same check and tolerance as "
                                f"cat_{cid}_below_equilibrium)", "reference_source": "aspen RGibbs block REQ in the same model",
                      "observed": exc, "expected": 0.0, "tolerance": EQ_MARGIN, "unit": "-",
                      "status": "pass" if exc <= EQ_MARGIN else "fail", "source_files": [w["file"]],
                      "note": ("runs above by more than 1e-4: %s. Remaining excess = PENG-ROB fugacity correction, not "
                               "representable in Aspen's built-in LHHW concentration bases (see "
                               "k1p2_*_cause items)" % over) if over else "all runs within 1e-4",
                      "provenance": _prov("results/research/aspen_kinetic/cpp_*.json", "aspen")})
        iso = [r for r in rs if r["iso"] and r["Xpy"] is not None]
        if iso:
            wp = max(iso, key=lambda r: abs(r["X"] - r["Xpy"]))
            dx = abs(wp["X"] - wp["Xpy"])
            items.append({"id": f"k1p2_{cid}_partialpres_vs_python", "description": f"{lbl}, partial-pressure form: "
                          f"largest |X_aspen - X_python| over {len(iso)} isothermal runs",
                          "method": "|X_aspen - X_python| <= 0.005", "reference_source":
                          "python model amcrax.reactor.pfr at identical conditions", "observed": dx, "expected": 0.0,
                          "tolerance": X_TOL, "unit": "-", "status": "pass" if dx <= X_TOL else "fail",
                          "source_files": [wp["file"]],
                          "provenance": _prov("results/research/aspen_kinetic/cpp_*.json", "aspen vs python")})
    p = os.path.join(KIN, "equilibrium_consistency.json")
    if os.path.exists(p):
        d = json.load(open(p, encoding="utf-8"))
        grid = _aspen_ideal_minus_pr()
        by_item = {}
        for r in d["rows"]:
            if r["fails_1e-4_check"]:
                by_item.setdefault(r["catalyst_id"], []).append(r)
        for cid, rs in by_item.items():
            w = max(rs, key=lambda r: r["excess_aspen"])
            z_part = w["X_stop_kinetic_predicted"] - w["X_eq_ideal_python"]
            phi_aspen = grid.get((w["T_C"], w["P_bar"]))
            pred = z_part + (phi_aspen if phi_aspen is not None else float("nan"))
            items.append({"id": f"k1p2_{cid}_below_equilibrium_cause", "description": f"quantitative cause of the "
                          f"failure cat_{cid}_below_equilibrium (worst run {w['case_id']})",
                          "method": "excess = (X_stop - X_eq,ideal) [driving-force basis: MOLARITY uses Z from PENG-ROB "
                                    "against an ideal-gas Kc; MOLEFRAC/PARTIALPRES give 0] + (X_eq,ideal - X_eq,PENG-ROB) "
                                    "[fugacity correction K_phi, from the stored Aspen RGibbs IDEAL vs PENG-ROB grid]",
                          "reference_source": "aspen RGibbs grid results/validation/equilibrium_aspen_grid.csv; "
                                              "python amcrax.thermodynamics (PR, k_ij = 0)",
                          "observed": w["excess_aspen"], "expected": pred, "tolerance": None, "unit": "conversion",
                          "status": "informational",
                          "components": {"compressibility_part": z_part, "Z_PR_at_stop": w["Z_PR_at_stop"],
                                         "fugacity_part_aspen_ideal_minus_pr": phi_aspen,
                                         "K_phi_python_PR_kij0": w["K_phi_PR"],
                                         "fugacity_part_python_PR_kij0": w["X_eq_ideal_python"] - w["X_eq_PR_python"],
                                         "rplug_minus_predicted_stop": w["rplug_minus_predicted_stop"],
                                         "concentration_basis": w["concentration_basis"]},
                          "source_files": ["results/research/kinetics/equilibrium_consistency.json",
                                           "results/validation/equilibrium_aspen_grid.csv"],
                          "note": "the original failure item is kept unchanged. The ideal-gas K in the reverse term "
                                  "explains the fugacity part" + (
                                      "; the MOLARITY basis (concentrations from the PENG-ROB Z against an ideal-gas Kc) "
                                      "the compressibility part" if w["concentration_basis"] == "MOLARITY" else
                                      "; with the mole-fraction basis there is no compressibility part, so the whole "
                                      "excess is the fugacity correction") +
                                  ". The remainder (observed - expected) is the ln Kp fit and Aspen's ideal-gas Kp vs "
                                  "AmCraX NASA7. Python PR with k_ij = 0 over-predicts the fugacity part (Aspen uses "
                                  "PRKBV k_ij from EOS-LIT), so the Aspen IDEAL vs PENG-ROB RGibbs grid is used",
                          "provenance": _prov("results/research/kinetics/equilibrium_consistency.json", "python")})
    return items


def _aspen_ideal_minus_pr() -> dict:
    import csv
    p = os.path.join(ROOT, "results", "validation", "equilibrium_aspen_grid.csv")
    if not os.path.exists(p):
        return {}
    g = {}
    for r in csv.DictReader(open(p, encoding="utf-8")):
        g.setdefault((float(r["T_C"]), float(r["P_bar"])), {})[r["property_method"]] = float(r["nh3_conversion"])
    return {k: v["IDEAL"] - v["PENG-ROB"] for k, v in g.items() if "IDEAL" in v and "PENG-ROB" in v}


def _update(path: str, prefix: str, new: list[dict], kind) -> dict:
    data = json.load(open(path, encoding="utf-8"))
    data = [i for i in data if not str(i.get("id", "")).startswith(prefix)] + new
    for i in data:
        i["evidence_kind"] = kind(i)
        assert i["evidence_kind"] in EVIDENCE_KINDS
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return {s: sum(i["status"] == s for i in data) for s in ("pass", "fail", "informational")}


def apply(which: tuple[str, ...] = ("kinetics", "aspen_kinetic")) -> dict:
    out = {}
    if "kinetics" in which:
        out["kinetics"] = _update(os.path.join(VAL, "kinetics.json"), "K1P2-", kinetics_items(), evidence_kind_kinetics)
    if "aspen_kinetic" in which:
        out["aspen_kinetic"] = _update(os.path.join(VAL, "aspen_kinetic.json"), "k1p2_", aspen_items(), evidence_kind_aspen)
    return out


if __name__ == "__main__":
    print(json.dumps(apply(), indent=1))
