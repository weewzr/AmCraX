"""Side-by-side comparison of two SimulationResults (e.g. Aspen Plus vs Python model).

CLI::

    python -m amcrax.process_model.compare a.json b.json --csv out.csv

Each row: quantity, a, b, abs_diff (= b - a), rel_diff (= (b - a) / |a|, None when a == 0 or missing).
Only quantities present (not None) in at least one result are listed; a missing value is None.
Enthalpy flows are compared too, but note they depend on each simulator's reference state.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from amcrax.schemas import COMPONENTS, KPIs, SimulationResult

STREAM_FIELDS = ("temperature_C", "pressure_bar", "vapor_fraction", "mole_flow_kmol_h", "mass_flow_kg_h",
                 "enthalpy_flow_kW")
BLOCK_FIELDS = ("duty_kW", "power_kW", "outlet_temperature_C", "outlet_pressure_bar")


def _row(q: str, a, b) -> dict:
    a = None if a is None else float(a)
    b = None if b is None else float(b)
    d = None if (a is None or b is None) else b - a
    r = None if (d is None or a == 0) else d / abs(a)
    return {"quantity": q, "a": a, "b": b, "abs_diff": d, "rel_diff": r}


def compare_results(a: SimulationResult, b: SimulationResult) -> list[dict]:
    rows: list[dict] = []
    for sid in sorted(set(a.streams) | set(b.streams)):
        sa, sb = a.streams.get(sid), b.streams.get(sid)
        for f in STREAM_FIELDS:
            va = getattr(sa, f) if sa else None
            vb = getattr(sb, f) if sb else None
            if va is not None or vb is not None:
                rows.append(_row(f"stream.{sid}.{f}", va, vb))
        for c in COMPONENTS:
            for kind, attr in (("flow_kmol_h", "component_mole_flow_kmol_h"), ("mole_frac", "mole_frac")):
                va = getattr(sa, attr).get(c) if sa else None
                vb = getattr(sb, attr).get(c) if sb else None
                if va is not None or vb is not None:
                    rows.append(_row(f"stream.{sid}.{kind}.{c}", va, vb))
    for bid in sorted(set(a.blocks) | set(b.blocks)):
        ba, bb = a.blocks.get(bid), b.blocks.get(bid)
        for f in BLOCK_FIELDS:
            va = getattr(ba, f) if ba else None
            vb = getattr(bb, f) if bb else None
            if va is not None or vb is not None:
                rows.append(_row(f"block.{bid}.{f}", va, vb))
    for f in KPIs.model_fields:
        va, vb = getattr(a.kpis, f), getattr(b.kpis, f)
        if va is not None or vb is not None:
            rows.append(_row(f"kpi.{f}", va, vb))
    return rows


def load(path: str | Path) -> SimulationResult:
    return SimulationResult.model_validate_json(Path(path).read_text(encoding="utf-8"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Compare two AmCraX SimulationResult JSON files")
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--csv", default=None, help="write the comparison table to this CSV file")
    args = ap.parse_args(argv)
    ra, rb = load(args.a), load(args.b)
    rows = compare_results(ra, rb)
    if args.csv:
        Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["quantity", "a", "b", "abs_diff", "rel_diff"])
            w.writeheader()
            w.writerows(rows)
    fmt = lambda v: "" if v is None else f"{v:.6g}"  # noqa: E731
    print(f"a = {args.a} [{ra.source.value}]\nb = {args.b} [{rb.source.value}]")
    print(f"{'quantity':52s} {'a':>14s} {'b':>14s} {'b-a':>12s} {'rel':>10s}")
    for r in rows:
        print(f"{r['quantity']:52s} {fmt(r['a']):>14s} {fmt(r['b']):>14s} {fmt(r['abs_diff']):>12s} "
              f"{fmt(r['rel_diff']):>10s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
