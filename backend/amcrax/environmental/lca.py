"""Scenario-based life-cycle greenhouse-gas assessment (research expansion, workstream U).

Additive to ``amcrax.environmental`` (the simplified carbon-intensity accounting is unchanged).

Boundary: cradle to gate of use in Singapore: upstream NH3 production (well-to-plant-gate), sea transport,
optional boil-off, cracking/turbine energy, grid electricity, direct N2O (as CO2e). NOx is a local pollutant and
is reported separately, never added to CO2e. Excluded: plant construction, catalyst manufacture, H2 leakage,
compression/delivery of H2, upstream natural-gas supply chain of the heating fuel (unless a leakage rate is given).

Every factor carries value, unit, source_type (literature | assumption), source and access date. Access date for
web data is 2026-11-23. Nothing here is an Aspen result; Aspen-derived activity data are read from stored results.
"""
from __future__ import annotations

from dataclasses import dataclass, field

ACCESS = "2026-11-23"

# value, unit, source_type, source, applicability_note
FACTORS: dict[str, dict] = {
    "ng_based_nh3_wtg": dict(
        value=2.60, unit="kg CO2e/kg NH3", source_type="literature",
        source="Lee et al. (2022) Green Chem. 24:4830, doi 10.1039/D2GC00843B, accepted manuscript p. 13 and Fig. 8 (OSTI 1960296)",
        note="Conventional NG-based NH3, well-to-plant-gate. Onsite 2.30, upstream (NG production, electricity) 0.30."),
    "nh3_process_co2": dict(
        value=1.49, unit="kg CO2/kg NH3", source_type="literature",
        source="Lee et al. (2022), manuscript p. 13 (process CO2 from aMDEA unit, captured in version 1)",
        note="Concentrated process CO2 stream; Lee capture it fully (rate implicit, not stated as a percentage)."),
    "nh3_combustion_co2": dict(
        value=0.45, unit="kg CO2/kg NH3", source_type="literature",
        source="Lee et al. (2022), manuscript p. 13 (boiler flue-gas CO2 captured with Cansolv in version 2)",
        note="Dilute combustion CO2 stream."),
    "capture_penalty_process": dict(
        value=0.05 / 1.49, unit="kg CO2e per kg CO2 captured", source_type="literature",
        source="Derived from Lee et al. (2022) p. 13: version 1 net 1.16 minus (2.60 - 1.49) = 0.05 kg CO2e/kg NH3 for capture, compression, transport electricity",
        note="Derived by AmCraX arithmetic from published totals."),
    "capture_penalty_combustion": dict(
        value=(0.11 - 0.05) / 0.45, unit="kg CO2e per kg CO2 captured", source_type="literature",
        source="Derived from Lee et al. (2022) p. 13: version 2 net 0.77 minus (2.60 - 1.49 - 0.45) = 0.11; minus 0.05 for the process stream",
        note="Derived by AmCraX arithmetic from published totals."),
    "ng_per_nh3": dict(
        value=32.52e3 / 47.1 / 1000.0, unit="kg NG/kg NH3", source_type="literature",
        source="Lee et al. (2022) energy table: 32.52 GJ NG (LHV)/t NH3; NG LHV 47.1 MJ/kg (manuscript p. 8)",
        note="Used to convert an upstream methane leakage rate into kg CH4 per kg NH3. Whole NG mass treated as CH4 (upper-bound simplification)."),
    "blue_nh3_lee_v1": dict(
        value=1.16, unit="kg CO2e/kg NH3", source_type="literature",
        source="Lee et al. (2022) p. 13 (carbon-capturing NH3 version 1)", note="Reproduced by blue_nh3_ef(capture_process=1)."),
    "blue_nh3_lee_v2": dict(
        value=0.77, unit="kg CO2e/kg NH3", source_type="literature",
        source="Lee et al. (2022) p. 13 (carbon-capturing NH3 version 2)", note="Reproduced by blue_nh3_ef(1, 1)."),
    "green_nh3_lee": dict(
        value=0.0, unit="kg CO2e/kg NH3", source_type="literature",
        source="Lee et al. (2022) p. 13 (renewable NH3 WTG = 0; equipment manufacture excluded)",
        note="Boundary limitation, not a claim that green NH3 is emission-free."),
    "embedded_renewable_h2_low": dict(
        value=0.4, unit="kg CO2e/kg H2", source_type="literature",
        source="IEA Global Hydrogen Review 2024, 'GHG emissions of hydrogen and its derivatives', highlights: embedded emissions of renewable assets 0.4-2.7 kg CO2-eq/kg H2",
        note="Converted to per kg NH3 with 0.1775 kg H2/kg NH3 (stoichiometry). Only the page highlights were read."),
    "embedded_renewable_h2_high": dict(
        value=2.7, unit="kg CO2e/kg H2", source_type="literature",
        source="IEA Global Hydrogen Review 2024 (as above)", note="Upper end of the embedded-emissions range."),
    "grey_nh3_range_low": dict(
        value=2.0, unit="kg CO2e/kg NH3", source_type="literature",
        source="cechetto2023membrane p. 19 (2.0-4.6 t CO2/t NH3), as recorded in amcrax/data/environmental.yaml",
        note="Lower end of the quoted grey-ammonia range."),
    "grey_nh3_range_high": dict(
        value=4.6, unit="kg CO2e/kg NH3", source_type="literature",
        source="cechetto2023membrane p. 19, as above", note="Upper end; likely includes coal-based plants."),
    "coal_nh3_low": dict(
        value=2.18, unit="kg CO2e/kg NH3", source_type="literature",
        source="Int. J. Life Cycle Assess. (2021), doi 10.1007/s11367-021-02010-z (Chinese pulverised-coal ammonia LCA): 3.88 -> 2.18 kg GHG per kg NH3",
        note="LOW CONFIDENCE: abstract-level value from a search extract; the publisher page could not be opened; boundary and unit not verified."),
    "coal_nh3_high": dict(
        value=3.88, unit="kg CO2e/kg NH3", source_type="literature",
        source="as above (older gasification technology)", note="LOW CONFIDENCE, see coal_nh3_low."),
    "gwp100_ch4_fossil": dict(
        value=29.8, unit="kg CO2e/kg CH4", source_type="literature",
        source="IPCC AR6 WGI Ch. 7 Table 7.15 (fossil CH4, GWP-100); US EPA 'Understanding Global Warming Potentials' confirms the AR6 range 27-30 (accessed 2026-11-23)",
        note="The exact 29.8 is from AR6 Table 7.15; the IPCC PDF returned HTTP 403 in this session so only the EPA range was re-checked."),
    "gwp100_n2o": dict(
        value=273.0, unit="kg CO2e/kg N2O", source_type="literature",
        source="IPCC AR6 WGI Ch. 7 Table 7.15; US EPA page accessed 2026-11-23 states 273", note="GWP-100."),
    "ship_ef": dict(
        value=0.011, unit="kg CO2e/(t km)", source_type="literature",
        source="GLEC Framework v3.0 liquefied-gas tanker 100-199 kcbm, VLSFO, WTW, via Climatiq listing (see amcrax/data/environmental.yaml)",
        note="Generic liquefied-gas carrier, not ammonia specific. Applied per tonne NH3 cargo, one way, no ballast return."),
    "ship_distance_baseline_km": dict(
        value=5000.0, unit="km", source_type="assumption",
        source="amcrax/data/environmental.yaml (existing illustrative assumption)",
        note="Route distance is a SCENARIO parameter. No sea-distance dataset could be opened in this session (port-distance site refused the connection), so Middle East and Australia distances are not quoted."),
    "ship_distance_range_km": dict(
        value=[2000.0, 12000.0], unit="km", source_type="assumption",
        source="scenario bounds chosen by AmCraX to span regional to long-haul voyages",
        note="Sensitivity bounds only; the shipping term is small either way (0.011 x 12000 / 1000 = 0.13 kg CO2e/kg NH3)."),
    "boil_off_fraction": dict(
        value=0.0, unit="fraction of cargo", source_type="assumption",
        source="no sourced boil-off or terminal-loss value found; excluded by default",
        note="Parameter kept in the model (default 0). Not varied because no source supports a value."),
    "grid_ef_singapore_2024": dict(
        value=0.402, unit="kg CO2/kWh", source_type="literature",
        source="EMA, Singapore Energy Statistics Ch. 2: average Grid Emission Factor 0.412 (2023) -> 0.402 (2024); page text confirmed by search extract 2026-11-23, https://www.ema.gov.sg/singapore-energy-statistics/Ch02/index2",
        note="Operating-margin average. Used both for process electricity and as the 'average grid' comparator."),
    "ng_co2_ef": dict(
        value=56100.0, unit="kg CO2/TJ (LHV)", source_type="literature",
        source="IPCC 2006 Guidelines Vol. 2 Ch. 2 Table 2.2 (natural gas)", note="Combustion CO2 only."),
    "ng_lhv": dict(
        value=47.1, unit="MJ/kg", source_type="literature",
        source="Lee et al. (2022) manuscript p. 8 (NG LHV 47.1 MJ/kg)", note="Used to convert NG leakage fraction to kg CH4 per MWh."),
    "ccgt_efficiency": dict(
        value=0.55, unit="-", source_type="assumption",
        source="no Singapore plant-level source retrieved; range 0.50-0.60",
        note="Net electrical efficiency (LHV) of the natural-gas CCGT comparator. Compare the EMA grid average above, which is a mix of plants."),
    "ccgt_efficiency_range": dict(
        value=[0.50, 0.60], unit="-", source_type="assumption", source="scenario bounds", note="Sensitivity bounds."),
    "ng_upstream_leak_scenarios": dict(
        value=[0.002, 0.015, 0.03], unit="fraction of NG supplied", source_type="literature",
        source="Leakage cases 0.2 %, 1.5 %, 3.0 % named in Analysis of Hydrogen Production Costs across the United States (arXiv 2206.10689), seen in a search extract only; Agora Energiewende chart cites 0.15 % (Norway) and 1.2 % (Russia) cases",
        note="LOW CONFIDENCE for the exact values (full text not opened). Used as scenario values for methane leakage; default is 0 (lower bound)."),
    "smr_h2_unabated": dict(
        value=[10.0, 12.0], unit="kg CO2e/kg H2", source_type="literature",
        source="IEA Global Hydrogen Review 2024, GHG emissions chapter highlights: unabated natural gas 10-12 kg CO2-eq/kg H2; 75-95 % occurs at the production site",
        note="Central value taken as the midpoint 11."),
    "smr_h2_ccs": dict(
        value=[3.4, 3.6], unit="kg CO2e/kg H2", source_type="literature",
        source="Frontiers in Energy Research 2024, doi 10.3389/fenrg.2024.1473383 (review: SMR with CCS 3.4-3.6 kg CO2e/kg H2), search extract only",
        note="LOW CONFIDENCE: capture rate and boundary not confirmed. Upper sensitivity 5.3 (90 % CCS, 3 % methane leakage, arXiv 2206.10689 interpolation)."),
    "smr_h2_ccs_high": dict(
        value=5.3, unit="kg CO2e/kg H2", source_type="literature",
        source="arXiv 2206.10689 (search extract): 5.3 with 90 % CCS at 3.0 % leakage; 12.9 without CCS", note="LOW CONFIDENCE, upper sensitivity only."),
    "ahmad_gas_flow_per_MWh": dict(
        value=150.52 / 43.1, unit="t flue gas/MWh net", source_type="literature",
        source="Ahmad et al. (2025) IJHE 173:151337 Table 6 (Case 2a: gas flow 150.52 t/h, W_net 43.1 MW)",
        note="Used only to turn exhaust ppmv values into mass per MWh. Assumes the ppmv values refer to the whole turbine exhaust stream (not stated unambiguously)."),
    "ahmad_n2o_ppmv_vnh3": dict(
        value=0.15, unit="ppmv", source_type="literature",
        source="Ahmad et al. (2025) p. 9 (Chemkin simulation, VNH3 case)", note="SIMULATED, not measured. Experiments cited by the paper show higher NO (282-337 ppmv)."),
    "ahmad_no_ppmv_vnh3": dict(
        value=107.0, unit="ppmv", source_type="literature",
        source="Ahmad et al. (2025) p. 9 (Chemkin simulation, VNH3 case)", note="SIMULATED; Chemkin underestimates NO per the paper. Local pollutant: reported separately."),
    "flue_gas_molar_mass": dict(
        value=28.8, unit="g/mol", source_type="assumption", source="air-like exhaust approximation",
        note="Used to convert ppmv to mass fraction."),
    "carbon_tax_sg_2026": dict(
        value=45.0, unit="SGD/t CO2e", source_type="literature",
        source="NEA Singapore carbon tax page (accessed 2026-11-23): SGD 25 in 2024-25, SGD 45 in 2026-27, SGD 50-80 by 2030; facilities emitting >= 25,000 t CO2e/yr direct; covers CO2, CH4, N2O",
        note="Applies only to direct in-scope Singapore emissions. Reported in SGD; no exchange rate is sourced, so it is not added to USD costs."),
}


def f(name: str):
    return FACTORS[name]["value"]


KG_H2_PER_KG_NH3 = 3 * 1.008 / 17.031  # stoichiometric hydrogen content, 0.1776 (fact sheet F1: 17.8 wt%)

ROUTES = ("green", "blue", "blue_v2", "blue_param", "grey", "coal")


def blue_nh3_ef(capture_process: float = 1.0, capture_combustion: float = 0.0, leak_frac: float = 0.0,
                gwp_ch4: float | None = None) -> float:
    """Blue NH3 well-to-gate, kg CO2e/kg NH3, from Lee's grey total and capture streams.

    capture_process / capture_combustion: captured fraction (0-1) of Lee's process-CO2 (1.49) and flue-gas CO2
    (0.45) streams; Lee's version 1 is (1, 0) = 1.16 and version 2 is (1, 1) = 0.77 (both reproduced exactly).
    leak_frac: ADDITIONAL upstream methane leakage as a fraction of NG mass supplied (default 0; Lee's own 0.30
    kg/kg upstream term is retained and its leakage assumption is not stated in the text read).
    """
    if not (0 <= capture_process <= 1 and 0 <= capture_combustion <= 1 and leak_frac >= 0):
        raise ValueError("capture fractions must be in [0, 1] and leak_frac >= 0")
    g = f("gwp100_ch4_fossil") if gwp_ch4 is None else gwp_ch4
    cp, cc = capture_process * f("nh3_process_co2"), capture_combustion * f("nh3_combustion_co2")
    return (f("ng_based_nh3_wtg") - cp - cc + cp * f("capture_penalty_process")
            + cc * f("capture_penalty_combustion") + leak_frac * f("ng_per_nh3") * g)


def green_nh3_ef(embedded: str = "mid") -> float:
    """Green NH3 incl. embedded renewable-asset emissions (IEA range), kg CO2e/kg NH3; 'lee' gives 0."""
    if embedded == "lee":
        return f("green_nh3_lee")
    lo, hi = f("embedded_renewable_h2_low"), f("embedded_renewable_h2_high")
    v = {"low": lo, "high": hi, "mid": 0.5 * (lo + hi)}[embedded]
    return v * KG_H2_PER_KG_NH3


@dataclass
class RouteSpec:
    name: str
    ef: float                      # kg CO2e / kg NH3 at the producer's gate
    low: float
    high: float
    source_type: str = "literature"
    label: str = ""


def route_spec(route: str) -> RouteSpec:
    """Central value and sourced range for each route (the range is what the sensitivity uses)."""
    if route == "green":
        return RouteSpec("green", green_nh3_ef("mid"), green_nh3_ef("low"), green_nh3_ef("high"), label="green NH3 (renewable, incl. embedded asset emissions)")
    if route == "green_lee":
        return RouteSpec("green_lee", 0.0, 0.0, green_nh3_ef("high"), label="green NH3 (Lee boundary, zero)")
    if route == "blue":
        return RouteSpec("blue", blue_nh3_ef(1, 0), f("blue_nh3_lee_v2"), blue_nh3_ef(0.9, 0, 0.03), label="blue NH3 (Lee v1: process CO2 captured)")
    if route == "blue_v2":
        return RouteSpec("blue_v2", blue_nh3_ef(1, 1), blue_nh3_ef(1, 1), blue_nh3_ef(0.9, 0.9, 0.03), label="blue NH3 (Lee v2: process + flue-gas CO2 captured)")
    if route == "blue_param":
        return RouteSpec("blue_param", blue_nh3_ef(0.95, 0.0, 0.015), blue_nh3_ef(1.0, 0.0, 0.002),
                         blue_nh3_ef(0.9, 0.0, 0.03), "assumption", label="blue NH3 (95 % process capture, 1.5 % extra CH4 leakage)")
    if route == "grey":
        return RouteSpec("grey", f("ng_based_nh3_wtg"), f("grey_nh3_range_low"), f("grey_nh3_range_high"), label="grey NH3 (NG SMR, no capture)")
    if route == "coal":
        mid = 0.5 * (f("coal_nh3_low") + f("coal_nh3_high"))
        return RouteSpec("coal", mid, f("coal_nh3_low"), f("coal_nh3_high"), "literature (low confidence)", label="coal-based NH3")
    raise ValueError(f"unknown route {route!r}")


def ship_kg_per_kg_nh3(distance_km: float, ef_per_tkm: float | None = None) -> float:
    ef = f("ship_ef") if ef_per_tkm is None else ef_per_tkm
    return ef * distance_km / 1000.0


def delivered_nh3_ef(ef_gate: float, distance_km: float, boil_off: float | None = None,
                     ef_per_tkm: float | None = None) -> float:
    """kg CO2e per kg NH3 *used* in Singapore: gate EF plus shipping, divided by (1 - boil-off loss)."""
    bo = f("boil_off_fraction") if boil_off is None else boil_off
    if not 0 <= bo < 1:
        raise ValueError("boil_off must be in [0, 1)")
    return (ef_gate + ship_kg_per_kg_nh3(distance_km, ef_per_tkm)) / (1.0 - bo)


def n2o_noX_per_MWh() -> dict:
    """Direct N2O (as CO2e) and NO per MWh for direct NH3 combustion, from Ahmad's simulated exhaust ppmv.

    Returns kg/MWh. NO is reported separately and is never added to CO2e.
    """
    flow_kg = f("ahmad_gas_flow_per_MWh") * 1000.0
    mm = f("flue_gas_molar_mass")
    n2o = f("ahmad_n2o_ppmv_vnh3") * 1e-6 * 44.013 / mm * flow_kg
    no = f("ahmad_no_ppmv_vnh3") * 1e-6 * 30.006 / mm * flow_kg
    return {"N2O_kg_per_MWh": n2o, "N2O_kgCO2e_per_MWh": n2o * f("gwp100_n2o"), "NO_kg_per_MWh": no}


def ccgt_ci_kg_per_MWh(eff: float | None = None, leak_frac: float = 0.0) -> float:
    """Natural-gas CCGT, kg CO2e/MWh: combustion CO2 (IPCC) plus optional upstream methane leakage."""
    e = f("ccgt_efficiency") if eff is None else eff
    fuel_GJ = 3.6 / e
    co2 = fuel_GJ / 1000.0 * f("ng_co2_ef")
    ch4 = leak_frac * fuel_GJ * 1000.0 / f("ng_lhv") * f("gwp100_ch4_fossil")
    return co2 + ch4


def smr_h2_ci(ccs: bool, central: bool = True) -> float:
    lo, hi = f("smr_h2_ccs") if ccs else f("smr_h2_unabated")
    return 0.5 * (lo + hi)


__all__ = ["FACTORS", "f", "blue_nh3_ef", "green_nh3_ef", "route_spec", "RouteSpec", "ship_kg_per_kg_nh3",
           "delivered_nh3_ef", "n2o_noX_per_MWh", "ccgt_ci_kg_per_MWh", "smr_h2_ci", "KG_H2_PER_KG_NH3", "ROUTES", "ACCESS"]
