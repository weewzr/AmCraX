"""Heat-integration (pinch) analysis of one AmCraX SimulationResult."""
from __future__ import annotations

import math

import numpy as np

from ..schemas import MOLAR_MASS, DataSource, SimulationResult
from .models import (ConfigurationRow, ConsistencyCheck, FEHEAssessment, HeatIntegrationResult, HIStream,
                     PinchTargets, ProblemTableRow)
from .pinch import Curve, PinchResult, problem_table
from .streams import ASSUMPTIONS, extract_streams

C0 = 273.15

#: ASSUMPTION - overall heat-transfer coefficient of the FEHE (gas-gas, both sides ~20 bar).
#: Gas-to-gas shell-and-tube exchangers are commonly quoted in the order of 10-100 W/(m2 K)
#: (low-pressure to moderate-pressure gases); 50 W/(m2 K) is taken as a central value. This
#: is an engineering assumption for an order-of-magnitude area only - no specific textbook
#: page was verified for it. Area is reported over the whole range.
U_ASSUMED_W_M2K = 50.0
U_RANGE_W_M2K = (10.0, 100.0)
U_NOTE = ("ASSUMPTION: overall U for a gas-gas exchanger, central 50 W/(m2 K), range 10-100 W/(m2 K) "
          "(typical order of magnitude for gas-gas service; not taken from a verified textbook table). "
          "Area = UA/U is an order-of-magnitude sizing estimate, not a design.")


def _targets(label: str, curves: list[Curve], dT: float) -> tuple[PinchTargets, PinchResult]:
    r = problem_table(curves, dT)
    rows = [ProblemTableRow(T_shifted_hi_C=float(hi - C0), T_shifted_lo_C=float(lo - C0), deficit_kW=float(d),
                            cascade_out_kW=float(c))
            for hi, lo, d, c in zip(r.boundaries_shifted_K[:-1], r.boundaries_shifted_K[1:],
                                    r.interval_deficit_kW, r.cascade_kW[1:])]
    c = lambda x: None if x is None else float(x - C0)  # noqa: E731
    t = PinchTargets(
        label=label, dT_min_K=dT, hot_utility_kW=r.hot_utility_kW, cold_utility_kW=r.cold_utility_kW,
        total_hot_streams_kW=r.total_hot_kW, total_cold_streams_kW=r.total_cold_kW,
        heat_recovery_kW=r.total_cold_kW - r.hot_utility_kW,
        pinch_shifted_C=c(r.pinch_shifted_K), pinch_hot_C=c(r.pinch_hot_K), pinch_cold_C=c(r.pinch_cold_K),
        threshold_problem=r.threshold,
        energy_balance_residual_kW=(r.hot_utility_kW - r.cold_utility_kW) - (r.total_cold_kW - r.total_hot_kW),
        hot_composite_H_kW=r.hot_composite[0].tolist(), hot_composite_T_C=(r.hot_composite[1] - C0).tolist(),
        cold_composite_H_kW=r.cold_composite[0].tolist(), cold_composite_T_C=(r.cold_composite[1] - C0).tolist(),
        gcc_H_kW=r.cascade_kW.tolist(), gcc_T_shifted_C=(r.boundaries_shifted_K - C0).tolist(), problem_table=rows,
    )
    return t, r


def _hi_stream(c: Curve, included: list[str]) -> HIStream:
    hot = c.kind == "hot"
    return HIStream(id=c.id, name=c.name, kind=c.kind,
                    supply_temperature_C=(c.T_max_K if hot else c.T_min_K) - C0,
                    target_temperature_C=(c.T_min_K if hot else c.T_max_K) - C0,
                    duty_kW=c.duty_kW, included_in=included,
                    curve_T_C=(c.T_K - C0).tolist(), curve_H_kW=c.H_kW.tolist())


def _lmtd(d1: float, d2: float) -> float | None:
    if d1 <= 0 or d2 <= 0:
        return None
    return d1 if abs(d1 - d2) < 1e-9 else (d1 - d2) / math.log(d1 / d2)


def _block_duty(res: SimulationResult, bid: str) -> float | None:
    b = res.blocks.get(bid)
    return None if b is None or b.duty_kW is None else float(b.duty_kW)


def _fehe(res: SimulationResult, feed: Curve, cracked: Curve, dT: float) -> FEHEAssessment:
    st = res.streams
    T = lambda sid: st[sid].temperature_C + C0 if sid in st and st[sid].temperature_C is not None else None  # noqa: E731
    T2, T5 = T("S2"), T("S5")
    if T2 is None:
        T2 = feed.meta.get("T_switch_K") or feed.T_min_K
    present = bool(res.inputs.heat_integration and T("S3") is not None and T("S6") is not None)
    if present:
        T3, T6 = T("S3"), T("S6")
        q_sim = _block_duty(res, "FEHE")
        Q = abs(q_sim) if q_sim is not None else feed.H_at(T3) - feed.H_at(T2)
        src = "FEHE block duty (simulation result)" if q_sim is not None else "model cold-side enthalpy change S2->S3"
    else:
        T3 = T5 - res.inputs.fehe_hot_end_approach_K
        Q = feed.H_at(T3) - feed.H_at(T2)
        T6 = cracked.T_at(cracked.H_at(T5) - Q)
        src = ("MODEL ESTIMATE (FEHE absent in simulation): cold outlet = S5 T - fehe_hot_end_approach_K, "
               "duty from model H-T curves")
    q = np.linspace(0.0, Q, 201)
    Hh5, Hc3 = cracked.H_at(T5), feed.H_at(T3)
    Th = np.array([cracked.T_at(Hh5 - x) for x in q])
    Tc = np.array([feed.T_at(Hc3 - x) for x in q])
    dTs = Th - Tc
    lm = _lmtd(T5 - T3, T6 - T2)
    ua_seg = None
    if np.all(dTs > 0):
        ua_seg = float(sum((q[i + 1] - q[i]) / _lmtd(dTs[i], dTs[i + 1]) for i in range(len(q) - 1)))
    ua_lm = Q / lm if lm else None
    ua_for_area = ua_seg if ua_seg is not None else ua_lm
    area = None if ua_for_area is None else ua_for_area * 1000.0 / U_ASSUMED_W_M2K
    area_rng = [] if ua_for_area is None else [ua_for_area * 1000.0 / U_RANGE_W_M2K[1],
                                               ua_for_area * 1000.0 / U_RANGE_W_M2K[0]]
    return FEHEAssessment(
        present_in_simulation=present, duty_kW=float(Q), duty_source=src,
        hot_in_C=T5 - C0, hot_out_C=T6 - C0, cold_in_C=T2 - C0, cold_out_C=T3 - C0,
        hot_end_approach_K=T5 - T3, cold_end_approach_K=T6 - T2,
        min_internal_approach_K=float(dTs.min()), temperature_cross=bool(dTs.min() < 0),
        approach_violation=bool(dTs.min() < dT), lmtd_K=lm, ua_lmtd_kW_K=ua_lm, ua_segmented_kW_K=ua_seg,
        U_assumed_W_m2K=U_ASSUMED_W_M2K, U_range_W_m2K=list(U_RANGE_W_M2K), area_m2=area, area_range_m2=area_rng,
        U_note=U_NOTE, hot_side_duty_model_kW=cracked.H_at(T5) - cracked.H_at(T6),
        cold_side_duty_model_kW=feed.H_at(T3) - feed.H_at(T2),
        profile_duty_kW=q[::10].tolist(), profile_hot_T_C=(Th[::10] - C0).tolist(),
        profile_cold_T_C=(Tc[::10] - C0).tolist(),
    )


def _h2_kg_h(res: SimulationResult) -> float | None:
    if res.kpis.h2_product_kg_h:
        return float(res.kpis.h2_product_kg_h)
    s = res.streams.get("H2PROD")
    if s is not None and s.component_mole_flow_kmol_h.get("H2"):
        return s.component_mole_flow_kmol_h["H2"] * MOLAR_MASS["H2"]
    return None


def analyse(result: SimulationResult, dT_min_K: float = 20.0) -> HeatIntegrationResult:
    """Pinch / heat-recovery analysis. Works for Aspen (source aspen_plus_v15) or Python results."""
    if dT_min_K <= 0:
        raise ValueError("dT_min_K must be > 0")
    x = extract_streams(result)
    feed, rxn, cracked, flue = x["feed"], x["reaction"], x["cracked"], x["flue"]
    feed.meta.update(x["feed_meta"])
    warnings = list(x["warnings"])
    notes: list[str] = []
    h2 = _h2_kg_h(result)
    if not result.status.converged:
        warnings.append("Input simulation is not marked converged: heat-integration numbers inherit that status.")

    process = [feed, rxn, cracked]
    tp, rp = _targets("Process streams only", process, dT_min_K)
    tf = rf = None
    if flue is not None:
        tf, rf = _targets("Process streams + tail-gas flue gas", process + [flue], dT_min_K)

    fe = _fehe(result, feed, cracked, dT_min_K)
    if fe.temperature_cross:
        warnings.append(f"FEHE temperature cross: minimum internal approach {fe.min_internal_approach_K:.1f} K < 0.")
    elif fe.approach_violation:
        warnings.append(f"FEHE minimum internal approach {fe.min_internal_approach_K:.1f} K is below dT_min = {dT_min_K} K.")

    total_cold = feed.duty_kW + rxn.duty_kW
    total_hot = cracked.duty_kW
    spec = lambda q: None if not h2 else q / h2  # noqa: E731  (kW / (kg/h) = kWh/kg)
    red = lambda q: 0.0 if total_cold <= 0 else 1.0 - q / total_cold  # noqa: E731
    rows = [ConfigurationRow(id="a", label="(a) No heat recovery", external_heating_kW=total_cold,
                             external_cooling_kW=total_hot, process_heat_recovered_kW=0.0,
                             reduction_vs_no_recovery=0.0, specific_heat_demand_kWh_per_kgH2=spec(total_cold),
                             basis="Model H-T curves: all cold duties (S1->S4 + reaction) external; all cracked-gas heat to cooling.")]
    Qf = fe.duty_kW
    heat_b = total_cold - Qf
    rows.append(ConfigurationRow(id="b", label="(b) Feed/effluent exchanger only", external_heating_kW=heat_b,
                                 external_cooling_kW=total_hot - Qf, process_heat_recovered_kW=Qf,
                                 reduction_vs_no_recovery=red(heat_b), specific_heat_demand_kWh_per_kgH2=spec(heat_b),
                                 basis=f"FEHE duty: {fe.duty_source}; remaining duties from model H-T curves."))
    if flue is not None:
        T1, T2, T3, T4 = feed.T_min_K, fe.cold_in_C + C0, fe.cold_out_C + C0, feed.T_max_K
        resid = [rxn]
        if T2 > T1 + 1e-6:
            resid.append(feed.slice(T1, T2, id="VAPORISER_DUTY"))
        if T4 > T3 + 1e-6:
            resid.append(feed.slice(T3, T4, id="TRIM_HEATER_DUTY"))
        rc = problem_table(resid + [flue], dT_min_K)
        resid_total = sum(c.duty_kW for c in resid)
        used = resid_total - rc.hot_utility_kW
        rows.append(ConfigurationRow(
            id="c", label="(c) FEHE + tail-gas firing", external_heating_kW=rc.hot_utility_kW,
            external_cooling_kW=total_hot - Qf, process_heat_recovered_kW=Qf, tailgas_heat_used_kW=used,
            reduction_vs_no_recovery=red(rc.hot_utility_kW), specific_heat_demand_kWh_per_kgH2=spec(rc.hot_utility_kW),
            basis=("Residual duties after FEHE (vaporiser S1->S2, trim heater S3->S4, isothermal reaction) "
                   f"vs flue gas {flue.T_max_K - C0:.0f}->{flue.T_min_K - C0:.0f} degC by problem table at dT_min: "
                   "flue heat below T_reactor + dT_min cannot supply the reaction heat. "
                   f"Unused flue heat {flue.duty_kW - used:.1f} kW (leaves via stack/flue cooler).")))
    rows.append(ConfigurationRow(
        id="d1", label=f"(d) Pinch target, process only (dT_min {dT_min_K:g} K)", external_heating_kW=tp.hot_utility_kW,
        external_cooling_kW=tp.cold_utility_kW, process_heat_recovered_kW=tp.heat_recovery_kW,
        reduction_vs_no_recovery=red(tp.hot_utility_kW), specific_heat_demand_kWh_per_kgH2=spec(tp.hot_utility_kW),
        basis="Problem-table target (minimum utilities), process streams only."))
    if tf is not None:
        flue_used = tp.hot_utility_kW - tf.hot_utility_kW
        rows.append(ConfigurationRow(
            id="d2", label=f"(d) Pinch target incl. tail-gas flue gas (dT_min {dT_min_K:g} K)",
            external_heating_kW=tf.hot_utility_kW, external_cooling_kW=tp.cold_utility_kW,
            process_heat_recovered_kW=tp.heat_recovery_kW, tailgas_heat_used_kW=flue_used,
            reduction_vs_no_recovery=red(tf.hot_utility_kW), specific_heat_demand_kWh_per_kgH2=spec(tf.hot_utility_kW),
            basis=("Problem-table target with flue gas as a hot stream. Process cooling = process-only target; "
                   f"unused flue heat {tf.cold_utility_kW - tp.cold_utility_kW:.1f} kW.")))
        if tf.hot_utility_kW > 1e-6:
            notes.append(f"Even at the pinch target with tail-gas firing, {tf.hot_utility_kW:.1f} kW must be imported "
                         "(e.g. by burning extra NH3 or H2, or electric heating).")
        else:
            notes.append("At the pinch target the tail-gas flue gas covers all heating: no external heat import needed.")

    # consistency of model curves vs simulated block duties (reported, never tuned)
    checks: list[ConsistencyCheck] = []

    def chk(item: str, model: float, sim: float | None):
        rel = None if sim in (None, 0) else (model - sim) / abs(sim)
        checks.append(ConsistencyCheck(item=item, model_kW=model, simulated_kW=sim, rel_deviation=rel))

    bd = {b: _block_duty(result, b) for b in ("VAPORIZR", "HEATER", "FEHE", "COOLER", "FLUEHX", "CRACKER")}
    sim_feed = None
    if bd["VAPORIZR"] is not None and bd["HEATER"] is not None:
        sim_feed = bd["VAPORIZR"] + bd["HEATER"] + (abs(bd["FEHE"]) if fe.present_in_simulation and bd["FEHE"] else 0.0)
    chk("Feed heating S1->S4 (VAPORIZR+FEHE cold+HEATER)", feed.duty_kW, sim_feed)
    if "S2" in result.streams and result.streams["S2"].temperature_C is not None:
        chk("Vaporiser S1->S2", feed.H_at(result.streams["S2"].temperature_C + C0) - feed.H_at(feed.T_min_K), bd["VAPORIZR"])
    sim_hot = None
    if bd["COOLER"] is not None:
        sim_hot = abs(bd["COOLER"]) + (abs(bd["FEHE"]) if fe.present_in_simulation and bd["FEHE"] else 0.0)
    chk("Cracked gas S5->S7 (FEHE hot+COOLER)", cracked.duty_kW, sim_hot)
    if flue is not None:
        chk("Flue gas FLUE->STACK (FLUEHX)", flue.duty_kW, None if bd["FLUEHX"] is None else abs(bd["FLUEHX"]))
    for c in checks:
        if c.rel_deviation is not None and abs(c.rel_deviation) > 0.03:
            warnings.append(f"Model vs simulated duty differ by {100 * c.rel_deviation:.1f} % for '{c.item}' "
                            "(different property methods/reference; reported, not adjusted).")

    streams = [_hi_stream(feed, ["process", "with_flue"]), _hi_stream(rxn, ["process", "with_flue"]),
               _hi_stream(cracked, ["process", "with_flue"])]
    if flue is not None:
        streams.append(_hi_stream(flue, ["with_flue"]))
    notes.append("Targets are thermodynamic minima (problem table); they are not an exchanger network design.")
    return HeatIntegrationResult(
        case_id=result.case_id, input_source=result.source, dT_min_K=dT_min_K,
        reactor_temperature_C=x["T_reactor_K"] - C0, h2_product_kg_h=h2, reaction_duty_source=x["reaction_source"],
        feed_saturation_temperature_C=x["feed_meta"]["T_sat_K"] - C0, feed_latent_heat_kW=x["feed_meta"]["latent_heat_kW"],
        streams=streams, targets_process=tp, targets_with_flue=tf, configurations=rows, fehe=fe, consistency=checks,
        assumptions=list(ASSUMPTIONS) + [U_NOTE], warnings=warnings, notes=notes,
    )
