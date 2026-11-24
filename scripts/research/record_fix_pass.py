"""Record every stored number and verdict that changed in the Phase 2 fix pass of 24 November 2026.

The fix pass applied the accepted findings of three independent reviews (verdicts; documents; models and code):
membrane annualised with the capital recovery factor at the membrane life, centred Sobol first-order estimator,
three row verdicts (H2-b, H3-d, H4-e) moved to INCONCLUSIVE under coded rules that can fail, and new computed blocks
(fuel-efficiency envelope, fired-cracking threshold shift, solved break-even CRF).

Old values are read from git commit PRE_FIX (the last commit before the fix-pass outputs were regenerated); new values
from the working tree. Writes results/research/fix_pass_2026-11-24.json, which build_evidence_matrix.py copies into
docs/research/phase2_findings_changed.md. Run from the project root after the fix-pass scripts and before the matrix:

    python scripts/research/record_fix_pass.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRE_FIX = "70993a5"
OUT = ROOT / "results" / "research" / "fix_pass_2026-11-24.json"

# (file, key regex on the flattened path, quantity, reason)
SELECT = [
    ("results/research/purification/phase2_comparison.json",
     r"^specs/[^/]+/(thresholds/(psa_recovery_at_parity_with_central_membrane|psa_recovery_at_parity_with_high_cost_membrane/value|"
     r"(low|central|high)/(membrane_cost_USD_per_m2_at_parity|membrane_life_yr_at_parity))|"
     r"configurations/MEM_[^/]+/lcoh_usd_per_kg_usable|factorial_summary/(share_membrane_cheaper|membrane_range/\d|central/membrane_minus_psa))$",
     "H4 PSA against Pd-Ag membrane (sourced ranges)", "membrane annualised with CRF(10 %, membrane life) instead of 1/life (review C m2)"),
    ("results/research/purification/purification_study.json",
     r"^cases/[^/]+/configs/\[MEM[^\]]*\]/costs/[^/]+/usd_per_kg_usable_h2$",
     "H4 membrane configuration cost per kg usable H2 (Phase 1 configurations)", "membrane annualised with CRF(10 %, membrane life) (review C m2)"),
    ("results/research/uq/row_evidence.json", r"^row_evidence/H2-a/numbers/sobol_nh3_price_lcoh_HIon/[^/]+/(S1|S1_ci/\d|ST|ST_ci/\d)$",
     "Sobol index of the NH3 price on LCOH (heat integration on)", "first-order estimator on centred outputs (review C m1); total-effect unchanged"),
]
VERDICT_FILE = "results/research/evidence_matrix.json"


def git_json(rel: str):
    out = subprocess.run(["git", "show", f"{PRE_FIX}:{rel}"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if out.returncode != 0:
        return None
    return json.loads(out.stdout)


def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, f"{path}/{k}" if path else str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            idk = v.get("id") if isinstance(v, dict) else None
            yield from walk(v, f"{path}/[{idk}]" if idk is not None else f"{path}/{i}")
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        yield path, float(o)
    elif o is None:
        yield path, None


def verdicts(m) -> dict:
    out = {}
    for h in m["hypotheses"]:
        out[f"hypothesis {h['id']}"] = h["verdict"]
        for c in h.get("components", []):
            out[f"component {c['id']}"] = c["verdict"]
        for r in h["rows"]:
            out[f"row {r['row_id']}"] = r["verdict"]
    return out


def main() -> int:
    rows = []
    for rel, rx, qty, why in SELECT:
        old = git_json(rel)
        new = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        if old is None:
            print(f"{rel}: not in {PRE_FIX}", file=sys.stderr)
            return 2
        o, n = dict(walk(old)), dict(walk(new))
        for k in sorted(set(o) | set(n)):
            if not re.search(rx, k):
                continue
            a, b = o.get(k), n.get(k)
            if a == b or (a is not None and b is not None and abs(a - b) <= 1e-12 * max(1.0, abs(a))):
                continue
            rows.append({"quantity": qty, "file": rel, "key": k, "old": a, "new": b, "reason": why})
    # new verdicts derived in memory by the matrix builder (it is not written here), so this record can be made first
    sys.path.insert(0, str(ROOT / "scripts" / "research"))
    import build_evidence_matrix as bem  # noqa: E402
    vo, vn = verdicts(git_json(VERDICT_FILE)), verdicts(bem.build())
    vrows = [{"quantity": k, "file": VERDICT_FILE, "old": vo.get(k), "new": vn.get(k)} for k in vn if vo.get(k) != vn.get(k)]
    OUT.write_text(json.dumps({
        "provenance": {"script": "scripts/research/record_fix_pass.py", "old_values": f"git commit {PRE_FIX}",
                       "new_values": "working tree after the fix-pass re-runs", "plan": "findings of three independent reviews (verdicts; documents against the result files; models and code)"},
        "description": "Every selected stored number and every verdict that changed in the Phase 2 fix pass of 24 November 2026.",
        "verdict_changes": vrows, "number_changes": rows,
        "new_computed_blocks": [
            {"file": "results/research/reference_scenario/baseline.json", "key": "fuel_efficiency_sensitivity",
             "what": "LCOH, NPV, break-even NH3 price and heat-integration saving with supplementary NH3 fuel at 1.0, 0.9225 and 0.85 of its LHV; baseline unchanged"},
            {"file": "results/research/enduse/turbine_threshold.json", "key": "cracker_heat_fuel_efficiency_sensitivity",
             "what": "fired-cracking and cracking + PSA turbine-efficiency thresholds with the cracker heat at 1.0, 0.9225 and 0.85 of the fuel LHV"},
            {"file": "results/research/heat_exchanger/heat_exchanger_study.json", "key": "row_evidence/H3-d/breakeven_crf_solved",
             "what": "break-even capital recovery factor solved at U low / central / high"},
            {"file": "results/research/catalyst_economics/catalyst_economics.json", "key": "resolution",
             "what": "fired-duty offset and its spread across catalysts (both resolution readings)"}],
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"verdict changes {len(vrows)}, number changes {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
