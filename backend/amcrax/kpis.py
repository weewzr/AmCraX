"""KPI and balance definitions shared by every result source.

The functions operate only on :class:`StreamResult` / :class:`BlockResult` objects, so the same
definitions are applied to Aspen Plus results and to the independent Python process model.

Definitions
-----------
nh3_conversion            X = 1 - n_NH3(S5) / n_NH3(S4)
h2_yield_overall          n_H2(H2PROD) / (1.5 * n_NH3(FEED))
total_external_heating    Q(VAPORIZR) + Q(HEATER) + Q(CRACKER)        [kW]
                          (+ Q(FLUEHX) in the unusual case that the flue gas must be heated)
tailgas_combustion_heat   max(-Q(FLUEHX), 0): heat released cooling the burner flue gas to stack T
net_fuel_heat_deficit     total_external_heating - tailgas_combustion_heat (first-law credit only;
                          temperature-level feasibility is assessed in amcrax.heat_integration)
lhv_efficiency            LHV(H2 product) / (LHV(NH3 feed) + max(deficit, 0) + pump power)
"""
from __future__ import annotations

from typing import Mapping, Optional

from amcrax.schemas import LHV_KJ_PER_MOL, MOLAR_MASS, Balances, BlockResult, KPIs, StreamResult

_KJ_PER_MOL_KMOL_H_TO_KW = 1000.0 / 3600.0  # (kJ/mol)*(kmol/h) -> kW

#: atoms per molecule
N_ATOMS = {"NH3": 1, "N2": 2}
H_ATOMS = {"NH3": 3, "H2": 2, "H2O": 2}

FEED_STREAMS = ("FEED", "AIR")
PRODUCT_STREAMS = ("H2PROD", "STACK")


def _n(streams: Mapping[str, StreamResult], sid: str, comp: str) -> Optional[float]:
    st = streams.get(sid)
    if st is None:
        return None
    return st.component_mole_flow_kmol_h.get(comp, 0.0)


def _duty(blocks: Mapping[str, BlockResult], bid: str) -> Optional[float]:
    b = blocks.get(bid)
    return None if b is None else b.duty_kW


def lhv_kW(stream: StreamResult) -> float:
    """Lower heating value flow of a stream (H2 and NH3 are the only combustibles), kW."""
    return sum(
        stream.component_mole_flow_kmol_h.get(c, 0.0) * LHV_KJ_PER_MOL[c] * _KJ_PER_MOL_KMOL_H_TO_KW
        for c in LHV_KJ_PER_MOL
    )


def compute_kpis(streams: Mapping[str, StreamResult], blocks: Mapping[str, BlockResult]) -> KPIs:
    k = KPIs()
    nh3_in, nh3_out = _n(streams, "S4", "NH3"), _n(streams, "S5", "NH3")
    if nh3_in and nh3_out is not None:
        k.nh3_conversion = 1.0 - nh3_out / nh3_in
    k.h2_in_cracked_gas_kmol_h = _n(streams, "S5", "H2")

    prod = streams.get("H2PROD")
    if prod is not None:
        h2p = prod.component_mole_flow_kmol_h.get("H2", 0.0)
        k.h2_product_kmol_h = h2p
        k.h2_product_kg_h = h2p * MOLAR_MASS["H2"]
        k.h2_purity_mole_frac = prod.mole_frac.get("H2")
        nh3_feed = _n(streams, "FEED", "NH3")
        if nh3_feed:
            k.h2_yield_overall = h2p / (1.5 * nh3_feed)

    k.reactor_duty_kW = _duty(blocks, "CRACKER")
    k.preheat_duty_kW = _duty(blocks, "HEATER")
    k.vaporiser_duty_kW = _duty(blocks, "VAPORIZR")
    k.recovered_heat_kW = _duty(blocks, "FEHE") if "FEHE" in blocks else 0.0
    parts = (k.reactor_duty_kW, k.preheat_duty_kW, k.vaporiser_duty_kW)
    if all(p is not None for p in parts):
        k.total_external_heating_kW = float(sum(parts))  # type: ignore[arg-type]
    q_cool = _duty(blocks, "COOLER")
    if q_cool is not None:
        k.cooling_duty_kW = abs(q_cool)
    pump = blocks.get("PUMP")
    if pump is not None:
        k.pump_power_kW = pump.power_kW
    q_flue = _duty(blocks, "FLUEHX")
    if q_flue is not None:
        # Heat released while the flue gas is COOLED to stack temperature (duty < 0). If the flue gas
        # had to be heated instead (flame temperature below stack temperature: almost no fuel in the
        # tail gas), there is no combustion credit and the positive duty is an additional heat demand.
        k.tailgas_combustion_heat_kW = max(-q_flue, 0.0)
        if q_flue > 0 and k.total_external_heating_kW is not None:
            k.total_external_heating_kW += q_flue
    tail = streams.get("TAILGAS")
    if tail is not None:
        k.tailgas_lhv_kW = lhv_kW(tail)

    if k.total_external_heating_kW is not None and k.h2_product_kg_h:
        k.specific_heat_demand_kWh_per_kgH2 = k.total_external_heating_kW / k.h2_product_kg_h
    if k.total_external_heating_kW is not None and k.tailgas_combustion_heat_kW is not None:
        k.net_fuel_heat_deficit_kW = k.total_external_heating_kW - k.tailgas_combustion_heat_kW

    feed = streams.get("FEED")
    if feed is not None and prod is not None and k.net_fuel_heat_deficit_kW is not None:
        lhv_in = lhv_kW(feed)
        denom = lhv_in + max(k.net_fuel_heat_deficit_kW, 0.0) + (k.pump_power_kW or 0.0)
        if denom > 0:
            k.lhv_efficiency = lhv_kW(prod) / denom
    return k


def _atoms(stream: StreamResult, table: Mapping[str, int]) -> float:
    return sum(stream.component_mole_flow_kmol_h.get(c, 0.0) * n for c, n in table.items())


def compute_balances(streams: Mapping[str, StreamResult], blocks: Mapping[str, BlockResult]) -> Balances:
    """Overall plant balances over the boundary {FEED, AIR} -> {H2PROD, STACK}."""
    b = Balances()
    feeds = [streams[s] for s in FEED_STREAMS if s in streams]
    prods = [streams[s] for s in PRODUCT_STREAMS if s in streams]
    if not feeds or not prods:
        return b
    if all(s.mass_flow_kg_h is not None for s in feeds + prods):
        b.mass_in_kg_h = sum(s.mass_flow_kg_h for s in feeds)  # type: ignore[misc]
        b.mass_out_kg_h = sum(s.mass_flow_kg_h for s in prods)  # type: ignore[misc]
        if b.mass_in_kg_h:
            b.mass_closure_rel = (b.mass_in_kg_h - b.mass_out_kg_h) / b.mass_in_kg_h
    b.n_atoms_in_kmol_h = sum(_atoms(s, N_ATOMS) for s in feeds)
    b.n_atoms_out_kmol_h = sum(_atoms(s, N_ATOMS) for s in prods)
    b.h_atoms_in_kmol_h = sum(_atoms(s, H_ATOMS) for s in feeds)
    b.h_atoms_out_kmol_h = sum(_atoms(s, H_ATOMS) for s in prods)

    if all(s.enthalpy_flow_kW is not None for s in feeds + prods):
        h_in = sum(s.enthalpy_flow_kW for s in feeds)  # type: ignore[misc]
        h_out = sum(s.enthalpy_flow_kW for s in prods)  # type: ignore[misc]
        # every block except the internal exchanger FEHE exchanges heat/work with the surroundings
        q_net = sum((blk.duty_kW or 0.0) for bid, blk in blocks.items() if bid != "FEHE")
        w_net = sum((blk.power_kW or 0.0) for blk in blocks.values())
        b.energy_in_kW = h_in + q_net + w_net
        b.energy_out_kW = h_out
        scale = sum(abs(blk.duty_kW or 0.0) for bid, blk in blocks.items() if bid != "FEHE") or 1.0
        b.energy_closure_rel = (b.energy_in_kW - b.energy_out_kW) / scale
    return b
