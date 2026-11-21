"""Shared matplotlib style for AmCraX figures (light, report-ready).

Colours follow docs/reference_projects/design_tokens.md (light theme species/heat/cold tokens).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

C_NH3 = "#15803d"
C_H2 = "#be185d"
C_N2 = "#4f46e5"
C_HEAT = "#c2410c"
C_COLD = "#1d4ed8"
C_PRIMARY = "#0369a1"
C_AMBER = "#a16207"
C_GREY = "#5b6788"
PALETTE = [C_PRIMARY, C_HEAT, C_NH3, C_H2, C_N2, C_AMBER]

PROVENANCE = "Source: Aspen Plus V15 (PENG-ROB), AmCraX automated runs"

_ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = _ROOT / "results" / "figures"


def apply_style() -> None:
    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
        "font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "Arial", "DejaVu Sans"],
        "font.size": 9.5, "axes.titlesize": 10.5, "axes.labelsize": 9.5,
        "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 8.5,
        "axes.grid": True, "grid.linewidth": 0.4, "grid.alpha": 0.5, "grid.color": "#b4bfda",
        "axes.edgecolor": "#33415f", "axes.linewidth": 0.8,
        "axes.prop_cycle": matplotlib.cycler(color=PALETTE),
        "lines.linewidth": 1.8, "lines.markersize": 4.5,
        "legend.frameon": True, "legend.framealpha": 0.9, "legend.edgecolor": "#d6ddee",
        "axes.spines.top": False, "axes.spines.right": False,
        "figure.dpi": 100, "savefig.dpi": 300,
    })


def add_provenance(fig, extra: str = "") -> None:
    txt = PROVENANCE + (" | " + extra if extra else "")
    fig.text(0.01, 0.005, txt, fontsize=7, color=C_GREY, ha="left", va="bottom")


def save(fig, name: str) -> Path:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    p = FIG_DIR / (name if name.endswith(".png") else name + ".png")
    fig.savefig(p, dpi=300, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    return p
