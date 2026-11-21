"""Extraction of Aspen Plus results into :class:`amcrax.schemas.SimulationResult`.

All numbers come from the Aspen variable tree of a completed run. KPI and balance calculations
are simple arithmetic on those extracted values (:mod:`amcrax.kpis`).
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Optional

from amcrax.aspen.session import (
    HAP_NO_RESULTS,
    HAP_RESULTS_ERRORS,
    HAP_RESULTS_WARNINGS,
    AspenSession,
)
from amcrax.kpis import compute_balances, compute_kpis
from amcrax.paths import CONFIG_DIR
from amcrax.schemas import (
    COMPONENTS,
    BlockResult,
    CaseInputs,
    DataSource,
    RunStatus,
    SimulationResult,
    StreamResult,
)

S = r"\Data\Streams"
B = r"\Data\Blocks"


@lru_cache(maxsize=1)
def flowsheet_config() -> dict:
    return json.loads((CONFIG_DIR / "flowsheet.json").read_text(encoding="utf-8"))


def _phase(vfrac: Optional[float]) -> Optional[str]:
    if vfrac is None:
        return None
    if vfrac >= 1.0 - 1e-9:
        return "vapor"
    if vfrac <= 1e-9:
        return "liquid"
    return "mixed"


def extract_stream(s: AspenSession, sid: str, meta: Optional[dict] = None) -> StreamResult:
    o = rf"{S}\{sid}\Output"
    comps = [c for c in COMPONENTS if s.has(rf"{o}\MOLEFLOW\MIXED\{c}")]
    mole_flows = {c: float(s.get(rf"{o}\MOLEFLOW\MIXED\{c}", 0.0) or 0.0) for c in comps}
    total = s.get_quantity(rf"{o}\MOLEFLMX\MIXED", "kmol/hr")
    vfrac = s.get(rf"{o}\VFRAC_OUT\MIXED")
    meta = meta or {}
    return StreamResult(
        id=sid,
        name=meta.get("name", ""),
        source_block=s.get(rf"{o}\SOURCE") or meta.get("from"),
        dest_block=s.get(rf"{o}\DESTINATION") or meta.get("to"),
        phase=_phase(vfrac),
        temperature_C=s.get_quantity(rf"{o}\TEMP_OUT\MIXED", "C"),
        pressure_bar=s.get_quantity(rf"{o}\PRES_OUT\MIXED", "bar"),
        vapor_fraction=None if vfrac is None else float(vfrac),
        mole_flow_kmol_h=total,
        mass_flow_kg_h=s.get_quantity(rf"{o}\MASSFLMX\MIXED", "kg/hr"),
        enthalpy_flow_kW=s.get_quantity(rf"{o}\HMX_FLOW\MIXED", "kW"),
        mole_frac={c: float(s.get(rf"{o}\MOLEFRAC\MIXED\{c}", 0.0) or 0.0) for c in comps},
        mass_frac={c: float(s.get(rf"{o}\MASSFRAC\MIXED\{c}", 0.0) or 0.0) for c in comps},
        component_mole_flow_kmol_h=mole_flows,
    )


def _status_text(code: int) -> str:
    if code & HAP_RESULTS_ERRORS:
        return "errors"
    if code & HAP_NO_RESULTS:
        return "no results"
    if code & HAP_RESULTS_WARNINGS:
        return "warnings"
    return "ok"


def extract_block(s: AspenSession, bid: str, meta: Optional[dict] = None) -> BlockResult:
    o = rf"{B}\{bid}\Output"
    meta = meta or {}
    btype = meta.get("aspen_type", "")
    code = s.comp_status(rf"{B}\{bid}")
    details: dict[str, Optional[float | str]] = {"aspen_status": _status_text(code)}
    duty = power = t_out = p_out = None

    if btype == "Pump":
        power = s.get_quantity(rf"{o}\WNET", "kW")
        details["fluid_power_kW"] = s.get(rf"{o}\FLUID_POWER")
        details["brake_power_kW"] = s.get(rf"{o}\BRAKE_POWER")
        details["efficiency"] = s.get(rf"{o}\CEFF")
        details["head_developed"] = s.get(rf"{o}\HEAD_CAL")
        details["pressure_change_bar"] = s.get(rf"{o}\PDRP")
    elif btype == "HeatX":
        duty = s.get_quantity(rf"{o}\HX_DUTY", "kW")
        details["hot_inlet_temperature_C"] = s.get(rf"{o}\HOTINT")
        details["hot_outlet_temperature_C"] = s.get(rf"{o}\HOT_TEMP")
        details["cold_inlet_temperature_C"] = s.get(rf"{o}\COLDINT")
        details["cold_outlet_temperature_C"] = s.get(rf"{o}\COLD_TEMP")
        details["lmtd_K"] = s.get(rf"{o}\HX_DTLM")
        ua, ua_unit = s.get_with_unit(rf"{o}\HX_UA")
        details["UA"] = ua
        details["UA_unit"] = ua_unit
        area, area_unit = s.get_with_unit(rf"{o}\HX_AREAC")
        details["required_area"] = area
        details["required_area_unit"] = area_unit
        details["lmtd_correction_factor"] = s.get(rf"{o}\HX_FMTD")
    else:  # Heater, RGibbs, RStoic, Sep
        duty = s.get_quantity(rf"{o}\QCALC", "kW")
        t_out = s.get(rf"{o}\B_TEMP")
        p_out = s.get(rf"{o}\B_PRES")
        if btype == "RStoic":
            details["heat_of_reaction_note"] = "adiabatic (duty = 0); outlet temperature is the adiabatic flame temperature"
        if btype == "Sep":
            details["model_note"] = "reduced-order component splitter (not a designed PSA)"

    return BlockResult(
        id=bid,
        name=meta.get("name", ""),
        block_type=btype,
        duty_kW=duty,
        power_kW=power,
        outlet_temperature_C=None if t_out is None else float(t_out),
        outlet_pressure_bar=None if p_out is None else float(p_out),
        details=details,
    )


def extract_status(s: AspenSession, engine_time_s: Optional[float] = None) -> RunStatus:
    messages = s.run_messages()
    has_errors = has_warnings = False
    missing: list[str] = []
    for bid in s.block_ids():
        code = s.comp_status(rf"{B}\{bid}")
        if code & HAP_RESULTS_ERRORS:
            has_errors = True
            messages.append(f"Block {bid}: completed with errors")
        elif code & HAP_NO_RESULTS:
            missing.append(bid)
        elif code & HAP_RESULTS_WARNINGS:
            has_warnings = True
            messages.append(f"Block {bid}: completed with warnings")
    if missing:
        has_errors = True
        messages.append("Blocks without results: " + ", ".join(missing))
    text = " ".join(messages).upper()
    if "ERROR" in text and "WITH ERRORS" in text:
        has_errors = True
    if "WARNING" in text:
        has_warnings = True
    return RunStatus(
        converged=not has_errors,
        has_errors=has_errors,
        has_warnings=has_warnings,
        messages=messages,
        engine_time_s=engine_time_s,
    )


def extract_result(
    s: AspenSession,
    inputs: CaseInputs,
    *,
    engine_time_s: Optional[float] = None,
    model_file: Optional[str] = None,
) -> SimulationResult:
    cfg = flowsheet_config()
    stream_meta = {m["id"]: m for m in cfg["streams"]}
    block_meta = {m["id"]: m for m in cfg["blocks"]}
    streams = {sid: extract_stream(s, sid, stream_meta.get(sid)) for sid in s.stream_ids()}
    blocks = {bid: extract_block(s, bid, block_meta.get(bid)) for bid in s.block_ids()}
    status = extract_status(s, engine_time_s)
    result = SimulationResult(
        case_id=inputs.case_id,
        source=DataSource.ASPEN,
        model_file=model_file,
        inputs=inputs,
        status=status,
        streams=streams,
        blocks=blocks,
    )
    result.kpis = compute_kpis(streams, blocks)
    result.balances = compute_balances(streams, blocks)
    result.notes.append(
        "All stream and block values were extracted from an Aspen Plus V15 run through COM; "
        "KPIs and balance closures are arithmetic on those values (amcrax.kpis)."
    )
    return result
