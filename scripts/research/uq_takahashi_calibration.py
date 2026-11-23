"""Task U1 / T2b: Bayesian inverse UQ of the Takahashi and Fujitani (2016) rate-determining-step parameters
(model-form diagnostic; not propagated to plant cost; kinetics.yaml is not changed).

Deterministic (seed 20261123); run from the project root:  python scripts/research/uq_takahashi_calibration.py
Writes results/research/uq/takahashi_digitised_points.json, takahashi_calibration_{ni,ru}.json,
takahashi_posterior_{ni,ru}.csv, checks_t2b.json and results/figures/research/uq_takahashi_ppc.png.

theta = (ln s, dE, ln sigma_d). Forward model: the existing PFR (amcrax.reactor.pfr, 1 atm, isothermal, no pressure
drop, approach factor at its registry default) with the Takahashi law perturbed through param_overrides:
    k2, k3, k4 multiplied by s; RDS constant k_j(T) = s A_j exp(dE/(R T_ref)) exp(-(Ea_j + dE)/(R T)).
Numerical device (stated): the PFR is solved on a (ln s, dE) grid for every data point and interpolated with bicubic
splines in logit(X); the interpolation error is checked against direct PFR solves at posterior draws.
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy.interpolate import RectBivariateSpline

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from amcrax.kinetics import rate_laws  # noqa: E402
from amcrax.uq import LABEL, SEED  # noqa: E402
from amcrax.uq.kinetic_hook import simulate_with  # noqa: E402
from amcrax.uq.mcmc import adaptive_metropolis, ess_bulk, rhat  # noqa: E402

OUT = ROOT / "results" / "research" / "uq"
FIG = ROOT / "results" / "figures" / "research"
SCRIPT = "scripts/research/uq_takahashi_calibration.py"
ATM = 1.01325
R = rate_laws.R_KIN_J_molK
RHO_BED = 1000.0                       # kg/m3, assumption (spec T2b.2); absorbed by s
C0 = 101325.0 / (R * 273.15)           # mol/m3 at 0 degC, 1 atm (SV normal basis, assumption)
F_TOT_KMOL_H = 1.0                     # arbitrary: only W/F matters
SIGMA_R = 0.01                         # 2 pp / 1.96 (assumption: +/-2 pp is a 95 % bound)
N_ITER = int(os.environ.get("AMCRAX_UQ_T2B_ITER", "20000"))
N_ITER_SYN = int(os.environ.get("AMCRAX_UQ_T2B_ITER_SYN", "8000"))
BURN, ADAPT = 5000, 1000
LNS_STEP = float(os.environ.get("AMCRAX_UQ_T2B_LNS_STEP", "0.4"))
DE_STEP = float(os.environ.get("AMCRAX_UQ_T2B_DE_STEP", "8"))
LNS_GRID = np.arange(-6.0, 6.0001, LNS_STEP)
DE_GRID = np.arange(-96.0, 96.0001, DE_STEP)
NOTE = "research/notes/takahashi2016kinetic.md"
CAT = {
    "ni": {"id": "ni_takahashi_microkinetic", "rds": "2", "T_ref_K": 773.15, "Ea_rds": None},
    "ru": {"id": "ru_takahashi_microkinetic", "rds": "3", "T_ref_K": 723.15, "Ea_rds": None},
}


def P(fig, series, T, SV, X, y_nh3=1.0, y_h2=0.0, line=None, x=None, unit=None, role=None):
    return {"figure": fig, "series": series, "T_C": T, "SV_h_inv": SV, "y_NH3": y_nh3, "y_H2": y_h2,
            "y_Ar": round(1.0 - y_nh3 - y_h2, 6), "value": X, "x": x, "unit_x": unit, "unit_value": "fraction (H2 yield % / 100)",
            "source_type": "literature", "derived": "read from figure", "note_line": line, "role": role}


def digitised():
    ni = [P("3a", "T, 1 atm NH3, SV 15000", T, 15000, X, line=127, x=T, unit="degC", role="calibration") for T, X in ((550, .62), (600, .94), (650, .99))]
    ni += [P("3b", "p_NH3 at 500 degC, SV 15000", 500, 15000, X, y_nh3=p, line=128, x=p, unit="atm", role="held_out") for p, X in ((.25, .705), (.5, .47), (.75, .355), (1.0, .30))]
    tab = {550: [(2000, .96), (4000, .90), (7000, .82), (12000, .70), (20000, .58)],
           500: [(2000, .69), (4000, .55), (7000, .43), (12000, .34), (15000, .29)],
           450: [(2000, .32), (4000, .24), (7000, .19), (12000, .15), (15000, .12)]}
    for T, row in tab.items():
        ni += [P("3c", f"SV at {T} degC, 1 atm NH3", T, sv, X, line=133 + (550 - T) // 50, x=sv, unit="1/h",
                 role="calibration" if T == 500 else "held_out") for sv, X in row]
    ni += [P("5a", "p_H2 at 500 degC, 0.3 atm NH3, SV 15000", 500, 15000, X, y_nh3=0.3, y_h2=ph, line=137, x=ph, unit="atm", role="held_out")
           for ph, X in ((0, .61), (.1, .54), (.3, .37), (.5, .27), (.7, .23))]
    ni += [P("1a", "T, low-conversion fitting data, SV 15000", T, 15000, X, line=138, x=T, unit="degC", role="paper_fitting_data")
           for T, X in ((350, .01), (375, .025), (400, .04), (425, .075), (450, .12))]
    ru = [P("4a", "T, 1 atm NH3, SV 15000", 550, 15000, .995, line=141, x=550, unit="degC", role="calibration")]
    ru += [P("4b", "p_NH3 at 450 degC, SV 15000", 450, 15000, X, y_nh3=p, line=142, x=p, unit="atm", role="held_out") for p, X in ((.25, .925), (.5, .645), (.75, .50), (1.0, .425))]
    tab = {500: [(2000, 1.0), (7000, 1.0), (12000, .93), (15000, .855), (20000, .805)],
           450: [(2000, .92), (7000, .70), (12000, .50), (15000, .42), (20000, .36)],
           400: [(2000, .555), (4000, .415), (7000, .32), (12000, .25), (15000, .165)]}
    for T, row in tab.items():
        ru += [P("4c", f"SV at {T} degC, 1 atm NH3", T, sv, X, line=147 + (500 - T) // 50, x=sv, unit="1/h",
                 role="calibration" if T == 450 else "held_out") for sv, X in row]
    ru += [P("5b", "p_H2 at 450 degC, 0.3 atm NH3, SV 15000", 450, 15000, X, y_nh3=0.3, y_h2=ph, line=151, x=ph, unit="atm", role="held_out")
           for ph, X in ((0, .89), (.1, .81), (.3, .68), (.5, .59), (.7, .53))]
    ru += [P("2a", "T, low-conversion fitting data, SV 15000", T, 15000, X, line=152, x=T, unit="degC", role="paper_fitting_data")
           for T, X in ((300, .01), (325, .025), (350, .045), (375, .09), (400, .16))]
    for pts in (ni, ru):
        for p in pts:
            p["repeats_calibration_condition"] = (p["figure"] in ("3b", "4b") and p["y_NH3"] == 1.0)
    return {"ni": ni, "ru": ru}


def overrides(key, lns, dE, jc=None):
    """jc: index of the rate constant whose activation energy is shifted (default: the RDS of CAT)."""
    c = CAT[key]
    par = rate_laws._p(c["id"])
    s = math.exp(lns)
    ov = {"A2": s * par["A2"], "A3": s * par["A3"], "A4": s * par["A4"]}
    j = c["rds"] if jc is None else jc
    ov[f"A{j}"] = ov[f"A{j}"] * math.exp(dE * 1e3 / (R * c["T_ref_K"]))
    ov[f"Ea{j}"] = par[f"Ea{j}"] + dE
    return ov


def x_direct(key, lns, dE, p, ov=None, jc=None):
    sv = p["SV_h_inv"]
    W_over_F = RHO_BED / (sv / 3600.0 * C0)                    # kg s / mol (total flow)
    F = F_TOT_KMOL_H
    W = W_over_F * F * 1000.0 / 3600.0
    feed = {"NH3": F * p["y_NH3"], "H2": F * p["y_H2"], "Ar": F * p["y_Ar"]}
    feed = {k: v for k, v in feed.items() if v > 1e-12}
    o = overrides(key, lns, dE, jc) if ov is None else ov
    return float(simulate_with(CAT[key]["id"], o, W, T_in_C=float(p["T_C"]), P_in_bar=ATM, feed_kmol_h=feed,
                               mode="isothermal", pressure_drop=False, n_points=2).outlet["conversion"])


def _grid_task(args):
    key, i, j, pts, jc = args
    out = []
    for p in pts:
        try:
            out.append(x_direct(key, float(LNS_GRID[i]), float(DE_GRID[j]), p, jc=jc))
        except Exception:  # noqa: BLE001
            out.append(float("nan"))
    return i, j, out


def logit(x):
    x = np.clip(x, 1e-7, 1 - 1e-7)
    return np.log(x / (1 - x))


class Surrogate:
    def __init__(self, grid):  # grid: (n_lns, n_dE, n_pts)
        self.sp = [RectBivariateSpline(LNS_GRID, DE_GRID, logit(grid[:, :, k]), kx=3, ky=3) for k in range(grid.shape[2])]

    def __call__(self, lns, dE, idx):
        z = np.array([self.sp[k].ev(lns, dE) for k in idx], float)
        return 1.0 / (1.0 + np.exp(-z))


def in_grid(lns, dE):
    return LNS_GRID[0] <= lns <= LNS_GRID[-1] and DE_GRID[0] <= dE <= DE_GRID[-1]


def make_logp(sur, idx, y, dE_sd=20.0):
    y = np.asarray(y, float)

    def logp(th):
        lns, dE, lsd = th
        if not in_grid(lns, dE) or lsd < -12 or lsd > 1:
            return -np.inf
        sd = math.exp(lsd)
        var = SIGMA_R ** 2 + sd ** 2
        mu = sur(lns, dE, idx)
        ll = -0.5 * np.sum((y - mu) ** 2) / var - 0.5 * len(y) * math.log(2 * math.pi * var)
        lp = -0.5 * lns ** 2 / 4.0 - 0.5 * dE ** 2 / dE_sd ** 2 + (-0.5 * sd ** 2 / 0.05 ** 2 + lsd)
        return ll + lp
    return logp


def run_chains(logp, rng, n_iter, dE_sd=20.0):
    chains, acc = [], []
    for child in rng.spawn(4):
        while True:
            x0 = np.array([child.normal(0, 2.0) * 1.5, child.normal(0, dE_sd) * 1.5, math.log(abs(child.normal(0, 0.05)) + 1e-3)])
            x0[0] = np.clip(x0[0], LNS_GRID[0] + 0.1, LNS_GRID[-1] - 0.1)
            x0[1] = np.clip(x0[1], DE_GRID[0] + 1, DE_GRID[-1] - 1)
            if np.isfinite(logp(x0)):
                break
        r = adaptive_metropolis(logp, x0, n_iter, child, adapt_start=ADAPT, burn_in=min(BURN, n_iter // 2),
                                cov0=np.diag([0.05, 4.0, 0.1]))
        chains.append(r["chain"][min(BURN, n_iter // 2):])
        acc.append(r["accept_rate"])
    C = np.stack(chains)  # (4, n, 3)
    names = ["ln_s", "dE_kJ_mol", "ln_sigma_d"]
    diag = {n: {"rhat": rhat(C[:, :, k]), "ess_bulk": ess_bulk(C[:, :, k])} for k, n in enumerate(names)}
    return C, diag, acc


def summarise(C):
    flat = C.reshape(-1, C.shape[2])
    names = ["ln_s", "dE_kJ_mol", "ln_sigma_d"]
    out = {n: {"mean": float(flat[:, k].mean()), "sd": float(flat[:, k].std(ddof=1)), "p5": float(np.percentile(flat[:, k], 5)),
               "p50": float(np.percentile(flat[:, k], 50)), "p95": float(np.percentile(flat[:, k], 95))} for k, n in enumerate(names)}
    sd = np.exp(flat[:, 2])
    out["sigma_d"] = {"mean": float(sd.mean()), "p5": float(np.percentile(sd, 5)), "p50": float(np.percentile(sd, 50)), "p95": float(np.percentile(sd, 95))}
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    from amcrax.economics.reference import provenance_stamp
    pts_all = digitised()
    (OUT / "takahashi_digitised_points.json").write_text(json.dumps({
        "provenance": {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "script": SCRIPT,
                       "source_type": "literature", "inputs_summary": f"transcribed from {NOTE} lines 123-152 (figure readings, about +/-2 pp)"},
        "note": "Duplicates removed: the SV 15000 points of Fig. 3a (Ni, 500 degC) and Fig. 4a (Ru, 450 and 500 degC) repeat Fig. 3c/4c; "
                "the Fig. 3c/4c values are kept. Figs. 3b/4b at p_NH3 = 1 atm repeat the same condition as a calibration point "
                "(flag repeats_calibration_condition). Figs. 1a/2a are the paper's fitting data. All 1 atm. Catalyst mass and SV volume basis not reported.",
        "points": pts_all}, indent=1), encoding="utf-8")
    nproc = int(os.environ.get("AMCRAX_UQ_NPROC", max(1, (os.cpu_count() or 2) - 1)))
    rng_master = np.random.default_rng(SEED)
    checks, results = [], {}
    for key in ("ni", "ru"):
        pts = pts_all[key]
        cid = CAT[key]["id"]
        # ---- local screening at the calibration points (nominal, s = 1, dE = 0)
        cal = [i for i, p in enumerate(pts) if p["role"] == "calibration"]
        par = rate_laws._p(cid)
        screen = {}
        for name, pk in (("k1", "A1"), ("k2", "A2"), ("k3", "A3"), ("k4", "A4"), ("K1", "A5"), ("K4", "A6")):
            sens = []
            for i in cal:
                xp = x_direct(key, 0, 0, pts[i], ov={**overrides(key, 0, 0), pk: par[pk] * 1.05} if pk not in overrides(key, 0, 0) else
                              {**overrides(key, 0, 0), pk: overrides(key, 0, 0)[pk] * 1.05})
                xm = x_direct(key, 0, 0, pts[i], ov={**overrides(key, 0, 0), pk: par[pk] / 1.05} if pk not in overrides(key, 0, 0) else
                              {**overrides(key, 0, 0), pk: overrides(key, 0, 0)[pk] / 1.05})
                sens.append((xp - xm) / (2 * math.log(1.05)))
            screen[name] = {"mean_abs_dX_dlnk": float(np.mean(np.abs(sens))), "per_point": sens}
        most = max(screen, key=lambda k: screen[k]["mean_abs_dX_dlnk"])
        # the equilibrium constants K1, K4 are fixed by the specification; the choice is among the rate constants k1-k4
        most_rate = max(("k1", "k2", "k3", "k4"), key=lambda k: screen[k]["mean_abs_dX_dlnk"])
        rds_name = "k" + CAT[key]["rds"]
        jc = most_rate[1]

        def build(jc_):
            with Pool(nproc) as pool:
                tasks = [(key, i, j, pts, jc_) for i in range(len(LNS_GRID)) for j in range(len(DE_GRID))]
                g = np.full((len(LNS_GRID), len(DE_GRID), len(pts)), np.nan)
                for i, j, out in pool.imap_unordered(_grid_task, tasks, chunksize=4):
                    g[i, j] = out
            nn = int(np.isnan(g).sum())
            return Surrogate(np.where(np.isnan(g), 1e-7, g)), nn

        # ---- grid of direct PFR solves (calibrated constant = most sensitive rate constant)
        sur, n_nan = build(jc)
        y = np.array([p["value"] for p in pts])
        rds_alt = None
        if jc != CAT[key]["rds"]:
            sur_r, _ = build(CAT[key]["rds"])
            cal_ = [i for i, p in enumerate(pts) if p["role"] == "calibration"]
            Cr, dgr, _ = run_chains(make_logp(sur_r, cal_, y[cal_]), np.random.default_rng(SEED + 50), N_ITER)
            fr = Cr.reshape(-1, 3)[::20]
            ho_ = [i for i, p in enumerate(pts) if p["role"] == "held_out"]
            prr = np.random.default_rng(SEED)
            mu_r = np.array([sur_r(t[0], t[1], ho_) for t in fr])
            pr = mu_r + prr.standard_normal(mu_r.shape) * np.sqrt(SIGMA_R ** 2 + np.exp(fr[:, 2]) ** 2)[:, None]
            lo_r, hi_r = np.percentile(pr, 5, axis=0), np.percentile(pr, 95, axis=0)
            rds_alt = {"calibrated_constant": rds_name, "posterior": summarise(Cr), "diagnostics": dgr,
                       "held_out_coverage_90": {"n": len(ho_), "n_inside": int(sum(lo_r[k] <= y[i] <= hi_r[k] for k, i in enumerate(ho_)))}}
        ho = [i for i, p in enumerate(pts) if p["role"] == "held_out"]
        fit = [i for i, p in enumerate(pts) if p["role"] == "paper_fitting_data"]
        cal_noceil = [i for i in cal if y[i] <= 0.98]
        runs = {}
        rng = np.random.default_rng(SEED + (0 if key == "ni" else 1))
        for name, idx, dsd in (("main", cal, 20.0), ("without_ceiling_points", cal_noceil, 20.0), ("prior_dE_sd40", cal, 40.0)):
            C, diag, acc = run_chains(make_logp(sur, idx, y[idx], dsd), rng, N_ITER, dsd)
            runs[name] = {"C": C, "diag": diag, "acc": acc, "idx": idx}
        C = runs["main"]["C"]
        flat = C.reshape(-1, 3)
        thin = flat[:: max(1, flat.shape[0] // 2000)]
        # ---- posterior predictive (model + iid noise of variance sigma_r^2 + sigma_d^2)
        prng = np.random.default_rng(SEED)
        allidx = list(range(len(pts)))
        mu = np.array([sur(t[0], t[1], allidx) for t in thin])
        sdv = np.sqrt(SIGMA_R ** 2 + np.exp(thin[:, 2]) ** 2)
        pred = mu + prng.standard_normal(mu.shape) * sdv[:, None]
        lo, med, hi = np.percentile(pred, 5, axis=0), np.percentile(pred, 50, axis=0), np.percentile(pred, 95, axis=0)
        ppc = [{"figure": p["figure"], "series": p["series"], "T_C": p["T_C"], "SV_h_inv": p["SV_h_inv"], "y_NH3": p["y_NH3"], "y_H2": p["y_H2"],
                "role": p["role"], "observed": p["value"], "median": float(med[i]), "p5": float(lo[i]), "p95": float(hi[i]),
                "model_median_no_noise": float(np.median(mu[:, i])), "inside_90": bool(lo[i] <= p["value"] <= hi[i]),
                "residual_obs_minus_median": float(p["value"] - med[i]), "repeats_calibration_condition": p["repeats_calibration_condition"]}
               for i, p in enumerate(pts)]
        def cov(sel):
            s = [ppc[i]["inside_90"] for i in sel]
            return {"n": len(s), "n_inside": int(sum(s)), "fraction": float(np.mean(s)) if s else None}
        ho_norep = [i for i in ho if not pts[i]["repeats_calibration_condition"]]
        trends = {}
        for fig_s in sorted({ppc[i]["series"] for i in ho + fit}):
            r = [ppc[i]["residual_obs_minus_median"] for i in range(len(pts)) if ppc[i]["series"] == fig_s]
            trends[fig_s] = {"mean_residual": float(np.mean(r)), "all_same_sign": bool(all(v > 0 for v in r) or all(v < 0 for v in r)),
                             "n": len(r)}
        # ---- surrogate accuracy against direct solves
        vrng = np.random.default_rng(SEED)
        sel = flat[vrng.integers(0, flat.shape[0], 25)]
        errs = [abs(x_direct(key, float(t[0]), float(t[1]), pts[i], jc=jc) - float(sur(t[0], t[1], [i])[0])) for t in sel for i in allidx]
        sur_err = float(max(errs))
        checks.append({"id": f"T2B-SURROGATE-{key}", "evidence_kind": "numerical_verification",
                       "description": "bicubic logit(X) interpolation of the PFR grid against direct PFR solves at 25 posterior draws x all points",
                       "max_abs_error_X": sur_err, "tolerance": 0.002, "status": "pass" if sur_err <= 0.002 else "fail"})
        summ = summarise(C)
        d90 = (summ["dE_kJ_mol"]["p5"], summ["dE_kJ_mol"]["p95"])
        interp = ("published temperature dependence consistent with the paper's extrapolation data within reading error"
                  if d90[0] <= 0 <= d90[1] else f"activation-energy shift dE = {summ['dE_kJ_mol']['p50']:+.1f} kJ/mol "
                  f"(90 % interval {d90[0]:+.1f} to {d90[1]:+.1f}); sign {'positive' if d90[0] > 0 else 'negative'}")
        conv_ok = all(v["rhat"] < 1.01 and v["ess_bulk"] > 400 for v in runs["main"]["diag"].values())
        checks.append({"id": f"T2B-CONV-{key}", "evidence_kind": "numerical_verification",
                       "description": "rank-normalised split R-hat < 1.01 and bulk ESS > 400 for every parameter (main run)",
                       "diagnostics": runs["main"]["diag"], "status": "pass" if conv_ok else "fail"})
        # ---- synthetic recovery (20 sets) at the calibration design points
        th_star = np.array([0.5, 10.0, math.log(0.02)])
        mu_star = sur(th_star[0], th_star[1], cal)
        srng = np.random.default_rng(SEED)
        hit = {"ln_s": 0, "dE_kJ_mol": 0}
        syn_rows = []
        for k in range(20):
            ysyn = mu_star + srng.standard_normal(len(cal)) * math.sqrt(SIGMA_R ** 2 + 0.02 ** 2)
            Cs, dg, _ = run_chains(make_logp(sur, cal, ysyn), np.random.default_rng(SEED + 100 + k), N_ITER_SYN)
            fl = Cs.reshape(-1, 3)
            row = {}
            for j, n in enumerate(("ln_s", "dE_kJ_mol")):
                a, b = np.percentile(fl[:, j], [5, 95])
                inside = bool(a <= th_star[j] <= b)
                hit[n] += inside
                row[n] = [float(a), float(b), inside]
            row["max_rhat"] = max(v["rhat"] for v in dg.values())
            syn_rows.append(row)
        ok_syn = all(14 <= v <= 20 for v in hit.values())
        checks.append({"id": f"T2B-SYNTH-{key}", "evidence_kind": "numerical_verification",
                       "description": "synthetic recovery at theta* = (ln s 0.5, dE +10 kJ/mol, sigma_d 0.02), 20 data sets: 90 % interval coverage between 14 and 20",
                       "coverage": hit, "iterations_per_chain": N_ITER_SYN, "status": "pass" if ok_syn else "fail"})
        sens = {n: runs["prior_dE_sd40"]["C"].reshape(-1, 3)[:, j].mean() - flat[:, j].mean() for j, n in enumerate(("ln_s", "dE_kJ_mol", "ln_sigma_d"))}
        res = {
            "provenance": {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "script": SCRIPT, "source_type": "python",
                           "inputs_summary": "takahashi_digitised_points.json; amcrax.reactor.pfr with the Takahashi law (kinetics.yaml Table 1) through param_overrides",
                           "reference_scenario": provenance_stamp(), "seed": SEED},
            "evidence_kind": "numerical_verification", "analysis_kind": "bayesian_calibration_diagnostic", "label": LABEL,
            "label_t2b": "calibration to digitised published figures (about +/-2 percentage points reading error); 1 atm only; not independent experimental validation of AmCraX",
            "catalyst_id": cid, "rds_constant": rds_name, "calibrated_constant": most_rate, "T_ref_K": CAT[key]["T_ref_K"],
            "screening": {"dX_dlnk_at_calibration_points": screen, "most_sensitive_overall": most,
                          "most_sensitive_rate_constant": most_rate, "rds_is_most_sensitive_rate_constant": most_rate == rds_name,
                          "note": "K1 and K4 (equilibrium constants) are fixed at Table 1 by the specification; K1 has the same sensitivity as k2 "
                                  "because the rate depends on their product at these conditions; K4 (H2 adsorption) is the most sensitive "
                                  "quantity overall but is not calibrated.",
                          "decision": "calibrate the activation-energy shift of the RDS as specified" if most_rate == rds_name else
                                      f"RDS {rds_name} is not the most sensitive rate constant on the data; the shift is calibrated on {most_rate} "
                                      f"(rule of the specification); the RDS-shift calibration is reported under rds_shift_as_specified"},
            "rds_shift_as_specified": rds_alt,
            "priors": {"ln_s": "N(0, 2^2)", "dE_kJ_mol": "N(0, 20^2)", "sigma_d": "half-normal(0.05)", "sigma_r": SIGMA_R,
                       "truncation": f"ln s in [{LNS_GRID[0]}, {LNS_GRID[-1]}], dE in [{DE_GRID[0]}, {DE_GRID[-1]}] kJ/mol (grid domain)"},
            "assumptions": ["W/F_total = rho_bed / (SV c0), rho_bed 1000 kg/m3, SV on total flow at 0 degC 1 atm (assumption; absorbed by s)",
                            "H2 yield taken as NH3 conversion; equilibrium approach factor ON (AmCraX extension, registry default)",
                            "iid Gaussian discrepancy (Kennedy-O'Hagan term reduced to iid because the series are short)",
                            "forward model tabulated on the grid and interpolated (checked, see T2B-SURROGATE)"],
            "n_points": {"calibration": len(cal), "held_out": len(ho), "paper_fitting_data": len(fit)},
            "mcmc": {"algorithm": "adaptive Metropolis (Haario et al. 2001)", "chains": 4, "iterations": N_ITER, "burn_in": BURN, "adapt_from": ADAPT,
                     "acceptance_rate": runs["main"]["acc"], "diagnostics": runs["main"]["diag"]},
            "posterior": summ,
            "posterior_without_ceiling_points": {"posterior": summarise(runs["without_ceiling_points"]["C"]),
                                                 "n_calibration": len(cal_noceil), "diagnostics": runs["without_ceiling_points"]["diag"]},
            "prior_sensitivity_dE_sd40": {"posterior": summarise(runs["prior_dE_sd40"]["C"]), "change_in_posterior_mean": sens,
                                          "diagnostics": runs["prior_dE_sd40"]["diag"]},
            "interpretation": interp,
            "posterior_predictive": ppc,
            "coverage_90": {"calibration": cov(cal), "held_out": cov(ho), "held_out_excluding_repeated_condition": cov(ho_norep),
                            "paper_fitting_data_reported_separately": cov(fit)},
            "residual_trends_by_series": trends,
            "synthetic_recovery": {"theta_star": {"ln_s": 0.5, "dE_kJ_mol": 10.0, "sigma_d": 0.02}, "coverage": hit, "sets": syn_rows},
            "grid": {"ln_s": [LNS_GRID[0], LNS_GRID[-1], LNS_STEP], "dE": [DE_GRID[0], DE_GRID[-1], DE_STEP], "n_failed_solves": n_nan,
                     "surrogate_max_abs_error": sur_err},
            "no_change": "kinetics.yaml is not changed (no tuning); not propagated to plant catalyst mass or LCOH",
        }
        results[key] = res
        (OUT / f"takahashi_calibration_{key}.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
        with open(OUT / f"takahashi_posterior_{key}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["ln_s", "dE_kJ_mol", "ln_sigma_d"])
            w.writerows(thin.tolist())
        checks.append({"id": f"T2B-PPC-{key}", "evidence_kind": "literature_comparison",
                       "description": "coverage of the 90 % posterior predictive interval (informational; no pass threshold on real data)",
                       "coverage": res["coverage_90"], "status": "informational"})
        checks.append({"id": f"T2B-PRIOR-{key}", "evidence_kind": "numerical_verification",
                       "description": "prior sensitivity: dE prior sd 40 kJ/mol, change in posterior mean (informational)",
                       "change": sens, "status": "informational"})
        print("done", key, interp, res["coverage_90"], flush=True)
    (OUT / "checks_t2b.json").write_text(json.dumps(checks, indent=1, default=float), encoding="utf-8")
    # ---- figure
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.5))
    for ax, key in zip(axs, ("ni", "ru")):
        ppc = results[key]["posterior_predictive"]
        for role, mk, col in (("calibration", "o", "#2a6f97"), ("held_out", "s", "#e07a5f"), ("paper_fitting_data", "^", "#777777")):
            r = [q for q in ppc if q["role"] == role]
            ax.errorbar([q["observed"] for q in r], [q["median"] for q in r],
                        yerr=[[q["median"] - q["p5"] for q in r], [q["p95"] - q["median"] for q in r]], fmt=mk, color=col, ms=4, capsize=2,
                        label=role.replace("_", " "), lw=0.8)
        ax.plot([0, 1], [0, 1], "k--", lw=0.8)
        ax.set_title(f"{key.upper()} (Takahashi and Fujitani 2016), 90 % predictive bands", fontsize=9)
        ax.set_xlabel("Observed conversion (read from figure)")
        ax.set_ylabel("Posterior predictive")
        ax.legend(fontsize=7)
    fig.text(0.01, 0.005, "Source: python (amcrax PFR) calibrated to digitised published figures (+/-2 pp); 1 atm only; model-form diagnostic, "
             "not independent experimental validation.", fontsize=6.5, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIG / "uq_takahashi_ppc.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()

