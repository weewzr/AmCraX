"""PSA vs Pd-membrane comparison for the cracked gas of one SimulationResult (reduced-order models)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from amcrax.schemas import SimulationResult

from .compression import compression_power_kW
from .membrane import MembraneResult, area_for_recovery, membrane_separator
from .params import MODEL_LABEL
from .psa import PSAResult, psa_performance
from .slip import AmmoniaSlipResult, ammonia_slip


class ComparisonRow(BaseModel):
    option: str
    basis: str
    h2_recovery: float
    h2_purity_mole_frac: float
    product_h2_kg_h: float
    membrane_area_m2: Optional[float] = None
    feed_pressure_bar: float
    product_pressure_bar: float
    compression_power_kW: float
    energy_kWh_per_kgH2: float
    energy_kWh_per_kgH2_incl_product_recompression: float
    h2_loss_kmol_h: float
    h2_loss_lhv_kW: float
    h2_loss_fraction: float


class PurificationComparison(BaseModel):
    model: str = MODEL_LABEL
    case_id: str
    input_source: str
    feed_stream: str
    feed_kmol_h: dict[str, float]
    feed_pressure_bar: float
    feed_temperature_C: Optional[float]
    rows: list[ComparisonRow]
    psa: dict[str, PSAResult]
    membrane: dict[str, MembraneResult]
    ammonia_slip: AmmoniaSlipResult
    notes: list[str] = Field(default_factory=list)


PSA_BASES = ("cho2026_5A", "hansen2024_cha_AC", "kum2026_lumped", "amcrax_baseline")


def cracked_gas(result: SimulationResult) -> tuple[str, dict[str, float], float, Optional[float]]:
    """(stream id, component flows kmol/h, P bar, T degC) of the PSA feed stream."""
    for sid, s in result.streams.items():
        if s.dest_block == "PSA":
            return sid, {k: v for k, v in s.component_mole_flow_kmol_h.items() if v}, s.pressure_bar, s.temperature_C
    raise ValueError("no stream with dest_block 'PSA' in result")


def compare_purification(result: SimulationResult, *, membrane_recoveries: tuple[float, ...] = (0.756, 0.90),
                         membrane_T_K: float | None = None, permeate_pressure_bar: float | None = None,
                         product_pressure_bar: float | None = None, compressor_eta: float | None = None
                         ) -> PurificationComparison:
    sid, feed, P, T_C = cracked_gas(result)
    T_K = (T_C if T_C is not None else 40.0) + 273.15
    h2_in = feed.get("H2", 0.0)
    prod_s = next((s for s in result.streams.values() if s.source_block == "PSA" and s.id.upper().startswith("H2")), None)
    if product_pressure_bar is None:
        product_pressure_bar = prod_s.pressure_bar if prod_s and prod_s.pressure_bar else P
    notes = [f"{MODEL_LABEL}s; PSA rows apply literature operating points (no interpolation); membrane row "
             "uses ideal Sieverts flux with literature Pd-Ag permeability. Neither is a designed or validated unit.",
             f"input {result.source.value} case '{result.case_id}', feed stream {sid}",
             "energy = cracked-gas compression to the PSA feed requirement (zero if already above); the "
             "'incl. product recompression' column adds compression of the H2 product to "
             f"{product_pressure_bar:g} bar (eta as for the cracked-gas compressor), which is what the membrane "
             "permeate at low pressure needs to match the PSA product pressure",
             "membrane heating not counted: the membrane is assumed placed where the effluent is at the "
             "membrane temperature (upstream of COOLER); the cooled stream composition is used"]
    rows: list[ComparisonRow] = []
    psa: dict[str, PSAResult] = {}
    for b in PSA_BASES:
        tp = None
        if b == "amcrax_baseline" and result.kpis.h2_purity_mole_frac:
            tp = result.kpis.h2_purity_mole_frac  # purity of the simulated product (psa_n2_slip input)
        r = psa_performance(feed, P, target_purity=tp, basis=b, feed_temperature_K=T_K, compressor_eta=compressor_eta)
        if tp is not None:
            r.notes.append(f"purity {tp:.6f} = simulated H2PROD purity of the input case ({result.source.value})")
        psa[b] = r
        e = r.specific_energy_kWh_per_kgH2
        rows.append(ComparisonRow(option=f"PSA ({b})", basis=r.basis_source, h2_recovery=r.h2_recovery,
                                  h2_purity_mole_frac=r.h2_purity_mole_frac, product_h2_kg_h=r.product_h2_kg_h,
                                  feed_pressure_bar=P, product_pressure_bar=max(P, r.required_feed_pressure_bar),
                                  compression_power_kW=r.compression_power_kW, energy_kWh_per_kgH2=e,
                                  energy_kWh_per_kgH2_incl_product_recompression=e,
                                  h2_loss_kmol_h=r.h2_loss_kmol_h, h2_loss_lhv_kW=r.h2_loss_lhv_kW,
                                  h2_loss_fraction=r.h2_loss_kmol_h / h2_in if h2_in else 0.0))
    mem: dict[str, MembraneResult] = {}
    for R in membrane_recoveries:
        A = area_for_recovery(feed, R, P, permeate_pressure_bar, membrane_T_K)
        if A is None:
            notes.append(f"membrane recovery {R} above pinch limit at {P:g} bar - row omitted")
            continue
        m = membrane_separator(feed, A, P, permeate_pressure_bar, membrane_T_K)
        mem[f"R{R:g}"] = m
        rc = compression_power_kW(m.permeate_kmol_h["H2"], {"H2": 1.0}, T_K, m.permeate_pressure_bar,
                                  product_pressure_bar, None, compressor_eta)
        kg = m.product_h2_kg_h
        rows.append(ComparisonRow(option=f"Pd-Ag membrane (R={R:g})", basis=m.permeability_source, h2_recovery=m.h2_recovery,
                                  h2_purity_mole_frac=m.h2_purity_mole_frac, product_h2_kg_h=kg, membrane_area_m2=A,
                                  feed_pressure_bar=P, product_pressure_bar=m.permeate_pressure_bar,
                                  compression_power_kW=0.0, energy_kWh_per_kgH2=0.0,
                                  energy_kWh_per_kgH2_incl_product_recompression=rc["power_kW"] / kg if kg else 0.0,
                                  h2_loss_kmol_h=m.h2_loss_kmol_h, h2_loss_lhv_kW=m.h2_loss_lhv_kW,
                                  h2_loss_fraction=m.h2_loss_kmol_h / h2_in if h2_in else 0.0))
    return PurificationComparison(case_id=result.case_id, input_source=result.source.value, feed_stream=sid,
                                  feed_kmol_h=feed, feed_pressure_bar=P, feed_temperature_C=T_C, rows=rows, psa=psa,
                                  membrane=mem, ammonia_slip=ammonia_slip(feed), notes=notes)
