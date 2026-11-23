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
- Hypothesis verdict rule (HYPOTHESIS_RULE below): SUPPORTED if every row is SUPPORTED;
  CONTRADICTED if no row is SUPPORTED and at least half of the rows are CONTRADICTED;
  otherwise INCONCLUSIVE, with the mixed outcome spelled out in ``verdict_conditions``.

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
    counts = {"pass": 0, "fail": 0, "informational": 0}
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
        python_model="amcrax.economics.singapore.evaluate (equipment-level CAPEX screening estimate), tornado sensitivity.",
        case_ids=["baseline (stored Aspen)", "grey|heat_integration_on"],
        input_assumptions=[f"NH3 price scenarios and the {f(lo_in,0)}-{f(hi_in,0)} USD/t tornado range are inputs (Cho Table 8 and secondary web prices); the feed share is computed but scales with these assumed prices.",
                           "Equipment-level CAPEX is a feed-scaled screening estimate and probably optimistic, which raises the feed share."],
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
    pr_ni = r.num("Ni catalyst price (Cho, proxy)", CA, "[name=catalyst_price_Ni]/value", "USD/kg", "assumption")
    pr_ru = r.num("Ru catalyst price (Cho, proxy; also used for NiRu/CeO2)", CA, "[name=catalyst_price_Ru]/value", "USD/kg", "assumption")
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
    mcost = r.num("membrane cost (applied as USD at parity)", PA, "[name=Membrane cost]/value", "EUR/m2", "assumption")
    cond = resolve(F_PUR, C.format("MEM_1bar_polish", "costs/fuel_cell_grade_D/conditional_on"))
    verdict = "INCONCLUSIVE" if cond else ("SUPPORTED" if mem < dmb2 else "CONTRADICTED")
    rows.append(make_row(
        "H4-d", "A Pd-Ag membrane balances purity, recovery and cost better than PSA for fuel-cell hydrogen.",
        verdict, rowobj=r, singapore_scenario=sg, aspen_model="No Aspen membrane model: Python/literature only.",
        python_model=py_p, case_ids=["MEM_1bar_polish", "MEM_1bar_raw", "PSA_D_MB"],
        input_assumptions=["Infinite H2/N2 selectivity in the base case (no numeric selectivity in the library).",
                           f"Membrane cost {f(mcost,0)} EUR/m2 applied as USD at parity; housing, skid and compression CAPEX not modelled.",
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
    "H2": "Ammonia price dominates hydrogen cost and only green (or very well-captured blue) ammonia cuts emissions against Singapore alternatives; but under current Singapore carbon pricing low carbon intensity earns no cost advantage, so affordable and low-carbon pull apart.",
    "H3": "Lower temperature and heat integration both cut energy, heat integration by far the more; the catalyst cost question is unresolved because the differences are inside the uncertainty band, and Cho's fuel and REC findings are not reproduced on AmCraX boundaries.",
    "H4": "Recovery losses partly return as furnace fuel (computed energy balance), and the published Cho PSA point fails ISO 14687 grades B and D; the cost increase with purity, the PSA purity-recovery slope and the membrane advantage rest on assumed recoveries and an unsourced selectivity.",
}


# Row verdicts the hand-written summaries were written for. If the computed verdicts differ (for example
# after a result file is regenerated), the summary falls back to an automatic one so it cannot go stale.
SUMMARY_FOR = {
    "H1": {"H1-a": "INCONCLUSIVE", "H1-b": "CONTRADICTED", "H1-c": "INCONCLUSIVE", "H1-d": "INCONCLUSIVE"},
    "H2": {"H2-a": "SUPPORTED", "H2-b": "SUPPORTED", "H2-c": "SUPPORTED", "H2-d": "SUPPORTED", "H2-e": "CONTRADICTED"},
    "H3": {"H3-a": "SUPPORTED", "H3-b": "INCONCLUSIVE", "H3-c": "INCONCLUSIVE", "H3-d": "SUPPORTED", "H3-e": "INCONCLUSIVE", "H3-f": "INCONCLUSIVE"},
    "H4": {"H4-a": "INCONCLUSIVE", "H4-b": "INCONCLUSIVE", "H4-c": "CONTRADICTED", "H4-d": "INCONCLUSIVE", "H4-e": "SUPPORTED"},
}


def summary_for(hid: str, rows: list[dict]) -> str:
    if {r["row_id"]: r["verdict"] for r in rows} == SUMMARY_FOR[hid]:
        return SUMMARY_LEAD[hid]
    return "Automatic summary (row verdicts changed since the hand-written summary): " + " ".join(
        f"{r['row_id']} {r['verdict']}: {r['conclusion']}" for r in rows)


def build() -> dict:
    builders = {"H1": h1_rows, "H2": h2_rows, "H3": h3_rows, "H4": h4_rows}
    hyps = []
    for hid, fn in builders.items():
        rows = fn()
        v = hypothesis_verdict(rows)
        hyps.append({
            "id": hid,
            "statement": STATEMENTS[hid],
            "verdict": v,
            "verdict_conditions": (HYPOTHESIS_RULE + " Row outcomes: " + mixed_text(rows) + "."
                                   + ("" if v != "INCONCLUSIVE" else
                                      " Qualified verdict: the hypothesis holds only in the parts marked SUPPORTED, under each row's conclusion_conditions; "
                                      "rows marked CONTRADICTED are findings against the essay statement; INCONCLUSIVE rows are unresolved by the models.")),
            "summary": summary_for(hid, rows),
            "rows": rows,
        })
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
            "hypothesis_rule": HYPOTHESIS_RULE,
            "row_rule": "Each row's conclusion_conditions states the rule that produced its verdict. SUPPORTED only within the stated conditions and when the evidence is computed rather than an assumption built into the model; model-form limited, extrapolated or within-band evidence gives INCONCLUSIVE.",
            "key_format": "JSON-pointer-like path with '/' separators ('~1' = '/', '~0' = '~'); '[a=b;c=d]' selects one list element; for CSV files '[col=val]/col'.",
            "extra_row_fields": "verdict, key_uncertainty and validation_status are added to the 15 contract fields.",
            "input_sha256": hashes,
        },
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
    L = ["# Research evidence matrix (H1-H4)", "",
         f"Generated from `{OUT_JSON}` by `{SCRIPT}` ({m['provenance']['generated_utc']}). Do not edit by hand; re-run the script.", "",
         "Verdicts: SUPPORTED, CONTRADICTED, INCONCLUSIVE. " + m["provenance"]["hypothesis_rule"], "",
         m["provenance"]["row_rule"], "",
         "## Verdict table", "",
         "| Hypothesis | Row | Verdict | Sub-claim |", "|---|---|---|---|"]
    for h in m["hypotheses"]:
        L.append(f"| **{h['id']}** | | **{h['verdict']}** | {_md_escape(h['statement'])} |")
        for r in h["rows"]:
            L.append(f"| | {r['row_id']} | {r['verdict']} | {_md_escape(r['sub_claim'])} |")
    L.append("")
    for h in m["hypotheses"]:
        L += [f"## {h['id']}: {h['verdict']}", "", f"**Statement.** {h['statement']}", "",
              f"**Summary.** {h['summary']}", "", f"**Verdict conditions.** {h['verdict_conditions']}", ""]
        for r in h["rows"]:
            L += [f"### {r['row_id']}: {r['verdict']}", "", f"**Sub-claim.** {r['sub_claim']}", "",
                  f"**Conclusion.** {r['conclusion']}", "", f"**Conditions and rule.** {r['conclusion_conditions']}", "",
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
    for h in m["hypotheses"]:
        print(h["id"], h["verdict"], " ".join(f"{r['row_id']}={r['verdict']}" for r in h["rows"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
