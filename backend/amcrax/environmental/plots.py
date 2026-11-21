"""Figures for the simplified carbon-intensity accounting (not a life-cycle assessment)."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from amcrax.plotstyle import C_AMBER, C_GREY, C_HEAT, C_N2, C_NH3, C_PRIMARY, apply_style, plt

from . import HEATING_LABELS, HEATING_OPTIONS, NH3_ROUTES, CarbonIntensityResult, ScenarioComparison

_PARTS = (("upstream_ammonia", "upstream NH3", C_NH3), ("transport", "NH3 transport", C_N2),
          ("electricity", "electricity", C_AMBER), ("external_heat", "external heat", C_HEAT))


def _provenance(fig, input_source: str) -> None:
    fig.text(0.01, 0.005, f"AmCraX simplified carbon-intensity accounting (NOT an LCA) | flowsheet: {input_source} | "
             "factors: amcrax/data/environmental.yaml", fontsize=6.5, color=C_GREY, ha="left", va="bottom")


def _refs(ax, lines) -> None:
    lines = sorted(lines, key=lambda r: r.value_kgCO2e_per_kgH2)
    for i, rl in enumerate(lines):
        c = [C_PRIMARY, C_GREY][i % 2]
        ax.axhline(rl.value_kgCO2e_per_kgH2, color=c, ls="--", lw=1.0)
        # lowest line: label below it; others: label above it (avoids overlap of close lines)
        ax.annotate(f"{rl.label}: {rl.value_kgCO2e_per_kgH2:.2f}", xy=(1.0, rl.value_kgCO2e_per_kgH2),
                    xycoords=("axes fraction", "data"), xytext=(-2, -3 if i == 0 else 3), textcoords="offset points",
                    fontsize=6.5, ha="right", va="top" if i == 0 else "bottom", color=c,
                    bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="none", alpha=0.85))


def plot_scenarios(cmp: ScenarioComparison, out_dir: Path) -> Path:
    apply_style()
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = np.arange(len(NH3_ROUTES))
    w = 0.26
    colors = {"natural_gas": C_HEAT, "self_firing": C_NH3, "electric": C_AMBER}
    tab = {(r.nh3_route, r.heating_option): r.total_kgCO2e_per_kgH2 for r in cmp.rows}
    for j, h in enumerate(HEATING_OPTIONS):
        vals = [tab[(r, h)] for r in NH3_ROUTES]
        b = ax.bar(x + (j - 1) * w, vals, w, label=HEATING_LABELS[h], color=colors[h])
        ax.bar_label(b, fmt="%.2f", fontsize=6.5, padding=1)
    ax.set_xticks(x, [f"{r} NH3" for r in NH3_ROUTES])
    ax.set_ylabel("kg CO$_2$e / kg H$_2$")
    ax.set_title(f"Carbon intensity of H2 at cracker outlet - case {cmp.case_id} (grid {cmp.grid}, "
                 f"{cmp.transport_distance_km:g} km ship)")
    ax.set_xlim(-0.6, len(NH3_ROUTES) - 0.4)
    _refs(ax, cmp.reference_lines)
    ax.legend(loc="upper left")
    _provenance(fig, cmp.input_source.value)
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"ci_scenarios_{cmp.case_id}.png"
    fig.savefig(p, dpi=300, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    return p


def plot_breakdown(cmp: ScenarioComparison, out_dir: Path) -> Path:
    apply_style()
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    labels = [f"{r.nh3_route}\n{r.heating_option.replace('_', ' ')}" for r in cmp.rows]
    x = np.arange(len(cmp.rows))
    bottom = np.zeros(len(cmp.rows))
    for key, lab, c in _PARTS:
        v = np.array([getattr(r.breakdown_kgCO2e_per_kgH2, key) for r in cmp.rows])
        ax.bar(x, v, 0.65, bottom=bottom, label=lab, color=c)
        bottom += v
    for xi, t in zip(x, bottom):
        ax.text(xi, t, f"{t:.2f}", ha="center", va="bottom", fontsize=6.5)
    ax.set_xticks(x, labels, fontsize=7)
    ax.set_ylabel("kg CO$_2$e / kg H$_2$")
    ax.set_title(f"Carbon-intensity breakdown - case {cmp.case_id}")
    ax.set_xlim(-0.6, len(cmp.rows) - 0.4)
    _refs(ax, cmp.reference_lines)
    ax.legend(loc="upper left", fontsize=7.5)
    _provenance(fig, cmp.input_source.value)
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"ci_breakdown_{cmp.case_id}.png"
    fig.savefig(p, dpi=300, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    return p


def plot_all(cmp: ScenarioComparison, out_dir: Path) -> list[Path]:
    return [plot_scenarios(cmp, out_dir), plot_breakdown(cmp, out_dir)]


__all__ = ["plot_scenarios", "plot_breakdown", "plot_all", "CarbonIntensityResult"]
