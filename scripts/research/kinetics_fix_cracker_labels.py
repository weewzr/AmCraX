"""Correct the stored cracker block entry of integrated RPLUG case JSONs (Phase 2, task K1 item 5).

Defect: results/research/aspen_kinetic/{ci,ki}_*.json listed the kinetic cracker with block_type 'RGibbs' and outlet
temperature/pressure 1.0/1.0 (the generic flowsheet extractor uses the RGibbs flowsheet metadata and reads RGibbs
scalar paths, which are profile arrays in RPLUG). The extraction code is fixed in
backend/amcrax/aspen/kinetic.py (correct_cracker_block_entry). This script applies the same correction to the stored
JSONs from values already in each file (cracker outlet stream S5, RPLUG duty): no re-solve is needed, because the
duty is correct and the outlet stream is stored. Idempotent. Run from the AmCraX root.
"""
from __future__ import annotations

import glob
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from amcrax.aspen.kinetic import correct_cracker_block_entry  # noqa: E402


def main() -> int:
    files = sorted(glob.glob(os.path.join(ROOT, "results", "research", "aspen_kinetic", "ci_*.json"))
                   + glob.glob(os.path.join(ROOT, "results", "research", "aspen_kinetic", "ki_*.json")))
    changed = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        a = d.get("aspen") or {}
        fr = a.get("flowsheet_result")
        if not fr or "CRACKER" not in (fr.get("blocks") or {}):
            continue
        before = json.dumps(fr["blocks"]["CRACKER"], sort_keys=True)
        correct_cracker_block_entry(fr, a)
        after = json.dumps(fr["blocks"]["CRACKER"], sort_keys=True)
        if before != after:
            with open(f, "w", encoding="utf-8") as fh:
                json.dump(d, fh, indent=2)
            changed.append(os.path.basename(f))
    print(json.dumps({"files_checked": len(files), "files_changed": changed}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
