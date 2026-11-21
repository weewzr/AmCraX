"""Canonical project paths. Every module resolves files through this module."""
from __future__ import annotations

import os
from pathlib import Path

#: Project root (the directory that contains ``backend/``, ``aspen/``, ``results/`` ...).
ROOT: Path = Path(os.environ.get("AMCRAX_ROOT") or Path(__file__).resolve().parents[2])

ASPEN_DIR = ROOT / "aspen"
ASPEN_MODELS = ASPEN_DIR / "models"
ASPEN_RUNS = ASPEN_DIR / "runs"
ASPEN_SCREENSHOTS = ASPEN_DIR / "screenshots"

CONFIG_DIR = ROOT / "config"
RESEARCH_DIR = ROOT / "research"

RESULTS_DIR = ROOT / "results"
RESULTS_SIMULATIONS = RESULTS_DIR / "simulations"
RESULTS_FIGURES = RESULTS_DIR / "figures"
RESULTS_SENSITIVITY = RESULTS_DIR / "sensitivity"
RESULTS_OPTIMISATION = RESULTS_DIR / "optimisation"
RESULTS_VALIDATION = RESULTS_DIR / "validation"

DOCS_DIR = ROOT / "docs"
FRONTEND_DIR = ROOT / "frontend"


def ensure_dirs() -> None:
    """Create the output directories if they do not exist yet."""
    for p in (
        ASPEN_MODELS,
        ASPEN_RUNS,
        ASPEN_SCREENSHOTS,
        RESULTS_SIMULATIONS,
        RESULTS_FIGURES,
        RESULTS_SENSITIVITY,
        RESULTS_OPTIMISATION,
        RESULTS_VALIDATION,
    ):
        p.mkdir(parents=True, exist_ok=True)
