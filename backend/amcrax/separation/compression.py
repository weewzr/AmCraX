"""Multi-stage intercooled compression of cracked gas (ideal gas, reduced-order model).

Per stage (equal pressure ratio r = (P_out/P_in)**(1/stages), suction always at T_in):
    isentropic outlet T2s from  integral_{T_in}^{T2s} cp(T)/T dT = R ln r     (ideal gas, cp(T) NASA-7)
    W_stage = n * [h(T2s) - h(T_in)] / eta_s
Intercooling back to T_in between stages is ideal (assumption, see data/separation.yaml).
If ``cp_J_molK`` is given, a constant cp is used (closed form, used for hand-calculation checks).
"""
from __future__ import annotations

import math

from scipy.optimize import brentq

from amcrax.thermodynamics import R_J_molK, species_cp_J_molK, species_enthalpy_kJ_mol

from .params import params


def _mix_cp(y: dict[str, float], T_K: float) -> float:
    return sum(v * species_cp_J_molK(s, T_K) for s, v in y.items() if v > 0)


def _mix_h_J(y: dict[str, float], T_K: float) -> float:
    return 1000.0 * sum(v * species_enthalpy_kJ_mol(s, T_K) for s, v in y.items() if v > 0)


def _mix_s_int(y: dict[str, float], T1: float, T2: float, n: int = 40) -> float:
    """integral cp/T dT (Simpson)."""
    if n % 2:
        n += 1
    h = (T2 - T1) / n
    tot = 0.0
    for i in range(n + 1):
        T = T1 + i * h
        w = 1 if i in (0, n) else (4 if i % 2 else 2)
        tot += w * _mix_cp(y, T) / T
    return tot * h / 3.0


def default_stages(P_in_bar: float, P_out_bar: float) -> int:
    """Smallest stage count with ratio <= max per stage (cho2026nickel p. 5, Table 2: 3.5)."""
    rmax = params()["compression"]["max_pressure_ratio_per_stage"]["value"]
    if P_out_bar <= P_in_bar:
        return 0
    return max(1, math.ceil(math.log(P_out_bar / P_in_bar) / math.log(rmax) - 1e-12))


def compression_power_kW(n_kmol_h: float, composition: dict[str, float], T_in_K: float, P_in_bar: float,
                         P_out_bar: float, stages: int | None = None, eta: float | None = None,
                         *, cp_J_molK: float | None = None) -> dict:
    """Shaft power of an intercooled multi-stage compressor, kW (>= 0). Reduced-order model.

    Returns dict with power_kW, stages, pressure_ratio_per_stage, T_out_stage_K (actual discharge),
    intercooler_duty_kW (heat removed, negative = removed from the process), eta, notes.
    """
    if eta is None:
        eta = params()["compression"]["isentropic_efficiency"]["default"]
    if not 0 < eta <= 1:
        raise ValueError("eta must be in (0, 1]")
    if P_out_bar <= P_in_bar or n_kmol_h <= 0:
        return {"power_kW": 0.0, "stages": 0, "pressure_ratio_per_stage": 1.0, "T_out_stage_K": T_in_K,
                "intercooler_duty_kW": 0.0, "eta": eta, "notes": ["no compression required"]}
    if stages is None:
        stages = default_stages(P_in_bar, P_out_bar)
    if stages < 1:
        raise ValueError("stages must be >= 1")
    tot = sum(composition.values())
    y = {s: v / tot for s, v in composition.items() if v > 0}
    r = (P_out_bar / P_in_bar) ** (1.0 / stages)
    n_mol_s = n_kmol_h / 3.6
    if cp_J_molK is not None:
        T2s = T_in_K * r ** (R_J_molK / cp_J_molK)
        dh_s = cp_J_molK * (T2s - T_in_K)
        dh = dh_s / eta
        T2 = T_in_K + dh / cp_J_molK
    else:
        target = R_J_molK * math.log(r)
        T2s = brentq(lambda T: _mix_s_int(y, T_in_K, T) - target, T_in_K, T_in_K * r ** 0.7 + 50.0)
        dh_s = _mix_h_J(y, T2s) - _mix_h_J(y, T_in_K)
        dh = dh_s / eta
        h_target = _mix_h_J(y, T_in_K) + dh
        T2 = brentq(lambda T: _mix_h_J(y, T) - h_target, T_in_K, T_in_K + 3 * dh / _mix_cp(y, T_in_K) + 50)
    W_kW = stages * n_mol_s * dh / 1000.0
    # heat removed by the (stages-1) intercoolers plus the aftercooler back to T_in
    q_kW = -W_kW
    return {"power_kW": W_kW, "stages": stages, "pressure_ratio_per_stage": r, "T_out_stage_K": T2,
            "intercooler_duty_kW": q_kW, "eta": eta,
            "notes": ["reduced-order model: ideal gas, equal stage ratios, ideal intercooling to T_in"]}
