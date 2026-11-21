"""Aspen Plus RGibbs equilibrium grid for validating the independent Python equilibrium model.

Pure NH3 at (T, P) -> isothermal RGibbs at (T, P), for PENG-ROB (the flowsheet method) and IDEAL
(isolates thermochemical-data differences from equation-of-state effects). Every point is a
re-initialised run.

Outputs
-------
results/validation/equilibrium_aspen_grid.csv
    columns T_C,P_bar,property_method,nh3_conversion,y_NH3,y_H2,y_N2,heat_duty_kJ_per_mol_NH3_fed
results/validation/aspen_binary_parameters.json
    raw dump of the binary-interaction parameter forms of the PENG-ROB model (e.g. PRKBV kij that
    Aspen retrieved from the EOS-LIT databank), for the equation-of-state discrepancy analysis
"""
from __future__ import annotations

import csv
import json
import logging

from amcrax.aspen.runner import run_equilibrium_grid
from amcrax.aspen.session import AspenSession
from amcrax.paths import RESULTS_VALIDATION, ensure_dirs

TEMPERATURES_C = [float(t) for t in range(250, 901, 50)]
PRESSURES_BAR = [1.0, 5.0, 10.0, 20.0, 30.0, 40.0]
REPEAT_CHECK = [(400.0, 1.0), (600.0, 20.0), (600.0, 30.0), (500.0, 40.0)]
COLUMNS = ["T_C", "P_bar", "property_method", "nh3_conversion", "y_NH3", "y_H2", "y_N2", "heat_duty_kJ_per_mol_NH3_fed"]
BIP = r"\Data\Properties\Parameters\Binary Interaction"


def _dump(s: AspenSession, path: str, depth: int) -> object:
    """Recursively dump a variable-tree branch (values of leaves, dict of children otherwise)."""
    kids = s.children(path)
    if not kids or depth == 0:
        return s.get(path)
    return {k: _dump(s, path + "\\" + k, depth - 1) for k in kids}


def dump_binary_parameters(s: AspenSession) -> None:
    out = {"source": "Aspen Plus V15 variable tree, PENG-ROB equilibrium validation model", "forms": {}}
    for form in s.children(BIP):
        out["forms"][form] = _dump(s, rf"{BIP}\{form}\Input", depth=4)
    path = RESULTS_VALIDATION / "aspen_binary_parameters.json"
    path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"wrote {path} (forms: {list(out['forms'])})")


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    ensure_dirs()
    rows: list[dict] = []
    for method in ("PENG-ROB", "IDEAL"):
        hook = dump_binary_parameters if method == "PENG-ROB" else None
        grid = rows_m = run_equilibrium_grid(TEMPERATURES_C, PRESSURES_BAR, property_method=method, session_hook=hook)
        rows += rows_m
        # repeatability: independent single-point sessions must reproduce the grid values
        lookup = {(r["T_C"], r["P_bar"]): r for r in grid}
        worst_x = worst_q = 0.0
        for t, p in REPEAT_CHECK:
            again = run_equilibrium_grid([t], [p], property_method=method)[0]
            worst_x = max(worst_x, abs(again["nh3_conversion"] - lookup[(t, p)]["nh3_conversion"]))
            worst_q = max(worst_q, abs(again["heat_duty_kJ_per_mol_NH3_fed"] - lookup[(t, p)]["heat_duty_kJ_per_mol_NH3_fed"]))
        print(f"{method}: {len(grid)} points; repeatability max |dX| = {worst_x:.2e}, max |dQ| = {worst_q:.2e} kJ/mol")
        if worst_x > 1e-6 or worst_q > 1e-4:
            print("REPEATABILITY CHECK FAILED - do not use this grid")
            return 1
        # internal consistency: duty per mole converted must vary smoothly with T only (ideal gas)
        if method == "IDEAL":
            by_t: dict[float, list[float]] = {}
            for r in grid:
                by_t.setdefault(r["T_C"], []).append(r["heat_duty_kJ_per_mol_NH3_fed"] / r["nh3_conversion"])
            spread = max(max(v) - min(v) for v in by_t.values())
            print(f"IDEAL: max spread of duty/conversion across pressures at fixed T = {spread:.2e} kJ/mol")
            if spread > 1e-3:
                print("STALE-RESULT CHECK FAILED (duty/conversion must not depend on pressure for an ideal gas)")
                return 1
    out = RESULTS_VALIDATION / "equilibrium_aspen_grid.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
