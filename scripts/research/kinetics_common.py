"""Shared helpers for the workstream K kinetics scripts (scripts/research/kinetics_*.py)."""
from __future__ import annotations

import contextlib
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")

from amcrax.kinetics.rate_laws import _all_cats  # noqa: E402

OUT = ROOT / "results" / "research" / "kinetics"
FIG = ROOT / "results" / "figures" / "research"
VAL = ROOT / "results" / "research" / "validation"
for _d in (OUT, FIG, VAL):
    _d.mkdir(parents=True, exist_ok=True)

NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")
ATM_BAR = 1.01325
VM_0C_L_PER_MOL = 22.414    # ideal gas, 0 degC, 1 atm (assumption: reference state of mL/min flows)
VM_25C_L_PER_MOL = 24.465   # ideal gas, 25 degC, 1 atm (sensitivity)

ALL_STUDY_CATALYSTS = [
    "ni_takahashi_microkinetic",
    "ru_takahashi_microkinetic",
    "ru_kum_temkin_pyzhev",
    "nire_ceo2_5ni1ru_lucentini_lhhw",
    "nire_ceo2_2p5ni0p5ru_lucentini_lhhw",
]


def provenance(script: str, inputs_summary: str, source_type: str = "python") -> dict:
    return {"generated_utc": NOW, "script": script, "source_type": source_type, "inputs_summary": inputs_summary,
            "model_versions": {"kinetics_registry": "backend/amcrax/data/kinetics.yaml (catalysts + research_catalysts)",
                               "reactor": "amcrax.reactor.pfr.simulate_pfr (1-D pseudo-homogeneous PFR)",
                               "thermo": "amcrax.thermodynamics (NASA7 / GRI-Mech 3.0, ideal gas)"}}


def _clean(o):
    """Strict JSON: NaN/inf -> null, numpy scalars -> float."""
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if hasattr(o, "item") and not isinstance(o, (str, bytes)):
        o = o.item()
    if isinstance(o, float) and (o != o or o in (float("inf"), float("-inf"))):
        return None
    return o


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(_clean(obj), indent=2, allow_nan=False), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    keys = list(rows[0].keys())
    for r in rows[1:]:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


@contextlib.contextmanager
def parameter_override(catalyst_id: str, **values):
    """Temporarily replace registry parameter values in memory (sensitivity runs only; restored on exit)."""
    par = _all_cats()[catalyst_id]["parameters"]
    old = {k: par[k]["value"] for k in values}
    try:
        for k, v in values.items():
            par[k]["value"] = v
        yield
    finally:
        for k, v in old.items():
            par[k]["value"] = v


def footer(fig, text: str) -> None:
    from amcrax.plotstyle import C_GREY
    fig.text(0.01, -0.04, text, fontsize=6.5, color=C_GREY, ha="left", va="bottom")
