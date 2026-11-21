"""Hydrogen purification study (reduced-order PSA / Pd-Ag membrane models) for one SimulationResult.

Usage:
    python scripts/run_separation_study.py [results/simulations/baseline.json] [--out-dir DIR]

Without an argument: results/simulations/baseline.json (Aspen) if present, else python_baseline.json,
else a fresh Python baseline (run_python_case). The input source is written into every output.
Writes results/simulations/separation_<case_id>.json, results/sensitivity/membrane_recovery_vs_area.csv,
results/sensitivity/psa_recovery_cases.csv and results/figures/sep_*.png.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

from amcrax import paths
from amcrax.plotstyle import C_GREY, C_H2, C_HEAT, C_N2, C_PRIMARY, apply_style, plt
from amcrax.schemas import CaseInputs, SimulationResult
from amcrax.separation import (MODEL_LABEL, compare_purification, cracked_gas, membrane_separator, params,
                               psa_performance)
from amcrax.separation.compare import PSA_BASES


def load_input(p: Path | None) -> tuple[SimulationResult, str]:
    if p is not None:
        return SimulationResult.model_validate_json(p.read_text(encoding="utf-8")), str(p)
    for f in (paths.RESULTS_SIMULATIONS / "baseline.json", paths.RESULTS_SIMULATIONS / "python_baseline.json"):
        if f.exists():
            return SimulationResult.model_validate_json(f.read_text(encoding="utf-8")), f"{f} (fallback default)"
    from amcrax.process_model import run_python_case
    return run_python_case(CaseInputs()), "run_python_case(CaseInputs()) (fallback: no result file found)"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("result_json", type=Path, nargs="?", default=None)
    ap.add_argument("--out-dir", type=Path, default=None)
    a = ap.parse_args(argv)
    res, origin = load_input(a.result_json)
    sim_dir = a.out_dir or paths.RESULTS_SIMULATIONS
    sens_dir = a.out_dir or paths.RESULTS_SENSITIVITY
    fig_dir = a.out_dir or paths.RESULTS_FIGURES
    for d in (sim_dir, sens_dir, fig_dir):
        d.mkdir(parents=True, exist_ok=True)
    src_label = f"input: {res.source.value} case '{res.case_id}'"
    cmp = compare_purification(res)
    sid, feed, P, T_C = cracked_gas(res)
    T_K = (T_C or 40.0) + 273.15
    Tm_C = params()["membrane"]["default_temperature_C"]["value"]

    out = json.loads(cmp.model_dump_json())
    out["metadata"] = {"model": MODEL_LABEL, "input_file": origin, "input_source": res.source.value,
                       "parameters": "backend/amcrax/data/separation.yaml",
                       "disclaimer": "reduced-order models; literature PSA points applied as splits and ideal "
                                     "Sieverts membrane - not designed or validated separation units"}
    jpath = sim_dir / f"separation_{res.case_id}.json"
    jpath.write_text(json.dumps(out, indent=2), encoding="utf-8")

    # membrane recovery vs area for feed / permeate pressure
    areas = np.linspace(0, 80, 41)
    mrows = []
    sweeps = [(pf, 1.0) for pf in (5.0, 10.0, P, 30.0)] + [(P, pp) for pp in (0.5, 2.0, 4.0)]
    curves = {}
    for pf, pp in sweeps:
        m = membrane_separator(feed, float(areas[-1]), pf, pp, n_profile=len(areas))
        curves[(pf, pp)] = [pt.recovery for pt in m.profile]
        for pt in m.profile:
            mrows.append({"case_id": res.case_id, "input_source": res.source.value, "model": MODEL_LABEL,
                          "membrane_T_C": Tm_C, "feed_pressure_bar": pf, "permeate_pressure_bar": pp,
                          "area_m2": round(pt.area_m2, 6), "h2_recovery": pt.recovery,
                          "max_recovery_at_pinch": m.max_recovery_at_pinch, "permeability_set": m.permeability_set})
    mcsv = sens_dir / "membrane_recovery_vs_area.csv"
    with open(mcsv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(mrows[0]))
        w.writeheader()
        w.writerows(mrows)

    # PSA literature points x feed pressure (compression need)
    prows = []
    for b in PSA_BASES:
        for pf in sorted({P, 5.0, 2.0}, reverse=True):
            r = psa_performance(feed, pf, basis=b, feed_temperature_K=T_K)
            prows.append({"case_id": res.case_id, "input_source": res.source.value, "model": MODEL_LABEL,
                          "basis": b, "basis_source": r.basis_source, "feed_pressure_bar": pf,
                          "required_feed_pressure_bar": r.required_feed_pressure_bar,
                          "tailgas_pressure_bar": r.tailgas_pressure_bar, "h2_recovery": r.h2_recovery,
                          "h2_purity": r.h2_purity_mole_frac, "h2_product_kg_h": r.product_h2_kg_h,
                          "tailgas_kmol_h": sum(r.tailgas_kmol_h.values()), "tailgas_y_H2": r.tailgas_mole_frac.get("H2", 0),
                          "tailgas_y_N2": r.tailgas_mole_frac.get("N2", 0), "tailgas_y_NH3": r.tailgas_mole_frac.get("NH3", 0),
                          "compression_power_kW": r.compression_power_kW, "compression_stages": r.compression_stages,
                          "energy_kWh_per_kgH2": r.specific_energy_kWh_per_kgH2, "h2_loss_lhv_kW": r.h2_loss_lhv_kW})
    pcsv = sens_dir / "psa_recovery_cases.csv"
    with open(pcsv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(prows[0]))
        w.writeheader()
        w.writerows(prows)

    # figures
    apply_style()
    figs = []
    foot = f"AmCraX {MODEL_LABEL} (ideal Sieverts, Pd-Ag {cmp.membrane[next(iter(cmp.membrane))].permeability_set if cmp.membrane else ''}, " \
           f"{Tm_C:g} degC); feed composition from {src_label}"
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    cols = [C_GREY, C_N2, C_PRIMARY, C_HEAT]
    for i, pf in enumerate((5.0, 10.0, P, 30.0)):
        axs[0].plot(areas, curves[(pf, 1.0)], color=cols[i], label=f"feed {pf:g} bar")
    axs[0].set_title("H2 recovery vs area (permeate 1 bar)")
    for i, pp in enumerate((0.5, 1.0, 2.0, 4.0)):
        axs[1].plot(areas, curves[(P, pp)], color=cols[i], label=f"permeate {pp:g} bar")
    axs[1].set_title(f"H2 recovery vs area (feed {P:g} bar)")
    for ax in axs:
        ax.set_xlabel("membrane area, m2")
        ax.set_ylabel("H2 recovery factor, -")
        ax.set_ylim(0, 1)
        ax.legend()
    fig.text(0.01, 0.005, foot, fontsize=7, color=C_GREY)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    f1 = fig_dir / "sep_membrane_recovery_vs_area.png"
    fig.savefig(f1, dpi=300)
    plt.close(fig)
    figs.append(f1)

    if cmp.membrane:
        m = list(cmp.membrane.values())[-1]
        fig, ax = plt.subplots(figsize=(6, 4))
        A = [p.area_m2 for p in m.profile]
        ax.plot(A, [p.y_h2_retentate for p in m.profile], color=C_H2, label="y_H2 retentate")
        ax.plot(A, [p.recovery for p in m.profile], color=C_PRIMARY, label="H2 recovery")
        ax2 = ax.twinx()
        ax2.plot(A, [p.flux_mol_m2_s for p in m.profile], color=C_HEAT, ls="--", label="flux")
        ax2.set_ylabel("H2 flux, mol m-2 s-1")
        ax2.grid(False)
        ax.set_xlabel("membrane area, m2")
        ax.set_ylabel("-")
        ax.set_title(f"Membrane profile (R={m.h2_recovery:.2f}, {m.feed_pressure_bar:g}/{m.permeate_pressure_bar:g} bar)")
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, loc="center right")
        fig.text(0.01, 0.005, f"AmCraX {MODEL_LABEL}; {src_label}", fontsize=7, color=C_GREY)
        fig.tight_layout(rect=(0, 0.04, 1, 1))
        f2 = fig_dir / f"sep_membrane_profile_{res.case_id}.png"
        fig.savefig(f2, dpi=300)
        plt.close(fig)
        figs.append(f2)

    fig, axs = plt.subplots(1, 2, figsize=(10, 4.2))
    lab = [r.option.replace("Pd-Ag membrane", "Membrane").replace(" (", "\n(").replace("_", "\n", 1) for r in cmp.rows]
    x = np.arange(len(cmp.rows))
    axs[0].bar(x, [r.h2_recovery for r in cmp.rows], color=[C_PRIMARY if r.option.startswith("PSA") else C_H2 for r in cmp.rows])
    axs[0].set_ylabel("H2 recovery, -")
    axs[0].set_ylim(0, 1)
    axs[0].set_title("H2 recovery")
    axs[1].bar(x - 0.2, [r.energy_kWh_per_kgH2 for r in cmp.rows], 0.4, color=C_PRIMARY, label="compression")
    axs[1].bar(x + 0.2, [r.energy_kWh_per_kgH2_incl_product_recompression for r in cmp.rows], 0.4, color=C_HEAT,
               label="incl. product recompression")
    axs[1].set_ylabel("kWh/kg H2")
    axs[1].set_title("Specific electricity")
    axs[1].legend()
    for ax in axs:
        ax.set_xticks(x)
        ax.set_xticklabels(lab, fontsize=6.5)
    fig.text(0.01, 0.005, f"AmCraX {MODEL_LABEL}s - PSA = literature operating points; {src_label}", fontsize=7, color=C_GREY)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    f3 = fig_dir / f"sep_comparison_{res.case_id}.png"
    fig.savefig(f3, dpi=300)
    plt.close(fig)
    figs.append(f3)

    print(f"{src_label} ({origin}); feed stream {sid} at {P:g} bar")
    print(f"  {'option':28s} {'recov':>6s} {'purity':>8s} {'area m2':>8s} {'kWh/kg':>7s} {'+recomp':>8s} {'H2 loss kW LHV':>15s}")
    for r in cmp.rows:
        A = "" if r.membrane_area_m2 is None else f"{r.membrane_area_m2:.1f}"
        print(f"  {r.option:28s} {r.h2_recovery:6.3f} {r.h2_purity_mole_frac:8.5f} {A:>8s} {r.energy_kWh_per_kgH2:7.3f} "
              f"{r.energy_kWh_per_kgH2_incl_product_recompression:8.3f} {r.h2_loss_lhv_kW:15.1f}")
    s = cmp.ammonia_slip
    print(f"  NH3 in cracked gas {s.nh3_cracked_gas_ppm:.0f} ppm vs limit {s.limit_ppm} ppm -> required removal "
          f"{s.required_nh3_removal_factor:.7f}")
    for p in (jpath, mcsv, pcsv, *figs):
        print("wrote", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
