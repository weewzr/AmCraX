"""Build the four-hypothesis research evidence matrix (H1-H4).

Reads every number from the stored research result files and writes

    results/research/evidence_matrix.json   (contract shared with the website and report)
    docs/research/evidence_matrix.md        (human-readable, generated from the JSON)

Rules followed here:
- No number is typed in this script. Every value in ``numerical_findings`` is read with
  :func:`resolve` from a named file and key, and text that quotes a number formats a value that
  was read the same way. A missing file or key raises :class:`EvidenceError` (fail loudly).
- Verdict logic is explicit and conservative. Each row carries the rule that produced its verdict
  in ``conclusion_conditions``. A row is SUPPORTED only within stated conditions and only when the
  evidence is computed rather than an assumption built into the model; evidence that is
  model-form limited, extrapolated, or inside the uncertainty band gives INCONCLUSIVE.
- Verdicts follow methodology version 2 (docs/research/verdict_methodology_v2.md): each row has a role
  (primary rows vote, secondary rows do not) and belongs to a component. Row verdicts are SUPPORTED,
  CONTRADICTED or INCONCLUSIVE and are derived by the coded rules v2_h1a to v2_h4e. Component verdicts
  (component_verdict, COMPONENT_RULE) and hypothesis verdicts (hypothesis_verdict_v2, HYPOTHESIS_RULE_V2)
  add MIXED and PARTIALLY SUPPORTED. The version 1 rule (HYPOTHESIS_RULE: SUPPORTED only if every row is
  SUPPORTED) and the version 1 verdicts are kept beside them for comparison only.
- Disclosure (DISCLOSURES, printed in the matrix): only the roles, components, aggregation and generic row
  standard were fixed before the analyses; the row-specific rules were written after the results and were
  tightened in the fix pass of 24 November 2026 after an independent adversarial review.

Key syntax (``key`` field): a JSON-pointer-like path separated by "/" ("~1" encodes a literal "/",
"~0" a literal "~"). A segment ``[a=b;c=d]`` selects the single list element whose fields match
(numbers compared as floats); an integer segment indexes a list. For CSV files the first
segment selects a row the same way and the second names the column.

Run from the project root:  python scripts/research/build_evidence_matrix.py
"""
from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_JSON = "results/research/evidence_matrix.json"
OUT_MD = "docs/research/evidence_matrix.md"
SCRIPT = "scripts/research/build_evidence_matrix.py"
VERDICTS = ("SUPPORTED", "CONTRADICTED", "INCONCLUSIVE")
SOURCE_TYPES = ("aspen", "python", "literature", "assumption")
P_ROBUST = 0.05  # method threshold (not a result): Monte Carlo probability below which an outcome counts as robust
HYPOTHESIS_RULE = (
    "Hypothesis verdict from its rows: SUPPORTED if every row is SUPPORTED; CONTRADICTED if no row is "
    "SUPPORTED and at least half of the rows are CONTRADICTED; otherwise INCONCLUSIVE, with the mixed "
    "row outcomes stated in verdict_conditions."
)

# Result files (repo-relative)
F_ENDUSE = "results/research/enduse/enduse_results.json"
F_LCA = "results/research/lca/lca_results.json"
F_SCEN = "results/research/singapore/scenario_results.json"
F_BE = "results/research/singapore/breakeven_ammonia_price.json"
F_TOR = "results/research/singapore/tornado.json"
F_MC = "results/research/singapore/monte_carlo.json"
F_CAP = "results/research/singapore/cost_vs_capacity.csv"
F_BENCH = "results/research/singapore/benchmarks.json"
F_CAT = "results/research/catalyst_comparison/catalyst_comparison.json"
F_CHO = "results/research/catalyst_comparison/catalyst_cho_comparison.json"
F_ACAT = "results/research/aspen_kinetic/catalyst_comparison.json"
F_KT = "results/research/kinetics/study_temperature_for_target_conversion.json"
F_PUR = "results/research/purification/purification_study.json"
F_VAL = "results/research/validation/{}.json"
F_MANIFEST = "docs/images/aspen_evidence/manifest.json"
REF_FILES = ["research/references.json"]
REF_ADDITIONS_GLOB = "research/reference_additions/*.json"


class EvidenceError(RuntimeError):
    """A result file or key the matrix depends on is missing or unusable."""


# --------------------------------------------------------------------------------------------
# File access
# --------------------------------------------------------------------------------------------
_CACHE: dict[str, object] = {}
_USED_FILES: set[str] = set()


def load(rel: str):
    if rel in _CACHE:
        return _CACHE[rel]
    path = ROOT / rel
    if not path.is_file():
        raise EvidenceError(f"missing result file: {rel}")
    if rel.endswith(".csv"):
        with path.open(newline="", encoding="utf-8") as fh:
            data = list(csv.DictReader(fh))
    else:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    _CACHE[rel] = data
    _USED_FILES.add(rel)
    return data


def _split_key(key: str) -> list[str]:
    segs = [s for s in key.strip("/").split("/")]
    return [s.replace("~1", "/").replace("~0", "~") for s in segs]


def _match(value, want: str) -> bool:
    if isinstance(value, bool):
        return str(value).lower() == want.lower()
    if isinstance(value, (int, float)):
        try:
            return float(value) == float(want)
        except ValueError:
            return False
    if isinstance(value, str):
        if value == want:
            return True
        try:
            return float(value) == float(want)
        except ValueError:
            return False
    return False


def resolve(rel: str, key: str):
    """Return the value at ``key`` in result file ``rel``; raise EvidenceError if absent."""
    node = load(rel)
    for seg in _split_key(key):
        if seg.startswith("[") and seg.endswith("]"):
            if not isinstance(node, list):
                raise EvidenceError(f"{rel}: selector {seg} applied to a non-list in key {key}")
            conds = [c.split("=", 1) for c in seg[1:-1].split(";")]
            hits = [e for e in node if isinstance(e, dict)
                    and all(k in e and _match(e[k], v) for k, v in conds)]
            if len(hits) != 1:
                raise EvidenceError(f"{rel}: selector {seg} matched {len(hits)} elements (key {key})")
            node = hits[0]
        elif isinstance(node, list):
            try:
                node = node[int(seg)]
            except (ValueError, IndexError) as exc:
                raise EvidenceError(f"{rel}: bad list index {seg} in key {key}") from exc
        elif isinstance(node, dict):
            if seg not in node:
                raise EvidenceError(f"{rel}: key segment '{seg}' not found (key {key})")
            node = node[seg]
        else:
            raise EvidenceError(f"{rel}: cannot descend into scalar at '{seg}' (key {key})")
    return node


def as_number(value, rel: str, key: str) -> float:
    if isinstance(value, bool) or value is None:
        raise EvidenceError(f"{rel}: value at {key} is not numeric ({value!r})")
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise EvidenceError(f"{rel}: value at {key} is not numeric ({value!r})") from exc


def esc(seg: str) -> str:
    return seg.replace("~", "~0").replace("/", "~1")


class Row:
    """Collects numerical findings for one row; each value is read from its file."""

    def __init__(self):
        self.findings: list[dict] = []

    def num(self, quantity: str, rel: str, key: str, unit: str, source_type: str) -> float:
        if source_type not in SOURCE_TYPES:
            raise EvidenceError(f"bad source_type {source_type}")
        value = as_number(resolve(rel, key), rel, key)
        self.findings.append({"quantity": quantity, "value": value, "unit": unit,
                              "source_type": source_type, "source_file": rel, "key": key})
        return value


def val(rel: str, key: str) -> float:
    """Read a number used only inside logic or text (not listed as a finding)."""
    return as_number(resolve(rel, key), rel, key)


def f(x: float, nd: int = 2) -> str:
    return f"{x:.{nd}f}"


def pct(x: float, nd: int = 1) -> str:
    return f"{100.0 * x:.{nd}f} %"


# --------------------------------------------------------------------------------------------
# Validation status, references, screenshots
# --------------------------------------------------------------------------------------------
def validation_status(area: str) -> dict:
    rel = F_VAL.format(area)
    data = load(rel)
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise EvidenceError(f"{rel}: no list of validation items")
    counts = {"pass": 0, "fail": 0, "informational": 0, "not_available": 0}
    failures = []
    for it in items:
        st = it.get("status")
        if st not in counts:
            raise EvidenceError(f"{rel}: unknown status {st!r} in item {it.get('id')}")
        counts[st] += 1
        if st == "fail":
            failures.append(it.get("id"))
    return {"file": rel, **counts, "failures": failures}


def validation_text(areas: list[str]) -> tuple[str, list[dict]]:
    stats = [validation_status(a) for a in areas]
    parts = []
    for s in stats:
        t = f"{s['file']}: {s['pass']} pass, {s['fail']} fail, {s['informational']} informational"
        if s["not_available"]:
            t += f", {s['not_available']} not available"
        if s["failures"]:
            t += " (failures: " + ", ".join(s["failures"]) + ")"
        parts.append(t)
    return "; ".join(parts), stats


_REFKEYS: set[str] | None = None


def ref_keys() -> set[str]:
    global _REFKEYS
    if _REFKEYS is None:
        keys = set()
        files = REF_FILES + sorted(str(p.relative_to(ROOT)).replace("\\", "/")
                                   for p in ROOT.glob(REF_ADDITIONS_GLOB))
        for rel in files:
            for entry in load(rel):
                k = entry.get("citekey") or entry.get("key")
                if k:
                    keys.add(k)
        _REFKEYS = keys
    return _REFKEYS


def lit(*pairs: tuple[str, str]) -> list[dict]:
    out = []
    for key, label in pairs:
        if key not in ref_keys():
            raise EvidenceError(f"reference key not in research/references.json or reference_additions: {key}")
        out.append({"key": key, "label": label})
    return out


def screenshots(case_ids: list[str]) -> list[str]:
    man = load(F_MANIFEST)
    caps = man.get("captures", [])
    out = []
    for c in caps:
        if c.get("case_id") in case_ids:
            rel = "docs/images/aspen_evidence/" + c["file"]
            if not (ROOT / rel).is_file():
                raise EvidenceError(f"manifest lists a screenshot that does not exist: {rel}")
            out.append(rel)
    return out


def checked_paths(paths: list[str]) -> list[str]:
    for p in paths:
        if not (ROOT / p).is_file():
            raise EvidenceError(f"linked file does not exist: {p}")
    return paths


def make_row(row_id, sub_claim, verdict, *, rowobj: Row, singapore_scenario, aspen_model, python_model,
             case_ids, input_assumptions, literature, validation_areas, validation_method,
             uncertainty_range, key_uncertainty, limitations, conclusion, conclusion_conditions,
             data, figures, shots):
    if verdict not in VERDICTS:
        raise EvidenceError(f"{row_id}: bad verdict {verdict}")
    vtext, vstats = validation_text(validation_areas)
    files = sorted({x["source_file"] for x in rowobj.findings})
    return {
        "row_id": row_id,
        "sub_claim": sub_claim,
        "verdict": verdict,
        "singapore_scenario": singapore_scenario,
        "aspen_model": aspen_model,
        "python_model": python_model,
        "case_ids": case_ids,
        "input_assumptions": input_assumptions,
        "literature": literature,
        "validation_method": validation_method + " Validation status of the underlying models: " + vtext + ".",
        "validation_status": vstats,
        "numerical_findings": rowobj.findings,
        "uncertainty_range": uncertainty_range,
        "key_uncertainty": key_uncertainty,
        "limitations": limitations,
        "conclusion": conclusion,
        "conclusion_conditions": conclusion_conditions,
        "provenance": ("Values read by " + SCRIPT + " from " + ", ".join(files)
                       + "; verdict logic in the same script (function for " + row_id + ")."),
        "links": {"data": checked_paths(sorted(set(files + data))),
                  "figures": checked_paths(figures), "screenshots": shots},
    }


def hypothesis_verdict(rows: list[dict]) -> str:
    v = [r["verdict"] for r in rows]
    if all(x == "SUPPORTED" for x in v):
        return "SUPPORTED"
    if "SUPPORTED" not in v and v.count("CONTRADICTED") * 2 >= len(v):
        return "CONTRADICTED"
    return "INCONCLUSIVE"


def mixed_text(rows: list[dict]) -> str:
    groups = {k: [r["row_id"] for r in rows if r["verdict"] == k] for k in VERDICTS}
    return "; ".join(f"{k}: {', '.join(ids)}" for k, ids in groups.items() if ids)


# --------------------------------------------------------------------------------------------
# H1 End use
# --------------------------------------------------------------------------------------------
PW = "power_pathways/[id={}]/{}"
HZ = "hydrogen_pathways/[id={}]/{}"
class _Halim:
    T = "halim_claim_check/computed/[basis={};cracking_pathway={}]/" + esc("direct_cheaper_by_pct_of_cracking(1-d/c)")

    def format(self, basis: str, pathway: str) -> str:
        return self.T.format(esc(basis), pathway)


HALIM = _Halim()
BASIS_SG = "AmCraX price set (450 USD/t, 8000 h)"
BASIS_AHMAD = "Ahmad basis (480 USD/t, 7200 h)"
BASIS_GREEN = "renewable NH3 today (1000 USD/t)"
SG_POWER = ("Jurong Island representative power plant burning imported NH3; common reference NH3 price "
            "from the Singapore price set (grey), operating hours, Singapore electricity and carbon tax inputs "
            "as in price_set of enduse_results.json")


def h1_rows() -> list[dict]:
    rows = []
    enduse_figs = ["results/figures/research/enduse_power_cost_vs_ci.png",
                   "results/figures/research/enduse_power_cost_vs_price.png",
                   "results/figures/research/enduse_power_efficiency.png"]
    common_lit = lit(("ahmad2025gtcc", "Ahmad et al. 2025: NH3 and cracked-NH3 GTCC efficiencies and Case 2a cost basis"),
                     ("halim2025ammoniapower", "Halim et al. 2025 (abstract only): direct use preferred to cracking for power"))

    # H1-a direct vs standalone fired / purified cracking for power
    r = Row()
    d = r.num("LCOE direct NH3 CCGT", F_ENDUSE, PW.format("direct", "cost_USD_per_MWh_at_450"), "USD/MWh", "python")
    ff = r.num("LCOE full cracking, fired cracker", F_ENDUSE, PW.format("full_fired", "cost_USD_per_MWh_at_450"), "USD/MWh", "python")
    fp = r.num("LCOE full cracking + PSA H2", F_ENDUSE, PW.format("full_purified", "cost_USD_per_MWh_at_450"), "USD/MWh", "python")
    ed = r.num("NH3 LHV to electricity, direct", F_ENDUSE, PW.format("direct", "efficiency_NH3_LHV_to_electricity"), "fraction", "literature")
    ep = r.num("NH3 LHV to electricity, cracked + PSA H2", F_ENDUSE, PW.format("full_purified", "efficiency_NH3_LHV_to_electricity"), "fraction", "python")
    gf = r.num("direct cheaper than fired cracking, 1 - direct/cracking", F_ENDUSE, HALIM.format(BASIS_SG, "full_fired"), "%", "python")
    gp = r.num("direct cheaper than cracking + PSA, 1 - direct/cracking", F_ENDUSE, HALIM.format(BASIS_SG, "full_purified"), "%", "python")
    gpa = r.num("same, Ahmad basis", F_ENDUSE, HALIM.format(BASIS_AHMAD, "full_purified"), "%", "python")
    gpg = r.num("same, renewable NH3 at today's price", F_ENDUSE, HALIM.format(BASIS_GREEN, "full_purified"), "%", "python")
    sweep = load(F_ENDUSE)["price_sweep"]
    lo_p, hi_p = val(F_ENDUSE, "price_sweep/0/NH3_price_USD_t"), val(F_ENDUSE, f"price_sweep/{len(sweep) - 1}/NH3_price_USD_t")
    always = all(val(F_ENDUSE, f"price_sweep/{i}/direct") < min(val(F_ENDUSE, f"price_sweep/{i}/full_fired"),
                                                                val(F_ENDUSE, f"price_sweep/{i}/full_purified"))
                 for i in range(len(sweep)))
    cross_f = resolve(F_ENDUSE, "halim_claim_check/crossover_prices/full_fired_vs_direct")
    cross_p = resolve(F_ENDUSE, "halim_claim_check/crossover_prices/full_purified_vs_direct")
    # Final verification (integration phase): if the H2-rich-fuel turbine efficiency is the assumed copy of the
    # direct-NH3 efficiency, a fired or purified cracker can only add NH3 burn and capital, so the sign of the
    # comparison is fixed by that assumption and the row cannot be SUPPORTED.
    eta_gas = r.num("turbine efficiency on H2-rich fuel (copy of direct case)", "results/research/enduse/assumptions.json", "[name=eta_gt_gas]/value", "fraction", "assumption")
    eta_copied = abs(eta_gas - ed) < 1e-12
    computed_ok = always and cross_f is None and cross_p is None and gf > 0 and gp > 0
    verdict = "SUPPORTED" if (computed_ok and not eta_copied) else "INCONCLUSIVE"
    rows.append(make_row(
        "H1-a", "Where ammonia can be burned directly (power), direct NH3 combustion is cheaper than power from a standalone (fired) cracker or from cracked and purified hydrogen.",
        verdict, rowobj=r, singapore_scenario=SG_POWER,
        aspen_model="Stored Aspen Plus V15 baseline (results/simulations/baseline.json): cracker reactor and pre-heater duty, PSA heat deficit used as cracker heat; no Aspen combustion model.",
        python_model="amcrax.enduse.pathways power pathways (energy balance, Ahmad-scaled plant capital, amcrax.economics).",
        case_ids=["baseline (stored Aspen)", "direct", "full_fired", "full_purified"],
        input_assumptions=["Fired variants apply the direct-NH3 turbine efficiency to H2-rich fuel (assumption).",
                           "PSA recovery of the stored baseline (assumption) for the purified route.",
                           "Plant capital outside the cracker: Ahmad Case 2a scaled with plant power.",
                           "No NOx abatement cost; no combustion simulated."],
        literature=common_lit,
        validation_areas=["enduse"],
        validation_method="Energy balance closure of every power pathway; Ahmad Case 2a LCOE reproduced; Aspen LHV efficiency reproduced (results/research/validation/enduse.json).",
        uncertainty_range=f"Direct is cheaper by {f(gf,1)} % (fired) and {f(gp,1)} % (purified) at the common price; {f(gpa,1)} % (purified, Ahmad basis) and {f(gpg,1)} % (purified, renewable NH3 today). The ranking holds at every NH3 price of the sweep ({f(lo_p,0)}-{f(hi_p,0)} USD/t); no crossover price exists for these two pathways.",
        key_uncertainty="The fired-cracker efficiency (direct turbine efficiency applied to H2-rich fuel) and the cracker capital; a real H2-fired turbine efficiency gain large enough to exceed the cracker heat penalty would remove the fired-route gap.",
        limitations=load(F_ENDUSE)["limitations"],
        conclusion=f"Direct NH3 power costs {f(d,0)} USD/MWh against {f(ff,0)} (fired cracker) and {f(fp,0)} (cracked + PSA H2); efficiency {pct(ed)} against {pct(ep)} for the purified route. Direct use is cheaper at every swept NH3 price, but the sign of this result is set by the assumption that the turbine reaches the direct-NH3 efficiency ({pct(eta_gas)}) on H2-rich fuel: a fired or purified cracker can then only add NH3 burn and capital. The computed content is the size of the gap, not its sign.",
        conclusion_conditions=f"Rule: SUPPORTED only if direct is cheaper than both pathways at every NH3 price in the sweep, no crossover exists and the H2-rich-fuel turbine efficiency is not an assumed copy of the direct-NH3 efficiency; otherwise INCONCLUSIVE (here: {'efficiency copied, so the ranking reproduces an assumption' if eta_copied else 'efficiency independent'}). Conditions: AmCraX plant boundary, {f(val(F_ENDUSE, 'price_set/operating_hours'),0)} h/yr, no NOx abatement cost.",
        data=["results/research/enduse/pathway_table_power.csv", "results/research/enduse/price_sweep.csv"],
        figures=enduse_figs, shots=[]))

    # H1-b magnitude "about 40 % cheaper"
    r = Row()
    claim = r.num("essay/Halim claim: direct cheaper than cracking-based power", "results/research/validation/enduse.json", "[id=EU-halim-claim]/expected", "%", "literature")
    gaps = [r.num(f"computed gap, {b.split(' (')[0]}, {p}", F_ENDUSE, HALIM.format(b, p), "%", "python")
            for b in (BASIS_SG, BASIS_AHMAD, BASIS_GREEN) for p in ("full_exhaust", "full_fired", "full_purified")]
    gmax = max(gaps)
    verdict = "CONTRADICTED" if gmax < claim / 2 else "INCONCLUSIVE"
    rows.append(make_row(
        "H1-b", f"Direct NH3 combustion is about {f(claim,0)} % cheaper than cracking-based power (essay, citing Halim et al. 2025).",
        verdict, rowobj=r, singapore_scenario=SG_POWER,
        aspen_model="No Aspen combustion model; cracker duties from the stored Aspen baseline.",
        python_model="amcrax.enduse.pathways (halim_claim_check).",
        case_ids=["direct", "full_exhaust", "full_fired", "full_purified"],
        input_assumptions=["Same as H1-a; three price and operating-hour bases (AmCraX, Ahmad, renewable NH3 today)."],
        literature=common_lit,
        validation_areas=["enduse"],
        validation_method="Claim check against computed 1 - direct/cracking on three bases (validation item EU-halim-claim, informational because Halim's inputs were not accessed).",
        uncertainty_range=f"Largest computed gap {f(gmax,1)} % across {len(gaps)} basis/pathway combinations; smallest {f(min(gaps),1)} % (negative: cracking cheaper).",
        key_uncertainty="Halim's own inputs (full text not accessed): a purified-H2 turbine with a standalone fired cracker, a much higher cracker capital or a lower capacity factor could produce a larger gap.",
        limitations=["Halim et al. (2025) full text not accessible; the claimed figure is from the essay and the abstract-level record."],
        conclusion=f"Not reproduced: the computed cost advantage of direct use is at most {f(gmax,1)} % against the essay's {f(claim,0)} %; against an exhaust-heated cracker direct use is dearer.",
        conclusion_conditions="Rule: CONTRADICTED if the largest computed gap on any basis is below half the claimed value; otherwise INCONCLUSIVE. Holds on AmCraX boundaries; does not show that Halim's own calculation is wrong.",
        data=["results/research/enduse/claim_check_direct_vs_cracking.csv"],
        figures=["results/figures/research/enduse_power_cost_vs_price.png"], shots=[]))

    # H1-c exhaust-heated / partial cracking for power
    r = Row()
    fe = r.num("LCOE full cracking, exhaust-heated, unpurified", F_ENDUSE, PW.format("full_exhaust", "cost_USD_per_MWh_at_450"), "USD/MWh", "python")
    pe = r.num("LCOE partial cracking 40 vol% H2, exhaust-heated", F_ENDUSE, PW.format("partial_exhaust_40", "cost_USD_per_MWh_at_450"), "USD/MWh", "python")
    pf = r.num("LCOE partial cracking 40 vol% H2, fired", F_ENDUSE, PW.format("partial_fired_40", "cost_USD_per_MWh_at_450"), "USD/MWh", "python")
    d2 = r.num("LCOE direct NH3", F_ENDUSE, PW.format("direct", "cost_USD_per_MWh_at_450"), "USD/MWh", "python")
    ge = r.num("exhaust-heated efficiency (literature end point)", F_ENDUSE, PW.format("full_exhaust", "efficiency_NH3_LHV_to_electricity"), "fraction", "literature")
    gain = r.num("share of Ahmad's efficiency gain needed for 40 vol% partial cracking to match direct, 450 USD/t", F_ENDUSE, "partial_cracking/breakeven_efficiency_gain/[NH3_price_USD_t=450]/gain_scale_where_partial_40vol_equals_direct", "fraction", "python")
    xo = r.num("NH3 price above which exhaust-heated full cracking beats direct", F_ENDUSE, "halim_claim_check/crossover_prices/full_exhaust_vs_direct_NH3_price_USD_t", "USD/t", "python")
    hv = r.num("H2 fraction of the partial-cracking case", F_ENDUSE, PW.format("partial_exhaust_40", "H2_vol_fraction_in_fuel"), "vol fraction", "assumption")
    verdict = "INCONCLUSIVE"
    rows.append(make_row(
        "H1-c", "Cracking is not justified where ammonia can be used directly: partial or full cracking in front of a turbine does not pay.",
        verdict, rowobj=r, singapore_scenario=SG_POWER,
        aspen_model="Partial-cracking heat is the stored Aspen baseline reactor + pre-heater duty scaled with the cracked share; no Aspen combustion or exhaust-heated reactor model.",
        python_model="amcrax.enduse.pathways partial-cracking scan and break-even efficiency gain.",
        case_ids=["direct", "partial_exhaust_40", "partial_fired_40", "full_exhaust"],
        input_assumptions=["Exhaust-heated cracker efficiency taken from Ahmad's two end points (literature).",
                           "Efficiency of intermediate blends linearly interpolated between Ahmad's end points (assumption).",
                           "Fired variants: direct-NH3 turbine efficiency (assumption)."],
        literature=common_lit,
        validation_areas=["enduse"],
        validation_method="Ahmad bypass table reproduced by stoichiometry; N and H atom balance and blend round trip (enduse.json).",
        uncertainty_range=f"Exhaust-heated partial cracking ({pct(hv,0)} H2 by volume) is {f(d2 - pe,1)} USD/MWh cheaper than direct; it needs {pct(gain,0)} of Ahmad's efficiency gain to break even. Exhaust-heated full cracking beats direct above {f(xo,0)} USD/t NH3.",
        key_uncertainty="The exhaust-heat efficiency gain (one literature source, not simulated here): with less than the break-even share of Ahmad's gain, direct use wins at every scanned H2 fraction.",
        limitations=["No combustion simulation; NOx not quantified for blends and cracked fuels.",
                     "Turbine H2 tolerance ranges are flags only (Ahmad p. 2; brief value unverified)."],
        conclusion=f"Fired partial cracking ({f(pf,0)} USD/MWh) is dearer than direct ({f(d2,0)}), but exhaust-heated cracking is slightly cheaper ({f(pe,0)} partial, {f(fe,0)} full; efficiency {pct(ge)}). The sign of the difference rests on a literature efficiency gain that this project did not simulate.",
        conclusion_conditions="Rule: INCONCLUSIVE because the ranking reverses on an input efficiency gain (literature, single source) rather than on a computed result, and the difference is a few per cent of LCOE.",
        data=["results/research/enduse/partial_cracking_scan.csv"],
        figures=["results/figures/research/enduse_partial_cracking_cost.png"], shots=[]))

    # H1-d hydrogen end uses
    r = Row()
    eh = r.num("NH3 LHV to H2 LHV, cracker + PSA", F_ENDUSE, HZ.format("h2_industrial", "efficiency_NH3_LHV_to_H2"), "fraction", "aspen")
    ci = r.num("cost industrial H2 (99.9 %), stored Aspen baseline", F_ENDUSE, HZ.format("h2_industrial", "cost_USD_per_kg_at_grey_450"), "USD/kg H2", "python")
    cd = r.num("cost Grade D candidate, PSA_D_MB at 350 bar (lower bound)", F_ENDUSE, HZ.format("h2_fuelcell_gradeD_purif_study", "cost_USD_per_kg_at_grey_450"), "USD/kg H2", "python")
    kd = r.num("electricity per kg NH3, direct combustion", F_ENDUSE, "detour/kWh_electricity_per_kg_NH3_direct", "kWh/kg NH3", "python")
    kc = r.num("electricity per kg NH3, cracked + purified H2", F_ENDUSE, "detour/kWh_electricity_per_kg_NH3_cracked_purified", "kWh/kg NH3", "python")
    # Final verification: kc < kd follows from eh < 1 when the H2 turbine efficiency is a copy of the direct-NH3
    # efficiency (see H1-a), and eh (chemical energy) is not like-for-like with ed (electricity).
    eta_gas_d = r.num("turbine efficiency on H2-rich fuel (copy of direct case)", "results/research/enduse/assumptions.json", "[name=eta_gt_gas]/value", "fraction", "assumption")
    eta_copied_d = abs(eta_gas_d - ed) < 1e-12
    verdict = "SUPPORTED" if (eh > ed and kc < kd and not eta_copied_d) else "INCONCLUSIVE"
    rows.append(make_row(
        "H1-d", "Cracking is most justified when the end use needs molecular hydrogen: the conversion loss is small when H2 is the product and larger when H2 is only an intermediate fuel.",
        verdict, rowobj=r,
        singapore_scenario="Jurong Island cracker supplying industrial or fuel-cell hydrogen from imported grey NH3 (Singapore price set).",
        aspen_model="Stored Aspen Plus V15 baseline flowsheet (RGibbs cracker, FEHE, PSA split block) for the LHV efficiency.",
        python_model="amcrax.enduse hydrogen pathways with amcrax.economics; purification workstream PSA_D_MB for Grade D.",
        case_ids=["baseline (stored Aspen)", "scn_fuel_cell_grade (stored Aspen)", "PSA_D_MB"],
        input_assumptions=["PSA purity and recovery of the stored Aspen baseline are set by an assumed split (they support no purity claim).",
                           "Grade D cost is a lower bound: NH3 polishing and contaminants other than NH3, N2 and H2O not evaluated."],
        literature=lit(("iso14687_2019", "ISO 14687:2019 grade limits"), ("ahmad2025gtcc", "turbine efficiencies")),
        validation_areas=["enduse", "purification"],
        validation_method="Aspen LHV efficiency matched within tolerance; stored LCOH reproduced; purification mass closure (enduse.json, purification.json).",
        uncertainty_range=f"H2 cost {f(ci)} USD/kg (industrial) to {f(cd)} USD/kg (Grade D candidate, lower bound) at the grey price.",
        key_uncertainty="Purification recovery at fuel-cell purity (not in the library) and NH3 price; neither changes the efficiency ranking.",
        limitations=["No route other than cracking is evaluated for producing H2 from NH3; the comparison is between end uses, not between H2 sources (see H2 for SMR comparators)."],
        conclusion=f"When H2 is the product the cracker + PSA keeps {pct(eh)} of the NH3 LHV (Aspen). For power, routing NH3 through cracking and PSA gives {f(kc)} kWh/kg NH3 against {f(kd)} kWh/kg NH3 for direct combustion. The electricity comparison is fixed by construction: the H2 turbine is assumed to reach the direct-NH3 efficiency, so any cracker loss lowers the output. The H2-product efficiency is chemical energy and is not like-for-like with an electrical efficiency. The numbers quantify the cracking loss; they do not test whether cracking is most justified for H2 end uses.",
        conclusion_conditions="Rule: SUPPORTED if the H2-product efficiency exceeds the direct power efficiency, cracking for power yields less electricity than direct combustion, and the H2 turbine efficiency is not an assumed copy of the direct-NH3 efficiency; otherwise INCONCLUSIVE (here the efficiency is copied, assumption eta_gt_gas). Conditions: stored Aspen baseline operating point, PSA recovery assumed. The comparison is between end uses; whether cracked H2 is competitive with other H2 sources is tested in H2.",
        data=["results/research/enduse/pathway_table_hydrogen.csv"],
        figures=["results/figures/research/enduse_hydrogen_cost_ci.png", "results/figures/research/enduse_power_efficiency.png"],
        shots=[]))
    return rows


# --------------------------------------------------------------------------------------------
# H2 Feedstock
# --------------------------------------------------------------------------------------------
SC = "results/{}|heat_integration_on/{}"


def h2_rows() -> list[dict]:
    rows = []
    sg_lit_econ = lit(("cho2026nickel", "Cho et al. 2026: NH3 price range for sensitivity (Table 8) and feed share of LCOH"),
                      ("sp_blue_ammonia_2025", "S&P Global 2025: blue ammonia prices (search-result text)"),
                      ("argus_h2_markers", "Argus 2026: NE Asia SMR hydrogen cost marker (sample report issue 26-01, p. 2, incl. capex)"),
                      ("sp_singapore_h2_2025", "S&P Global 2025: Singapore willingness to pay (search-result text)"))
    econ_figs = ["results/figures/research/singapore_tornado.png", "results/figures/research/singapore_cost_breakdown.png",
                 "results/figures/research/singapore_monte_carlo.png"]
    sg = "Jurong Island cracker (stored Aspen baseline capacity), imported NH3 at the Singapore price scenarios (grey, blue, green 2050, green 2030, green current), heat integration on."

    # H2-a feed dominates LCOH
    r = Row()
    lc = r.num("LCOH grey, HI on", F_SCEN, SC.format("grey", "lcoh_USD_per_kg"), "USD/kg H2", "python")
    fe = r.num("feed NH3 cost component, grey", F_SCEN, SC.format("grey", "breakdown_USD_per_kg/ammonia_feed"), "USD/kg H2", "python")
    kg = r.num("NH3 feed per kg H2 (Aspen activity)", F_SCEN, SC.format("grey", "kg_nh3_feed_per_kg_h2"), "kg/kg", "aspen")
    sw = r.num("tornado swing, NH3 price 300-610 USD/t", F_TOR, "bars/[parameter=nh3_price_USD_per_t]/swing", "USD/kg H2", "python")
    bars = load(F_TOR)["bars"]
    others = [val(F_TOR, f"bars/{i}/swing") for i, b in enumerate(bars) if b["parameter"] != "nh3_price_USD_per_t"]
    nxt = r.num("next-largest tornado swing (capacity x0.25-x4)", F_TOR, "bars/[parameter=capacity_scale]/swing", "USD/kg H2", "python")
    lo_in = val(F_TOR, "bars/[parameter=nh3_price_USD_per_t]/low_input")
    hi_in = val(F_TOR, "bars/[parameter=nh3_price_USD_per_t]/high_input")
    lo_lc = val(F_TOR, "bars/[parameter=nh3_price_USD_per_t]/lcoh_at_low_input")
    share = fe / lc
    share_lo = (kg * lo_in / 1000.0) / lo_lc
    largest = sw > max(others)
    verdict = "SUPPORTED" if (largest and share_lo > 0.5) else "INCONCLUSIVE"
    rows.append(make_row(
        "H2-a", "Ammonia feed cost dominates the cost of cracked hydrogen, so affordable ammonia is essential to economic competitiveness.",
        verdict, rowobj=r, singapore_scenario=sg,
        aspen_model="Stored Aspen Plus V15 baseline (results/simulations/baseline.json): NH3 feed and fuel per kg H2.",
        python_model="amcrax.economics.singapore.evaluate (unified reference scenario, CAPEX cho2026_itemised_v1), tornado sensitivity.",
        case_ids=["baseline (stored Aspen)", "grey|heat_integration_on"],
        input_assumptions=[f"NH3 price scenarios and the {f(lo_in,0)}-{f(hi_in,0)} USD/t tornado range are inputs (Cho Table 8 and secondary web prices); the feed share is computed but scales with these assumed prices.",
                           "Reference CAPEX (cho2026_itemised_v1) is the highest of the comparable estimates, which lowers the feed share (conservative for this row)."],
        literature=sg_lit_econ, validation_areas=["economics"],
        validation_method="Stored LCOH reproduced exactly; cost-share closure; NH3 feed per kg H2 above the stoichiometric floor (economics.json).",
        uncertainty_range=f"Feed share {pct(share,0)} at {f(val(F_SCEN, SC.format('grey', 'nh3_price_USD_per_t')),0)} USD/t and {pct(share_lo,0)} at the low end of the tornado range ({f(lo_in,0)} USD/t); NH3 price swing {f(sw)} USD/kg against {f(nxt)} USD/kg for the next parameter.",
        key_uncertainty="CAPEX: Cho reports a lower feed share with a fuller plant boundary; a CAPEX several times higher would lower the share but the NH3 price would still be the largest single driver unless CAPEX uncertainty exceeds the price range.",
        limitations=["Benchmark and price inputs partly from search-result text (secondary_web).", "No product compression, NOx treatment or storage in the plant boundary."],
        conclusion=f"Feed NH3 is {f(fe)} of {f(lc)} USD/kg ({pct(share,0)}) and the NH3 price is the largest tornado bar ({f(sw)} USD/kg). This is a computed share of an input price: it follows from the {f(kg)} kg NH3 needed per kg H2, and its size depends on the assumed price scenarios.",
        conclusion_conditions=f"Rule: SUPPORTED if the NH3 price bar is the largest tornado swing and the feed share exceeds one half even at the low price bound. Conditions: price range {f(lo_in,0)}-{f(hi_in,0)} USD/t, AmCraX screening CAPEX, heat integration on.",
        data=["results/research/singapore/tornado.csv", "results/research/singapore/scenario_breakdown.csv"],
        figures=econ_figs, shots=[]))

    # H2-b break-even vs benchmarks
    r = Row()
    be_smr = r.num("break-even NH3 price vs NE Asia SMR benchmark", F_BE, "results/heat_integration_on/ne_asia_smr_production_cost/breakeven_nh3_USD_per_t", "USD/t", "python")
    h_smr = r.num("NE Asia SMR benchmark", F_BE, "results/heat_integration_on/ne_asia_smr_production_cost/h2_price_USD_per_kg", "USD/kg H2", "literature")
    be_wtp = r.num("break-even NH3 price vs Singapore willingness to pay", F_BE, "results/heat_integration_on/sg_low_carbon_willingness_to_pay/breakeven_nh3_USD_per_t", "USD/t", "python")
    be_blue = r.num("break-even NH3 price vs blue H2 delivered East Asia", F_BE, "results/heat_integration_on/blue_delivered_east_asia/breakeven_nh3_USD_per_t", "USD/t", "python")
    p_grey = r.num("grey NH3 price", F_SCEN, SC.format("grey", "nh3_price_USD_per_t"), "USD/t", "assumption")
    p_g30 = r.num("green 2030 NH3 price", F_SCEN, SC.format("green_2030", "nh3_price_USD_per_t"), "USD/t", "assumption")
    p_gc = r.num("green current NH3 price", F_SCEN, SC.format("green_current", "nh3_price_USD_per_t"), "USD/t", "assumption")
    l_gc = r.num("LCOH green current", F_SCEN, SC.format("green_current", "lcoh_USD_per_kg"), "USD/kg H2", "python")
    g95 = r.num("Monte Carlo LCOH p95, grey", F_MC, "results/grey/lcoh_p95", "USD/kg H2", "python")
    gc5 = r.num("Monte Carlo LCOH p5, green current", F_MC, "results/green_current/lcoh_p5", "USD/kg H2", "python")
    h_blue = val(F_BE, "results/heat_integration_on/blue_delivered_east_asia/h2_price_USD_per_kg")
    g5 = r.num("Monte Carlo LCOH p5, grey", F_MC, "results/grey/lcoh_p5", "USD/kg H2", "python")
    g30_5 = r.num("Monte Carlo LCOH p5, green 2030", F_MC, "results/green_2030/lcoh_p5", "USD/kg H2", "python")
    robust = (be_smr < p_g30) and (be_smr < p_gc) and (g30_5 > h_smr) and (gc5 > h_blue)
    verdict = "SUPPORTED" if robust else "INCONCLUSIVE"
    grey_state = ("below" if g95 < h_smr else ("above" if g5 > h_smr else "straddling"))
    rows.append(make_row(
        "H2-b", "Only affordable ammonia keeps cracked hydrogen competitive with the hydrogen benchmarks relevant to Singapore.",
        verdict, rowobj=r, singapore_scenario=sg,
        aspen_model="Stored Aspen Plus V15 baseline activities.",
        python_model="amcrax.economics.singapore.breakeven_nh3_price and Monte Carlo (n and seed in monte_carlo.json).",
        case_ids=["grey|heat_integration_on", "green_2030|heat_integration_on", "green_current|heat_integration_on"],
        input_assumptions=["Hydrogen benchmarks in breakeven_ammonia_price.json have different bases and source qualities (listed per benchmark there); none is a Singapore transaction price.",
                           "NH3 price scenarios are inputs (data/singapore.yaml)."],
        literature=sg_lit_econ + lit(("ace_h2_delivered", "ASEAN Centre for Energy: delivered blue/green H2 cost to East Asia (search-result text)")),
        validation_areas=["economics"],
        validation_method="Break-even consistency check (LCOH at the break-even price equals the benchmark) in economics.json.",
        uncertainty_range=f"Monte Carlo LCOH p5-p95: grey {f(g5)}-{f(g95)} USD/kg ({grey_state} the {f(h_smr)} USD/kg SMR benchmark); green 2030 p5 {f(g30_5)} USD/kg (above the SMR benchmark); green current p5 {f(gc5)} USD/kg (above the {f(h_blue)} USD/kg blue-delivered benchmark).",
        key_uncertainty="The benchmark values (different bases, none a Singapore transaction price): a hydrogen value above the green-2030 LCOH, for example a low-carbon premium, would make green NH3 competitive.",
        limitations=["Break-even is for the cracker gate; landed cost and product compression excluded.", "Constant prices, pre-tax NPV.",
                     "Benchmarks are read from breakeven_ammonia_price.json as stored at build time; their sources are listed there."],
        conclusion=f"Cracked H2 matches the NE Asia SMR benchmark ({f(h_smr)} USD/kg) at {f(be_smr,0)} USD/t NH3 and Singapore willingness to pay at {f(be_wtp,0)} USD/t. Grey NH3 ({f(p_grey,0)} USD/t) is {'below' if p_grey < be_smr else 'above'} the SMR break-even; green 2030 ({f(p_g30,0)}) and green current ({f(p_gc,0)} USD/t, LCOH {f(l_gc)}) are well above it, and green current is above even the blue-delivered break-even ({f(be_blue,0)} USD/t). Competitiveness with the SMR benchmark requires NH3 at or below {f(be_smr,0)} USD/t.",
        conclusion_conditions="Rule: SUPPORTED if the SMR break-even NH3 price is below both green price scenarios and the Monte Carlo p5 of green 2030 (vs SMR) and green current (vs blue delivered) stay above the benchmark. Conditional on the benchmark values.",
        data=["results/research/singapore/breakeven_ammonia_price.json", "results/research/singapore/monte_carlo.json"],
        figures=["results/figures/research/singapore_breakeven.png", "results/figures/research/singapore_monte_carlo.png"], shots=[]))

    # H2-c low-carbon NH3 needed for power to cut emissions
    dist = val(F_LCA, "distance_km_baseline")
    BE = "breakeven/[comparison={};distance_km=" + f"{dist:g}" + "]/breakeven_NH3_gate_EF_kgCO2e_per_kgNH3"
    RT = "routes/[route={}]/{}"
    r = Row()
    r.num("baseline sea distance (scenario value)", F_LCA, "distance_km_baseline", "km", "assumption")
    be_ng = r.num("break-even NH3 gate EF, direct NH3 CCGT vs NG CCGT (baseline distance)", F_LCA, BE.format("direct NH3 CCGT vs NG CCGT"), "kg CO2e/kg NH3", "python")
    be_grid = r.num("break-even NH3 gate EF, direct NH3 CCGT vs grid average", F_LCA, BE.format("direct NH3 CCGT vs grid average"), "kg CO2e/kg NH3", "python")
    ef_g = r.num("green NH3 gate EF", F_LCA, RT.format("green", "gate_kgCO2e_per_kgNH3"), "kg CO2e/kg NH3", "literature")
    ef_b = r.num("blue NH3 gate EF (Lee v1)", F_LCA, RT.format("blue", "gate_kgCO2e_per_kgNH3"), "kg CO2e/kg NH3", "literature")
    ef_b2 = r.num("blue NH3 gate EF (Lee v2)", F_LCA, RT.format("blue_v2", "gate_kgCO2e_per_kgNH3"), "kg CO2e/kg NH3", "literature")
    ef_gr = r.num("grey NH3 gate EF", F_LCA, RT.format("grey", "gate_kgCO2e_per_kgNH3"), "kg CO2e/kg NH3", "literature")
    ci_g = r.num("CI direct NH3 power, green", F_LCA, RT.format("green", "direct_NH3_CCGT_kgCO2e_per_MWh"), "kg CO2e/MWh", "python")
    ci_b = r.num("CI direct NH3 power, blue", F_LCA, RT.format("blue", "direct_NH3_CCGT_kgCO2e_per_MWh"), "kg CO2e/MWh", "python")
    ci_ng = r.num("CI NG CCGT", F_LCA, "alternatives/ccgt_ng_kgCO2e_per_MWh/central", "kg CO2e/MWh", "assumption")
    ci_grid = r.num("CI Singapore grid average (EMA 2024)", F_LCA, "alternatives/grid_average_kgCO2e_per_MWh/central", "kg CO2e/MWh", "literature")
    pmc = r.num("Monte Carlo P(blue direct power below NG CCGT)", F_LCA, "monte_carlo/blue_direct_NH3_power/P_cuts_emissions_vs_NG_CCGT", "probability", "python")
    verdict = "SUPPORTED" if (ef_g < be_ng and ef_b > be_ng and ef_gr > be_ng and pmc < P_ROBUST) else "INCONCLUSIVE"
    rows.append(make_row(
        "H2-c", "Low-carbon ammonia is essential for environmental competitiveness of ammonia-based power in Singapore.",
        verdict, rowobj=r,
        singapore_scenario=f"Imported NH3 shipped {dist:.0f} km (scenario distance) and burned in a Jurong Island CCGT; comparators NG CCGT and the EMA grid average.",
        aspen_model="No Aspen model for combustion: Python/literature only (NH3 per MWh from Ahmad-calibrated efficiency).",
        python_model="amcrax.environmental.lca (GWP100 AR6) and its Monte Carlo (uniform over stated ranges).",
        case_ids=["routes: green, blue, blue_v2, grey", "direct_NH3_CCGT"],
        input_assumptions=["NG CCGT efficiency (central value and range in results/research/lca/assumptions.json) is an assumption.", "Sea distance is a scenario value, not a sourced route length.",
                           "Blue capture and methane leakage are scenario parameters."],
        literature=lit(("lee2022ammonia", "Lee et al. 2022: blue and grey NH3 cradle-to-gate factors"),
                       ("iea2024ghr", "IEA Global Hydrogen Review 2024 (highlights): green NH3 range"),
                       ("ema2025ses", "EMA Singapore Energy Statistics: grid emission factor (not verified at source; third-party listing)"),
                       ("ipcc2021ar6wg1ch7", "IPCC AR6 WG1 Ch. 7: GWP100")),
        validation_areas=["lca"],
        validation_method="Lee v1 and v2 factors reproduced exactly; existing environmental baseline reproduced; breakdown sums (lca.json).",
        uncertainty_range=f"Break-even gate EF {f(be_ng)} (vs NG CCGT) and {f(be_grid)} (vs grid) kg CO2e/kg NH3; Monte Carlo probability that blue direct power beats NG CCGT {f(pmc,4)}.",
        key_uncertainty=f"Blue NH3 capture and leakage: Lee v2 blue ({f(ef_b2)}) is below the break-even, so blue with near-full process and flue-gas capture and low leakage would also qualify.",
        limitations=load(F_LCA)["limitations"],
        conclusion=f"Direct NH3 power emits {f(ci_g,0)} kg CO2e/MWh with green NH3 and {f(ci_b,0)} with blue (Lee v1), against {f(ci_ng,0)} for NG CCGT and {f(ci_grid,0)} for the grid. Only NH3 below {f(be_ng)} kg CO2e/kg NH3 at the gate cuts emissions: green ({f(ef_g)}) does, blue v1 ({f(ef_b)}) and grey ({f(ef_gr)}) do not.",
        conclusion_conditions=f"Rule: SUPPORTED if green is below and blue v1 and grey are above the break-even and the Monte Carlo probability for blue is below {P_ROBUST} (method threshold). Conditions: GWP100, {dist:.0f} km, CCGT efficiency assumption.",
        data=["results/research/lca/lca_breakeven.csv", "results/research/lca/lca_routes.csv"],
        figures=["results/figures/research/lca_power_by_route.png", "results/figures/research/lca_breakeven_power.png",
                 "results/figures/research/lca_sensitivity_blue_power.png"], shots=[]))

    # H2-d hydrogen vs SMR
    r = Row()
    h_g = r.num("CI industrial H2, green NH3", F_LCA, RT.format("green", "H2_kgCO2e_per_kg"), "kg CO2e/kg H2", "python")
    h_b = r.num("CI industrial H2, blue NH3 (Lee v1)", F_LCA, RT.format("blue", "H2_kgCO2e_per_kg"), "kg CO2e/kg H2", "python")
    h_gr = r.num("CI industrial H2, grey NH3", F_LCA, RT.format("grey", "H2_kgCO2e_per_kg"), "kg CO2e/kg H2", "python")
    smr = r.num("CI SMR unabated (central)", F_LCA, "alternatives/smr_h2_unabated_kgCO2e_per_kgH2/central", "kg CO2e/kg H2", "literature")
    ccs = r.num("CI SMR + CCS (central, low confidence)", F_LCA, "alternatives/smr_h2_ccs_kgCO2e_per_kgH2/central", "kg CO2e/kg H2", "literature")
    p_smr = r.num("Monte Carlo P(blue H2 below SMR unabated)", F_LCA, "monte_carlo/blue_industrial_H2/P_below_SMR_unabated", "probability", "python")
    p_ccs = r.num("Monte Carlo P(blue H2 below SMR + CCS)", F_LCA, "monte_carlo/blue_industrial_H2/P_below_SMR_CCS", "probability", "python")
    be_s = r.num("break-even NH3 gate EF vs SMR unabated (5000 km)", F_LCA, BE.format("industrial H2 vs SMR unabated"), "kg CO2e/kg NH3", "python")
    be_c = r.num("break-even NH3 gate EF vs SMR + CCS (5000 km)", F_LCA, BE.format("industrial H2 vs SMR + CCS"), "kg CO2e/kg NH3", "python")
    verdict = "SUPPORTED" if (h_gr > smr and h_g < ccs and p_ccs == 0) else "INCONCLUSIVE"
    rows.append(make_row(
        "H2-d", "Low-carbon ammonia is essential for cracked hydrogen to have lower carbon intensity than fossil hydrogen.",
        verdict, rowobj=r,
        singapore_scenario=f"Industrial H2 from a Jurong Island cracker fed with imported NH3 ({dist:.0f} km), compared with SMR hydrogen.",
        aspen_model="Stored Aspen Plus V15 baseline: NH3 per kg H2 and process electricity.",
        python_model="amcrax.environmental.lca and Monte Carlo.",
        case_ids=["baseline (stored Aspen)", "routes: green, blue, grey"],
        input_assumptions=["SMR + CCS factor is low confidence (search extracts).", "Leakage and capture are scenario parameters."],
        literature=lit(("lee2022ammonia", "Lee et al. 2022 NH3 factors"), ("frontiers2024smrccs", "Elgowainy et al. 2024: SMR + CCS literature range quoted from other studies (secondary, low confidence)"),
                       ("arxiv2206.10689smr", "SMR hydrogen emissions (search extract)")),
        validation_areas=["lca"],
        validation_method="As H2-c (lca.json).",
        uncertainty_range=f"Blue H2 is below unabated SMR in {pct(p_smr,0)} of Monte Carlo draws and below SMR + CCS in {pct(p_ccs,0)}.",
        key_uncertainty="The SMR + CCS comparator (low confidence) and blue capture rate; a higher SMR + CCS value would let blue NH3 compete.",
        limitations=load(F_LCA)["limitations"],
        conclusion=f"Grey-NH3 hydrogen ({f(h_gr,1)} kg CO2e/kg) is worse than unabated SMR ({f(smr,1)}); blue ({f(h_b,1)}) beats it only narrowly and never beats SMR + CCS ({f(ccs,1)}); green ({f(h_g,1)}) beats both. Break-even gate EF {f(be_s)} (SMR) and {f(be_c)} (SMR + CCS) kg CO2e/kg NH3.",
        conclusion_conditions=f"Rule: SUPPORTED if grey is above unabated SMR, green is below SMR + CCS and blue never beats SMR + CCS in the Monte Carlo. Conditions: GWP100, {dist:.0f} km, comparator values as stated.",
        data=["results/research/lca/lca_breakeven.csv"],
        figures=["results/figures/research/lca_h2_by_route.png"], shots=[]))

    # H2-e carbon tax does not reward low-carbon NH3
    r = Row()
    tax_rate = r.num("Singapore carbon tax rate used", F_LCA, "carbon_tax_sg/rate_SGD_per_t", "SGD/t CO2e", "literature")
    tax_h2 = r.num("carbon tax in LCOH, grey, NH3-fired heat", F_SCEN, SC.format("grey", "breakdown_USD_per_kg/carbon_tax"), "USD/kg H2", "python")
    tsw = r.num("tornado swing, carbon tax", F_TOR, "bars/[parameter=carbon_tax_SGD_per_t]/swing", "USD/kg H2", "python")
    lg = r.num("LCOH grey", F_SCEN, SC.format("grey", "lcoh_USD_per_kg"), "USD/kg H2", "python")
    l30 = r.num("LCOH green 2030", F_SCEN, SC.format("green_2030", "lcoh_USD_per_kg"), "USD/kg H2", "python")
    verdict = "CONTRADICTED" if (tax_h2 == 0 and tsw == 0 and l30 > lg) else "INCONCLUSIVE"
    rows.append(make_row(
        "H2-e", "Low-carbon ammonia is essential to economic competitiveness (that is, low carbon intensity is rewarded in the Singapore cost of hydrogen).",
        verdict, rowobj=r, singapore_scenario=sg + " Singapore carbon tax at the current legislated rate, Scope 1 only, with the NEA facility threshold.",
        aspen_model="Stored Aspen Plus V15 baseline: direct emissions of the NH3-fired cracker (no CO2).",
        python_model="amcrax.economics.singapore carbon-tax treatment; amcrax.environmental.lca carbon_tax_sg.",
        case_ids=["grey|heat_integration_on", "green_2030|heat_integration_on"],
        input_assumptions=["Upstream and shipping emissions are outside Singapore's carbon-tax base (NEA rules).",
                           "N2O factor from one simulated source (Ahmad)."],
        literature=lit(("nea_carbon_tax", "NEA carbon tax rates, threshold and covered gases")),
        validation_areas=["economics", "lca"],
        validation_method="Zero tax on NH3-fired heat and gas-fired heat below the threshold (economics.json).",
        uncertainty_range=f"Carbon-tax swing in LCOH {f(tsw)} USD/kg. Direct NH3 power: its only in-scope emission is simulated N2O (one Chemkin source, assumed exhaust basis), far below the NEA facility threshold, so its carbon-tax liability is zero.",
        key_uncertainty="Policy: a carbon price on imported embedded emissions, a low-carbon hydrogen mandate or a buyer premium (for example willingness to pay) would reward low-carbon NH3.",
        limitations=["Only current, legislated Singapore carbon-tax rules; no low-carbon premium or contract-for-difference modelled.",
                     "The 'hypothetical' gas-heat carbon-tax heatmap ignores the threshold and is not used here."],
        conclusion=f"Under Singapore's carbon tax ({f(tax_rate,0)} SGD/t, Scope 1) the cracker pays {f(tax_h2)} USD/kg H2 of tax and direct NH3 power, below the facility threshold, pays none, so the tax does not reward low-carbon NH3. Green-2030 NH3 raises LCOH from {f(lg)} to {f(l30)} USD/kg. Affordability and low carbon intensity therefore pull in opposite directions at current prices and policy.",
        conclusion_conditions="Rule: CONTRADICTED if the carbon tax contributes zero to LCOH, its tornado swing is zero and the low-carbon price scenario raises LCOH. Holds only under current Singapore policy; the environmental part of H2 is assessed in H2-c and H2-d.",
        data=["results/research/singapore/heatmap_nh3_price_x_carbon_tax_nh3_heat.csv"],
        figures=["results/figures/research/singapore_heatmap_nh3_price_carbon_tax.png"], shots=[]))
    return rows


# --------------------------------------------------------------------------------------------
# H3 Catalyst and heat integration
# --------------------------------------------------------------------------------------------
CATS = [("ru_kum_temkin_pyzhev", "Ru/Al2O3"), ("ru_takahashi_microkinetic", "Ru/MgO"),
        ("nire_ceo2_5ni1ru_lucentini_lhhw", "5Ni1Ru/CeO2"), ("nire_ceo2_2p5ni0p5ru_lucentini_lhhw", "2.5Ni0.5Ru/CeO2"),
        ("ni_takahashi_microkinetic", "Ni/MgO")]
CI_CASES = ["ci_kum_T499_P20_W100_hi", "ci_kum_T499_P20_W100_nohi", "ci_tru_T522_P20_W100_hi", "ci_tru_T522_P20_W100_nohi",
            "ci_luc5_T572_P20_W100_hi", "ci_luc5_T572_P20_W100_nohi", "ci_luc25_T576_P20_W100_hi", "ci_luc25_T576_P20_W100_nohi",
            "ci_tni_T594_P20_W100_hi", "ci_tni_T594_P20_W100_nohi"]


def h3_rows() -> list[dict]:
    rows = []
    kin_lit = lit(("kum2026heatintegrated", "Kum et al. 2026: Ru/Al2O3 Temkin-Pyzhev law"),
                  ("takahashi2016kinetic", "Takahashi & Fujitani 2016: Ni/MgO and Ru/MgO microkinetics"),
                  ("lucentini2021nirukinetic", "Lucentini et al. 2021: Ni-Ru/CeO2 LHHW (Table 3)"))
    cat_figs = ["results/figures/research/catalyst_heat_duty.png", "results/figures/research/catalyst_cost_breakdown.png"]
    basis = resolve(F_CAT, "basis/feed")
    sg = f"Jurong Island cracker; {basis}; grey NH3 price scenario; {resolve(F_CAT, 'basis/economics')}."
    approx_note = resolve(F_ACAT, "notes/0")
    CA = "results/research/catalyst_comparison/assumptions.json"
    ci_csv = "results/research/aspen_kinetic/catalyst_integrated.csv"
    ci_json = ["results/research/aspen_kinetic/" + c + ".json" for c in CI_CASES]
    shots_ci = screenshots(["ci_luc5_T572_P20_W100_hi", "cs_OP_tni_T594_P20_W100"])
    A = "rows/[catalyst_id={}]/{}"

    # H3-a lower T reduces external energy at equal conversion (Aspen)
    r = Row()
    t_lo = r.num("operating T, Ru/Al2O3 (100 kg, 95 %)", F_ACAT, A.format("ru_kum_temkin_pyzhev", "operating_temperature_C"), "degC", "python")
    t_hi = r.num("operating T, Ni/MgO (100 kg, 95 %)", F_ACAT, A.format("ni_takahashi_microkinetic", "operating_temperature_C"), "degC", "python")
    e_lo = r.num("external heating with HI, Ru/Al2O3", F_ACAT, A.format("ru_kum_temkin_pyzhev", "integrated_hi_total_external_heating_kW"), "kW", "aspen")
    e_hi = r.num("external heating with HI, Ni/MgO", F_ACAT, A.format("ni_takahashi_microkinetic", "integrated_hi_total_external_heating_kW"), "kW", "aspen")
    n_lo = r.num("external heating without HI, Ru/Al2O3", F_ACAT, A.format("ru_kum_temkin_pyzhev", "integrated_nohi_total_external_heating_kW"), "kW", "aspen")
    n_hi = r.num("external heating without HI, Ni/MgO", F_ACAT, A.format("ni_takahashi_microkinetic", "integrated_nohi_total_external_heating_kW"), "kW", "aspen")
    fd_hi = r.num("fired duty reduction Ru/Al2O3 vs Ni/MgO, with HI", F_CAT, "findings/fixed_inventory_100kg_aspen/Ru_Al2O3_vs_Ni_fired_duty_reduction_HI", "fraction", "aspen")
    fd_no = r.num("fired duty reduction Ru/Al2O3 vs Ni/MgO, without HI", F_CAT, "findings/fixed_inventory_100kg_aspen/Ru_Al2O3_vs_Ni_fired_duty_reduction_noHI", "fraction", "aspen")
    eff_lo = r.num("LHV efficiency with HI, Ru/Al2O3", F_ACAT, A.format("ru_kum_temkin_pyzhev", "integrated_hi_lhv_efficiency"), "fraction", "aspen")
    eff_hi = r.num("LHV efficiency with HI, Ni/MgO", F_ACAT, A.format("ni_takahashi_microkinetic", "integrated_hi_lhv_efficiency"), "fraction", "aspen")
    w_inv = r.num("catalyst inventory in every ci_* case", F_ACAT, A.format("ru_kum_temkin_pyzhev", "W_kg"), "kg", "assumption")
    feff = r.num("furnace efficiency", CA, "[name=furnace_efficiency]/value", "fraction of NH3 LHV", "assumption")
    tloss = r.num("thermal-loss allowance", CA, "[name=thermal_loss_fraction]/value", "fraction of reactor + trim heater duty", "assumption")
    red_hi = 1 - e_lo / e_hi
    red_no = 1 - n_lo / n_hi
    verdict = "SUPPORTED" if (e_lo < e_hi and n_lo < n_hi and fd_hi > 0) else "INCONCLUSIVE"
    rows.append(make_row(
        "H3-a", "Energy half of the catalyst claim: at equal conversion, running the cracker at the lower temperature that a more active catalyst allows reduces energy use.",
        verdict, rowobj=r, singapore_scenario=sg,
        aspen_model=f"Aspen Plus V15 integrated flowsheet with kinetic RPLUG cracker (ci_* cases, with and without heat integration), {f(w_inv,0)} kg catalyst, each catalyst at its operating temperature as defined in aspen_kinetic/catalyst_comparison.json.",
        python_model="amcrax.research.catalyst_comparison fired-duty post-processing (tail-gas firing, furnace efficiency).",
        case_ids=CI_CASES,
        input_assumptions=["Operating temperatures come from the Python kinetics study (Aspen confirms conversion).",
                           f"Furnace efficiency {f(feff,2)} and thermal-loss allowance {pct(tloss,0)} (assumptions) for the fired duty.",
                           approx_note],
        literature=kin_lit, validation_areas=["aspen_kinetic", "catalyst_comparison"],
        validation_method="Aspen RPLUG vs Python PFR (|dX| below tolerance), integrated cases not above RGibbs equilibrium; Python vs Aspen heat duties (aspen_kinetic.json, catalyst_comparison.json).",
        uncertainty_range=f"External heating {pct(red_hi)} lower with HI and {pct(red_no)} lower without HI for {f(t_lo,0)} vs {f(t_hi,0)} degC; fired duty (after tail-gas firing) {pct(fd_hi,0)} lower with HI and {pct(fd_no,0)} lower without.",
        key_uncertainty=f"Which metric is meant by 'energy use': total external heating changes by {pct(red_hi)} with HI, the fired supplementary duty by {pct(fd_hi,0)}; LHV efficiency is practically unchanged.",
        limitations=["The temperature difference between catalysts rests on extrapolated rate laws (see H3-b); the energy effect of temperature itself is thermodynamic and computed by Aspen.",
                     "Python FEHE recovered duty is above Aspen beyond the validation tolerance (HCAT-ASPY-*-HI-heat failures)."],
        conclusion=f"At equal conversion the lower-temperature case needs less external heating ({f(e_lo,0)} vs {f(e_hi,0)} kW with HI; {f(n_lo,0)} vs {f(n_hi,0)} kW without), but the LHV efficiency barely moves ({f(eff_lo,4)} vs {f(eff_hi,4)}). The energy saving is real but small once heat is integrated.",
        conclusion_conditions=f"Rule: SUPPORTED if the lower-temperature Aspen case has lower external heating with and without HI and a lower fired duty. Conditions: {basis}; {f(w_inv,0)} kg catalyst; the AmCraX FEHE flowsheet.",
        data=[ci_csv] + ci_json, figures=cat_figs + ["results/figures/research/aspen_kinetic_operating_point.png"], shots=shots_ci))

    # H3-b high activity lowers the required T
    r = Row()
    KT = "rows/[catalyst_id={};P_bar={};W_cat_kg=100;X_target={}]/{}"
    t95 = {c: r.num(f"T for 95 % at 20 bar, 100 kg, {lab}", F_KT, KT.format(c, 20, 0.95, "T_required_C"), "degC", "python") for c, lab in CATS}
    t99 = r.num("T for 99 % at 20 bar, any catalyst (equilibrium minimum)", F_KT, KT.format("ni_takahashi_microkinetic", 20, 0.99, "T_equilibrium_min_C"), "degC", "python")
    t1_ru = r.num("T for 99 % at 1 atm, 100 kg, Ru/MgO (within fitted range)", F_KT, KT.format("ru_takahashi_microkinetic", 1.01325, 0.99, "T_required_C"), "degC", "python")
    t1_ni = r.num("T for 99 % at 1 atm, 100 kg, Ni/MgO (within fitted range)", F_KT, KT.format("ni_takahashi_microkinetic", 1.01325, 0.99, "T_required_C"), "degC", "python")
    in_range = [resolve(F_KT, KT.format(c, 20, 0.95, "within_fitted_range")) for c, _ in CATS]
    all_99_eq = all(abs(val(F_KT, KT.format(c, 20, 0.99, "T_required_C")) - t99) < 1.0 for c, _ in CATS)
    verdict = "INCONCLUSIVE" if (not any(in_range)) else "SUPPORTED"
    rows.append(make_row(
        "H3-b", "Low-temperature, high-activity catalysts allow the cracker to run at a lower temperature for the same duty.",
        verdict, rowobj=r, singapore_scenario=sg,
        aspen_model="Aspen standalone RPLUG operating-point checks (cs_OP_* cases) confirm the Python temperatures.",
        python_model="amcrax.kinetics laws in the isothermal PFR (study_temperature_for_target_conversion).",
        case_ids=["cs_OP_kum_T499_P20_W100", "cs_OP_tru_T522_P20_W100", "cs_OP_luc5_T572_P20_W100", "cs_OP_luc25_T576_P20_W100", "cs_OP_tni_T594_P20_W100"],
        input_assumptions=["Effectiveness factor 1, no pressure drop (assumptions); catalyst masses are lower bounds.",
                           approx_note],
        literature=kin_lit + lit(("lucentini2019ceo2", "Lucentini et al. 2019: Ru/CeO2 vs Ni/CeO2 conversion at atmospheric pressure (no rate law)"),
                                 ("sayas2020high", "Sayas et al. 2020: Ru-K/CaO (full text not obtained; values unverified)")),
        validation_areas=["kinetics", "aspen_kinetic"],
        validation_method="Lucentini Table 1 points reproduced (consistency, not independent); Takahashi predictions carried over as failures; Aspen native laws vs spec points (kinetics.json, aspen_kinetic.json).",
        uncertainty_range=f"At 20 bar and 95 %: {', '.join(f'{lab} {f(t95[c],0)}' for c, lab in CATS)} degC. At 99 % every catalyst needs at least {f(t99,1)} degC (equilibrium). The Lucentini Ek confidence interval alone moves the predicted conversion over most of its range (kinetics validation JSON).",
        key_uncertainty="Rate laws at 20 bar: every law is extrapolated beyond its fitted pressure (and for Kum temperature) range; a pressure-valid law, or kinetics measured on industrial pellets, could change the temperature gaps either way.",
        limitations=["All 20 bar operating points are outside the fitted ranges (within_fitted_range false).",
                     "Ni/CeO2, Ru/CeO2 and Ru-K/CaO not modelled: no usable rate law.",
                     "Takahashi Ni and Ru predictions fail the existing validation (EXISTING-KIN-NI-PRED, EXISTING-KIN-RU-PRED)."],
        conclusion=f"Within the fitted range (1 atm) a more active catalyst lowers the temperature for 99 % conversion ({f(t1_ru,0)} vs {f(t1_ni,0)} degC, Ru/MgO vs Ni/MgO). At the 20 bar design point the gap ({f(t95['ru_kum_temkin_pyzhev'],0)} to {f(t95['ni_takahashi_microkinetic'],0)} degC for 95 %) comes from extrapolated laws, and for 99 % conversion activity cannot lower the temperature at all{' (equilibrium-limited for every catalyst)' if all_99_eq else ''}.",
        conclusion_conditions="Rule: INCONCLUSIVE if no 20 bar operating point lies within its law's fitted range. The 1 atm result is within range but is not the Singapore design condition, and the Takahashi law fails its own prediction check.",
        data=["results/research/kinetics/study_temperature_for_target_conversion.csv", "results/research/aspen_kinetic/catalyst_standalone_runs.csv"],
        figures=["results/figures/research/kinetics_conversion_vs_T.png", "results/figures/research/aspen_kinetic_conversion_vs_T.png"],
        shots=screenshots(["cs_OP_tni_T594_P20_W100"])))

    # H3-c energy savings outweigh higher catalyst cost
    r = Row()
    CO = "findings/cost_optimal_python/{}/HI/lcoh_USD_per_kg"
    l_ru = r.num("LCOH at cost-optimal T, Ru/Al2O3, HI", F_CAT, CO.format(esc("Ru/Al2O3")), "USD/kg H2", "python")
    l_ni = r.num("LCOH at cost-optimal T, Ni/MgO, HI", F_CAT, CO.format(esc("Ni/MgO")), "USD/kg H2", "python")
    dfix_hi = r.num("LCOH Ru/Al2O3 minus Ni/MgO, fixed 100 kg, HI (Aspen duties)", F_CAT, "findings/fixed_inventory_100kg_aspen/Ru_Al2O3_minus_Ni_lcoh_HI", "USD/kg H2", "python")
    dfix_no = r.num("LCOH Ru/Al2O3 minus Ni/MgO, fixed 100 kg, no HI (Aspen duties)", F_CAT, "findings/fixed_inventory_100kg_aspen/Ru_Al2O3_minus_Ni_lcoh_noHI", "USD/kg H2", "python")
    dmax = r.num("largest |best low-T catalyst minus Ni| over 32 sensitivity cases", F_CAT, "findings/ranking_robustness/max_abs_best_low_T_minus_Ni_USD_per_kg", "USD/kg H2", "python")
    nsame = r.num("cases with unchanged best catalyst", F_CAT, "findings/ranking_robustness/n_same_best_as_base", "count", "python")
    ncase = r.num("sensitivity cases", F_CAT, "findings/ranking_robustness/n_cases", "count", "python")
    BP = "findings/breakeven_price/[catalyst=" + esc("Ru/Al2O3 (Kum)") + ";reference={}]/breakeven_price_USD_per_kg"
    bp_opt = r.num("break-even Ru/Al2O3 price vs Ni/MgO at its cost optimum", F_CAT, BP.format(esc("Ni/MgO (Takahashi) at its cost-optimal T")), "USD/kg", "python")
    bp_735 = r.num("break-even Ru/Al2O3 price vs Ni/MgO fixed at 735 degC", F_CAT, BP.format(esc("Ni/MgO fixed at 735 degC")), "USD/kg", "python")
    mc95 = r.num("Monte Carlo LCOH p95, grey (economic uncertainty band, upper)", F_MC, "results/grey/lcoh_p95", "USD/kg H2", "python")
    mc5 = r.num("Monte Carlo LCOH p5, grey (economic uncertainty band, lower)", F_MC, "results/grey/lcoh_p5", "USD/kg H2", "python")
    mc_band = mc95 - mc5
    # Phase 2: these keys hold the published TEA prices of Cho et al., now a labelled historical case only
    pr_ni = r.num("Ni catalyst price (Cho published TEA, historical case)", CA, "[name=catalyst_price_Ni_published_TEA]/value", "USD/kg", "assumption")
    pr_ru = r.num("Ru catalyst price (Cho published TEA, historical case, below the Ru metal value)", CA, "[name=catalyst_price_Ru_published_TEA]/value", "USD/kg", "assumption")
    life = r.num("catalyst lifetime", CA, "[name=catalyst_lifetime]/value", "yr", "assumption")
    within_band = dmax < mc_band
    verdict = "INCONCLUSIVE" if within_band else ("SUPPORTED" if l_ru < l_ni else "CONTRADICTED")
    rows.append(make_row(
        "H3-c", "The energy saved by a low-temperature, high-activity catalyst can outweigh its higher catalyst cost.",
        verdict, rowobj=r, singapore_scenario=sg,
        aspen_model="Aspen duties for the fixed-inventory comparison (ci_* cases); no Aspen run at the Python cost-optimal temperatures (those rows are Python only).",
        python_model="amcrax.research.catalyst_comparison: W(T) from PFR kinetics, T_opt = argmin LCOH, heat_integration configuration (c), amcrax.economics.singapore.evaluate.",
        case_ids=CI_CASES,
        input_assumptions=[f"Catalyst prices: Cho Ni {f(pr_ni,1)} and Ru {f(pr_ru,0)} USD/kg used as proxies, {f(life,0)}-year life (assumption); no sourced NiRu/CeO2 price.",
                           "CAPEX does not respond to reactor volume, exchanger area or temperature (volume scaling is a sensitivity only).",
                           "Furnace efficiency and thermal-loss allowance as in H3-a (assumptions)."],
        literature=kin_lit + lit(("cho2026nickel", "Cho et al. 2026: Ni and Ru catalyst prices")),
        validation_areas=["catalyst_comparison", "kinetics"],
        validation_method="Analytic catalyst-cost addition matches full evaluate(); T_opt interior to the grid; mass and energy closure (catalyst_comparison.json).",
        uncertainty_range=f"Catalyst LCOH differences at most {f(dmax,3)} USD/kg against a Monte Carlo p5-p95 band of {f(mc_band,2)} USD/kg; best catalyst unchanged in {f(nsame,0)} of {f(ncase,0)} cases.",
        key_uncertainty=f"The Ni reference design: against Ni forced to 735 degC (Cho's temperature) Ru pays at up to {f(bp_735,0)} USD/kg; against a Ni design optimised on the Takahashi law the break-even is {f(bp_opt,0)} USD/kg. A pressure-valid Ni law and a sourced Ru price would settle it.",
        limitations=["Ni/MgO law fails its prediction check (EXISTING-KIN-NI-PRED).", "No sourced price for NiRu/CeO2.", "N2O not quantified."],
        conclusion=f"At cost-optimal temperatures Ni/MgO ({f(l_ni,4)}) and Ru/Al2O3 ({f(l_ru,4)} USD/kg) are practically equal; at equal 100 kg inventory Ru is dearer by {f(dfix_hi,3)} USD/kg with HI and cheaper by {f(-dfix_no,3)} without. The differences are far inside the economic uncertainty, so the model cannot rank the catalysts on cost and the claim is neither shown nor refuted. The Ru break-even price against an optimised Ni design ({f(bp_opt,0)} USD/kg, against the {f(pr_ru,0)} USD/kg proxy) lies inside the same model resolution; against Ni fixed at Cho's temperature it is {f(bp_735,0)} USD/kg.",
        conclusion_conditions=f"Rule: INCONCLUSIVE when the largest catalyst LCOH difference is smaller than the Monte Carlo p5-p95 LCOH band; otherwise the sign of the cost-optimal difference decides. Conditions: {basis}; grey NH3; proxy catalyst prices.",
        data=["results/research/catalyst_comparison/catalyst_comparison.csv", "results/research/catalyst_comparison/catalyst_breakeven_price.json",
              "results/research/catalyst_comparison/catalyst_ranking_robustness.json", "results/research/catalyst_comparison/catalyst_design_curves.csv"],
        figures=["results/figures/research/catalyst_breakeven_price.png", "results/figures/research/catalyst_ranking_robustness.png",
                 "results/figures/research/catalyst_cost_breakdown.png"], shots=[]))

    # H3-d heat integration reduces energy use and cost
    r = Row()
    hi_save = {}
    for c, lab in CATS:
        on = val(F_ACAT, A.format(c, "integrated_hi_total_external_heating_kW"))
        off = val(F_ACAT, A.format(c, "integrated_nohi_total_external_heating_kW"))
        hi_save[lab] = off - on
    rec = r.num("recovered heat with HI, Ru/Al2O3 (FEHE)", F_ACAT, A.format("ru_kum_temkin_pyzhev", "integrated_hi_recovered_heat_kW"), "kW", "aspen")
    rec_ni = r.num("recovered heat with HI, Ni/MgO (FEHE)", F_ACAT, A.format("ni_takahashi_microkinetic", "integrated_hi_recovered_heat_kW"), "kW", "aspen")
    bh = r.num("baseline external heating with HI (RGibbs, 600 degC)", F_ACAT, "rgibbs_baseline_600C/heat_integration/total_external_heating_kW", "kW", "aspen")
    bn = r.num("baseline external heating without HI", F_ACAT, "rgibbs_baseline_600C/no_heat_integration/total_external_heating_kW", "kW", "aspen")
    lsw = r.num("LCOH reduction from heat integration (tornado)", F_TOR, "bars/[parameter=heat_integration]/swing", "USD/kg H2", "python")
    verdict = "SUPPORTED" if (all(v > 0 for v in hi_save.values()) and lsw > dmax) else "INCONCLUSIVE"
    rows.append(make_row(
        "H3-d", "Effective heat integration reduces energy use (and cost) of the cracker, and matters more than the catalyst's temperature.",
        verdict, rowobj=r, singapore_scenario=sg,
        aspen_model="Aspen Plus V15 integrated flowsheets with and without FEHE (ci_* cases) and the stored RGibbs baseline (rgibbs_baseline_600C).",
        python_model="amcrax.heat_integration pinch analysis (catalyst_pinch_dTmin.csv); amcrax.economics.singapore tornado.",
        case_ids=CI_CASES + ["baseline (stored Aspen)", "baseline_no_hi (stored Aspen)"],
        input_assumptions=["Heat-exchanger capital does not respond to heat integration (no sourced cost per area): HI acts only through fuel and cooling."],
        literature=lit(("linnhoff1983pinch", "Linnhoff & Hindmarsh 1983: pinch method")),
        validation_areas=["aspen_kinetic", "catalyst_comparison", "economics"],
        validation_method="Pinch baseline reproduced (HCAT-PINCH-BASELINE); Python vs Aspen external heating within tolerance, FEHE recovered duty outside tolerance (HCAT-ASPY-*-HI-heat).",
        uncertainty_range=f"Heat integration saves {min(hi_save.values()):.0f}-{max(hi_save.values()):.0f} kW of external heating across the five catalysts; LCOH saving {f(lsw)} USD/kg against at most {f(dmax,3)} USD/kg between catalysts.",
        key_uncertainty="Exchanger capital (not costed): a large FEHE cost could cut the net saving; the pinch target (catalyst_pinch_dTmin.csv) shows further scope with a better exchanger network.",
        limitations=["Python FEHE duty above Aspen beyond the validation tolerance (HCAT-ASPY-*-HI-heat failures)."],
        conclusion=f"Heat integration lowers external heating for every catalyst ({', '.join(f'{k} {v:.0f} kW' for k, v in hi_save.items())}; baseline {f(bh,0)} vs {f(bn,0)} kW) and LCOH by {f(lsw)} USD/kg (an upper bound, because exchanger capital is not costed), an order of magnitude more than the catalyst choice. This holds on AmCraX boundaries only; it does not show that low-temperature catalysts are unnecessary in general. It also shrinks the energy advantage of low-temperature operation (see H3-a).",
        conclusion_conditions="Rule: SUPPORTED if HI lowers external heating for every catalyst and its LCOH effect exceeds the largest between-catalyst LCOH difference. Conditions: AmCraX FEHE flowsheet, exchanger capital not costed.",
        data=["results/research/catalyst_comparison/catalyst_pinch_dTmin.csv", ci_csv],
        figures=["results/figures/research/catalyst_heat_duty.png", "results/figures/research/singapore_tornado.png"], shots=shots_ci))

    # H3-e Cho supplementary fuel
    r = Row()
    CS = "summary/[psa_recovery={};inventory_basis={}]/{}"
    psas = sorted({s["psa_recovery"] for s in load(F_CHO)["summary"]})
    if len(psas) != 2:
        raise EvidenceError(f"{F_CHO}: expected two PSA recovery cases, found {psas}")
    psa_cho, psa_am = psas[0], psas[1]
    designs = load(F_CHO)["designs"]
    ni_d = [d for d in designs if d["catalyst"].startswith("Ni/")][0]["design"]
    ru_d = [d for d in designs if d["catalyst"].startswith("Ru/Al2O3")][0]["design"]
    DS = "designs/[design={};psa_recovery=" + f"{psa_am:g}" + ";inventory_basis=kinetic_minimum]/{}"
    t_ni = r.num("Cho Ni design temperature", F_CHO, DS.format(ni_d, "T_C"), "degC", "literature")
    t_ru = r.num("Cho Ru design temperature", F_CHO, DS.format(ru_d, "T_C"), "degC", "literature")
    x_d = r.num("conversion of the rebuilt designs", F_CHO, DS.format(ru_d, "X"), "fraction", "literature")
    ni_f = r.num("supplementary NH3, Ni design, AmCraX PSA recovery", F_CHO, CS.format(psa_am, "kinetic_minimum", "Ni_supp_nh3_kg_h"), "kg/h", "python")
    ru_f = r.num("supplementary NH3, Ru design, AmCraX PSA recovery", F_CHO, CS.format(psa_am, "kinetic_minimum", "Ru_supp_nh3_kg_h"), "kg/h", "python")
    cho_ru_fuel = r.num("Cho: Ru supplementary fuel", F_CHO, CS.format(psa_am, "kinetic_minimum", "cho_values/Ru_fuel_kmol_h"), "kmol/h", "literature")
    cho_ni_fuel = r.num("Cho: Ni supplementary fuel", F_CHO, CS.format(psa_am, "kinetic_minimum", "cho_values/Ni_fuel_kmol_h"), "kmol/h", "literature")
    ru_needs = resolve(F_CHO, CS.format(psa_am, "kinetic_minimum", "Ru_needs_supplementary_fuel"))
    # Final verification: the rebuild is not on Cho's boundaries (independent review M5: no compression, recycle,
    # TSA, expander or SCR; proxy kinetics; PSA recovery and CAPEX fixed), so a mismatch can only show that the
    # claim is not reproduced on AmCraX boundaries, not that it is contradicted.
    like_for_like = False
    verdict = ("CONTRADICTED" if (ru_needs is True and ru_f > 0) else "INCONCLUSIVE") if like_for_like else "INCONCLUSIVE"
    rows.append(make_row(
        "H3-e", f"Cho et al. (2026): the Ru process at {f(t_ru,0)} degC needs no supplementary fuel while the Ni process at {f(t_ni,0)} degC burns supplementary NH3.",
        verdict, rowobj=r, singapore_scenario=f"Cho's operating points rebuilt on AmCraX boundaries (conversion {f(x_d,2)}, Cho economic inputs).",
        aspen_model="No Aspen run at Cho's operating points: Python only (heat balance calibrated against the Aspen ci_* cases).",
        python_model="amcrax.research.catalyst_comparison Cho rebuild (catalyst_cho_comparison.json).",
        case_ids=[ni_d, ru_d],
        input_assumptions=["Proxy kinetics: Ni/MgO (Takahashi) and Ru/Al2O3 (Kum) instead of Cho's Collins Ni/Al2O3 and Sayas Ru-K/CaO (in an unavailable SI).",
                           f"PSA recovery {psa_am:g} (AmCraX) or {psa_cho:g} (Cho)."],
        literature=lit(("cho2026nickel", "Cho et al. 2026: Table 7 p. 13, pp. 14-15")),
        validation_areas=["catalyst_comparison"],
        validation_method="Cho REC-direction items recorded as informational (catalyst_comparison.json).",
        uncertainty_range=f"At PSA {psa_am:g} both designs need supplementary NH3 (Ni {f(ni_f,0)}, Ru {f(ru_f,0)} kg/h); at Cho's PSA {psa_cho:g} the tail gas covers the process heat for both (pinch import zero; only the thermal-loss allowance remains).",
        key_uncertainty="Cho's boiler, compression, H2 recycle and expander units, which AmCraX does not have; with them the heat balance and the role of the catalyst could differ.",
        limitations=load(F_CHO)["boundary_differences"],
        conclusion=f"Not reproduced on AmCraX boundaries: Cho reports {f(cho_ru_fuel,1)} kmol/h fuel for Ru and {f(cho_ni_fuel,3)} kmol/h for Ni, whereas here both designs need supplementary fuel at PSA {psa_am:g} and neither does at PSA {psa_cho:g}. PSA recovery, not the catalyst, decides whether supplementary fuel is needed.",
        conclusion_conditions="Rule: CONTRADICTED only if the Ru design needs supplementary fuel on a boundary like-for-like with Cho's; the AmCraX rebuild lacks Cho's compression, recycle, TSA, expander and SCR units and uses proxy kinetics, so a mismatch is INCONCLUSIVE (not reproduced on AmCraX boundaries). It does not show that Cho's flowsheet is wrong.",
        data=["results/research/catalyst_comparison/catalyst_cho_comparison.csv"], figures=[], shots=[]))

    # H3-f Cho REC difference
    r = Row()
    rk = r.num("REC Ru lower by, kinetic-minimum mass, AmCraX PSA recovery", F_CHO, CS.format(psa_am, "kinetic_minimum", "rec_Ru_lower_by_pct"), "%", "python")
    rg = r.num("REC Ru lower by, Cho GHSV mass, AmCraX PSA recovery", F_CHO, CS.format(psa_am, "cho_ghsv_9000", "rec_Ru_lower_by_pct"), "%", "python")
    rk7 = r.num("REC Ru lower by, kinetic-minimum mass, Cho PSA recovery", F_CHO, CS.format(psa_cho, "kinetic_minimum", "rec_Ru_lower_by_pct"), "%", "python")
    rg7 = r.num("REC Ru lower by, Cho GHSV mass, Cho PSA recovery", F_CHO, CS.format(psa_cho, "cho_ghsv_9000", "rec_Ru_lower_by_pct"), "%", "python")
    cho7 = r.num("Cho: REC Ru lower by", F_CHO, CS.format(psa_am, "kinetic_minimum", "cho_values/rec_Ru_lower_by_pct"), "%", "literature")
    rec_ni = r.num("Cho: REC Ni", F_CHO, CS.format(psa_am, "kinetic_minimum", "cho_values/rec_Ni"), "USD/kg H2", "literature")
    rec_ru = r.num("Cho: REC Ru", F_CHO, CS.format(psa_am, "kinetic_minimum", "cho_values/rec_Ru"), "USD/kg H2", "literature")
    signs = {x > 0 for x in (rk, rg, rk7, rg7)}
    verdict = "INCONCLUSIVE" if len(signs) > 1 else ("SUPPORTED" if True in signs else "CONTRADICTED")
    rows.append(make_row(
        "H3-f", f"Cho et al. (2026): the Ru process has a {f(cho7,1)} % lower relative economic cost (REC) than the Ni process.",
        verdict, rowobj=r, singapore_scenario="Cho's operating points rebuilt on AmCraX boundaries.",
        aspen_model="No Aspen run at Cho's operating points: Python only.",
        python_model="amcrax.research.catalyst_comparison Cho rebuild with amcrax.economics.singapore.",
        case_ids=[ni_d, ru_d],
        input_assumptions=["Catalyst inventory basis (kinetic minimum vs Cho's space-velocity charge) and PSA recovery varied.", "CAPEX does not respond to T or P."],
        literature=lit(("cho2026nickel", "Cho et al. 2026: REC of the Ni and Ru processes, Fig. 8d")),
        validation_areas=["catalyst_comparison", "economics"],
        validation_method=f"Cho's own REC difference ({f(rec_ni,3)} vs {f(rec_ru,3)} USD/kg) reproduced as {f(cho7,1)} % (economics.json); AmCraX rebuild informational.",
        uncertainty_range=f"Ru REC lower by {f(rk,1)} % / {f(rg,1)} % (kinetic / GHSV mass, PSA {psa_am:g}) and {f(rk7,1)} % / {f(rg7,1)} % (PSA {psa_cho:g}), against Cho's {f(cho7,1)} %.",
        key_uncertainty="Inventory basis and CAPEX response to temperature (absent in AmCraX); Cho's Ru advantage sits in boiler, exchanger and NOx SCR capital.",
        limitations=load(F_CHO)["boundary_differences"],
        conclusion=f"The sign of the Ru-Ni REC difference changes with the catalyst inventory basis and PSA recovery ({f(min(rk, rg, rk7, rg7),1)} to {f(max(rk, rg, rk7, rg7),1)} %, negative meaning Ru dearer), and no case reaches Cho's value. Cho's {f(cho7,1)} % is not reproduced, but the comparison is boundary-limited.",
        conclusion_conditions="Rule: INCONCLUSIVE if the sign of the REC difference changes across the inventory and PSA cases; otherwise the sign decides.",
        data=["results/research/catalyst_comparison/catalyst_cho_comparison.csv", F_BENCH], figures=[], shots=[]))
    # Final verification (independent review M2): every H3 row carries the extrapolation condition.
    m2 = ("All rate laws are extrapolated to 20 bar from their fit pressure (1 atm; Kum: 10 bar); the Takahashi laws are "
          "evaluated on a mole-fraction basis and the Lucentini laws on concentrations; the Ni/MgO law fails its own "
          "validation (EXISTING-KIN-NI-PRED). No catalyst ranking at 20 bar is a property of the catalysts.")
    for row in rows:
        if m2 not in row["limitations"]:
            row["limitations"] = list(row["limitations"]) + [m2]
    return rows


# --------------------------------------------------------------------------------------------
# H4 Purification
# --------------------------------------------------------------------------------------------
def h4_rows() -> list[dict]:
    rows = []
    C = "cases/20bar_baseline/configs/[id={}]/{}"
    p_r = val(F_PUR, "cases/20bar_baseline/reactor_pressure_bar")
    d_ind = val(F_PUR, "delivery_pressures_bar/industrial_99.9")
    d_fc = val(F_PUR, "delivery_pressures_bar/fuel_cell_grade_D")
    PA = "results/research/purification/assumptions.json"
    sg = (f"Jurong Island cracker, {f(p_r,0)} bar Aspen baseline cracked gas; base costs use the existing AmCraX economics defaults "
          f"(purification assumptions.json), Singapore NH3 and electricity prices in singapore_price_scenario.json; "
          f"delivery {f(d_ind,0)} bar (industrial, blend) or {f(d_fc,0)} bar (Grade D).")
    p_lit = lit(("iso14687_2019", "ISO 14687:2019 Tables 2-4 (grade D, E3, B limits)"),
                ("cho2026nickel", "Cho et al. 2026: published PSA recovery and purity point"),
                ("hansen2024hysys", "Hansen et al. 2024: lowest published PSA recovery point"),
                ("richard2024technoeconomic", "Richard et al. 2024: Pd-Ag permeability, Table 2"),
                ("cechetto2023membrane", "Cechetto et al. 2023: membrane review, NH3 in permeate"))
    p_figs = ["results/figures/research/purification_recovery_purity.png", "results/figures/research/purification_recovery_cost.png",
              "results/figures/research/purification_config_comparison.png"]
    p_data = ["results/research/purification/purification_configurations.csv", "results/research/purification/psa_recovery_vs_purity.csv"]
    aspen_p = "Stored Aspen Plus V15 baseline stream S7 (cracked gas) and H2PROD; PSA in Aspen is a split block with assumed fractions (no adsorption model)."
    py_p = "amcrax.separation.purification: PSA mass-balance relation, Sieverts membrane with pinch limit, ISO 14687 evaluator."

    # H4-a recovery vs purity trade-off for PSA
    r = Row()
    rc = r.num("PSA recovery, Cho point", F_PUR, C.format("PSA_CHO", "h2_recovery"), "fraction", "literature")
    pc = r.num("PSA purity, Cho point", F_PUR, C.format("PSA_CHO", "product_purity_h2_mole_frac"), "mol fraction", "literature")
    rd = r.num("PSA recovery at Grade D purity, mass-balance relation", F_PUR, C.format("PSA_D_MB", "h2_recovery"), "fraction", "assumption")
    pd_ = r.num("PSA purity for Grade D", F_PUR, C.format("PSA_D_MB", "product_purity_h2_mole_frac"), "mol fraction", "python")
    rl = r.num("PSA recovery, lowest published point applied out of range", F_PUR, C.format("PSA_D_LOW", "h2_recovery"), "fraction", "literature")
    verdict = "INCONCLUSIVE"
    rows.append(make_row(
        "H4-a", "Higher hydrogen purity from PSA costs hydrogen recovery (purity-recovery trade-off).",
        verdict, rowobj=r, singapore_scenario=sg, aspen_model=aspen_p, python_model=py_p,
        case_ids=["PSA_CHO", "PSA_D_MB", "PSA_D_LOW"],
        input_assumptions=[f"PSA recovery at {pct(pd_,3)} purity is not in the library: {f(rd,3)} from holding Cho's tail-H2 fraction (optimistic) and {f(rl,2)} from the lowest published point applied outside its range."],
        literature=p_lit, validation_areas=["purification"],
        validation_method="PSA point reproduction is true by construction (informational); mass closure for all configurations (purification.json).",
        uncertainty_range=f"Recovery at Grade D purity bounded {f(rl,3)}-{f(rd,3)} against {f(rc,3)} at {pct(pc,2)}.",
        key_uncertainty="A sourced PSA recovery at Grade D purity (adsorption-cycle simulation or plant data) would settle the slope.",
        limitations=["Only two usable published PSA points (Cho; Hansen), at different adsorbents and pressures; the Mehr points are mutually inconsistent.",
                     "The mass-balance relation is flat by construction and is not evidence of a small penalty."],
        conclusion=f"The model cannot test the PSA trade-off: the recovery at Grade D purity ({f(rd,3)}) is set by an assumed relation, not computed, and the alternative bound ({f(rl,2)}) is extrapolated.",
        conclusion_conditions="Rule: INCONCLUSIVE because the recovery at the purity of interest is an assumption built into the model.",
        data=p_data, figures=["results/figures/research/purification_recovery_purity.png"], shots=[]))

    # H4-b purity requirement drives cost per end use
    r = Row()
    raw = r.num("cost usable H2, raw cracked gas for turbine blend", F_PUR, C.format("RAW", "costs/turbine_blend/usd_per_kg_usable_h2"), "USD/kg H2", "python")
    ind = r.num("cost usable H2, industrial 99.9 %, PSA_AMCRAX (industrial delivery)", F_PUR, C.format("PSA_AMCRAX", "costs/industrial_99.9/usd_per_kg_usable_h2"), "USD/kg H2", "python")
    dmb = r.num("cost usable H2, Grade D, PSA_D_MB (fuel-cell delivery)", F_PUR, C.format("PSA_D_MB", "costs/fuel_cell_grade_D/usd_per_kg_usable_h2"), "USD/kg H2", "python")
    dlo = r.num("cost usable H2, Grade D, PSA_D_LOW (fuel-cell delivery)", F_PUR, C.format("PSA_D_LOW", "costs/fuel_cell_grade_D/usd_per_kg_usable_h2"), "USD/kg H2", "python")
    po_b = r.num("purification-only cost, PSA_D_MB at industrial delivery", F_PUR, C.format("PSA_D_MB", "costs/industrial_99.9/purification_only_usd_per_kg"), "USD/kg H2", "python")
    po_a = r.num("purification-only cost, PSA_AMCRAX at industrial delivery", F_PUR, C.format("PSA_AMCRAX", "costs/industrial_99.9/purification_only_usd_per_kg"), "USD/kg H2", "python")
    ce30 = r.num("compression energy to industrial delivery, PSA", F_PUR, C.format("PSA_D_MB", "costs/industrial_99.9/compression_kWh_per_kg_h2"), "kWh/kg H2", "python")
    ce350 = r.num("compression energy to fuel-cell delivery, PSA", F_PUR, C.format("PSA_D_MB", "costs/fuel_cell_grade_D/compression_kWh_per_kg_h2"), "kWh/kg H2", "python")
    ra = r.num("PSA recovery, PSA_AMCRAX (assumed split)", F_PUR, C.format("PSA_AMCRAX", "h2_recovery"), "fraction", "assumption")
    rdb = val(F_PUR, C.format("PSA_D_MB", "h2_recovery"))
    rlb = val(F_PUR, C.format("PSA_D_LOW", "h2_recovery"))
    SPS = "results/research/purification/singapore_price_scenario.json"
    SR = "rows/[nh3_price_case={};config={};end_use={}]/usd_per_kg_usable_h2"
    cases = sorted({x["nh3_price_case"] for x in load(SPS)["rows"]})
    sg_ok = True
    for pc_ in cases:
        tag = pc_.replace("nh3_price_", "")
        s_raw = r.num(f"Singapore prices ({tag}): raw gas, turbine blend", SPS, SR.format(pc_, "RAW", "turbine_blend"), "USD/kg H2", "python")
        s_ind = r.num(f"Singapore prices ({tag}): PSA_AMCRAX, industrial", SPS, SR.format(pc_, "PSA_AMCRAX", "industrial_99.9"), "USD/kg H2", "python")
        s_dmb = r.num(f"Singapore prices ({tag}): PSA_D_MB, Grade D", SPS, SR.format(pc_, "PSA_D_MB", "fuel_cell_grade_D"), "USD/kg H2", "python")
        s_dlo = r.num(f"Singapore prices ({tag}): PSA_D_LOW, Grade D", SPS, SR.format(pc_, "PSA_D_LOW", "fuel_cell_grade_D"), "USD/kg H2", "python")
        sg_ok = sg_ok and (s_raw < s_ind < min(s_dmb, s_dlo))
    ordered = raw < ind < min(dmb, dlo) and sg_ok
    # Final verification: raw < purified holds by construction (a purification step only adds cost), and the
    # industrial-to-Grade-D step is set by the assumed PSA recoveries (H4-a: recovery at Grade D purity is an
    # assumed relation) plus the higher delivery pressure. The ordering reproduces assumptions, so not SUPPORTED.
    recoveries_assumed = True
    verdict = ("SUPPORTED" if ordered else "INCONCLUSIVE") if not recoveries_assumed else "INCONCLUSIVE"
    rows.append(make_row(
        "H4-b", "Purification must be matched to the end use: stricter purity requirements raise the cost per kg of usable hydrogen.",
        verdict, rowobj=r, singapore_scenario=sg, aspen_model=aspen_p, python_model=py_p,
        case_ids=["RAW", "PSA_AMCRAX", "PSA_D_MB", "PSA_D_LOW"],
        input_assumptions=[f"PSA recoveries are assumed ({f(ra,2)} AmCraX; {f(rdb,3)} and {f(rlb,2)} bounds for Grade D).",
                           "TSA regeneration energy, compression CAPEX, membrane housing and skid not modelled: purified-route costs are lower bounds.",
                           f"Grade D cost includes delivery to {f(d_fc,0)} bar; industrial and blend to {f(d_ind,0)} bar."],
        literature=p_lit, validation_areas=["purification"],
        validation_method="Component and mass closure for all configuration/case combinations; ISO limit transcription (purification.json).",
        uncertainty_range=f"Grade D cost {f(dmb)}-{f(dlo)} USD/kg across the two recovery bounds (base economics); the ordering raw < industrial < Grade D {'holds' if sg_ok else 'does not hold'} at both bounds and at every Singapore NH3 price case ({len(cases)} cases, Singapore electricity price). Unmodelled costs only add to the purified routes.",
        key_uncertainty="If membrane routes meet Grade D (conditional on H2/N2 selectivity, see H4-d) the Grade D penalty shrinks, but stays above the raw-gas cost.",
        limitations=["Part of the Grade D increment is delivery pressure ({} vs {} kWh/kg compression), not purity.".format(f(ce350), f(ce30)),
                     "Contaminants other than NH3, N2 and H2O are not evaluated for Grade D."],
        conclusion=f"Cost per kg usable H2 rises with the purity requirement: {f(raw)} (raw gas for a turbine blend), {f(ind)} (99.9 % industrial), {f(dmb)}-{f(dlo)} USD/kg (Grade D candidate at {f(d_fc,0)} bar). At equal {f(d_ind,0)} bar delivery the purification step costs {f(po_a,3)} (PSA_AMCRAX) against {f(po_b,3)} USD/kg (PSA at Grade D purity). The ordering is set by the model's inputs: raw gas skips purification, and the Grade D increment comes from assumed PSA recoveries (see H4-a) and the higher delivery pressure. The magnitudes are lower bounds, not a test of the hypothesis.",
        conclusion_conditions=f"Rule: SUPPORTED if raw < industrial < both Grade D bounds in the base case and in every Singapore price case and the recoveries that set the Grade D increment are computed, not assumed; otherwise INCONCLUSIVE (here the recoveries are assumed, so the ordering, which {'holds' if ordered else 'does not hold'}, reproduces an assumption). Conditions: {f(p_r,0)} bar baseline gas, grey NH3, assumed recoveries; costs are lower bounds for purified routes.",
        data=p_data + ["results/research/purification/recovery_vs_cost.csv", "results/research/purification/singapore_price_scenario.csv"],
        figures=p_figs, shots=[]))

    # H4-c published PSA point vs specs
    r = Row()
    rcho = r.num("H2 recovery, Cho PSA point", F_PUR, C.format("PSA_CHO", "h2_recovery"), "fraction", "literature")
    n2c = r.num("N2 in product, Cho PSA point", F_PUR, C.format("PSA_CHO", "product_ppm/N2"), "ppm", "python")
    pcho = r.num("H2 purity, Cho PSA point", F_PUR, C.format("PSA_CHO", "product_purity_h2_mole_frac"), "mol fraction", "literature")
    n2_aspen = r.num("N2 in product, PSA_AMCRAX (Aspen baseline split)", F_PUR, C.format("PSA_AMCRAX", "product_ppm/N2"), "ppm", "assumption")
    meets_b = resolve(F_PUR, C.format("PSA_CHO", "spec_evaluation/B/meets_within_model_scope"))
    meets_d = resolve(F_PUR, C.format("PSA_CHO", "spec_evaluation/D/meets_within_model_scope"))
    aspen_d = resolve(F_PUR, C.format("PSA_AMCRAX", "spec_evaluation/D/meets_within_model_scope"))
    verdict = "CONTRADICTED" if (meets_b is False and meets_d is False) else "INCONCLUSIVE"
    rows.append(make_row(
        "H4-c", f"A published PSA operating point (Cho: {pct(rcho,1)} recovery at {pct(pcho,2)} H2) is sufficient for hydrogen end uses with ISO 14687 grades.",
        verdict, rowobj=r, singapore_scenario=sg, aspen_model=aspen_p, python_model=py_p,
        case_ids=["PSA_CHO", "PSA_AMCRAX"],
        input_assumptions=["NH3 at the PSA outlet set to the TSA design target rather than computed.",
                           "The Aspen baseline PSA split is an assumption; its purity supports no purity claim."],
        literature=p_lit, validation_areas=["purification"],
        validation_method="ISO 14687 evaluator applied per modelled contaminant (NH3, N2, H2O); P-ISO-2 Aspen H2PROD vs Grade D informational (purification.json).",
        uncertainty_range=f"Cho point: N2 {f(n2c,0)} ppm at {pct(pcho,2)} H2; fails grade B (99.9 %) and grade D on the index alone.",
        key_uncertainty="None for the spec check itself (it follows from the published composition); the industrial usefulness depends on the end user's specification.",
        limitations=["Only NH3, N2 and H2O are evaluated; meeting a grade within model scope is not a fuel-cell grade claim.",
                     f"The Aspen baseline product (N2 {f(n2_aspen,0)} ppm, Grade D within model scope: {aspen_d}) is not Grade D and must not be called fuel-cell grade."],
        conclusion=f"The Cho PSA point does not meet the 99.9 % industrial grade or Grade D (N2 {f(n2c,0)} ppm). Fuel-cell use needs a higher-purity PSA plus NH3 removal, at lower recovery (see H4-a).",
        conclusion_conditions="Rule: CONTRADICTED if the published composition fails both grade B and grade D in the ISO evaluator.",
        data=p_data, figures=["results/figures/research/purification_config_comparison.png"], shots=[]))

    # H4-d membrane vs PSA
    r = Row()
    mem = r.num("cost usable H2, Grade D, Pd-Ag membrane + polishing (350 bar)", F_PUR, C.format("MEM_1bar_polish", "costs/fuel_cell_grade_D/usd_per_kg_usable_h2"), "USD/kg H2", "python")
    mrec = r.num("membrane H2 recovery (design)", F_PUR, C.format("MEM_1bar_polish", "h2_recovery"), "fraction", "assumption")
    marea = r.num("membrane area", F_PUR, C.format("MEM_1bar_polish", "area_m2"), "m2", "python")
    dmb2 = r.num("cost usable H2, Grade D, PSA_D_MB", F_PUR, C.format("PSA_D_MB", "costs/fuel_cell_grade_D/usd_per_kg_usable_h2"), "USD/kg H2", "python")
    nh3raw = r.num("NH3 in membrane permeate without polishing", F_PUR, C.format("MEM_1bar_raw", "product_ppm/NH3"), "ppm", "literature")
    mcost = r.num("membrane cost, Phase 1 point (EUR/m2, converted at the reference USD/EUR)", PA, "[name=Membrane cost]/value", "EUR/m2", "assumption")
    cond = resolve(F_PUR, C.format("MEM_1bar_polish", "costs/fuel_cell_grade_D/conditional_on"))
    # Phase 2 sourced membrane inputs (review B M9: the Phase 1 'infinite selectivity' and 'parity' text is superseded)
    PCI = "inputs/"
    mc_lo = val(F_PC, PCI + "membrane_cost_USD_per_m2/low/value")
    mc_c = val(F_PC, PCI + "membrane_cost_USD_per_m2/central/value")
    mc_hi = val(F_PC, PCI + "membrane_cost_USD_per_m2/high/value")
    usd_eur = val(F_BASE, "inputs/" + esc("currency.usd_per_eur") + "/value")
    sel_lo = val(F_PC, "row_evidence/H4-d/numbers/sourced_selectivity/0")
    sel_hi = val(F_PC, "row_evidence/H4-d/numbers/sourced_selectivity/2")
    sel_req = val(F_PC, "row_evidence/H4-d/numbers/required_selectivity")
    mlife = val(F_PC, PCI + "membrane_life_yr/central/value")
    verdict = "INCONCLUSIVE" if cond else ("SUPPORTED" if mem < dmb2 else "CONTRADICTED")
    rows.append(make_row(
        "H4-d", "A Pd-Ag membrane balances purity, recovery and cost better than PSA for fuel-cell hydrogen.",
        verdict, rowobj=r, singapore_scenario=sg, aspen_model="No Aspen membrane model: Python/literature only.",
        python_model=py_p, case_ids=["MEM_1bar_polish", "MEM_1bar_raw", "PSA_D_MB"],
        input_assumptions=[f"Ideal H2/N2 selectivity {f(sel_lo,0)} to {f(sel_hi,0)} (Cechetto et al. 2021, single gas, new membrane) against a requirement of {f(sel_req,0)}.",
                           f"Membrane cost {f(mc_lo,0)} USD/m2 ({f(mc_lo / usd_eur,0)} EUR at {f(usd_eur,3)} USD/EUR), {f(mc_c,0)} and {f(mc_hi,0)} USD/m2, "
                           f"annualised with the capital recovery factor at the membrane life (central {f(mlife,0)} years); housing, skid and compression CAPEX not modelled.",
                           f"Membrane recovery {f(mrec,2)} is a design choice."],
        literature=p_lit, validation_areas=["purification"],
        validation_method="Sieverts hand calculation and pinch limit checks (purification.json).",
        uncertainty_range=f"Membrane {f(mem)} vs PSA {f(dmb2)} USD/kg; the gap is driven by recovery ({f(mrec,2)} vs PSA bounds) rather than by membrane cost.",
        key_uncertainty=str(cond) if cond else "Selectivity and unmodelled membrane capital.",
        limitations=[f"Without polishing the permeate carries {f(nh3raw,1)} ppm NH3 (measured, Cechetto 2021) and fails Grade D.",
                     "Membrane results are lower bounds on cost."],
        conclusion=f"The membrane route is cheaper on paper ({f(mem)} vs {f(dmb2)} USD/kg, area {f(marea,0)} m2) but meets Grade D only conditionally on a selectivity that no source in the library supports.",
        conclusion_conditions="Rule: INCONCLUSIVE when the membrane Grade D result is conditional on an unsourced selectivity; otherwise cost decides.",
        data=["results/research/purification/membrane_recovery_area_cost.csv", "results/research/purification/membrane_required_selectivity.csv"],
        figures=["results/figures/research/purification_recovery_cost.png", "results/figures/research/purification_sensitivity.png"], shots=[]))

    # H4-e recovery losses vs energy (tail gas)
    r = Row()
    r85 = r.num("PSA recovery, PSA_AMCRAX", F_PUR, C.format("PSA_AMCRAX", "h2_recovery"), "fraction", "assumption")
    r75 = r.num("PSA recovery, PSA_D_MB", F_PUR, C.format("PSA_D_MB", "h2_recovery"), "fraction", "assumption")
    th85 = r.num("tail-gas heat to furnace, PSA_AMCRAX", F_PUR, C.format("PSA_AMCRAX", "tail_heat_to_furnace_kW"), "kW", "python")
    def85 = r.num("net heat deficit, PSA_AMCRAX", F_PUR, C.format("PSA_AMCRAX", "net_heat_deficit_kW"), "kW", "python")
    th75 = r.num("tail-gas heat to furnace, PSA_D_MB", F_PUR, C.format("PSA_D_MB", "tail_heat_to_furnace_kW"), "kW", "python")
    def75 = r.num("net heat deficit, PSA_D_MB", F_PUR, C.format("PSA_D_MB", "net_heat_deficit_kW"), "kW", "python")
    sur = r.num("surplus tail-gas heat not credited, PSA_D_MB", F_PUR, C.format("PSA_D_MB", "surplus_heat_kW_not_credited"), "kW", "python")
    dem = r.num("furnace demand (Aspen baseline external heating)", F_PUR, "cases/20bar_baseline/furnace_demand_kW", "kW", "aspen")
    verdict = "SUPPORTED" if (th75 > th85 and def75 < def85) else "INCONCLUSIVE"
    rows.append(make_row(
        "H4-e", "Recovery losses trade against energy: hydrogen not recovered by purification returns as fuel for the cracker, up to the furnace demand.",
        verdict, rowobj=r, singapore_scenario=sg, aspen_model=aspen_p + " Furnace demand from the stored Aspen baseline.",
        python_model=py_p, case_ids=["PSA_AMCRAX", "PSA_D_MB", "baseline (stored Aspen)"],
        input_assumptions=["Tail gas burned in the cracker furnace with the baseline furnace model; surplus heat beyond the demand is not credited."],
        literature=p_lit, validation_areas=["purification", "economics"],
        validation_method="Mass closure; tail-gas LHV from closed component balances (purification.json).",
        uncertainty_range=f"Tail-gas heat {f(th85,0)} kW at recovery {f(r85,2)} (deficit {f(def85,0)} kW) and {f(th75,0)} kW at the Grade D PSA, recovery {f(r75,3)} (deficit {f(def75,0)} kW, surplus {f(sur,0)} kW not credited) against a demand of {f(dem,0)} kW.",
        key_uncertainty="Whether surplus tail-gas heat has a use on site (credit) and the furnace efficiency; beyond the furnace demand lost H2 is a pure loss.",
        limitations=["Heat-integration effect of placing a membrane on the hot effluent not modelled."],
        conclusion=f"Lower recovery is partly self-compensating: at the Grade D candidate PSA (assumed recovery) the tail gas covers the whole furnace demand ({f(dem,0)} kW) so no NH3 is burned for heat, while at recovery {f(r85,2)} a {f(def85,0)} kW deficit remains. Beyond the demand ({f(sur,0)} kW surplus) the lost hydrogen has no use in this flowsheet.",
        conclusion_conditions=f"Rule: SUPPORTED if lower recovery raises tail-gas heat and lowers the furnace deficit (computed mass and energy balance). Conditions: {f(p_r,0)} bar baseline, furnace model as stated.",
        data=p_data, figures=["results/figures/research/purification_recovery_cost.png"], shots=[]))
    return rows


# --------------------------------------------------------------------------------------------
# Methodology version 2 (docs/research/verdict_methodology_v2.md, fixed before the Phase 2 analyses)
# --------------------------------------------------------------------------------------------
METHODOLOGY_VERSION = 2
METHODOLOGY = "docs/research/verdict_methodology_v2.md"
RELEASE_MATRIX = "results/research_releases/2026-11-23/evidence_matrix.json"
V2_VERDICTS = ("SUPPORTED", "CONTRADICTED", "MIXED", "PARTIALLY SUPPORTED", "INCONCLUSIVE")
EVIDENCE_KINDS = ("numerical_verification", "python_vs_aspen", "literature_comparison", "experimental_validation")
F_BASE = "results/research/reference_scenario/baseline.json"
F_TT = "results/research/enduse/turbine_threshold.json"
F_EUA = "results/research/enduse/assumptions.json"
F_CPR = "results/research/carbon_pricing/row_evidence.json"
F_UQR = "results/research/uq/row_evidence.json"
F_CE = "results/research/catalyst_economics/catalyst_economics.json"
F_HX = "results/research/heat_exchanger/heat_exchanger_study.json"
F_PC = "results/research/purification/phase2_comparison.json"
F_KV = "results/research/kinetics/validity_classification.json"
F_SUP = "results/research/reference_scenario/supersession.json"
F_FD = "results/research/carbon_pricing/feed_dominance.json"
F_FIX = "results/research/fix_pass_2026-11-24.json"
F_CAPA = "results/research/reference_scenario/capex_audit.json"
OUT_FC_JSON = "results/research/phase2_findings_changed.json"
OUT_FC_MD = "docs/research/phase2_findings_changed.md"

# Row roles and components, copied from the table "Row roles (fixed here)" of the methodology document.
# tests/test_phase2_evidence_matrix.py parses that table and checks that this constant equals it.
COMPONENTS = {
    "H1": [("H1-P", "Direct use is preferable where ammonia can be burned directly", ["H1-a", "H1-c"], ["H1-b"]),
           ("H1-Q", "Cracking is justified where molecular hydrogen is the product", ["H1-d"], [])],
    "H2": [("H2-E", "Affordable ammonia is essential to economic competitiveness", ["H2-a", "H2-b"], []),
           ("H2-C", "Low-carbon ammonia is essential to environmental competitiveness", ["H2-c", "H2-d"], []),
           ("H2-X", "Cross-claim: low carbon intensity is rewarded economically", ["H2-e"], [])],
    "H3": [("H3-T", "Lower-temperature operation reduces energy use", ["H3-a", "H3-b"], []),
           ("H3-H", "Heat integration reduces energy use", ["H3-d"], []),
           ("H3-K", "The savings can outweigh a higher catalyst cost", ["H3-c"], ["H3-e", "H3-f"])],
    "H4": [("H4-B", "Purity must be balanced against recovery, energy and cost", ["H4-a", "H4-b", "H4-e"], ["H4-c", "H4-d"])],
}
CROSS_CLAIM = {"H2": "H2-X"}
COMPONENT_RULE = (
    "Component verdict from its primary rows (methodology v2): SUPPORTED if every primary row is SUPPORTED; "
    "CONTRADICTED if no primary row is SUPPORTED and at least half are CONTRADICTED; MIXED if at least one is SUPPORTED "
    "and at least one CONTRADICTED; PARTIALLY SUPPORTED if at least one is SUPPORTED, none is CONTRADICTED and at least "
    "one is INCONCLUSIVE; otherwise INCONCLUSIVE. Secondary rows are reported but do not vote.")
HYPOTHESIS_RULE_V2 = (
    "Hypothesis verdict from its components (methodology v2; the cross-claim H2-X counts as a component): SUPPORTED if "
    "every component is SUPPORTED; CONTRADICTED if no component is SUPPORTED or PARTIALLY SUPPORTED and at least half "
    "are CONTRADICTED; MIXED if at least one component is SUPPORTED or PARTIALLY SUPPORTED and at least one is "
    "CONTRADICTED; PARTIALLY SUPPORTED if at least one component is SUPPORTED or PARTIALLY SUPPORTED, none is "
    "CONTRADICTED and not all are SUPPORTED; otherwise INCONCLUSIVE.")


def component_verdict(primary: list[str]) -> str:
    """Methodology v2 component rule, applied to the verdicts of the primary rows."""
    if not primary:
        raise EvidenceError("component without primary rows")
    for x in primary:
        if x not in VERDICTS:
            raise EvidenceError(f"bad row verdict {x}")
    n, s, c, i = len(primary), primary.count("SUPPORTED"), primary.count("CONTRADICTED"), primary.count("INCONCLUSIVE")
    if s == n:
        return "SUPPORTED"
    if s == 0 and 2 * c >= n:
        return "CONTRADICTED"
    if s >= 1 and c >= 1:
        return "MIXED"
    if s >= 1 and c == 0 and i >= 1:
        return "PARTIALLY SUPPORTED"
    return "INCONCLUSIVE"


def hypothesis_verdict_v2(components: list[str]) -> str:
    """Methodology v2 hypothesis rule, applied to the component verdicts."""
    if not components:
        raise EvidenceError("hypothesis without components")
    for x in components:
        if x not in V2_VERDICTS:
            raise EvidenceError(f"bad component verdict {x}")
    n = len(components)
    good = sum(1 for x in components if x in ("SUPPORTED", "PARTIALLY SUPPORTED"))
    c = components.count("CONTRADICTED")
    if components.count("SUPPORTED") == n:
        return "SUPPORTED"
    if good == 0 and 2 * c >= n:
        return "CONTRADICTED"
    if good >= 1 and c >= 1:
        return "MIXED"
    if good >= 1 and c == 0:
        return "PARTIALLY SUPPORTED"
    return "INCONCLUSIVE"


def role_of(row_id: str) -> tuple[str, str, str]:
    for hid, comps in COMPONENTS.items():
        for cid, _title, prim, sec in comps:
            if row_id in prim:
                return hid, cid, "primary"
            if row_id in sec:
                return hid, cid, "secondary"
    raise EvidenceError(f"row {row_id} has no role in the methodology table")


def fnd(quantity: str, rel: str, key: str, unit: str, source_type: str) -> dict:
    """A value read from a file, kept with its file and key (used in threshold objects)."""
    if source_type not in SOURCE_TYPES:
        raise EvidenceError(f"bad source_type {source_type}")
    return {"quantity": quantity, "value": as_number(resolve(rel, key), rel, key), "unit": unit,
            "source_type": source_type, "source_file": rel, "key": key}


def side(thresholds: list[float], lo: float, hi: float) -> str:
    """Where sourced values [lo, hi] lie relative to every threshold value."""
    if hi < min(thresholds):
        return "below"
    if lo > max(thresholds):
        return "above"
    return "straddle"


def text(rel: str, key: str) -> str:
    v = resolve(rel, key)
    if not isinstance(v, str):
        raise EvidenceError(f"{rel}: {key} is not text")
    return v


def kw_resolution() -> float:
    """Largest Aspen minus Python fired-duty offset at the same T and X (catalyst_economics resolution rows)."""
    rows = load(F_CE)["resolution"]["rows"]
    return max(val(F_CE, f"resolution/rows/{i}/fired_aspen_kW") - val(F_CE, f"resolution/rows/{i}/fired_python_kW")
               for i in range(len(rows)))


def _v2(verdict, rule, *, envelope, threshold, conclusions, assumptions, uncertainty, kinds, conclusion,
        areas, literature=(), extra=None):
    if verdict not in VERDICTS:
        raise EvidenceError(f"bad verdict {verdict}")
    for k in kinds:
        if k not in EVIDENCE_KINDS or k == "experimental_validation":
            raise EvidenceError(f"evidence kind {k} not allowed for a row (AmCraX has no experimental validation)")
    out = {"verdict": verdict, "rule": rule, "envelope": envelope, "threshold": threshold,
           "numerical_conclusions": conclusions, "assumptions": assumptions, "uncertainty": uncertainty,
           "evidence_kinds": list(kinds), "conclusion": conclusion, "areas": areas, "literature": list(literature)}
    if extra:
        out.update(extra)
    return out


# ---- H1 ------------------------------------------------------------------------------------
def v2_h1a(r: Row, v1row: dict) -> dict:
    RE = "row_evidence/H1-a/numbers/"
    d = r.num("LCOE direct NH3 (unified basis)", F_TT, RE + "LCOE_direct", "USD/MWh", "python")
    ff = r.num("LCOE fired cracking (unified basis)", F_TT, RE + "LCOE_full_fired", "USD/MWh", "python")
    fp = r.num("LCOE cracking + PSA (unified basis)", F_TT, RE + "LCOE_full_purified", "USD/MWh", "python")
    gf = r.num("direct cheaper than fired cracking, 1 - d/c", F_TT, RE + "direct_cheaper_pct_fired", "%", "python")
    gp = r.num("direct cheaper than cracking + PSA, 1 - d/c", F_TT, RE + "direct_cheaper_pct_purified", "%", "python")
    eta = r.num("turbine efficiency assumed on H2-rich fuel (copy of direct NH3)", F_EUA, "[name=eta_gt_gas]/value", "fraction", "assumption")
    halves = {}
    for half, path in (("fired", "full_fired"), ("purified", "full_purified")):
        bases = list(load(F_TT)["thresholds"][path]["bases"])
        vals = [fnd(f"threshold gain in turbine efficiency on fuel LHV, {path}, basis {b}", F_TT,
                    f"thresholds/{path}/bases/{esc(b)}/delta_fuel_pp_vs_direct_turbine", "pp", "python") for b in bases]
        halves[half] = vals
    thr_f_ref = r.num("threshold, fired cracking (reference basis)", F_TT, "thresholds/full_fired/threshold_delta_pp_reference", "pp", "python")
    thr_p_ref = r.num("threshold, cracking + PSA (reference basis)", F_TT, "thresholds/full_purified/threshold_delta_pp_reference", "pp", "python")
    FE = "cracker_heat_fuel_efficiency_sensitivity/cases/"
    n_fe = len(load(F_TT)["cracker_heat_fuel_efficiency_sensitivity"]["cases"])
    fe_t = [r.num(f"fired-cracking threshold with cracker heat delivered at {val(F_TT, FE + f'{i}/heat_fuel_efficiency'):g} of the fuel LHV",
                  F_TT, FE + f"{i}/full_fired/threshold_delta_fuel_pp_vs_direct_turbine", "pp", "python") for i in range(n_fe)]
    fired_src = resolve(F_TT, "sourced_values/fired_H2N2_fuel_delta_pp/sourced")
    p_src = [fnd("NETL pure-H2 minus NH3 combined-cycle efficiency, as a ratio on the AmCraX turbine", F_TT,
                 "sourced_values/purified_H2_fuel_delta_pp/netl_relative_on_AmCraX_turbine", "pp", "literature"),
             fnd("NETL pure-H2 minus NH3 combined-cycle efficiency, absolute (upper bound)", F_TT,
                 "sourced_values/purified_H2_fuel_delta_pp/netl_absolute", "pp", "literature")]
    lo, hi = min(x["value"] for x in p_src), max(x["value"] for x in p_src)
    side_f = "no_source" if fired_src is None else side([x["value"] for x in halves["fired"]], fired_src, fired_src)
    side_p = side([x["value"] for x in halves["purified"]], lo, hi)
    tf = [x["value"] for x in halves["fired"]]
    tp = [x["value"] for x in halves["purified"]]
    if side_f == "below" and side_p == "below":
        v = "SUPPORTED"
    elif side_f == "above" and side_p == "above":
        v = "CONTRADICTED"
    else:
        v = "INCONCLUSIVE"
    rule = ("Threshold rule (methodology v2): the direction rests on the assumed H2-rich-fuel turbine efficiency, so for each "
            "half (fired cracking, cracking + PSA) the efficiency gain at which cracking equals direct use is computed on "
            "every cost basis and compared with sourced gains. SUPPORTED if sourced gains lie below the threshold on every "
            "basis for both halves; CONTRADICTED if above on every basis for both; otherwise INCONCLUSIVE. Here: fired "
            f"half '{side_f}', cracking + PSA half '{side_p}'.")
    return _v2(v, rule,
               envelope=(text(F_TT, "row_evidence/H1-a/envelope") + " The cracking + PSA half holds on all "
                         f"{len(tp)} bases; the fired half has no sourced turbine efficiency."),
               threshold={"parameter": "gain in combined-cycle efficiency on the H2-rich fuel needed for cracking to equal direct use (percentage points)",
                          "values": halves["fired"] + halves["purified"], "sourced_values": p_src,
                          "comparison": {"fired": side_f, "purified": side_p}},
               conclusions=[f"Direct NH3 {f(d,1)} USD/MWh against fired cracking {f(ff,1)} ({f(gf,1)} % cheaper) and cracking + PSA {f(fp,1)} ({f(gp,1)} % cheaper), at the equal-efficiency assumption {pct(eta,2)}.",
                            f"Fired cracking needs +{f(thr_f_ref,2)} pp (range {f(min(tf),2)} to {f(max(tf),2)} over {len(tf)} bases); no turbine efficiency on fired-cracker H2/N2 fuel is sourced.",
                            "With the cracker heat delivered at less than 100 % of the fuel LHV the fired threshold rises: "
                            + ", ".join(f"+{f(fe_t[i],2)} pp at {val(F_TT, FE + f'{i}/heat_fuel_efficiency'):g}" for i in range(n_fe)) + " (reference basis, computed).",
                            f"Cracking + PSA needs +{f(thr_p_ref,2)} pp (range {f(min(tp),2)} to {f(max(tp),2)}), above the only sourced gain ({f(lo,2)} to {f(hi,2)} pp, NETL pure H2, an upper bound) on every basis."],
               assumptions=[f"H2-rich-fuel turbine at the direct-NH3 efficiency {pct(eta,2)} (fired and purified rows only).",
                            text(F_TT, "row_evidence/H1-a/assumptions")],
               uncertainty=text(F_TT, "row_evidence/H1-a/uncertainty"),
               kinds=["numerical_verification", "literature_comparison"],
               conclusion=(f"Under the modelled operating conditions direct NH3 combustion is cheaper than both standalone cracking pathways "
                           f"({f(gf,1)} % and {f(gp,1)} %), at an assumed equal turbine efficiency of {pct(eta,2)}. The cracking + PSA half survives the "
                           "threshold test on every basis against a single sourced gain (NETL 2023/2024, H-class cycle simulation with "
                           f"steam-diluted H2, not like-for-like with the {pct(eta,2)} AmCraX turbine; an upper bound); the fired half "
                           "cannot be tested because no efficiency is sourced, so the row is not SUPPORTED. Cracker heat is counted at "
                           f"100 % of the fuel LHV (optimistic, favourable to cracking): at 0.85 the fired threshold rises from "
                           f"+{f(fe_t[0],2)} to +{f(fe_t[-1],2)} pp (computed)."),
               areas=["enduse"])


def v2_h1b(r: Row, v1row: dict) -> dict:
    claim = r.num("essay figure: direct cheaper than cracking-based power", F_TT, "row_evidence/H1-b/numbers/claim_pct", "%", "literature")
    gmax = r.num("largest computed gap, stored bases", F_TT, "forty_percent_figure/largest_computed_pct", "%", "python")
    gmin = r.num("smallest computed gap, stored bases", F_TT, "forty_percent_figure/smallest_computed_pct", "%", "python")
    gsens = r.num("largest gap in any sensitivity", F_TT, "forty_percent_figure/largest_in_sensitivities_pct", "%", "python")
    xp = r.num("cracker CAPEX factor needed for the essay figure, cracking + PSA", F_TT, "forty_percent_figure/cracker_capex_factor_for_40pct_purified", "-", "python")
    xf = r.num("cracker CAPEX factor needed for the essay figure, fired cracking", F_TT, "forty_percent_figure/cracker_capex_factor_for_40pct_fired", "-", "python")
    v = "CONTRADICTED" if gmax < claim / 2 else "INCONCLUSIVE"
    return _v2(v, "Reproduction rule (unchanged from version 1): CONTRADICTED if the largest computed gap on any stored basis is below half the quoted figure; otherwise INCONCLUSIVE. Secondary row: does not vote.",
               envelope="AmCraX boundaries and the three stored price and hour bases; does not show that Halim et al.'s own calculation is wrong.",
               threshold={"parameter": "half the quoted figure", "values": [fnd("quoted figure", F_TT, "row_evidence/H1-b/numbers/claim_pct", "%", "literature")],
                          "sourced_values": [], "comparison": "largest computed gap below half" if gmax < claim / 2 else "not below half"},
               conclusions=[f"Largest computed gap {f(gmax,1)} % (smallest {f(gmin,1)} %) against the quoted {f(claim,0)} %; {f(gsens,1)} % at most in any sensitivity.",
                            f"The quoted figure would need a cracker CAPEX x{f(xp,1)} (cracking + PSA) or x{f(xf,1)} (fired)."],
               assumptions=["As H1-a; three stored price and operating-hour bases."],
               uncertainty=text(F_TT, "row_evidence/H1-b/uncertainty"),
               kinds=["numerical_verification", "literature_comparison"],
               conclusion=f"The {f(claim,0)} % figure is not reproduced on AmCraX boundaries (at most {f(gmax,1)} %). Halim et al. full text was not accessible.",
               areas=["enduse"])


def v2_h1c(r: Row, v1row: dict) -> dict:
    RE = "row_evidence/H1-c/numbers/"
    fe = r.num("LCOE exhaust-heated full cracking", F_TT, RE + "LCOE_full_exhaust", "USD/MWh", "python")
    pe = r.num("LCOE exhaust-heated partial cracking, 40 vol% H2", F_TT, RE + "LCOE_partial_exhaust_40", "USD/MWh", "python")
    d = r.num("LCOE direct NH3", F_TT, RE + "LCOE_direct", "USD/MWh", "python")
    tref = r.num("threshold system gain, exhaust-heated full cracking (reference basis)", F_TT, RE + "threshold_delta_system_pp_full_exhaust", "pp", "python")
    xcap = r.num("cracker CAPEX factor at which exhaust-heated full cracking equals direct", F_TT, RE + "capex_factor_where_full_exhaust_equals_direct", "-", "python")
    paths = [p for p in load(F_TT)["thresholds"] if p == "full_exhaust" or p.startswith("partial_exhaust_")]
    vals = []
    for p in paths:
        for b in load(F_TT)["thresholds"][p]["bases"]:
            vals.append(fnd(f"threshold full-cracking-equivalent gain, {p}, basis {b}", F_TT,
                            f"thresholds/{p}/bases/{esc(b)}/delta_full_cracking_equivalent_pp", "pp", "python"))
    src = [fnd("supported exhaust-heated system gain, low", F_TT, "sourced_values/exhaust_heated_system_delta_pp/supported_range/0", "pp", "literature"),
           fnd("supported exhaust-heated system gain, high", F_TT, "sourced_values/exhaust_heated_system_delta_pp/supported_range/1", "pp", "literature")]
    lo, hi = src[0]["value"], src[1]["value"]
    s_all = side([x["value"] for x in vals], lo, hi)
    s_ref = side([tref], lo, hi)
    v = {"below": "SUPPORTED", "above": "CONTRADICTED"}.get(s_all, "INCONCLUSIVE")
    tv = [x["value"] for x in vals]
    rule = ("Threshold rule (methodology v2): the row says cracking in front of the turbine does not pay. The exhaust-heat "
            "system-efficiency gain at which each exhaust-heated pathway equals direct use is computed on every basis and "
            "compared with the supported sourced gain. SUPPORTED if sourced gains lie below every threshold (direct cheaper "
            "everywhere); CONTRADICTED if above every threshold (cracking cheaper everywhere); otherwise INCONCLUSIVE. Here: "
            f"'{s_all}' over {len(paths)} pathways and all bases; reference basis, full cracking: '{s_ref}'.")
    return _v2(v, rule,
               envelope=text(F_TT, "row_evidence/H1-c/envelope") + f" The sign flips with the cost basis: cracker CAPEX x{f(xcap,2)} removes the cracking advantage.",
               threshold={"parameter": "exhaust-heat system-efficiency gain needed for cracking to equal direct use (pp, full-cracking equivalent)",
                          "values": vals, "sourced_values": src, "comparison": {"all_bases": s_all, "reference_full_exhaust": s_ref}},
               conclusions=[f"Exhaust-heated full cracking {f(fe,1)} USD/MWh against direct {f(d,1)}: {f(100*(1-fe/d),1)} % cheaper than direct on the reference basis (against the essay).",
                            f"Partial 40 vol% exhaust-heated cracking {f(pe,2)} USD/MWh, equal to direct within {f(abs(pe-d),3)} USD/MWh.",
                            f"Threshold +{f(tref,2)} pp on the reference basis against sourced {f(lo,1)} to {f(hi,1)} pp; thresholds range {f(min(tv),2)} to {f(max(tv),2)} pp over bases and blends."],
               assumptions=[text(F_TT, "row_evidence/H1-c/assumptions")],
               uncertainty=text(F_TT, "row_evidence/H1-c/uncertainty"),
               kinds=["numerical_verification", "literature_comparison"],
               conclusion=("On the reference basis exhaust-heated cracking is slightly cheaper than direct use, which goes against the essay; "
                           "across CAPEX, price and operating-hour bases the threshold moves across the sourced range, so the row is INCONCLUSIVE."),
               areas=["enduse"])


def v2_h1d(r: Row, v1row: dict) -> dict:
    RE = "row_evidence/H1-d/numbers/"
    eh = r.num("NH3 LHV to H2 LHV, cracker + PSA (Aspen)", F_TT, RE + "eta_H2_product", "fraction", "aspen")
    lc = r.num("LCOH grey NH3 450 USD/t", F_TT, RE + "LCOH_grey_USD", "USD/kg H2", "python")
    lcs = r.num("LCOH grey NH3 450 USD/t", F_TT, RE + "LCOH_grey_SGD", "SGD/kg H2", "python")
    r.findings[-1]["usd_counterpart"] = {"source_file": F_TT, "key": RE + "LCOH_grey_USD"}
    bm = r.num("NE Asia SMR production-cost marker", F_TT, RE + "benchmarks/ne_asia_smr_production_cost", "USD/kg H2", "literature")
    bm6 = r.num("delivered low-carbon H2 benchmark, East Asia", F_TT, RE + "benchmarks/blue_delivered_east_asia", "USD/kg H2", "literature")
    FS = "fuel_efficiency_sensitivity/cases/"
    eff_e = [val(F_BASE, FS + f"{i}/fuel_efficiency") for i in range(3)]
    lc_e = [r.num(f"baseline LCOH with supplementary NH3 fuel at {eff_e[i]:g} of its LHV", F_BASE, FS + f"{i}/lcoh_USD_per_kg", "USD/kg H2", "python")
            for i in range(3)]
    kd = r.num("electricity per kg NH3, direct", F_TT, RE + "kWh_per_kg_NH3/direct", "kWh/kg NH3", "python")
    kc = r.num("electricity per kg NH3, cracking + PSA at the efficiency copy", F_TT, RE + "kWh_per_kg_NH3/cracked_purified_at_eta_copy", "kWh/kg NH3", "python")
    src = [fnd("electricity per kg NH3, cracking + PSA at NETL gain as a ratio", F_TT, RE + "kWh_per_kg_NH3/cracked_purified_at_NETL_ratio_1p1225", "kWh/kg NH3", "python"),
           fnd("electricity per kg NH3, cracking + PSA at NETL gain absolute", F_TT, RE + "kWh_per_kg_NH3/cracked_purified_at_NETL_plus_7p3pp_absolute", "kWh/kg NH3", "python")]
    lo, hi = min(x["value"] for x in src), max(x["value"] for x in src)
    s = side([kd], lo, hi)
    v = {"below": "SUPPORTED", "above": "CONTRADICTED"}.get(s, "INCONCLUSIVE")
    rule = ("Energy rule (methodology v2): the 'larger loss when H2 is an intermediate fuel' half is tested at sourced H2-turbine "
            "efficiencies, not at the assumed copy. SUPPORTED if cracking + PSA gives less electricity per kg NH3 than direct "
            "combustion at every sourced efficiency; CONTRADICTED if more at every sourced efficiency; otherwise INCONCLUSIVE. "
            f"Here the sourced range gives '{s}' relative to direct.")
    return _v2(v, rule,
               envelope=text(F_TT, "row_evidence/H1-d/envelope"),
               threshold={"parameter": "electricity per kg NH3 of cracking + PSA at sourced turbine gains, against direct combustion",
                          "values": [fnd("electricity per kg NH3, direct", F_TT, RE + "kWh_per_kg_NH3/direct", "kWh/kg NH3", "python")],
                          "sourced_values": src, "comparison": s},
               conclusions=[f"H2 as product keeps {pct(eh)} of the NH3 LHV (Aspen).",
                            f"Electricity per kg NH3: direct {f(kd,3)}; cracking + PSA {f(kc,3)} at the efficiency copy, {f(lo,3)} to {f(hi,3)} at the NETL gains (straddles direct).",
                            f"Cracked H2 costs {f(lc,3)} USD/kg ({f(lcs,3)} SGD/kg), above the {f(bm,2)} USD/kg NE Asia SMR marker and below the "
                            f"{f(bm6,1)} USD/kg delivered low-carbon benchmark (fuel counted at 100 % of its lower heating value, optimistic; "
                            f"{f(lc_e[1],3)} to {f(lc_e[2],3)} USD/kg at fuel efficiencies {f(eff_e[1],4)} and {f(eff_e[2],2)})."],
               assumptions=[text(F_TT, "row_evidence/H1-d/assumptions")],
               uncertainty=text(F_TT, "row_evidence/H1-d/uncertainty"),
               kinds=["python_vs_aspen", "numerical_verification", "literature_comparison"],
               conclusion=(f"The conversion loss for power depends on the H2 turbine efficiency: at sourced gains cracking + PSA gives about the same "
                           f"electricity as direct combustion, so the energy half is unresolved; cracked H2 is dearer than the {f(bm,2)} USD/kg NE Asia "
                           f"SMR marker and cheaper than the {f(bm6,1)} USD/kg delivered low-carbon benchmark, so the cost comparison depends on the benchmark."),
               areas=["enduse"])


# ---- H2 ------------------------------------------------------------------------------------
def v2_h2a(r: Row, v1row: dict) -> dict:
    RE = "row_evidence/H2-a/"
    share = r.num("feed share of LCOH (grey, HI on)", F_CPR, RE + "numbers/feed_share", "fraction", "python")
    lc = r.num("LCOH grey (reference scenario)", F_CPR, RE + "numbers/lcoh_USD_per_kg", "USD/kg H2", "python")
    t50 = r.num("NH3 price at which feed is half of LCOH (base)", F_UQR, RE + "numbers/nh3_price_threshold_feed_share_50pct_USD_per_t/base", "USD/t", "python")
    t50a = r.num("same, adverse non-feed inputs", F_UQR, RE + "numbers/nh3_price_threshold_feed_share_50pct_USD_per_t/" + esc("adverse_capex1.5_psa0.756_cat_life1_price2x_hours7000"), "USD/t", "python")
    t50h = r.num("same, heat integration off", F_UQR, RE + "numbers/nh3_price_threshold_feed_share_50pct_USD_per_t/heat_integration_off_base", "USD/t", "python")
    pmin = r.num("lowest sourced NH3 price", F_UQR, RE + "numbers/lowest_sourced_nh3_price_USD_per_t", "USD/t", "literature")
    # one comparator throughout (fix pass 24 Nov 2026, review C M4): feed above 50 % of LCOH
    cx300 = r.num("CAPEX multiple at which the feed share falls to 50 % of LCOH, 300 USD/t", F_FD, "thresholds/capex_multiple/[nh3_price_USD_per_t=300]/feed_share_falls_to_50pct", "-", "python")
    cx450 = r.num("CAPEX multiple at which the feed share falls to 50 % of LCOH, 450 USD/t", F_FD, "thresholds/capex_multiple/[nh3_price_USD_per_t=450]/feed_share_falls_to_50pct", "-", "python")
    cxmax = r.num("largest CAPEX multiplier in the Cho Table 8 sensitivity (a sensitivity bound, not a sourced plant cost)", F_CPR, RE + "threshold/sourced_capex_multiplier_max", "-", "literature")
    ind_lo = val(F_CAPA, "independent_range_USD/0") / val(F_CAPA, "methods_on_amcrax_baseline/reference_cho2026_itemised_v1/capex_total_USD")
    ind_hi = val(F_CAPA, "independent_range_USD/1") / val(F_CAPA, "methods_on_amcrax_baseline/reference_cho2026_itemised_v1/capex_total_USD")
    st = r.num("Sobol total-effect index of NH3 price on LCOH (grey)", F_UQR, RE + "numbers/sobol_nh3_price_lcoh_HIon/grey/ST", "-", "python")
    stlo = r.num("lower 95 % bound of that index", F_UQR, RE + "numbers/sobol_nh3_price_lcoh_HIon/grey/ST_ci/0", "-", "python")
    sthi = r.num("upper 95 % bound of that index", F_UQR, RE + "numbers/sobol_nh3_price_lcoh_HIon/grey/ST_ci/1", "-", "python")
    ok_price = max(t50, t50a, t50h) < pmin
    ok_capex = cx300 > cxmax
    v = "SUPPORTED" if (ok_price and ok_capex) else "INCONCLUSIVE"
    rule = ("Threshold rule (methodology v2): the feed share follows from assumed prices, so the NH3 price at which feed falls to "
            "half of LCOH (base, adverse non-feed inputs, heat integration off) is compared with the lowest sourced NH3 price, and "
            "the CAPEX multiple at which the feed share falls to half of LCOH (at the lowest sourced price; same comparator) with "
            "the largest CAPEX multiplier considered (the Cho Table 8 sensitivity bound; the independent published estimates are "
            "lower). SUPPORTED if every value lies on the feed-dominant side of both thresholds; otherwise "
            f"INCONCLUSIVE. Here: price test {'passed' if ok_price else 'failed'}, CAPEX test {'passed' if ok_capex else 'failed'}. "
            "The Sobol index is reported as supporting evidence, not as the basis.")
    return _v2(v, rule,
               envelope=(f"Feed above 50 % of LCOH for NH3 above {f(t50,0)} USD/t (CAPEX x1) and for CAPEX below x{f(cx450,2)} at "
                         f"450 USD/t (x{f(cx300,2)} at 300 USD/t). The CAPEX multipliers considered reach x{f(cxmax,2)} (Cho Table 8 "
                         f"sensitivity bound); the independent published estimates correspond to x{f(ind_lo,2)} to x{f(ind_hi,2)}."),
               threshold={"parameter": "NH3 price for a 50 % feed share; CAPEX multiple at which the feed share falls to 50 %",
                          "values": [fnd("NH3 price threshold, base", F_UQR, RE + "numbers/nh3_price_threshold_feed_share_50pct_USD_per_t/base", "USD/t", "python"),
                                     fnd("NH3 price threshold, adverse", F_UQR, RE + "numbers/nh3_price_threshold_feed_share_50pct_USD_per_t/" + esc("adverse_capex1.5_psa0.756_cat_life1_price2x_hours7000"), "USD/t", "python"),
                                     fnd("CAPEX multiple threshold (50 % feed share) at 300 USD/t", F_FD, "thresholds/capex_multiple/[nh3_price_USD_per_t=300]/feed_share_falls_to_50pct", "-", "python")],
                          "sourced_values": [fnd("lowest sourced NH3 price", F_UQR, RE + "numbers/lowest_sourced_nh3_price_USD_per_t", "USD/t", "literature"),
                                             fnd("largest CAPEX multiplier in the Cho Table 8 sensitivity", F_CPR, RE + "threshold/sourced_capex_multiplier_max", "-", "literature")],
                          "comparison": {"price": "sourced above threshold" if ok_price else "straddle or below",
                                         "capex": "multipliers below threshold" if ok_capex else "straddle or above"}},
               conclusions=[f"Feed is {pct(share)} of LCOH {f(lc,3)} USD/kg.",
                            f"Feed stays above half of LCOH down to {f(t50,0)} USD/t ({f(t50a,0)} with adverse non-feed inputs, {f(t50h,0)} without heat integration); the lowest sourced price is {f(pmin,0)} USD/t.",
                            f"Feed stays above half of LCOH up to CAPEX x{f(cx450,2)} (x{f(cx300,2)} at 300 USD/t); the largest multiplier considered is x{f(cxmax,2)} (Cho Table 8 sensitivity bound), and the independent published estimates correspond to x{f(ind_lo,2)} to x{f(ind_hi,2)}.",
                            f"Sobol total-effect index of the NH3 price {f(st,3)} [{f(stlo,3)}, {f(sthi,3)}]."],
               assumptions=resolve(F_CPR, RE + "assumptions") + resolve(F_UQR, RE + "assumptions"),
               uncertainty=text(F_UQR, RE + "uncertainty") + " " + text(F_CPR, RE + "uncertainty"),
               kinds=["numerical_verification", "literature_comparison"],
               conclusion="Ammonia price dominates the cost of cracked hydrogen on every sourced price and CAPEX basis. Caveat: the cost excluding feed (REC) is driven by CAPEX and PSA recovery, not by the NH3 price.",
               areas=["carbon_pricing", "uq", "economics"], literature=lit(("saltelli2010sobol", "Sobol estimator")))


def v2_h2b(r: Row, v1row: dict) -> dict:
    RE = "row_evidence/H2-b/numbers/"
    be = r.num("break-even NH3 price against NE Asia SMR 3.06 USD/kg", F_CPR, RE + "breakeven_vs_ne_asia_smr_USD_per_t", "USD/t", "python")
    caps = list(resolve(F_CPR, RE + "breakeven_by_capex_multiplier"))
    bes = [fnd(f"break-even NH3 price, {c}", F_CPR, RE + "breakeven_by_capex_multiplier/" + esc(c), "USD/t", "python") for c in caps]
    prices = [fnd(f"central sourced NH3 price, {k}", F_CPR, RE + f"scenario_prices_USD_per_t/{k}/value", "USD/t", "literature")
              for k in resolve(F_CPR, RE + "scenario_prices_USD_per_t")]
    lows = [val(F_CPR, RE + f"scenario_prices_USD_per_t/{k}/low") for k in resolve(F_CPR, RE + "scenario_prices_USD_per_t")]
    p = r.num("Monte Carlo P(LCOH < 3.06), grey, under the assumed input distributions", F_CPR, RE + "mc_P_lcoh_below_3p06_grey", "probability", "python")
    bfav = r.num("break-even NH3 price against the 3.06 USD/kg marker, favourable non-feed inputs", F_UQR,
                 "row_evidence/H2-b/numbers/breakeven_nh3_price_favourable_nonfeed_inputs_USD_per_t", "USD/t", "python")
    b6 = r.num("break-even NH3 price against the 6.0 USD/kg delivered low-carbon benchmark", F_FD,
               "breakeven_nh3_USD_per_t/blue_delivered_east_asia", "USD/t", "python")
    bm6 = r.num("delivered low-carbon H2 benchmark, East Asia", F_FD, "breakeven_benchmarks_USD_per_kg/blue_delivered_east_asia", "USD/kg H2", "literature")
    bm3 = r.num("NE Asia SMR production-cost marker", F_FD, "breakeven_benchmarks_USD_per_kg/ne_asia_smr_production_cost", "USD/kg H2", "literature")
    skeys = list(resolve(F_CPR, RE + "scenario_prices_USD_per_t"))
    full = ([fnd(f"sourced NH3 price, {k}, low", F_CPR, RE + f"scenario_prices_USD_per_t/{k}/low", "USD/t", "literature") for k in skeys]
            + [fnd(f"sourced NH3 price, {k}, high", F_CPR, RE + f"scenario_prices_USD_per_t/{k}/high", "USD/t", "literature") for k in skeys])
    src_lo, src_hi = min(x["value"] for x in full), max(x["value"] for x in full)
    bmax = max(x["value"] for x in bes)
    bmin = min(x["value"] for x in bes)
    pc_min = min(x["value"] for x in prices)
    # Coded threshold rule (fix pass 24 Nov 2026, review A B2): the break-even range against EACH named benchmark is compared
    # with the FULL sourced price ranges (low to high of every scenario). The row ('affordable ammonia is essential') is
    # SUPPORTED if every sourced price lies above the highest break-even for every benchmark (competitiveness needs ammonia
    # cheaper than any sourced price); CONTRADICTED if every sourced price lies below the lowest break-even for every benchmark
    # (competitive at any sourced price, so affordability is not binding); otherwise INCONCLUSIVE and the threshold is the finding.
    thr3 = [x["value"] for x in bes] + [be, bfav]
    s3 = side(thr3, src_lo, src_hi)
    s6 = side([b6], src_lo, src_hi)
    sides = {f"{f(bm3,2)} USD/kg marker": s3, f"{f(bm6,1)} USD/kg delivered benchmark": s6}
    if all(s == "above" for s in sides.values()):
        v = "SUPPORTED"
    elif all(s == "below" for s in sides.values()):
        v = "CONTRADICTED"
    else:
        v = "INCONCLUSIVE"
    rule = ("Threshold rule (methodology v2): the break-even NH3 price is computed against each named benchmark (the "
            f"{f(bm3,2)} USD/kg NE Asia SMR marker over the CAPEX range and with favourable non-feed inputs; the {f(bm6,1)} USD/kg "
            "delivered low-carbon benchmark) and compared with the FULL sourced NH3 price ranges (low to high of every scenario). "
            "SUPPORTED if every sourced price lies above every break-even for every benchmark; CONTRADICTED if every sourced price "
            "lies below every break-even for every benchmark; otherwise INCONCLUSIVE and the threshold is the finding. Here: "
            + "; ".join(f"{k} '{s_}'" for k, s_ in sides.items()) + ". This rule replaces the earlier necessity reading against "
            "the central prices only, which had no way to fail (fix pass 24 Nov 2026).")
    return _v2(v, rule,
               envelope=(f"Plant gate, no compression or delivery. Benchmarks: the {f(bm3,2)} USD/kg NE Asia SMR marker gives a break-even of "
                         f"{f(bmin,0)} to {f(max(bmax, bfav),0)} USD/t (CAPEX x0.41 to x1.5 and favourable non-feed inputs); the "
                         f"{f(bm6,1)} USD/kg delivered low-carbon benchmark gives {f(b6,0)} USD/t. The Singapore willingness-to-pay "
                         f"figure gives {f(val(F_FD, 'breakeven_nh3_USD_per_t/sg_low_carbon_willingness_to_pay'),0)} USD/t and the "
                         f"low-carbon offer FOB Malaysia {f(val(F_FD, 'breakeven_nh3_USD_per_t/low_carbon_offer_fob_malaysia'),0)} USD/t."),
               threshold={"parameter": "NH3 price at which LCOH equals each named benchmark",
                          "values": bes + [fnd("break-even against the 3.06 marker, favourable non-feed inputs", F_UQR,
                                               "row_evidence/H2-b/numbers/breakeven_nh3_price_favourable_nonfeed_inputs_USD_per_t", "USD/t", "python"),
                                           fnd("break-even against the 6.0 delivered benchmark", F_FD, "breakeven_nh3_USD_per_t/blue_delivered_east_asia", "USD/t", "python")],
                          "sourced_values": full, "comparison": sides},
               conclusions=[f"Against the {f(bm3,2)} USD/kg NE Asia SMR marker the break-even NH3 price is {f(be,0)} USD/t ({f(bmin,0)} to {f(bmax,0)} over the CAPEX range; {f(bfav,0)} with favourable non-feed inputs).",
                            f"Against the {f(bm6,1)} USD/kg delivered low-carbon benchmark it is {f(b6,0)} USD/t.",
                            f"Sourced NH3 prices span {f(src_lo,0)} to {f(src_hi,0)} USD/t (central {f(pc_min,0)} or more): they lie on both sides of both break-evens.",
                            f"P(LCOH < 3.06) = {f(p,3)} for grey ammonia, conditional on the assumed triangular input distributions (the lower bound of the assumed NH3 price lies {f(be - min(lows),0)} USD/t below the break-even)."],
               assumptions=resolve(F_CPR, "row_evidence/H2-b/assumptions"),
               uncertainty=text(F_CPR, "row_evidence/H2-b/uncertainty") + " (P conditional on the assumed input distributions.)",
               kinds=["numerical_verification", "literature_comparison"],
               conclusion=(f"The threshold is the finding: competitiveness with the single NE Asia SMR marker ({f(bm3,2)} USD/kg) needs ammonia at or "
                           f"below about {f(be,0)} USD/t ({f(bmin,0)} to {f(max(bmax, bfav),0)} over CAPEX and non-feed inputs), which only the low "
                           f"ends of the sourced price ranges reach; against the {f(bm6,1)} USD/kg delivered low-carbon benchmark the break-even "
                           f"is {f(b6,0)} USD/t. Sourced prices straddle both, so the row is INCONCLUSIVE."
                           if v == "INCONCLUSIVE" else f"Break-even against the named benchmarks: {f(be,0)} and {f(b6,0)} USD/t."),
               areas=["carbon_pricing", "uq", "economics"])


def v2_h2c(r: Row, v1row: dict) -> dict:
    RE = "row_evidence/H2-c/"
    bmax = r.num("highest break-even gate emission factor (power, against NG CCGT or grid)", F_CPR, RE + "threshold/breakeven_gate_ef_max", "kg CO2e/kg NH3", "python")
    bmin = r.num("lowest break-even gate emission factor", F_CPR, RE + "numbers/power_breakeven_gate_ef_range_kgCO2e_per_kgNH3/0", "kg CO2e/kg NH3", "python")
    gmin = r.num("lowest sourced grey gate emission factor", F_CPR, RE + "threshold/grey_gate_ef_min", "kg CO2e/kg NH3", "literature")
    grn = r.num("green NH3 gate emission factor, high", F_CPR, RE + "numbers/green/high", "kg CO2e/kg NH3", "literature")
    b1 = r.num("blue NH3 (Lee v1) gate emission factor, central", F_CPR, RE + "numbers/blue_v1/central", "kg CO2e/kg NH3", "literature")
    v = "SUPPORTED" if (gmin > bmax and grn < bmin) else "INCONCLUSIVE"
    rule = ("Necessity rule (methodology v2 threshold form): SUPPORTED if the lowest sourced grey gate factor lies above the highest "
            "computed break-even (grey can never cut power-sector emissions) and a low-carbon route lies below the lowest break-even "
            "over its whole sourced range; otherwise INCONCLUSIVE.")
    return _v2(v, rule, envelope=text(F_CPR, RE + "envelope"),
               threshold={"parameter": "gate emission factor of NH3 at which NH3 power equals the fossil comparator",
                          "values": [fnd("lowest break-even", F_CPR, RE + "numbers/power_breakeven_gate_ef_range_kgCO2e_per_kgNH3/0", "kg CO2e/kg NH3", "python"),
                                     fnd("highest break-even", F_CPR, RE + "threshold/breakeven_gate_ef_max", "kg CO2e/kg NH3", "python")],
                          "sourced_values": [fnd("grey low", F_CPR, RE + "threshold/grey_gate_ef_min", "kg CO2e/kg NH3", "literature"),
                                             fnd("green high", F_CPR, RE + "numbers/green/high", "kg CO2e/kg NH3", "literature")],
                          "comparison": "grey above, green below" if v == "SUPPORTED" else "straddle"},
               conclusions=[f"Break-even gate factor {f(bmin,2)} to {f(bmax,2)} kg CO2e/kg NH3; lowest sourced grey value {f(gmin,2)}; green at most {f(grn,2)}.",
                            f"Not sufficient: blue (Lee v1, central {f(b1,2)}) passes only in part of its range."],
               assumptions=resolve(F_CPR, RE + "assumptions"), uncertainty=text(F_CPR, RE + "uncertainty"),
               kinds=["numerical_verification", "literature_comparison"],
               conclusion="Low-carbon ammonia is necessary for ammonia power to cut emissions against Singapore alternatives; grey ammonia cannot.",
               areas=["carbon_pricing", "lca"])


def v2_h2d(r: Row, v1row: dict) -> dict:
    RE = "row_evidence/H2-d/"
    bkeys = list(resolve(F_CPR, RE + "numbers/breakeven_vs_smr_unabated"))
    bvals = [fnd(f"break-even gate factor against unabated SMR at {k} kg CO2e/kg H2", F_CPR, RE + f"numbers/breakeven_vs_smr_unabated/{k}", "kg CO2e/kg NH3", "python") for k in bkeys]
    bmax = r.num("highest break-even gate factor against unabated SMR", F_CPR, RE + "threshold/breakeven_gate_ef_vs_smr_unabated_max", "kg CO2e/kg NH3", "python")
    gmin = r.num("lowest sourced grey gate factor", F_CPR, RE + "threshold/grey_gate_ef_min", "kg CO2e/kg NH3", "literature")
    grn = r.num("green NH3 gate factor, high", F_CPR, "row_evidence/H2-c/numbers/green/high", "kg CO2e/kg NH3", "literature")
    gci = r.num("cracked H2 carbon intensity, grey, low end", F_CPR, RE + "numbers/ci_kgCO2e_per_kgH2/grey/low", "kg CO2e/kg H2", "python")
    gr = r.num("cracked H2 carbon intensity, green, central", F_CPR, RE + "numbers/ci_kgCO2e_per_kgH2/green/central", "kg CO2e/kg H2", "python")
    bmin = min(x["value"] for x in bvals)
    ccs = [val(F_CPR, RE + f"numbers/breakeven_vs_smr_ccs/{k}") for k in resolve(F_CPR, RE + "numbers/breakeven_vs_smr_ccs")]
    v = "SUPPORTED" if (gmin > bmax and grn < bmin) else "INCONCLUSIVE"
    ccs_green = "passes in every case" if grn < min(ccs) else (f"passes only below {f(min(ccs),2)}-{f(max(ccs),2)} (its high value {f(grn,2)} fails "
                                                               "the lowest-CCS case)")
    rule = ("Necessity rule (methodology v2 threshold form): SUPPORTED if the lowest sourced grey gate factor lies above the highest "
            "break-even against unabated SMR and a low-carbon route lies below the lowest break-even over its whole sourced range; "
            f"otherwise INCONCLUSIVE. Against SMR + CCS (break-even {f(min(ccs),2)}-{f(max(ccs),2)}, reported, not voted) grey fails; "
            f"green {ccs_green}.")
    return _v2(v, rule, envelope=text(F_CPR, RE + "envelope"),
               threshold={"parameter": "gate factor at which cracked H2 equals unabated SMR", "values": bvals,
                          "sourced_values": [fnd("grey low", F_CPR, RE + "threshold/grey_gate_ef_min", "kg CO2e/kg NH3", "literature"),
                                             fnd("green high", F_CPR, "row_evidence/H2-c/numbers/green/high", "kg CO2e/kg NH3", "literature")],
                          "comparison": "grey above, green below" if v == "SUPPORTED" else "straddle"},
               conclusions=[f"Break-even gate factor {f(bmin,2)} to {f(bmax,2)}; lowest grey {f(gmin,2)}.",
                            f"Grey cracked H2 is at least {f(gci,1)} kg CO2e/kg H2; green central {f(gr,2)}."],
               assumptions=resolve(F_CPR, RE + "assumptions"), uncertainty=text(F_CPR, RE + "uncertainty"),
               kinds=["numerical_verification", "literature_comparison"],
               conclusion="Low-carbon ammonia is necessary for cracked hydrogen to be less carbon-intensive than unabated fossil hydrogen.",
               areas=["carbon_pricing", "lca"])


def v2_h2e(r: Row, v1row: dict) -> dict:
    A = "row_evidence/H2-e_mode_A_actual_policy/"
    B = "row_evidence/H2-e_mode_B_hypothetical_conditional/"
    tax = r.num("carbon tax, every NH3 route (actual Singapore boundary)", F_CPR, A + "numbers/carbon_tax_USD_per_kg_all_routes", "USD/kg H2", "python")
    lg = r.num("LCOH grey", F_CPR, A + "numbers/lcoh_by_route_USD_per_kg/grey", "USD/kg H2", "python")
    lb = r.num("LCOH blue", F_CPR, A + "numbers/lcoh_by_route_USD_per_kg/blue", "USD/kg H2", "python")
    lgc = r.num("LCOH green, current price", F_CPR, A + "numbers/lcoh_by_route_USD_per_kg/green_current", "USD/kg H2", "python")
    bc = r.num("hypothetical life-cycle price at which blue overtakes grey, central", F_CPR, B + "numbers/blue_over_grey/central", "SGD/tCO2e", "python")
    blo = r.num("same, low", F_CPR, B + "numbers/blue_over_grey/range/0", "SGD/tCO2e", "python")
    bhi = r.num("same, high", F_CPR, B + "numbers/blue_over_grey/range/1", "SGD/tCO2e", "python")
    gc = r.num("hypothetical price at which green (current) overtakes grey, central", F_CPR, B + "numbers/green_current_over_grey/central", "SGD/tCO2e", "python")
    glo = r.num("same, low", F_CPR, B + "numbers/green_current_over_grey/range/0", "SGD/tCO2e", "python")
    ghi = r.num("same, high", F_CPR, B + "numbers/green_current_over_grey/range/1", "SGD/tCO2e", "python")
    leg = r.num("legislated Singapore carbon tax, 2026 onward", F_CPR, B + "numbers/reference_prices/singapore_legislated_2026_onward", "SGD/tCO2e", "literature")
    a_contra = tax == 0 and lb > lg and lgc > lg
    mode_a = "CONTRADICTED" if a_contra else "INCONCLUSIVE"
    s_b = side([blo, bhi], leg, leg)
    mode_b = "SUPPORTED" if (blo <= leg and bhi <= leg) else ("CONTRADICTED" if (blo > leg and glo > leg) else "INCONCLUSIVE")
    rule = ("Policy rule (methodology v2: a hypothetical scenario cannot change a row about actual policy). Mode A, actual Singapore "
            "boundary (votes): CONTRADICTED if the carbon cost is zero for every NH3 route while low-carbon NH3 raises LCOH; otherwise "
            "INCONCLUSIVE. Mode B, HYPOTHETICAL life-cycle carbon price, not Singapore law (reported separately, does not vote): "
            "SUPPORTED if the price at which low-carbon NH3 overtakes grey lies at or below the legislated rate over its whole range; "
            "CONTRADICTED if blue and green both need more than that rate over their whole ranges; otherwise INCONCLUSIVE. "
            f"Here Mode A {mode_a}, Mode B {mode_b} (blue range '{s_b}' the legislated rate).")
    return _v2(mode_a, rule,
               envelope=text(F_CPR, A + "envelope"),
               threshold={"parameter": "HYPOTHETICAL life-cycle carbon price at which low-carbon NH3 overtakes grey (not Singapore law)",
                          "values": [fnd("blue over grey, low", F_CPR, B + "numbers/blue_over_grey/range/0", "SGD/tCO2e", "python"),
                                     fnd("blue over grey, high", F_CPR, B + "numbers/blue_over_grey/range/1", "SGD/tCO2e", "python"),
                                     fnd("green current over grey, low", F_CPR, B + "numbers/green_current_over_grey/range/0", "SGD/tCO2e", "python"),
                                     fnd("green current over grey, high", F_CPR, B + "numbers/green_current_over_grey/range/1", "SGD/tCO2e", "python")],
                          "sourced_values": [fnd("legislated rate", F_CPR, B + "numbers/reference_prices/singapore_legislated_2026_onward", "SGD/tCO2e", "literature")],
                          "comparison": s_b},
               conclusions=[f"Actual Singapore boundary: carbon tax {f(tax,3)} USD/kg for every route; LCOH grey {f(lg,3)}, blue {f(lb,3)}, green (current price) {f(lgc,3)} USD/kg.",
                            f"Hypothetical life-cycle price, not Singapore law: blue overtakes grey at {f(bc,0)} SGD/t (range {f(blo,0)} to {f(bhi,0)}); green at current prices needs {f(gc,0)} ({f(glo,0)} to {f(ghi,0)}). The legislated rate is {f(leg,0)} SGD/t for 2026 and any later year."],
               assumptions=resolve(F_CPR, A + "assumptions") + ["Mode B: " + a for a in resolve(F_CPR, B + "assumptions")],
               uncertainty=text(F_CPR, A + "uncertainty") + " Mode B: " + text(F_CPR, B + "uncertainty"),
               kinds=["numerical_verification", "literature_comparison"],
               conclusion="Under the actual Singapore carbon tax low carbon intensity earns no cost advantage. Under a hypothetical life-cycle price (not Singapore law) the outcome depends on the price and the carbon-intensity range.",
               areas=["carbon_pricing", "economics"], literature=lit(("nea_carbon_tax", "Singapore carbon tax")),
               extra={"verdict_by_mode": {"actual_sg": mode_a, "hypothetical_lca": mode_b},
                      "mode_note": "The voting verdict is the actual Singapore boundary (a row about actual policy). Mode B is hypothetical and is not Singapore law."})


# ---- H3 ------------------------------------------------------------------------------------
LOWT = ["Ru/Al2O3", "Ru/MgO", "5Ni1Ru/CeO2", "2.5Ni0.5Ru/CeO2"]


def v2_h3a(r: Row, v1row: dict) -> dict:
    RE = "row_evidence/H3-a/numbers/"
    res = kw_resolution()
    hi = {c: r.num(f"fired-duty saving against Ni/MgO at equal conversion, {c}, heat integration on", F_CE, RE + "python_Top_X095_fired_duty_saving_kW_HI/" + esc(c), "kW", "python") for c in LOWT}
    no = {c: r.num(f"same, heat integration off, {c}", F_CE, RE + "python_Top_X095_fired_duty_saving_kW_noHI/" + esc(c), "kW", "python") for c in LOWT}
    tt = {c: val(F_CE, "row_evidence/H3-b/numbers/aspen_T_op_100kg_C/" + esc(c)) for c in LOWT + ["Ni/MgO"]}
    no_reversal = all(hi[c] > -res and no[c] > -res for c in LOWT)
    resolved = [c for c in LOWT if hi[c] > res and no[c] > res]
    v = "SUPPORTED" if (no_reversal and resolved) else "INCONCLUSIVE"
    rule = ("Resolution rule (methodology v2): at equal conversion the fired-duty saving of each low-temperature catalyst against "
            "Ni/MgO is compared with the largest Aspen minus Python fired-duty offset at the same T and X "
            f"({f(res,1)} kW). SUPPORTED if no catalyst shows a reversal beyond that offset and at least one saving exceeds it with "
            "and without heat integration; the envelope is limited to the resolved catalysts. Otherwise INCONCLUSIVE.")
    ext = val(F_HX, "row_evidence/H3-d/numbers/energy_total_external_heating_kW_hi_vs_nohi/0")
    spr = val(F_CE, "resolution/spread_of_fired_duty_offset_between_catalysts_kW")
    return _v2(v, rule,
               # one temperature value only (the smallest resolved difference), both resolution readings, size on two metrics and
               # the cost-optimal reversal: computed in catalyst_economics.py (fix pass 24 Nov 2026, reviews A M3/m5, C M2)
               envelope=("PSA recovery 0.85. " + text(F_CE, "row_evidence/H3-a/envelope")
                         + f" Resolved catalysts on the absolute-offset reading: {', '.join(resolved) or 'none'} (temperature "
                         f"difference from Ni/MgO {', '.join(f(tt['Ni/MgO'] - tt[c],0) for c in resolved)} K)."),
               threshold=None,
               conclusions=[f"Saving with heat integration: " + ", ".join(f"{c} {f(hi[c],1)} kW" for c in LOWT)
                            + f"; resolution {f(res,1)} kW (absolute Python-Aspen offset, used for the verdict); on the spread of that offset ({f(spr,1)} kW) the NiRu savings would also be resolved.",
                            f"The largest saving, {f(max(hi.values()),1)} kW, is {pct(max(hi.values()) / ext, 1)} of the {f(ext,0)} kW total external heating with heat integration (Python only, equal conversion).",
                            f"Saving without heat integration: " + ", ".join(f"{c} {f(no[c],1)} kW" for c in LOWT) + ".",
                            "The Phase 1 figure of 17 % fired duty came from unequal conversion and is withdrawn."],
               assumptions=resolve(F_CE, "row_evidence/H3-a/assumptions"),
               uncertainty=text(F_CE, "row_evidence/H3-a/uncertainty"),
               kinds=["numerical_verification", "python_vs_aspen"],
               conclusion=("At equal conversion (Python) lower-temperature operation reduces fired duty, by at most "
                           f"{f(max(hi.values()),0)} kW with heat integration (about {pct(max(hi.values()) / ext, 0)} of total external heating) and more "
                           "without; the result is resolved only for the two Ru catalysts with the largest temperature difference. "
                           "Cost-optimised Ru designs run hotter and use more energy (see envelope)."),
               areas=["catalyst_economics", "aspen_kinetic", "catalyst_comparison"])


def v2_h3b(r: Row, v1row: dict) -> dict:
    cats = LOWT + ["Ni/MgO"]
    tt = {c: r.num(f"Aspen operating temperature for X 0.95 at 100 kg, {c}", F_CE, "row_evidence/H3-b/numbers/aspen_T_op_100kg_C/" + esc(c), "degC", "aspen") for c in cats}
    cls = {c: text(F_CE, "row_evidence/H3-b/numbers/kinetic_classes/" + esc(c)) for c in cats}
    nv = r.num("rate laws validated at relevant conditions", F_KV, "counts/validated_at_relevant_conditions", "count", "literature")
    nl = r.num("rate laws validated against literature (own fitting data)", F_KV, "counts/validated_against_literature", "count", "literature")
    ne = r.num("rate laws extrapolated", F_KV, "counts/extrapolated", "count", "literature")
    nu = r.num("catalysts without a rate law", F_KV, "counts/unmodelled", "count", "literature")
    all_valid = all(cls[c] == "validated_at_relevant_conditions" for c in cats)
    ordered = all(tt[c] < tt["Ni/MgO"] for c in LOWT)
    v = "SUPPORTED" if (all_valid and ordered) else ("CONTRADICTED" if (all_valid and not ordered) else "INCONCLUSIVE")
    rule = ("Validity rule (methodology v2: no model is called validated outside its checked range): the temperature ordering can "
            "support or contradict the row only if every rate law used is in the class validated_at_relevant_conditions "
            "(kinetics/validity_classification.json); otherwise INCONCLUSIVE.")
    return _v2(v, rule,
               envelope=text(F_CE, "row_evidence/H3-b/envelope"),
               threshold=None,
               conclusions=["Operating temperature at 100 kg: " + ", ".join(f"{c} {f(tt[c],0)}" for c in cats) + " degC.",
                            f"Kinetic validity: {f(nv,0)} laws validated at relevant conditions, {f(nl,0)} validated against literature (their own fitting data), {f(ne,0)} extrapolated, {f(nu,0)} catalysts unmodelled; no rate law is validated at 20 bar."],
               assumptions=resolve(F_CE, "row_evidence/H3-b/assumptions"),
               uncertainty=text(F_CE, "row_evidence/H3-b/uncertainty"),
               kinds=["python_vs_aspen", "literature_comparison"],
               conclusion="The temperature ordering exists in the models but rests on rate laws extrapolated to 20 bar.",
               areas=["kinetics", "aspen_kinetic"])


def v2_h3c(r: Row, v1row: dict) -> dict:
    RE = "row_evidence/H3-c/numbers/"
    res = r.num("Python against Aspen LCOH resolution", F_CE, "resolution/max_abs_python_minus_aspen_lcoh_USD_per_kg", "USD/kg H2", "python")
    net = {c: r.num(f"net LCOH change choosing {c} over Ni/MgO, equal conversion, derived central price (Python values; the key name 'fixed_inventory_aspen' is a mis-name kept for readers)", F_CE, RE + "fixed_inventory_aspen_HI_exchanger/" + esc(c) + "/net_lcoh_delta_USD_per_kg", "USD/kg H2", "python") for c in LOWT}
    bep = {c: r.num(f"break-even catalyst price, {c}", F_CE, RE + "fixed_inventory_aspen_HI_exchanger/" + esc(c) + "/breakeven_price_USD_per_kg", "USD/kg", "python") for c in LOWT}
    cen = {c: r.num(f"derived central catalyst price, {c}", F_CE, RE + "fixed_inventory_aspen_HI_exchanger/" + esc(c) + "/central_price_USD_per_kg", "USD/kg", "literature") for c in LOWT}
    n = len(load(F_CE)["row_evidence"]["H3-c"]["numbers"]["ni_temperature_threshold"])
    thr = [fnd(f"Ni design temperature above which the low-T design is cheaper, case {i}", F_CE, RE + f"ni_temperature_threshold/{i}/Ni_threshold_T_C", "degC", "python") for i in range(n)]
    above = [resolve(F_CE, RE + f"ni_temperature_threshold/{i}/sourced_values_above_threshold") for i in range(n)]
    src = [fnd("sourced Ni design temperature, Cho et al. 2026", F_CE, RE + "ni_temperature_threshold/0/sourced_Ni_design_T_C/cho2026nickel", "degC", "literature"),
           fnd("sourced Ni design temperature, Mehr et al. 2026 (outlet)", F_CE, RE + "ni_temperature_threshold/0/sourced_Ni_design_T_C/mehr2026highcapacity_outlet", "degC", "literature")]
    nimod = r.num("AmCraX Ni/MgO cost-optimal temperature (extrapolated law)", F_CE, RE + "ni_temperature_threshold/0/AmCraX_Ni_costopt_T_C_extrapolated", "degC", "python")
    tv = [x["value"] for x in thr]
    net_no = {c: r.num(f"net LCOH change choosing {c} over Ni/MgO, equal conversion, without heat integration", F_CE,
                       "findings/energy_and_cost/fixed_inventory_aspen_noHI_exchanger/" + esc(c) + "/net_lcoh_delta_USD_per_kg", "USD/kg H2", "python") for c in LOWT}
    t_ni = r.num("Ni/MgO reference temperature at equal conversion (extrapolated law)", F_CE, "row_evidence/H3-b/numbers/aspen_T_op_100kg_C/" + esc("Ni/MgO"), "degC", "aspen")
    dearer = [c for c in LOWT if net[c] > res]
    within = [c for c in LOWT if abs(net[c]) <= res]
    cheaper_no = [c for c in LOWT if net_no[c] < 0]
    any_cheaper = any(net[c] < -res for c in LOWT)
    all_dearer = all(net[c] > res for c in LOWT)
    src_low_t_wins = all(x is True for x in above)
    model_low_t_wins = nimod > max(tv)
    if any_cheaper and src_low_t_wins and model_low_t_wins:
        v = "SUPPORTED"
    elif all_dearer and not any(above) and not model_low_t_wins:
        v = "CONTRADICTED"
    else:
        v = "INCONCLUSIVE"
    rule = ("Cost and threshold rule (methodology v2): SUPPORTED if at least one low-temperature catalyst is cheaper than Ni/MgO by "
            "more than the Python against Aspen resolution at equal conversion and both the sourced Ni design temperatures and the "
            "AmCraX Ni optimum lie above the Ni temperature threshold; CONTRADICTED if every low-temperature catalyst is dearer by more "
            "than the resolution and both lie below the threshold; otherwise INCONCLUSIVE (sourced values and model straddle). Here: "
            f"cheaper at equal conversion {any_cheaper}, dearer for all beyond resolution {all_dearer}, sourced Ni temperatures above "
            f"threshold {src_low_t_wins}, AmCraX Ni optimum above threshold {model_low_t_wins}.")
    return _v2(v, rule,
               envelope=text(F_CE, "row_evidence/H3-c/envelope"),
               threshold={"parameter": "Ni design temperature above which a low-temperature catalyst design is cheaper", "values": thr,
                          "sourced_values": src, "comparison": "sourced above, AmCraX Ni optimum below" if (src_low_t_wins and not model_low_t_wins) else "see rule"},
               conclusions=[(f"With heat integration, at equal conversion, derived central prices and with the Ni reference at its AmCraX-modelled "
                             f"{f(t_ni,0)} degC (extrapolated law), {len(dearer)} of the {len(LOWT)} low-temperature catalysts are dearer than Ni/MgO "
                             f"beyond the {f(res,3)} USD/kg H2 resolution (" + ", ".join(f"{c} +{f(net[c],3)}" for c in dearer) + " USD/kg H2)"
                             + ("; " + ", ".join(f"{c} ({'+' if net[c] >= 0 else ''}{f(net[c],3)})" for c in within) + " is within resolution" if within else "")
                             + "."),
                            ("Without heat integration " + (" and ".join(f"{c} ({f(net_no[c],4)} USD/kg H2)" for c in cheaper_no) + " are slightly cheaper than Ni/MgO."
                                                            if cheaper_no else "no low-temperature catalyst is cheaper than Ni/MgO.")),
                            ("Break-even catalyst prices (each design fixed at its equal-conversion temperature, exchanger mode, central inputs) "
                             + ", ".join(f"{c} {f(bep[c],0)}" for c in LOWT) + " USD/kg against derived central prices " + ", ".join(f"{f(cen[c],0)}" for c in LOWT) + " USD/kg."),
                            f"Ni temperature threshold {f(min(tv),0)} to {f(max(tv),0)} degC: against the sourced Ni design temperatures ({', '.join(f(x['value'],0) for x in src)} degC), every low-temperature design is cheaper; the AmCraX Ni optimum ({f(nimod,0)} degC, extrapolated law) is below the threshold."],
               assumptions=resolve(F_CE, "row_evidence/H3-c/assumptions"),
               uncertainty=text(F_CE, "row_evidence/H3-c/uncertainty"),
               kinds=["numerical_verification", "python_vs_aspen", "literature_comparison"],
               conclusion=(f"With heat integration, at equal conversion, derived central prices and with the Ni reference at its modelled {f(t_ni,0)} degC "
                           f"(extrapolated law), {len(dearer)} of the {len(LOWT)} low-temperature catalysts are dearer beyond the model resolution"
                           + (f"; {', '.join(within)} is within resolution" if within else "")
                           + ("; without heat integration " + " and ".join(cheaper_no) + " are slightly cheaper" if cheaper_no else "")
                           + f"; against sourced Ni design temperatures ({', '.join(f(x['value'],0) for x in src)} degC) every "
                           "low-temperature design is cheaper. The sourced and modelled Ni references straddle the threshold."),
               areas=["catalyst_economics", "catalyst_comparison", "kinetics"], literature=lit(("cho2026nickel", "Ni design temperature and published TEA prices")))


def v2_h3d(r: Row, v1row: dict) -> dict:
    RE = "row_evidence/H3-d/numbers/"
    res = kw_resolution()
    d_on = r.num("first-law heat deficit, heat integration on (Aspen)", F_HX, RE + "energy_first_law_deficit_kW_hi_vs_nohi/0", "kW", "aspen")
    d_off = r.num("first-law heat deficit, heat integration off (Aspen)", F_HX, RE + "energy_first_law_deficit_kW_hi_vs_nohi/1", "kW", "aspen")
    red = r.num("reduction of the first-law deficit", F_HX, RE + "energy_reduction_first_law", "fraction", "aspen")
    gs = r.num("gross fuel saving", F_HX, RE + "baseline_fuel_saving_USD_per_kg", "USD/kg H2", "python")
    nlo = r.num("net saving after exchanger cost, low U", F_HX, RE + "baseline_net_USD_per_kg/low", "USD/kg H2", "python")
    nhi = r.num("net saving after exchanger cost, high U", F_HX, RE + "baseline_net_USD_per_kg/high", "USD/kg H2", "python")
    ub = [fnd("break-even U, low", F_HX, "row_evidence/H3-d/threshold/breakeven_U_W_m2K_range_over_cases/0", "W/(m2 K)", "python"),
          fnd("break-even U, high", F_HX, "row_evidence/H3-d/threshold/breakeven_U_W_m2K_range_over_cases/1", "W/(m2 K)", "python")]
    cat_max = max(val(F_CE, "row_evidence/H3-a/numbers/python_Top_X095_fired_duty_saving_kW_HI/" + esc(c)) for c in LOWT)
    saving = d_off - d_on
    U_SRC = "row_evidence/H3-d/threshold/sourced_typical_U_W_m2K/" + esc("gas ~1 bar both sides")
    usrc = [fnd("sourced typical U, gas ~1 bar both sides, low (VDI Heat Atlas; no value at 20 bar)", F_HX, U_SRC + "/0", "W/(m2 K)", "literature"),
            fnd("sourced typical U, gas ~1 bar both sides, high", F_HX, U_SRC + "/1", "W/(m2 K)", "literature")]
    crf = {u: r.num(f"break-even capital recovery factor (solved), U {u}", F_HX, f"row_evidence/H3-d/breakeven_crf_solved/{u}", "1/yr", "python")
           for u in ("low", "central", "high")}
    worst = r.num("worst net saving over the sensitivities", F_HX, RE + "worst_sensitivity_net_USD_per_kg", "USD/kg H2", "python")
    negs = resolve(F_HX, RE + "net_benefit_negative_in")
    # Two halves, both needed (fix pass 24 Nov 2026, review A M1; same treatment as H1-a).
    if saving > res and saving > cat_max:
        energy = "SUPPORTED"
    elif saving < -res:
        energy = "CONTRADICTED"
    else:
        energy = "INCONCLUSIVE"
    # cost half: threshold rule with the sourced coefficient range; net saving positive above the break-even U
    s_u = side([x["value"] for x in ub], usrc[0]["value"], usrc[1]["value"])
    cost = {"above": "SUPPORTED", "below": "CONTRADICTED"}.get(s_u, "INCONCLUSIVE")
    if energy == "SUPPORTED" and cost == "SUPPORTED":
        v = "SUPPORTED"
    elif "CONTRADICTED" in (energy, cost) and "SUPPORTED" not in (energy, cost):
        v = "CONTRADICTED"
    else:
        v = "INCONCLUSIVE"
    rule = ("Two-half rule (methodology v2; the sub-claim says 'reduces energy use (and cost)', and a row with two halves needs "
            "both, as for H1-a). Energy half: SUPPORTED if heat integration lowers the Aspen first-law heat deficit by more than the "
            f"Python against Aspen fired-duty offset ({f(res,1)} kW) and by more than the largest equal-conversion catalyst-temperature "
            "saving. Cost half, threshold rule: the overall heat-transfer coefficient at which the exchanger cost equals the fuel "
            "saving is compared with the sourced coefficient range; SUPPORTED if the sourced values lie above every break-even U, "
            "CONTRADICTED if below, otherwise INCONCLUSIVE. The row is SUPPORTED only if both halves are SUPPORTED. Here: energy "
            f"half {energy}, cost half {cost} (sourced {f(usrc[0]['value'],0)}-{f(usrc[1]['value'],0)} W/(m2 K) at about 1 bar, "
            f"no value at 20 bar, '{s_u}' the break-even).")
    return _v2(v, rule,
               envelope=(text(F_HX, "row_evidence/H3-d/envelope") + f". Energy: the Aspen first-law deficit falls by {pct(red,0)} on the "
                         "baseline, and the fuel saving is positive in every catalyst case and FEHE approach checked. Cost: the net saving is negative at U below {f(ub[0]['value'],1)}-{f(ub[1]['value'],1)} W/(m2 K) "
                         f"and in {len(negs)} adverse corners (for example " + "; ".join(negs[:3]) + f"); worst case {f(worst,3)} USD/kg. "
                         f"Break-even capital recovery factor (solved) {f(crf['low'],3)} / {f(crf['central'],3)} / {f(crf['high'],3)} at U "
                         "low / central / high."),
               threshold={"parameter": "overall heat-transfer coefficient at which the exchanger cost equals the fuel saving", "values": ub,
                          "sourced_values": usrc, "comparison": {"energy_half": energy, "cost_half": cost, "sourced_U_vs_breakeven": s_u}},
               conclusions=[f"Energy half ({energy}): Aspen first-law heat deficit {f(d_off,0)} kW without and {f(d_on,0)} kW with heat integration ({pct(-red,0)}).",
                            f"That reduction ({f(saving,0)} kW) is larger than the largest equal-conversion catalyst-temperature saving ({f(cat_max,1)} kW).",
                            f"Cost half ({cost}): gross fuel saving {f(gs,3)} USD/kg; net {f(nlo,3)} to {f(nhi,3)} USD/kg after the exchanger cost on the "
                            f"reference basis; break-even U {f(ub[0]['value'],1)} to {f(ub[1]['value'],1)} W/(m2 K) lies inside the only sourced range "
                            f"({f(usrc[0]['value'],0)} to {f(usrc[1]['value'],0)}, about 1 bar); worst sensitivity {f(worst,3)} USD/kg.",
                            f"Break-even capital recovery factor (solved): {f(crf['low'],3)} / {f(crf['central'],3)} / {f(crf['high'],3)} at U low / central / high."],
               assumptions=resolve(F_HX, "row_evidence/H3-d/assumptions"),
               uncertainty=text(F_HX, "row_evidence/H3-d/uncertainty"),
               kinds=["python_vs_aspen", "numerical_verification", "literature_comparison"],
               conclusion=(f"Energy finding: heat integration reduces energy use (first-law heat deficit {f(d_off,0)} to {f(d_on,0)} kW, "
                           f"{pct(-red,0)}), by far more than the catalyst temperature does. The cost half depends on an overall heat-transfer "
                           "coefficient with no source at 20 bar and the sourced 1-bar range straddles the break-even, so the row as "
                           "worded (energy and cost) is " + v + "."),
               areas=["heat_exchanger", "aspen_kinetic", "economics"], literature=lit(("linnhoff1983pinch", "heat integration method")))


def v2_h3e(r: Row, v1row: dict) -> dict:
    RE = "row_evidence/H3-e/numbers/psa_recovery_threshold_for_zero_supplementary_fuel/"
    tn = r.num("PSA recovery above which Ni at Cho's point needs supplementary fuel", F_CE, RE + esc("Ni_735.52C_24.34bar") + "/psa_recovery_threshold", "fraction", "python")
    tr = r.num("PSA recovery above which Ru at Cho's point needs supplementary fuel", F_CE, RE + esc("RuAl2O3_566.69C_10bar") + "/psa_recovery_threshold", "fraction", "python")
    ni_lo = r.num("Ni import at the lowest checked recovery", F_CE, RE + esc("Ni_735.52C_24.34bar") + "/" + esc("import_kW_at_0.70"), "kW", "python")
    ru_hi = r.num("Ru import at the highest checked recovery", F_CE, RE + esc("RuAl2O3_566.69C_10bar") + "/" + esc("import_kW_at_0.95"), "kW", "python")
    if tr <= tn:
        v = "CONTRADICTED"
    elif ni_lo > 0 and ru_hi == 0:
        v = "SUPPORTED"
    else:
        v = "INCONCLUSIVE"
    rule = ("Reproduction rule: Cho's pattern (Ru needs no supplementary fuel, Ni does) holds for PSA recoveries between the Ni and Ru "
            "thresholds. SUPPORTED if it holds over the whole checked recovery range; CONTRADICTED if the band is empty; otherwise "
            "INCONCLUSIVE. Secondary row: does not vote.")
    return _v2(v, rule, envelope=text(F_CE, "row_evidence/H3-e/envelope"),
               threshold={"parameter": "PSA recovery at which supplementary fuel becomes necessary",
                          "values": [fnd("Ni threshold", F_CE, RE + esc("Ni_735.52C_24.34bar") + "/psa_recovery_threshold", "fraction", "python"),
                                     fnd("Ru threshold", F_CE, RE + esc("RuAl2O3_566.69C_10bar") + "/psa_recovery_threshold", "fraction", "python")],
                          "sourced_values": [], "comparison": "pattern only between the two thresholds"},
               conclusions=[f"Cho's pattern appears only for PSA recovery {f(tn,4)} to {f(tr,4)}."],
               assumptions=resolve(F_CE, "row_evidence/H3-e/assumptions"), uncertainty=text(F_CE, "row_evidence/H3-e/uncertainty"),
               kinds=["numerical_verification", "literature_comparison"],
               conclusion="The fuel pattern reported by Cho et al. is reproduced only in a narrow band of PSA recovery.",
               areas=["catalyst_economics", "catalyst_comparison"], literature=lit(("cho2026nickel", "Cho operating points")))


def v2_h3f(r: Row, v1row: dict) -> dict:
    RE = "row_evidence/H3-f/numbers/"
    keys = list(resolve(F_CE, RE + "rec_Ru_lower_by_pct"))
    vals = [r.num(f"Ru REC lower than Ni by, {k}", F_CE, RE + "rec_Ru_lower_by_pct/" + esc(k), "%", "python") for k in keys]
    cho = r.num("Cho et al. value", F_CE, RE + "cho_value_pct", "%", "literature")
    signs = {x > 0 for x in vals}
    if len(signs) > 1:
        v = "INCONCLUSIVE"
    else:
        v = "SUPPORTED" if signs == {True} and max(vals) >= cho / 2 else ("CONTRADICTED" if signs == {False} else "INCONCLUSIVE")
    rule = "Reproduction rule (unchanged from version 1): INCONCLUSIVE if the sign of the REC difference changes across inventory, PSA and price cases; otherwise the sign decides. Secondary row: does not vote."
    return _v2(v, rule, envelope=text(F_CE, "row_evidence/H3-f/envelope"), threshold=None,
               conclusions=[f"Ru REC difference {f(min(vals),1)} to {f(max(vals),1)} % across {len(vals)} cases, against Cho's {f(cho,1)} %."],
               assumptions=resolve(F_CE, "row_evidence/H3-f/assumptions"), uncertainty=text(F_CE, "row_evidence/H3-f/uncertainty"),
               kinds=["numerical_verification", "literature_comparison"],
               conclusion="Cho's 7 % REC advantage of Ru is not reproduced; the sign depends on the price and inventory basis.",
               areas=["catalyst_economics", "economics"], literature=lit(("cho2026nickel", "Cho REC values")))


# ---- H4 ------------------------------------------------------------------------------------
def v2_h4a(r: Row, v1row: dict) -> dict:
    RE = "row_evidence/H4-a/numbers/"
    y1 = r.num("Yanez 2020 recovery at 99.25 % (different feed)", F_PC, RE + esc("yanez2020_recovery_99.25"), "fraction", "literature")
    y2 = r.num("Yanez 2020 recovery at 99.97 % (different feed)", F_PC, RE + esc("yanez2020_recovery_99.97"), "fraction", "literature")
    m1 = r.num("mass-balance recovery at 99.91 %", F_PC, RE + esc("mass_balance_recovery_99.91"), "fraction", "assumption")
    m2 = r.num("mass-balance recovery at 99.975 %", F_PC, RE + esc("mass_balance_recovery_99.975"), "fraction", "assumption")
    inp = load(F_PC)["inputs"]["psa_recovery"]
    computed = all(str(inp[s][c]["source_type"]).split()[0] in ("python", "aspen") for s in inp for c in inp[s])
    v = "INCONCLUSIVE" if not computed else ("SUPPORTED" if m2 < m1 else "CONTRADICTED")
    rule = ("Computation rule (methodology v2): the trade-off can be SUPPORTED or CONTRADICTED only by a computed purity-recovery "
            "relation. In AmCraX every PSA recovery is an input (source_type of each entry in phase2_comparison.json inputs/psa_recovery "
            f"is literature or assumption: computed = {computed}), so the row is INCONCLUSIVE.")
    return _v2(v, rule, envelope=text(F_PC, "row_evidence/H4-a/envelope"), threshold=None,
               conclusions=[f"Only sourced slope: Yanez et al. 2020, recovery {f(y1,3)} at 99.25 % to {f(y2,3)} at 99.97 %, for ammonia-plant purge gas, not cracked ammonia.",
                            f"The AmCraX mass-balance relation is flat by construction ({f(m1,4)} and {f(m2,4)})."],
               assumptions=[text(F_PC, "row_evidence/H4-a/assumptions")], uncertainty=text(F_PC, "row_evidence/H4-a/uncertainty"),
               kinds=["literature_comparison"],
               conclusion="No purity-recovery relation is computed for cracked ammonia; the direction rests on one source for a different feed.",
               areas=["purification"])


def v2_h4b(r: Row, v1row: dict) -> dict:
    RE = "row_evidence/H4-b/numbers/"
    res = r.num("Python against Aspen LCOH resolution", F_CE, "resolution/max_abs_python_minus_aspen_lcoh_USD_per_kg", "USD/kg H2", "python")
    n = len(load(F_PC)["row_evidence"]["H4-b"]["numbers"]["by_electricity"])
    order = [resolve(F_PC, RE + f"by_electricity/{i}/order_raw_lt_industrial_lt_gradeD") for i in range(n)]
    incs = {k: r.num(f"purity-only Grade D increment at equal delivery pressure, {k}", F_PC, RE + f"equal_delivery_increment/{k}/increment", "USD/kg H2", "python")
            for k in load(F_PC)["row_evidence"]["H4-b"]["numbers"]["equal_delivery_increment"]}
    ordered = all(x is True for x in order)
    resolved = all(x > res for x in incs.values())
    v = "SUPPORTED" if (ordered and resolved) else ("CONTRADICTED" if not any(order) else "INCONCLUSIVE")
    rule = ("Resolution rule (methodology v2): raw < industrial is structural and most of the Grade D increment is 350 bar delivery, "
            "so the purity effect is tested at equal delivery pressure. SUPPORTED if the order raw < industrial < Grade D holds in every "
            "case and the purity-only increment exceeds the Python against Aspen LCOH resolution on every recovery basis; CONTRADICTED "
            "if the order is reversed everywhere; otherwise INCONCLUSIVE. Here: order holds everywhere "
            f"{ordered}, increment resolved on every basis {resolved}.")
    return _v2(v, rule, envelope=text(F_PC, "row_evidence/H4-b/envelope"), threshold=None,
               conclusions=[f"The order raw < industrial < Grade D holds in all {n} electricity cases.",
                            "Purity-only Grade D increment at equal delivery: " + ", ".join(f"{k} {f(x,4)}" for k, x in incs.items()) + f" USD/kg (resolution {f(res,4)})."],
               assumptions=[text(F_PC, "row_evidence/H4-b/assumptions")], uncertainty=text(F_PC, "row_evidence/H4-b/uncertainty"),
               kinds=["numerical_verification", "literature_comparison"],
               conclusion="Stricter purity costs more, but the purity-only part is small, partly below the model resolution, and rests on a cost proxy.",
               areas=["purification"])


def v2_h4c(r: Row, v1row: dict) -> dict:
    RE = "row_evidence/H4-c/numbers/"
    rc = r.num("Cho PSA recovery", F_PC, RE + "cho_recovery", "fraction", "literature")
    pc = r.num("Cho PSA purity", F_PC, RE + "cho_purity", "mol fraction", "literature")
    n2 = r.num("N2 in product", F_PC, RE + "n2_ppm", "ppm", "python")
    return _v2(v1row["verdict"], "Specification rule (unchanged from version 1): CONTRADICTED if the published composition fails both grade B and grade D in the ISO 14687 evaluator. Secondary row: does not vote.",
               envelope=text(F_PC, "row_evidence/H4-c/envelope"), threshold=None,
               conclusions=[f"Cho point: recovery {pct(rc,1)}, purity {pct(pc,2)}, N2 {f(n2,0)} ppm; fails the 99.9 % index and Grade D."],
               assumptions=[text(F_PC, "row_evidence/H4-c/assumptions")], uncertainty=text(F_PC, "row_evidence/H4-c/uncertainty"),
               kinds=["numerical_verification", "literature_comparison"],
               conclusion="The published PSA point does not meet ISO 14687 grades B or D.", areas=["purification"],
               literature=lit(("iso14687_2019", "ISO 14687 grade limits")))


def v2_h4d(r: Row, v1row: dict) -> dict:
    RE = "row_evidence/H4-d/numbers/"
    share = r.num("share of sourced input pairs in which the membrane is cheaper (Grade D)", F_PC, RE + "share_pairs_membrane_cheaper", "fraction", "python")
    par = r.num("PSA recovery at parity, central membrane", F_PC, RE + "psa_recovery_at_parity_central_membrane", "fraction", "python")
    pari = r.num("PSA recovery at parity, industrial", F_PC, RE + "industrial_psa_recovery_at_parity", "fraction", "python")
    req = r.num("required H2/N2 selectivity", F_PC, RE + "required_selectivity", "-", "python")
    s0 = r.num("ideal H2/N2 selectivity from the printed permeances (Cechetto et al. 2021)", F_PC, RE + "sourced_selectivity/0", "-", "literature")
    s2 = r.num("ideal H2/N2 selectivity as stated (Cechetto et al. 2021)", F_PC, RE + "sourced_selectivity/2", "-", "literature")
    v = "SUPPORTED" if share == 1 else ("CONTRADICTED" if share == 0 else "INCONCLUSIVE")
    return _v2(v, "Robustness rule: SUPPORTED if the membrane is cheaper in every sourced input combination; CONTRADICTED if in none; otherwise INCONCLUSIVE. Secondary row: does not vote.",
               envelope=text(F_PC, "row_evidence/H4-d/envelope"),
               threshold={"parameter": "PSA recovery at cost parity", "values": [fnd("parity, Grade D central membrane", F_PC, RE + "psa_recovery_at_parity_central_membrane", "fraction", "python"),
                                                                                 fnd("parity, industrial", F_PC, RE + "industrial_psa_recovery_at_parity", "fraction", "python")],
                          "sourced_values": [], "comparison": "sourced PSA recoveries straddle parity"},
               conclusions=[f"Membrane cheaper in {pct(share,0)} of sourced input pairs; parity at PSA recovery {f(par,3)} (Grade D) and {f(pari,3)} (industrial).",
                            f"Pd-Ag ideal H2/N2 selectivity {f(s0,0)} (printed permeances) to {f(s2,0)} (stated), single gas, new membrane, against a requirement of {f(req,0)}; the paper is internally inconsistent."],
               assumptions=[text(F_PC, "row_evidence/H4-d/assumptions")], uncertainty=text(F_PC, "row_evidence/H4-d/uncertainty"),
               kinds=["numerical_verification", "literature_comparison"],
               conclusion="PSA against Pd-Ag membrane is not robust either way; it turns on PSA recovery. Membrane TRL 4 to 5 against PSA 9.",
               areas=["purification"], literature=lit(("cechetto2021fpt", "Pd-Ag membrane permeances")))


def v2_h4e(r: Row, v1row: dict) -> dict:
    RE = "row_evidence/H4-e/numbers/"
    dem = r.num("furnace demand", F_PC, RE + "furnace_demand_kW", "kW", "python")
    thr = r.num("recovery at which tail-gas heat equals the furnace demand", F_PC, RE + "recovery_where_tail_heat_equals_demand", "fraction", "python")
    d85 = r.num("net deficit at PSA recovery 0.85", F_PC, RE + esc("psa_0.85_net_deficit_kW"), "kW", "python")
    # Threshold rule against sourced recoveries (fix pass 24 Nov 2026, review A B1). The direction (lost H2 is burned in the
    # cracker furnace) restates the flowsheet routing and cannot support the row by itself.
    inp = load(F_PC)["inputs"]["psa_recovery"]
    rec = [fnd(f"PSA recovery, {s}, {c} ({inp[s][c]['source_type']})", F_PC, f"inputs/psa_recovery/{esc(s)}/{c}/value", "fraction",
               "literature" if str(inp[s][c]["source_type"]).startswith("literature") else "assumption")
           for s in inp for c in ("low", "central", "high") if c in inp[s]]
    rlo, rhi = min(x["value"] for x in rec), max(x["value"] for x in rec)
    s_r = side([thr], rlo, rhi)
    v = {"above": "SUPPORTED", "below": "CONTRADICTED"}.get(s_r, "INCONCLUSIVE")
    rule = ("Threshold rule (methodology v2): that unrecovered hydrogen is burned in the cracker furnace restates the flowsheet's "
            "tail-gas routing (an assumption built into the model), so it cannot support the row by itself. The computed recovery at "
            "which the tail-gas heat equals the furnace demand is compared with the sourced and assumed PSA recoveries. SUPPORTED if "
            "every one lies above the threshold (all unrecovered hydrogen does useful work as furnace fuel); CONTRADICTED if every one "
            "lies below it (part of it is surplus with no use); otherwise INCONCLUSIVE and the threshold is the finding. Here the "
            f"recoveries {f(rlo,3)}-{f(rhi,3)} against the threshold {f(thr,3)} give '{s_r}'.")
    return _v2(v, rule,
               envelope=text(F_PC, "row_evidence/H4-e/envelope"),
               threshold={"parameter": "recovery where tail-gas heat equals furnace demand", "values": [fnd("threshold recovery", F_PC, RE + "recovery_where_tail_heat_equals_demand", "fraction", "python")],
                          "sourced_values": rec, "comparison": s_r},
               conclusions=[f"Furnace demand {f(dem,0)} kW; the tail gas covers it at PSA recovery {f(thr,3)}; at 0.85 the deficit is {f(d85,0)} kW.",
                            f"Sourced and assumed PSA recoveries {f(rlo,3)} to {f(rhi,3)} lie on both sides of {f(thr,3)}." if s_r == "straddle"
                            else f"Sourced and assumed PSA recoveries {f(rlo,3)} to {f(rhi,3)} lie {s_r} {f(thr,3)}."],
               assumptions=[text(F_PC, "row_evidence/H4-e/assumptions")], uncertainty=text(F_PC, "row_evidence/H4-e/uncertainty"),
               kinds=["numerical_verification"],
               conclusion=(f"In the AmCraX flowsheet unrecovered hydrogen is burned in the cracker furnace; it covers the furnace demand below a PSA "
                           f"recovery of {f(thr,3)}, and sourced recoveries lie on both sides of that value. The threshold is the finding."
                           if s_r == "straddle" else
                           f"In the AmCraX flowsheet unrecovered hydrogen is burned in the cracker furnace; the threshold recovery is {f(thr,3)}."),
               areas=["purification", "economics"])


V2_ROWS = {"H1-a": v2_h1a, "H1-b": v2_h1b, "H1-c": v2_h1c, "H1-d": v2_h1d,
           "H2-a": v2_h2a, "H2-b": v2_h2b, "H2-c": v2_h2c, "H2-d": v2_h2d, "H2-e": v2_h2e,
           "H3-a": v2_h3a, "H3-b": v2_h3b, "H3-c": v2_h3c, "H3-d": v2_h3d, "H3-e": v2_h3e, "H3-f": v2_h3f,
           "H4-a": v2_h4a, "H4-b": v2_h4b, "H4-c": v2_h4c, "H4-d": v2_h4d, "H4-e": v2_h4e}

# Verdicts listed in docs/internal/phase2_fix_plan.md section 1 (binding after the three independent reviews; it
# supersedes docs/internal/phase2_decisions.md, which now agrees with it). They are NOT used to set any verdict; they are
# only compared with the coded result so that a difference is printed and reported instead of forced. Disclosure: the
# row-specific rules v2_h1a to v2_h4e were written after the Phase 2 results were known (see DISCLOSURES), so agreement
# with this table is not an independent check; the rules for H2-b, H3-d and H4-e were rewritten in the fix pass of
# 24 November 2026 so that each can fail.
EXPECTED_ROW_V2 = {"H1-a": "INCONCLUSIVE", "H1-b": "CONTRADICTED", "H1-c": "INCONCLUSIVE", "H1-d": "INCONCLUSIVE",
                   "H2-a": "SUPPORTED", "H2-b": "INCONCLUSIVE", "H2-c": "SUPPORTED", "H2-d": "SUPPORTED", "H2-e": "CONTRADICTED",
                   "H3-a": "SUPPORTED", "H3-b": "INCONCLUSIVE", "H3-c": "INCONCLUSIVE", "H3-d": "INCONCLUSIVE",
                   "H3-e": "INCONCLUSIVE", "H3-f": "INCONCLUSIVE", "H4-a": "INCONCLUSIVE", "H4-b": "INCONCLUSIVE",
                   "H4-c": "CONTRADICTED", "H4-d": "INCONCLUSIVE", "H4-e": "INCONCLUSIVE"}

# Disclosures required by docs/internal/phase2_fix_plan.md section 2 (printed in the matrix provenance and markdown).
DISCLOSURES = [
    "Only the row roles, the components, the aggregation rule and the general row standard were fixed in commit f233509 "
    "before the analyses. The row-by-row coded rules (v2_h1a to v2_h4e in this script) were written after the results were "
    "known and were then tested by an independent adversarial review, which moved three rows (H2-b, H3-d, H4-e) from "
    "SUPPORTED to INCONCLUSIVE. Their agreement with the orchestrator's row decisions is by construction, not an independent "
    "check. The row standard was applied more strictly in that change, not relaxed.",
    "The CAPEX selection criteria were recorded together with the choice (commit 7447308); that they preceded the comparison "
    "cannot be shown. The chosen estimate is the highest of the candidates: it works against cracking (it raises LCOH, lowers "
    "the break-even ammonia price and widens the direct-use advantage in H1). No verdict changes across the independent CAPEX "
    "range.",
    "By the written aggregation rule a MIXED component counts for nothing at hypothesis level (for example [MIXED] gives "
    "INCONCLUSIVE and [MIXED, SUPPORTED] gives PARTIALLY SUPPORTED).",
    "Probabilities from the Monte Carlo and Sobol analyses (for example P(LCOH < 3.06 USD/kg)) are conditional on the assumed "
    "triangular and uniform input distributions.",
]


def release_verdicts() -> tuple[dict, dict]:
    rel = load(RELEASE_MATRIX)
    hyp = {h["id"]: h["verdict"] for h in rel["hypotheses"]}
    rows = {r["row_id"]: r["verdict"] for h in rel["hypotheses"] for r in h["rows"]}
    return hyp, rows


def apply_v2(hid: str, rows: list[dict]) -> dict:
    """Add the version 2 fields to the rows of one hypothesis and return the hypothesis-level v2 fields."""
    _hv1, rv1 = release_verdicts()
    for row in rows:
        rid = row["row_id"]
        h, cid, role = role_of(rid)
        if h != hid:
            raise EvidenceError(f"row {rid} listed under {hid} but its role table entry is {h}")
        r = Row()
        out = V2_ROWS[rid](r, row)
        row["verdict_phase2_logic_v1_function"] = row["verdict"]
        row["verdict"] = out["verdict"]
        row["verdict_v1"] = rv1[rid]
        row["role"] = role
        row["component"] = cid
        row["envelope"] = out["envelope"]
        row["threshold"] = out["threshold"]
        row["numerical_conclusions"] = out["numerical_conclusions"]
        row["assumptions"] = out["assumptions"]
        row["uncertainty"] = out["uncertainty"]
        row["evidence_kinds"] = out["evidence_kinds"]
        row["conclusion"] = out["conclusion"]
        row["conclusion_conditions"] = out["rule"]
        row["verdict_rule"] = out["rule"]
        row["uncertainty_range"] = out["uncertainty"]
        # the version 1 text could quote withdrawn Phase 1 figures; the version 2 envelope says what would change the verdict
        row["key_uncertainty"] = "Outside this envelope the verdict may change: " + out["envelope"]
        if "verdict_by_mode" in out:
            row["verdict_by_mode"] = out["verdict_by_mode"]
            row["mode_note"] = out["mode_note"]
        row["numerical_findings"] = row["numerical_findings"] + r.findings
        areas = sorted({Path(s["file"]).stem for s in row["validation_status"]} | set(out["areas"]))
        vtext, vstats = validation_text(areas)
        row["validation_status"] = vstats
        row["validation_method"] = row["validation_method"].split(" Validation status of the underlying models:")[0] + \
            " Validation status of the underlying models: " + vtext + "."
        have = {x["key"] for x in row["literature"]}
        row["literature"] = row["literature"] + [x for x in out["literature"] if x["key"] not in have]
        files = sorted({x["source_file"] for x in row["numerical_findings"]})
        row["links"]["data"] = checked_paths(sorted(set(row["links"]["data"]) | set(files)))
        row["provenance"] = ("Values read by " + SCRIPT + " from " + ", ".join(files)
                             + "; version 2 verdict derived in the same script (function v2_" + rid.replace("-", "").lower() + ").")
        if EXPECTED_ROW_V2[rid] != row["verdict"]:
            print(f"NOTE: {rid} coded verdict {row['verdict']} differs from phase2_decisions.md ({EXPECTED_ROW_V2[rid]}); kept as coded",
                  file=sys.stderr)
    by_id = {r["row_id"]: r for r in rows}
    comps = []
    for cid, title, prim, sec in COMPONENTS[hid]:
        pv = [by_id[x]["verdict"] for x in prim]
        cv = component_verdict(pv)
        env = [f"{x}: {by_id[x]['envelope']}" for x in prim if by_id[x]["verdict"] == "SUPPORTED"]
        comps.append({"id": cid, "title": title, "verdict": cv, "primary_rows": prim, "secondary_rows": sec,
                      "envelope": " ".join(env) if env else "none (no primary row is SUPPORTED)",
                      "note": ("Primary rows: " + ", ".join(f"{x} {by_id[x]['verdict']}" for x in prim)
                               + (". Secondary rows (do not vote): " + ", ".join(f"{x} {by_id[x]['verdict']}" for x in sec) if sec else "")
                               + ".")})
    hv = hypothesis_verdict_v2([c["verdict"] for c in comps])
    return {"verdict": hv, "components": comps, "verdict_v1_rule_on_current_rows": hypothesis_verdict(rows)}


def _num(rows, rid, quantity_start):
    for r in rows:
        if r["row_id"] == rid:
            for n in reversed(r["numerical_findings"]):  # version 2 findings are appended last
                if n["quantity"].startswith(quantity_start):
                    return n["value"]
    raise EvidenceError(f"{rid}: no finding starting with {quantity_start!r}")


def hypothesis_texts(hid: str, rows: list[dict], comps: list[dict]) -> dict:
    """Strongest defensible statement and findings against the essay; every number formatted from a file value."""
    cv = {c["id"]: c["verdict"] for c in comps}
    if hid == "H1":
        gf = _num(rows, "H1-a", "direct cheaper than fired cracking")
        gp = _num(rows, "H1-a", "direct cheaper than cracking + PSA")
        eta = _num(rows, "H1-a", "turbine efficiency assumed")
        oldf = val(F_TT, "statement_of_result/old_pre_unification/fired_pct")
        oldp = val(F_TT, "statement_of_result/old_pre_unification/purified_pct")
        fe = _num(rows, "H1-c", "LCOE exhaust-heated full cracking")
        d = _num(rows, "H1-c", "LCOE direct NH3")
        claim = _num(rows, "H1-b", "essay figure")
        fe0 = _num(rows, "H1-a", "fired-cracking threshold with cracker heat delivered at 1 ")
        fe1 = _num(rows, "H1-a", "fired-cracking threshold with cracker heat delivered at 0.85")
        gmax = _num(rows, "H1-b", "largest computed gap")
        s = (f"Under the modelled operating conditions, direct ammonia combustion produces electricity at a lower cost than the "
             f"standalone cracking pathways, with a calculated cost advantage of approximately {f(gf,0)} to {f(gp,0)} % "
             f"({f(oldf,0)} to {f(oldp,0)} % on the earlier cost basis). This comparison assumes that the hydrogen-rich turbine "
             f"operates at the same {pct(eta,2)} efficiency as the direct-ammonia turbine. The actual economic advantage depends on "
             "fuel-specific turbine performance. The advantage over cracking + PSA survives the threshold test on every basis against "
             "a single sourced gain (NETL 2023/2024, H-class cycle simulation with steam-diluted H2, not like-for-like with the "
             f"{pct(eta,2)} AmCraX turbine; an upper bound); the advantage over fired cracking cannot be tested because no turbine "
             "efficiency for its fuel is sourced. The cracker heat is counted at 100 % of the fuel's lower heating value "
             f"(optimistic, favourable to cracking); at 0.85 the fired-cracking threshold rises from +{f(fe0,2)} to +{f(fe1,2)} pp (computed).")
        against = [f"Exhaust-heated full cracking ({f(fe,1)} USD/MWh) is {f(100*(1-fe/d),1)} % cheaper than direct use ({f(d,1)}) on the reference basis.",
                   f"The essay's {f(claim,0)} % cost advantage of direct use is not reproduced (at most {f(gmax,1)} %)."]
        return {"statement": s, "against": against}
    if hid == "H2":
        share = _num(rows, "H2-a", "feed share")
        be = _num(rows, "H2-b", "break-even NH3 price against NE Asia SMR")
        bfav = _num(rows, "H2-b", "break-even NH3 price against the 3.06 USD/kg marker, favourable")
        b6 = _num(rows, "H2-b", "break-even NH3 price against the 6.0 USD/kg")
        bm3 = _num(rows, "H2-b", "NE Asia SMR production-cost marker")
        bm6 = _num(rows, "H2-b", "delivered low-carbon H2 benchmark")
        p = _num(rows, "H2-b", "Monte Carlo")
        bc = _num(rows, "H2-e", "hypothetical life-cycle price at which blue")
        h2b = next(r for r in rows if r["row_id"] == "H2-b")
        bes = [x["value"] for x in h2b["threshold"]["values"] if x["quantity"].startswith("break-even NH3 price, capex")]
        s = (f"Ammonia price dominates the cost of cracked hydrogen (feed {pct(share,0)} of LCOH on the reference basis, on every "
             f"sourced price and CAPEX basis). Competitiveness with the single NE Asia SMR marker ({f(bm3,2)} USD/kg) needs ammonia at "
             f"or below about {f(be,0)} USD/t ({f(min(bes),0)} to {f(max(max(bes), bfav),0)} over CAPEX and non-feed inputs), which only "
             f"the low ends of the sourced price ranges reach; against a {f(bm6,1)} USD/kg delivered low-carbon benchmark the "
             f"break-even is {f(b6,0)} USD/t (component H2-E {cv['H2-E']}). "
             f"Low-carbon ammonia is necessary for lower emissions than fossil alternatives (H2-C {cv['H2-C']}). Under the actual "
             f"Singapore carbon tax, low carbon intensity is not rewarded (cross-claim H2-X {cv['H2-X']}); under a hypothetical "
             f"life-cycle price, not Singapore law, blue overtakes grey near {f(bc,0)} SGD/t with a wide range.")
        against = [f"Grey ammonia at the central price is not cheap enough against the {f(bm3,2)} USD/kg marker: P(LCOH < {f(bm3,2)} USD/kg) = "
                   f"{f(p,3)}, conditional on the assumed triangular input distributions.",
                   "Under the actual Singapore carbon tax the tax is zero for every ammonia route, so low-carbon ammonia earns no cost advantage."]
        return {"statement": s, "against": against}
    if hid == "H3":
        hi = _num(rows, "H3-a", "fired-duty saving against Ni/MgO at equal conversion, Ru/Al2O3")
        gs = _num(rows, "H3-d", "gross fuel saving")
        nlo = _num(rows, "H3-d", "net saving after exchanger cost, low U")
        nhi = _num(rows, "H3-d", "net saving after exchanger cost, high U")
        d_off = _num(rows, "H3-d", "first-law heat deficit, heat integration off")
        d_on = _num(rows, "H3-d", "first-law heat deficit, heat integration on")
        h3c = next(r for r in rows if r["row_id"] == "H3-c")
        ext = val(F_HX, "row_evidence/H3-d/numbers/energy_total_external_heating_kW_hi_vs_nohi/0")
        comp_txt = ", ".join(f"{c['id']} {c['verdict']}" for c in comps)
        s = (f"{cv_h3_label(comps, rows)} Components: {comp_txt}. Heat integration reduces energy use substantially (Aspen first-law heat "
             f"deficit {f(d_off,0)} to {f(d_on,0)} kW); it saves {f(gs,3)} USD/kg gross and {f(nlo,3)} to {f(nhi,3)} net of the exchanger "
             "cost on the reference basis, but the cost half rests on an unsourced heat-transfer coefficient at 20 bar, so H3-H is "
             f"{cv['H3-H']}. Lower-temperature operation reduces fired duty at equal conversion only modestly (at most {f(hi,0)} kW with "
             f"heat integration, {pct(hi / ext, 1)} of total external heating; Python only) and only resolved for the Ru catalysts. "
             f"Whether the savings outweigh a higher catalyst cost (H3-K) is {cv['H3-K']} and the derived-price evidence leans against "
             f"it: {h3c['conclusion']}")
        against = [h3c["numerical_conclusions"][0] + " " + h3c["numerical_conclusions"][-1],
                   "The Phase 1 figure of a 17 % fired-duty reduction came from unequal conversion and is withdrawn."]
        return {"statement": s, "against": against}
    thr = _num(rows, "H4-e", "recovery at which tail-gas heat")
    par = _num(rows, "H4-d", "PSA recovery at parity, central")
    s = (f"In the AmCraX flowsheet unrecovered hydrogen is burned in the cracker furnace; it covers the furnace demand below a PSA "
         f"recovery of {f(thr,3)}, and sourced recoveries lie on both sides of that value. "
         "Stricter purity raises cost, but the purity-only part is small and rests on assumed recoveries. "
         f"PSA against Pd-Ag membrane is not robust either way (parity near PSA recovery {f(par,3)} for Grade D hydrogen; the industrial-grade value is in row H4-d).")
    against = ["The Phase 1 finding that a raw membrane is cheaper than PSA does not hold robustly on sourced ranges."]
    return {"statement": s, "against": against}


def cv_h3_label(comps: list[dict], rows: list[dict]) -> str:
    """H3 verdict is never printed bare (fix plan section 1): name the components and rows it rests on."""
    v = hypothesis_verdict_v2([c["verdict"] for c in comps])
    if v == "INCONCLUSIVE":
        return f"{v}."
    by = {r["row_id"]: r["verdict"] for r in rows}
    sup = [c for c in comps if c["verdict"] in ("SUPPORTED", "PARTIALLY SUPPORTED")]
    rws = [x for c in sup for x in c["primary_rows"] if by[x] == "SUPPORTED"]
    return (f"{v}, resting only on {', '.join(c['id'] for c in sup)} (supported row{'s' if len(rws) != 1 else ''} "
            f"{', '.join(rws)}, narrow envelope).")


def findings_changed(matrix_hyps: list[dict]) -> dict:
    """Findings that changed between the 23 November release and Phase 2, from supersession.json and the matrix."""
    sup = load(F_SUP)
    rows = sup["rows"]
    headline_sel = [  # (supersession quantity prefix, key) for the headline table
        ("baseline LCOH, Phase 1 equipment-level CAPEX", "results.grey|heat_integration_on.lcoh_USD_per_kg"),
        ("baseline LCOH, legacy correlation", "lcoh_USD_per_kg"),
        ("Singapore scenario LCOH/REC/CAPEX/NPV", "results.grey|heat_integration_on.capex_total_USD"),
        ("Singapore scenario LCOH/REC/CAPEX/NPV", "results.grey|heat_integration_on.npv_USD"),
        ("Singapore scenario LCOH/REC/CAPEX/NPV", "results.grey|heat_integration_on.rec_USD_per_kg"),
        ("break-even NH3 price", "results.heat_integration_on.ne_asia_smr_production_cost.breakeven_nh3_USD_per_t"),
        ("H1 power pathway LCOE / TCI", "power_pathways[full_fired].cost_USD_per_MWh_at_450"),
        ("H1 power pathway LCOE / TCI", "power_pathways[full_purified].cost_USD_per_MWh_at_450"),
        ("H1 power pathway LCOE / TCI", "power_pathways[full_exhaust].cost_USD_per_MWh_at_450"),
    ]
    head = []
    for q, k in headline_sel:
        hits = [i for i, x in enumerate(rows) if x["quantity"].startswith(q) and x["key"] == k]
        if len(hits) != 1:
            raise EvidenceError(f"supersession.json: {len(hits)} rows for {q} / {k}")
        x = rows[hits[0]]
        head.append({"finding": x["quantity"] + " (" + k + ")", "old": x["old_value"], "new": x["new_value"], "unit": x["unit"],
                     "reason": x["reason"], "file": x.get("new_file") or x["file"],
                     "source": {"source_file": F_SUP, "key": f"rows/{hits[0]}"}})
    # values that are not in supersession.json, read from the Phase 2 result files
    ru = load(F_CE)["row_evidence"]["H3-c"]["numbers"]["fixed_inventory_aspen_HI_exchanger"]
    head.append({"finding": "Ru/Al2O3 catalyst price", "old": val(F_CE, "row_evidence/H3-c/numbers/breakeven/0/published_TEA_price_USD_per_kg"),
                 "new": val(F_CE, "row_evidence/H3-c/numbers/fixed_inventory_aspen_HI_exchanger/" + esc("Ru/Al2O3") + "/central_price_USD_per_kg"),
                 "unit": "USD/kg", "reason": "published TEA price (Cho) replaced by a price derived from metal content; no supplier quotation exists",
                 "file": F_CE, "source": {"source_file": F_CE, "key": "row_evidence/H3-c/numbers/fixed_inventory_aspen_HI_exchanger/Ru~1Al2O3/central_price_USD_per_kg"}})
    RM = "hypotheses/[id={}]/rows/[row_id={}]/numerical_findings/{}/value"
    old_share = val(RELEASE_MATRIX, RM.format("H2", "H2-a", 1)) / val(RELEASE_MATRIX, RM.format("H2", "H2-a", 0))
    head.append({"finding": "feed share of LCOH (grey, HI on)", "old": old_share,
                 "new": val(F_CPR, "row_evidence/H2-a/numbers/feed_share"), "unit": "fraction",
                 "reason": "same feed cost on a larger LCOH (unified CAPEX basis); old value = feed / LCOH of the release matrix row H2-a",
                 "file": F_CPR, "source": {"source_file": F_CPR, "key": "row_evidence/H2-a/numbers/feed_share"}})
    head.append({"finding": "H3-a low-temperature saving (Ru/Al2O3 against Ni/MgO, heat integration on)",
                 "old": val(RELEASE_MATRIX, RM.format("H3", "H3-a", 6)),
                 "new": val(F_CE, "row_evidence/H3-a/numbers/python_Top_X095_fired_duty_saving_kW_HI/" + esc("Ru/Al2O3")),
                 "unit": "fraction of fired duty (old, unequal conversion) -> kW (new, equal conversion 0.95)",
                 "reason": ("the Phase 1 figure compared unequal conversions and is withdrawn; at equal conversion (Python) the saving is "
                            f"{pct(val(F_CE, 'row_evidence/H3-a/numbers/python_Top_X095_fired_duty_saving_kW_HI/' + esc('Ru/Al2O3')) / val(F_HX, 'row_evidence/H3-d/numbers/energy_total_external_heating_kW_hi_vs_nohi/0'), 1)} "
                            "of the total external heating (see the H3-a envelope for the share of fired duty)"),
                 "file": F_CE, "source": {"source_file": F_CE, "key": "row_evidence/H3-a/numbers/python_Top_X095_fired_duty_saving_kW_HI/Ru~1Al2O3"}})
    for h in matrix_hyps:
        head.append({"finding": f"{h['id']} verdict", "old": h["verdict_v1"], "new": h["verdict"], "unit": "verdict",
                     "reason": ("methodology v2 (roles, components and aggregation fixed before the Phase 2 analyses; row rules coded "
                                "after the results and tightened in the fix pass of 24 November 2026) on the Phase 2 rows; v1 verdict "
                                "from the 23 November release. Components: " + ", ".join(f"{c['id']} {c['verdict']}" for c in h["components"])),
                     "file": OUT_JSON, "source": {"source_file": RELEASE_MATRIX, "key": f"hypotheses/[id={h['id']}]/verdict"}})
        for r in h["rows"]:
            if r["verdict"] != r["verdict_v1"]:
                head.append({"finding": f"{r['row_id']} row verdict", "old": r["verdict_v1"], "new": r["verdict"], "unit": "verdict",
                             "reason": r["verdict_rule"], "file": OUT_JSON,
                             "source": {"source_file": RELEASE_MATRIX, "key": f"hypotheses/[id={h['id']}]/rows/[row_id={r['row_id']}]/verdict"}})
    fp = load(F_FIX) if (ROOT / F_FIX).exists() else None
    return {"provenance": {"script": SCRIPT, "inputs": [F_SUP, F_CE, RELEASE_MATRIX, OUT_JSON] + ([F_FIX] if fp else []),
                           "note": "Phase 1 values from the 23 November release, Phase 2 values from the current result files."},
            "headline": head,
            "fix_pass_2026_11_24": fp,
            "all_supersession_rows": [{"quantity": x["quantity"], "file": x["file"], "key": x["key"], "old": x.get("old_value"),
                                       "new": x.get("new_value"), "unit": x.get("unit"), "reason": x.get("reason")} for x in rows]}


def _fv(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return _fmt_value(v)
    return str(v)


def findings_changed_md(fc: dict) -> str:
    L = ["# Findings that changed between the 23 November 2026 release and Phase 2", "",
         f"Generated by `{SCRIPT}` from `{F_SUP}`, the Phase 2 result files and the evidence matrix. Do not edit by hand.", "",
         "Old values are those of the 23 November 2026 release (`results/research_releases/2026-11-23/`). New values are on the "
         "unified reference scenario (exchange rate 1.288444 SGD/USD, ECB reference rate of 20 November 2026).", "",
         "## Headline findings", "", "| Finding | Phase 1 | Phase 2 | Unit | Reason | File |", "|---|---|---|---|---|---|"]
    for x in fc["headline"]:
        L.append(f"| {_md_escape(x['finding'])} | {_fv(x['old'])} | {_fv(x['new'])} | {_md_escape(x['unit'])} | {_md_escape(x['reason'])} | `{x['file']}` |")
    fp = fc.get("fix_pass_2026_11_24")
    if fp:
        L += ["", "## Fix pass of 24 November 2026 (after the three independent reviews)", "",
              f"Applied from `docs/internal/phase2_fix_plan.md`. Old values: {fp['provenance']['old_values']} (Phase 2 before the fix pass); "
              f"new values: current files. Recorded by `{fp['provenance']['script']}` in `{F_FIX}`. The row standard was applied more "
              "strictly, not relaxed: three rows moved from SUPPORTED to INCONCLUSIVE under coded rules that can fail.", "",
              "### Verdicts", "", "| Verdict | Before the fix pass | After | File |", "|---|---|---|---|"]
        for x in fp["verdict_changes"]:
            L.append(f"| {_md_escape(x['quantity'])} | {x['old']} | {x['new']} | `{x['file']}` |")
        L += ["", "### Numbers", "", "| Quantity | Before | After | Reason | File and key |", "|---|---|---|---|---|"]
        for x in fp["number_changes"]:
            L.append(f"| {_md_escape(x['quantity'])} | {_fv(x['old']) if x['old'] is not None else 'none'} | "
                     f"{_fv(x['new']) if x['new'] is not None else 'none (no parity in range)'} | {_md_escape(x['reason'])} | "
                     f"`{x['file']}` `{_md_escape(x['key'])}` |")
        L += ["", "### New computed blocks", ""] + [f"- `{x['file']}` `{x['key']}`: {x['what']}." for x in fp["new_computed_blocks"]]
    L += ["", "## Every superseded number", "", f"All {len(fc['all_supersession_rows'])} rows of `{F_SUP}`.", "",
          "| Quantity | Phase 1 | Phase 2 | Unit | Reason | File and key |", "|---|---|---|---|---|---|"]
    for x in fc["all_supersession_rows"]:
        L.append(f"| {_md_escape(x['quantity'])} | {_fv(x['old'])} | {_fv(x['new'])} | {_md_escape(x['unit'])} | {_md_escape(x['reason'])} | `{x['file']}` `{_md_escape(x['key'])}` |")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------------------------
STATEMENTS = {
    "H1": "End-use suitability: cracking is most justified when the end use needs molecular hydrogen, not where ammonia can be used directly.",
    "H2": "Feedstock: affordable, low-carbon ammonia is essential to economic and environmental competitiveness.",
    "H3": "Catalyst and heat integration: low-temperature, high-activity catalysts with effective heat integration reduce energy use and can outweigh higher catalyst cost.",
    "H4": "Purification: must balance purity requirements against recovery losses, energy and equipment cost.",
}
SUMMARY_LEAD = {
    "H1": "Direct use is cheaper than standalone and purified cracking for power, but that ranking follows from the assumption that the turbine reaches the same efficiency on H2-rich fuel as on NH3, so it is not independent support; the essay's cost margin for direct use is not reproduced, and exhaust-heated cracking in front of a turbine is marginally cheaper than direct use on a single literature efficiency gain.",
    "H2": "Ammonia price dominates hydrogen cost and only green (or very well-captured blue) ammonia cuts emissions against Singapore alternatives; the break-even ammonia price against the named benchmarks is straddled by the sourced price ranges, so it is reported as a threshold; under current Singapore carbon pricing low carbon intensity earns no cost advantage, so affordable and low-carbon pull apart.",
    "H3": "Lower temperature and heat integration both cut energy, heat integration by far the more; the cost half of heat integration rests on an unsourced heat-transfer coefficient, the catalyst cost question is unresolved and leans against the low-temperature catalysts at derived ruthenium prices, and Cho's fuel and REC findings are not reproduced on AmCraX boundaries.",
    "H4": "Unrecovered hydrogen is burned in the cracker furnace by the flowsheet's routing, and sourced PSA recoveries lie on both sides of the recovery at which it covers the furnace demand; the published Cho PSA point fails ISO 14687 grades B and D; the cost increase with purity, the PSA purity-recovery slope and the membrane advantage rest on assumed recoveries.",
}


# Row verdicts the hand-written summaries were written for. If the computed verdicts differ (for example
# after a result file is regenerated), the summary falls back to an automatic one so it cannot go stale.
SUMMARY_FOR = {
    "H1": {"H1-a": "INCONCLUSIVE", "H1-b": "CONTRADICTED", "H1-c": "INCONCLUSIVE", "H1-d": "INCONCLUSIVE"},
    "H2": {"H2-a": "SUPPORTED", "H2-b": "INCONCLUSIVE", "H2-c": "SUPPORTED", "H2-d": "SUPPORTED", "H2-e": "CONTRADICTED"},
    "H3": {"H3-a": "SUPPORTED", "H3-b": "INCONCLUSIVE", "H3-c": "INCONCLUSIVE", "H3-d": "INCONCLUSIVE", "H3-e": "INCONCLUSIVE", "H3-f": "INCONCLUSIVE"},
    "H4": {"H4-a": "INCONCLUSIVE", "H4-b": "INCONCLUSIVE", "H4-c": "CONTRADICTED", "H4-d": "INCONCLUSIVE", "H4-e": "INCONCLUSIVE"},
}


def summary_for(hid: str, rows: list[dict]) -> str:
    if {r["row_id"]: r["verdict"] for r in rows} == SUMMARY_FOR[hid]:
        return SUMMARY_LEAD[hid]
    return "Automatic summary (row verdicts changed since the hand-written summary): " + " ".join(
        f"{r['row_id']} {r['verdict']}: {r['conclusion']}" for r in rows)


def build() -> dict:
    builders = {"H1": h1_rows, "H2": h2_rows, "H3": h3_rows, "H4": h4_rows}
    load(F_BASE)
    hv1, _rv1 = release_verdicts()
    hyps = []
    for hid, fn in builders.items():
        rows = fn()
        v2 = apply_v2(hid, rows)
        # rows in methodology order: primary rows first, then secondary rows (row ids kept)
        order = [x for _c, _t, prim, _s in COMPONENTS[hid] for x in prim] + [x for _c, _t, _p, sec in COMPONENTS[hid] for x in sec]
        rows = sorted(rows, key=lambda r: order.index(r["row_id"]))
        comps = v2["components"]
        txt = hypothesis_texts(hid, rows, comps)
        v = v2["verdict"]
        h = {
            "id": hid,
            "statement": STATEMENTS[hid],
            "primary_hypothesis": STATEMENTS[hid],
            "verdict": v,
            "verdict_v1": hv1[hid],
            "verdict_v1_rule_on_current_rows": v2["verdict_v1_rule_on_current_rows"],
            "verdict_conditions": (HYPOTHESIS_RULE_V2 + " Components: " + "; ".join(f"{c['id']} {c['verdict']}" for c in comps)
                                   + ". " + COMPONENT_RULE + " Row outcomes: " + mixed_text(rows) + "."),
            "components": comps,
            "strongest_defensible_statement": txt["statement"],
            "findings_against_essay": txt["against"],
            "summary": txt["statement"],
            "rows": rows,
        }
        if hid in CROSS_CLAIM:
            cc = next(c for c in comps if c["id"] == CROSS_CLAIM[hid])
            e = next(r for r in rows if r["row_id"] in cc["primary_rows"])
            h["cross_claim"] = {"component": cc["id"], "verdict": cc["verdict"], "row": e["row_id"],
                                "verdict_by_mode": e.get("verdict_by_mode"),
                                "statement": (f"Cross-claim {cc['id']} ({cc['title'].split(': ', 1)[-1]}): {cc['verdict']} under the actual Singapore carbon-tax boundary. "
                                              f"Under a hypothetical life-cycle carbon price (not Singapore law): {e['verdict_by_mode']['hypothetical_lca']}.")}
        hyps.append(h)
    stamp = os.environ.get("SOURCE_DATE_EPOCH")
    when = (_dt.datetime.fromtimestamp(int(stamp), _dt.timezone.utc) if stamp
            else _dt.datetime.now(_dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    hashes = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in sorted(_USED_FILES)}
    return {
        "provenance": {
            "generated_utc": when,
            "script": SCRIPT,
            "source_type": "derived (aspen, python, literature, assumption values read from stored result files)",
            "inputs_summary": "Research result files of the kinetics, Aspen RPlug, catalyst comparison, Singapore economics, purification, end-use and LCA workstreams, their validation files, the Aspen evidence manifest and the reference library. No number is typed in the script.",
            "model_versions": {"aspen": "Aspen Plus V15 (stored runs only; no Aspen run by this script)",
                               "python": "AmCraX research modules as of the stored result files"},
            "verdict_vocabulary": list(VERDICTS),
            "verdict_vocabulary_v2": list(V2_VERDICTS),
            "hypothesis_rule": HYPOTHESIS_RULE_V2,
            "hypothesis_rule_v1": HYPOTHESIS_RULE,
            "component_rule": COMPONENT_RULE,
            "currency": {"calculation_currency": "USD",
                         "fx_SGD_per_USD": val(F_BASE, "fx_SGD_per_USD"), "fx_date": text(F_BASE, "fx_date"),
                         "source": {"source_file": F_BASE, "key": "fx_SGD_per_USD"},
                         "note": "One exchange rate for every SGD value (reference scenario, ECB reference rates)."},
            "evidence_kinds": list(EVIDENCE_KINDS),
            "experimental_validation": "AmCraX has no independent experimental validation. No row lists it as an evidence kind.",
            "row_rule": "Each row's conclusion_conditions states the rule that produced its verdict. SUPPORTED only within the stated conditions and when the evidence is computed rather than an assumption built into the model; model-form limited, extrapolated or within-band evidence gives INCONCLUSIVE.",
            "key_format": "JSON-pointer-like path with '/' separators ('~1' = '/', '~0' = '~'); '[a=b;c=d]' selects one list element; for CSV files '[col=val]/col'.",
            "extra_row_fields": ("verdict, key_uncertainty and validation_status are added to the 15 contract fields. Methodology v2 adds role, "
                                 "component, verdict_v1, envelope, threshold, numerical_conclusions, assumptions, uncertainty, evidence_kinds, "
                                 "verdict_rule (also in conclusion_conditions), verdict_by_mode (H2-e) and verdict_phase2_logic_v1_function "
                                 "(the version 1 row function applied to the current files, kept for comparison)."),
            "input_sha256": hashes,
            "disclosures": DISCLOSURES,
            "fix_pass": ("24 November 2026: the accepted findings of three independent reviews were applied "
                         "(docs/internal/phase2_fix_plan.md): rows H2-b, H3-d and H4-e moved from SUPPORTED to INCONCLUSIVE under "
                         "rewritten coded rules that can fail; text corrections in H1, H2-a, H2-b, H2-d, H3-a, H3-c, H3-d, H4-d."),
        },
        "methodology_version": METHODOLOGY_VERSION,
        "methodology": METHODOLOGY,
        "hypotheses": hyps,
    }


# --------------------------------------------------------------------------------------------
# Markdown
# --------------------------------------------------------------------------------------------
def _md_escape(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def _fmt_value(v: float) -> str:
    if isinstance(v, int) or float(v).is_integer():
        return f"{v:.0f}"
    a = abs(v)
    if a >= 100:
        return f"{v:.1f}"
    if a >= 1:
        return f"{v:.3f}"
    return f"{v:.4g}"


def to_markdown(m: dict) -> str:
    cur = m["provenance"]["currency"]
    L = ["# Research evidence matrix (H1-H4), methodology version 2", "",
         f"Generated from `{OUT_JSON}` by `{SCRIPT}` ({m['provenance']['generated_utc']}). Do not edit by hand; re-run the script.", "",
         f"Verdict rule: `{m['methodology']}` (version {m['methodology_version']}, fixed before the Phase 2 analyses). "
         "Row verdicts: SUPPORTED, CONTRADICTED, INCONCLUSIVE. Component and hypothesis verdicts add MIXED and PARTIALLY SUPPORTED. "
         "Every row verdict is derived in code from the result files by the rule printed with the row. The version 1 verdict of "
         "the 23 November 2026 release is shown beside every verdict.", "",
         m["provenance"]["component_rule"], "", m["provenance"]["hypothesis_rule"], "",
         f"Evidence kinds are kept apart: numerical verification, Python against Aspen comparison, comparison with published "
         f"literature, and independent experimental validation. {m['provenance']['experimental_validation']}", "",
         f"Currency: calculations in {cur['calculation_currency']}; SGD values use {cur['fx_SGD_per_USD']} SGD/USD ({cur['fx_date']}).", "",
         "## Disclosures", ""] + [f"- {x}" for x in m["provenance"]["disclosures"]] + ["", f"Fix pass: {m['provenance']['fix_pass']}", "",
         "## Verdict table", "",
         "| Hypothesis | Component or row | Role | Verdict (v2) | Verdict (v1) | Statement |", "|---|---|---|---|---|---|"]
    for h in m["hypotheses"]:
        L.append(f"| **{h['id']}** | | | **{h['verdict']}** | {h['verdict_v1']} | {_md_escape(h['primary_hypothesis'])} |")
        rows = {r["row_id"]: r for r in h["rows"]}
        for c in h["components"]:
            L.append(f"| | **{c['id']}** | component | **{c['verdict']}** | | {_md_escape(c['title'])} |")
            for rid in c["primary_rows"] + c["secondary_rows"]:
                r = rows[rid]
                L.append(f"| | {rid} | {r['role']} | {r['verdict']} | {r['verdict_v1']} | {_md_escape(r['sub_claim'])} |")
    L.append("")
    for h in m["hypotheses"]:
        L += [f"## {h['id']}: {h['verdict']} (" + ", ".join(f"{c['id']} {c['verdict']}" for c in h["components"]) + ")", "",
              f"**Primary hypothesis.** {h['primary_hypothesis']}", "",
              f"**Verdict.** {h['verdict']} (methodology v2). Version 1 verdict of the 23 November release: {h['verdict_v1']}. "
              f"Version 1 rule applied to the current rows: {h['verdict_v1_rule_on_current_rows']}.", "",
              f"**Strongest defensible statement.** {h['strongest_defensible_statement']}", ""]
        if h.get("cross_claim"):
            L += [f"**Cross-claim.** {h['cross_claim']['statement']}", ""]
        L += ["**Findings against the essay.**", ""] + [f"- {x}" for x in h["findings_against_essay"]] + [""]
        L += ["**Components.**", "", "| Component | Verdict | Primary rows | Secondary rows | Envelope |", "|---|---|---|---|---|"]
        for c in h["components"]:
            L.append(f"| {c['id']} {_md_escape(c['title'])} | {c['verdict']} | {', '.join(c['primary_rows'])} | "
                     f"{', '.join(c['secondary_rows']) or '-'} | {_md_escape(c['envelope'])} |")
        L += ["", f"**Verdict conditions.** {h['verdict_conditions']}", ""]
        for r in h["rows"]:
            L += [f"### {r['row_id']}: {r['verdict']}", "",
                  f"Role: {r['role']} ({r['component']}). Version 1 verdict: {r['verdict_v1']}."
                  + (f" By mode: actual Singapore boundary {r['verdict_by_mode']['actual_sg']} (votes); hypothetical life-cycle price, not Singapore law, {r['verdict_by_mode']['hypothetical_lca']} (does not vote)." if r.get("verdict_by_mode") else ""), "",
                  f"**Sub-claim.** {r['sub_claim']}", "",
                  "**Numerical conclusions.**", ""] + [f"- {x}" for x in r["numerical_conclusions"]] + ["",
                  f"**Conclusion.** {r['conclusion']}", "", f"**Rule and outcome.** {r['conclusion_conditions']}", "",
                  f"**Envelope.** {r['envelope']}", ""]
            t = r.get("threshold")
            if t:
                vals = ", ".join(f"{_fmt_value(x['value'])}" for x in t["values"])
                srcs = ", ".join(f"{_md_escape(x['quantity'])} {_fmt_value(x['value'])}" for x in t["sourced_values"]) or "none sourced"
                L += [f"**Threshold.** {t['parameter']}: {vals}. Sourced: {srcs}. Comparison: {_md_escape(json.dumps(t['comparison']))}.", ""]
            L += ["**Assumptions.**", ""] + [f"- {_md_escape(x)}" for x in r["assumptions"]] + ["",
                  f"**Uncertainty.** {r['uncertainty']}", "",
                  f"**Validation status.** {r['validation_method']}", "",
                  "**Evidence kinds.** " + ", ".join(k.replace("_", " ") for k in r["evidence_kinds"]) + ".", "",
                  f"**Key uncertainty (what would change the verdict).** {r['key_uncertainty']}", "",
                  f"**Uncertainty range.** {r['uncertainty_range']}", "",
                  f"- Singapore scenario: {r['singapore_scenario']}",
                  f"- Aspen model: {r['aspen_model']}",
                  f"- Python model: {r['python_model']}",
                  f"- Case ids: {', '.join(r['case_ids'])}",
                  f"- Validation: {r['validation_method']}",
                  "- Input assumptions: " + "; ".join(r["input_assumptions"]),
                  "- Literature: " + "; ".join(f"`{x['key']}` ({x['label']})" for x in r["literature"]),
                  "- Limitations: " + "; ".join(r["limitations"]), "",
                  "| Quantity | Value | Unit | Source type | File | Key |", "|---|---|---|---|---|---|"]
            for n in r["numerical_findings"]:
                L.append(f"| {_md_escape(n['quantity'])} | {_fmt_value(n['value'])} | {_md_escape(n['unit'])} | {n['source_type']} | `{n['source_file']}` | `{_md_escape(n['key'])}` |")
            L.append("")
            lk = r["links"]
            if lk["figures"]:
                L.append("Figures: " + ", ".join(f"`{p}`" for p in lk["figures"]))
            if lk["screenshots"]:
                L.append("Aspen screenshots: " + ", ".join(f"`{p}`" for p in lk["screenshots"]))
            L.append("Data: " + ", ".join(f"`{p}`" for p in lk["data"]))
            L.append("")
    return "\n".join(L) + "\n"


def main() -> int:
    try:
        m = build()
    except EvidenceError as exc:
        print(f"EVIDENCE ERROR: {exc}", file=sys.stderr)
        return 2
    (ROOT / OUT_JSON).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / OUT_MD).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / OUT_JSON).write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (ROOT / OUT_MD).write_text(to_markdown(m), encoding="utf-8")
    fc = findings_changed(m["hypotheses"])
    (ROOT / OUT_FC_JSON).write_text(json.dumps(fc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (ROOT / OUT_FC_MD).write_text(findings_changed_md(fc), encoding="utf-8")
    for h in m["hypotheses"]:
        print(h["id"], h["verdict"], "(v1", h["verdict_v1"] + ")", " ".join(f"{c['id']}={c['verdict']}" for c in h["components"]))
        print("   ", " ".join(f"{r['row_id']}={r['verdict']}" for r in h["rows"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
