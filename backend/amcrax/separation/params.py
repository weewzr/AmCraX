"""Loader for backend/amcrax/data/separation.yaml (sourced reduced-order separation parameters)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "separation.yaml"

MODEL_LABEL = "reduced-order model"


@lru_cache(maxsize=1)
def params() -> dict:
    with open(DATA_FILE, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def psa_point(point_id: str) -> dict:
    for p in params()["psa"]["operating_points"]:
        if p["id"] == point_id:
            return p
    raise KeyError(f"unknown PSA operating point {point_id!r}")


def permeability_set(set_id: str | None = None) -> dict:
    m = params()["membrane"]
    set_id = set_id or m["default_permeability_set"]
    for s in m["permeability_sets"]:
        if s["id"] == set_id:
            if not s.get("usable", True):
                raise ValueError(f"permeability set {set_id!r} is flagged not usable: {s.get('reason')}")
            return s
    raise KeyError(f"unknown permeability set {set_id!r}")


def cite(d: dict) -> str:
    """'citekey p. X, locator' for a parameter entry."""
    if d.get("source") == "assumption":
        return "assumption: " + str(d.get("rationale", "")).strip()
    return f"{d['citekey']} p. {d['page']}, {d['locator']}"
