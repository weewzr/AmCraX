"""Matplotlib figures (300 dpi) for a HeatIntegrationResult."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .models import HeatIntegrationResult, PinchTargets  # noqa: E402

# Validated default categorical palette (dataviz skill references/palette.md, light mode)
HOT = "#eb6834"    # slot 2 orange - hot composite
COLD = "#2a78d6"   # slot 1 blue - cold composite
ACCENT = "#1baf7a"  # slot 3 aqua
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def _style(ax):
    ax.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=8)


def _composite_panel(ax, t: PinchTargets, src: str):
    ax.plot(t.hot_composite_H_kW, t.hot_composite_T_C, color=HOT, lw=2, label="Hot composite")
    ax.plot(t.cold_composite_H_kW, t.cold_composite_T_C, color=COLD, lw=2, label="Cold composite")
    title = f"{t.label}\nQh,min = {t.hot_utility_kW:.0f} kW, Qc,min = {t.cold_utility_kW:.0f} kW"
    if t.pinch_hot_C is not None:
        title += f", pinch {t.pinch_hot_C:.0f}/{t.pinch_cold_C:.0f} degC"
    else:
        title += " (threshold, no pinch)"
    ax.set_title(title, fontsize=9, color=INK)
    ax.set_xlabel("Enthalpy flow, kW", color=INK2)
    ax.set_ylabel("Temperature, degC", color=INK2)
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    _style(ax)


def plot_all(h: HeatIntegrationResult, fig_dir: Path) -> list[Path]:
    fig_dir.mkdir(parents=True, exist_ok=True)
    src = f"case {h.case_id}, input: {h.input_source.value}, dT_min = {h.dT_min_K:g} K"
    out: list[Path] = []
    panels = [h.targets_process] + ([h.targets_with_flue] if h.targets_with_flue else [])

    fig, axes = plt.subplots(1, len(panels), figsize=(6 * len(panels), 4.6), squeeze=False)
    for ax, t in zip(axes[0], panels):
        _composite_panel(ax, t, src)
    fig.suptitle(f"Composite curves - {src}", fontsize=10, color=INK)
    fig.tight_layout()
    p = fig_dir / f"hi_composite_{h.case_id}.png"
    fig.savefig(p, dpi=300)
    plt.close(fig)
    out.append(p)

    fig, axes = plt.subplots(1, len(panels), figsize=(6 * len(panels), 4.6), squeeze=False)
    for ax, t in zip(axes[0], panels):
        ax.plot(t.gcc_H_kW, t.gcc_T_shifted_C, color=ACCENT, lw=2)
        ax.axvline(0, color=INK2, lw=0.8)
        ax.set_title(f"{t.label}\nQh,min = {t.hot_utility_kW:.0f} kW (top), Qc,min = {t.cold_utility_kW:.0f} kW (bottom)",
                     fontsize=9, color=INK)
        ax.set_xlabel("Net heat flow, kW", color=INK2)
        ax.set_ylabel("Shifted temperature, degC", color=INK2)
        _style(ax)
    fig.suptitle(f"Grand composite curves - {src}", fontsize=10, color=INK)
    fig.tight_layout()
    p = fig_dir / f"hi_grand_composite_{h.case_id}.png"
    fig.savefig(p, dpi=300)
    plt.close(fig)
    out.append(p)

    rows = h.configurations
    labels = [r.label.replace(" (dT_min", "\n(dT_min").replace("(d) Pinch target, ", "(d) Pinch target\n")
              .replace("(d) Pinch target incl.", "(d) Pinch target\nincl.") for r in rows]
    import numpy as np

    y = np.arange(len(rows))
    w = 0.38
    fig, ax = plt.subplots(figsize=(8.5, 0.9 * len(rows) + 1.6))
    b1 = ax.barh(y - w / 2, [r.external_heating_kW for r in rows], height=w - 0.04, color=HOT, label="External heating")
    b2 = ax.barh(y + w / 2, [r.external_cooling_kW for r in rows], height=w - 0.04, color=COLD, label="External cooling (process)")
    for i, r in enumerate(rows):
        txt = f"{r.external_heating_kW:.0f} kW"
        if r.specific_heat_demand_kWh_per_kgH2 is not None:
            red = f", -{100 * r.reduction_vs_no_recovery:.0f} %" if r.reduction_vs_no_recovery > 0.005 else ""
            txt += f"  ({r.specific_heat_demand_kWh_per_kgH2:.2f} kWh/kg H2{red})"
        ax.text(r.external_heating_kW, i - w / 2, " " + txt, va="center", fontsize=7, color=INK)
        ax.text(r.external_cooling_kW, i + w / 2, f" {r.external_cooling_kW:.0f} kW", va="center", fontsize=7, color=INK2)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Duty, kW", color=INK2)
    ax.set_xlim(0, max(r.external_heating_kW for r in rows) * 1.75)
    ax.set_title(f"Heat-recovery configurations - {src}", fontsize=10, color=INK)
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    _style(ax)
    ax.grid(False, axis="y")
    fig.tight_layout()
    p = fig_dir / f"hi_configuration_comparison_{h.case_id}.png"
    fig.savefig(p, dpi=300)
    plt.close(fig)
    out.append(p)
    return out
