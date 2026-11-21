"""Tests of the Aspen Plus automation layer.

Three groups:

* input-file generator and KPI/balance arithmetic - pure Python, always run;
* stored Aspen results (``results/simulations/*.json`` with ``source == aspen_plus_v15``) - checks
  conservation laws on what Aspen actually returned; skipped if no result file exists;
* a live Aspen Plus V15 run through COM - opt-in (``AMCRAX_RUN_ASPEN=1``) because it needs a
  licensed Aspen installation and takes about 15 s.
"""
from __future__ import annotations

import os

import pytest

from amcrax.aspen.inp_writer import (
    MIN_FLOWSHEET_PRESSURE_BAR,
    build_equilibrium_input,
    build_flowsheet_input,
    validate_flowsheet_inputs,
)
from amcrax.kpis import compute_balances, compute_kpis, lhv_kW
from amcrax.paths import RESULTS_SIMULATIONS
from amcrax.schemas import LHV_KJ_PER_MOL, MOLAR_MASS, CaseInputs, DataSource, SimulationResult


# --------------------------------------------------------------------------- input generator
def test_flowsheet_input_contains_all_blocks_and_streams():
    text = build_flowsheet_input(CaseInputs())
    for block in ("PUMP PUMP", "VAPORIZR HEATER", "FEHE HEATX", "HEATER HEATER", "CRACKER RGIBBS",
                  "COOLER HEATER", "PSA SEP", "BURNER RSTOIC", "FLUEHX HEATER"):
        assert f"BLOCK {block}" in text
    assert "PROPERTIES PENG-ROB" in text
    assert "NH3 H3N" in text and "CALCULATOR AIRCALC" in text
    assert "BLOCK FEHE IN=S5 S2 OUT=S6 S3" in text


def test_flowsheet_input_specifications_follow_case_inputs():
    inputs = CaseInputs(reactor_temperature_C=650.0, reactor_pressure_bar=30.0, fehe_hot_end_approach_K=40.0,
                        psa_h2_recovery=0.8, burner_excess_air=0.2)
    text = build_flowsheet_input(inputs)
    assert "PARAM TEMP=650. PRES=30." in text            # CRACKER at reactor conditions
    assert "PARAM TEMP=650. PRES=30.2" in text           # HEATER outlet = reactor T, P + 0.2 bar
    assert "PARAM PRES=31. EFF=0.75" in text             # pump discharge = P + 1.0 bar
    assert "T-COLD=610." in text                         # FEHE cold outlet = T - approach
    assert "FLASH-SPECS H2PROD PRES=29." in text         # product at P - 1.0 bar
    assert "* 1.2 / 0.21" in text                        # air = stoichiometric O2 * (1 + excess) / 0.21


def test_no_heat_integration_removes_fehe_and_reroutes():
    text = build_flowsheet_input(CaseInputs(heat_integration=False))
    assert "FEHE" not in text and "S3" not in text and "S6" not in text
    assert "BLOCK HEATER IN=S2 OUT=S4" in text and "BLOCK COOLER IN=S5 OUT=S7" in text


def test_native_sensitivity_adds_tie_calculator_and_sensitivity_block():
    text = build_flowsheet_input(CaseInputs(), native_sensitivity=True)
    assert "CALCULATOR TLINK" in text and "SENSITIVITY STEMP" in text
    assert "WRITE-VARS THT TFE" in text
    assert "SENSITIVITY" not in build_flowsheet_input(CaseInputs())


def test_generator_rejects_unphysical_specifications():
    with pytest.raises(ValueError):
        validate_flowsheet_inputs(CaseInputs(reactor_pressure_bar=MIN_FLOWSHEET_PRESSURE_BAR - 0.5))
    with pytest.raises(ValueError):
        validate_flowsheet_inputs(CaseInputs(reactor_temperature_C=300.0, fehe_hot_end_approach_K=250.0))
    validate_flowsheet_inputs(CaseInputs(reactor_temperature_C=300.0, heat_integration=False))


def test_equilibrium_input_is_a_single_rgibbs():
    text = build_equilibrium_input(450.0, 10.0, "IDEAL")
    assert "BLOCK REQ RGIBBS" in text and "PROPERTIES IDEAL" in text
    assert "TEMP=450. PRES=10." in text and "PROD NH3 / H2 / N2" in text


def test_input_file_is_plain_ascii():
    build_flowsheet_input(CaseInputs(), native_sensitivity=True).encode("ascii")


# --------------------------------------------------------------------------- constants
def test_reference_constants_are_consistent():
    # NH3 molar mass must equal 0.5 N2 + 1.5 H2 within rounding of the tabulated values
    assert abs(MOLAR_MASS["NH3"] - (0.5 * MOLAR_MASS["N2"] + 1.5 * MOLAR_MASS["H2"])) < 1e-3
    # stoichiometric ammonia demand: kg NH3 per kg H2 at full conversion and recovery
    assert abs(MOLAR_MASS["NH3"] / (1.5 * MOLAR_MASS["H2"]) - 5.632) < 2e-3
    # LHV of ammonia in MJ/kg
    assert abs(LHV_KJ_PER_MOL["NH3"] / MOLAR_MASS["NH3"] - 18.60) < 0.02


# --------------------------------------------------------------------------- stored Aspen results
def _aspen_results() -> list[SimulationResult]:
    out = []
    for path in sorted(RESULTS_SIMULATIONS.glob("*.json")):
        try:
            r = SimulationResult.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception:
            continue  # analysis files of other modules live in the same folder
        if r.source == DataSource.ASPEN and r.status.converged:
            out.append(r)
    return out


ASPEN_RESULTS = _aspen_results()
needs_results = pytest.mark.skipif(not ASPEN_RESULTS, reason="no stored Aspen Plus results in results/simulations")


@needs_results
@pytest.mark.parametrize("result", ASPEN_RESULTS, ids=lambda r: r.case_id)
def test_aspen_result_conserves_mass_elements_energy(result: SimulationResult):
    b = result.balances
    assert abs(b.mass_closure_rel) < 1e-6
    assert abs(b.n_atoms_in_kmol_h - b.n_atoms_out_kmol_h) / b.n_atoms_in_kmol_h < 1e-6
    assert abs(b.h_atoms_in_kmol_h - b.h_atoms_out_kmol_h) / b.h_atoms_in_kmol_h < 1e-6
    assert abs(b.energy_closure_rel) < 1e-5


@needs_results
@pytest.mark.parametrize("result", ASPEN_RESULTS, ids=lambda r: r.case_id)
def test_aspen_result_is_physical(result: SimulationResult):
    for s in result.streams.values():
        assert s.mole_flow_kmol_h >= 0 and s.mass_flow_kg_h >= 0
        assert all(v >= -1e-12 for v in s.component_mole_flow_kmol_h.values())
        assert abs(sum(s.mole_frac.values()) - 1.0) < 1e-6
        assert 0.0 <= s.vapor_fraction <= 1.0
    k = result.kpis
    assert 0.0 < k.nh3_conversion < 1.0
    assert 0.0 < k.lhv_efficiency < 1.0
    assert k.reactor_duty_kW > 0            # endothermic reaction
    assert result.blocks["BURNER"].duty_kW == pytest.approx(0.0, abs=1e-6)   # adiabatic burner


@needs_results
@pytest.mark.parametrize("result", ASPEN_RESULTS, ids=lambda r: r.case_id)
def test_aspen_result_obeys_reaction_stoichiometry(result: SimulationResult):
    s4, s5 = result.streams["S4"].component_mole_flow_kmol_h, result.streams["S5"].component_mole_flow_kmol_h
    reacted = s4["NH3"] - s5["NH3"]
    assert s5["H2"] - s4.get("H2", 0.0) == pytest.approx(1.5 * reacted, rel=1e-6)
    assert s5["N2"] - s4.get("N2", 0.0) == pytest.approx(0.5 * reacted, rel=1e-6)
    assert s5.get("H2O", 0.0) == pytest.approx(s4.get("H2O", 0.0), rel=1e-6, abs=1e-9)   # water is inert


@needs_results
@pytest.mark.parametrize("result", ASPEN_RESULTS, ids=lambda r: r.case_id)
def test_psa_split_matches_specification(result: SimulationResult):
    s7 = result.streams["S7"].component_mole_flow_kmol_h
    prod = result.streams["H2PROD"].component_mole_flow_kmol_h
    assert prod["H2"] / s7["H2"] == pytest.approx(result.inputs.psa_h2_recovery, rel=1e-6)
    assert prod["N2"] / s7["N2"] == pytest.approx(result.inputs.psa_n2_slip, rel=1e-5)
    assert prod.get("NH3", 0.0) == pytest.approx(0.0, abs=1e-9)


@needs_results
@pytest.mark.parametrize("result", ASPEN_RESULTS, ids=lambda r: r.case_id)
def test_burner_air_follows_calculator_and_burns_out(result: SimulationResult):
    tail = result.streams["TAILGAS"].component_mole_flow_kmol_h
    air = result.streams["AIR"].mole_flow_kmol_h
    expected = (0.5 * tail["H2"] + 0.75 * tail["NH3"]) * (1.0 + result.inputs.burner_excess_air) / 0.21
    assert air == pytest.approx(expected, rel=1e-5)
    flue = result.streams["FLUE"].component_mole_flow_kmol_h
    assert flue.get("H2", 0.0) == pytest.approx(0.0, abs=1e-8)
    assert flue.get("NH3", 0.0) == pytest.approx(0.0, abs=1e-8)
    assert flue["O2"] > 0


@needs_results
@pytest.mark.parametrize("result", ASPEN_RESULTS, ids=lambda r: r.case_id)
def test_kpis_are_reproducible_from_streams_and_blocks(result: SimulationResult):
    again = compute_kpis(result.streams, result.blocks)
    assert again.model_dump() == pytest.approx(result.kpis.model_dump(), rel=1e-12, nan_ok=True)
    assert compute_balances(result.streams, result.blocks).mass_closure_rel == pytest.approx(
        result.balances.mass_closure_rel, abs=1e-12)
    # combustion heat recovered to stack temperature cannot exceed the tail-gas lower heating value
    assert result.kpis.tailgas_combustion_heat_kW <= lhv_kW(result.streams["TAILGAS"]) * (1 + 1e-9)


@needs_results
def test_heat_integration_reduces_external_heating():
    by_id = {r.case_id: r for r in ASPEN_RESULTS}
    if not {"baseline", "baseline_no_hi"} <= by_id.keys():
        pytest.skip("baseline pair not available")
    hi, no_hi = by_id["baseline"], by_id["baseline_no_hi"]
    saved = no_hi.kpis.total_external_heating_kW - hi.kpis.total_external_heating_kW
    assert saved == pytest.approx(hi.kpis.recovered_heat_kW, rel=1e-6)   # FEHE duty displaces trim heating 1:1
    assert hi.kpis.nh3_conversion == pytest.approx(no_hi.kpis.nh3_conversion, rel=1e-9)


# --------------------------------------------------------------------------- live Aspen (opt-in)
@pytest.mark.skipif(os.environ.get("AMCRAX_RUN_ASPEN") != "1", reason="set AMCRAX_RUN_ASPEN=1 to run Aspen Plus V15 live")
def test_live_aspen_run_converges_and_closes_balances():
    from amcrax.aspen.runner import run_case

    result = run_case(CaseInputs(case_id="pytest_live", reactor_temperature_C=625.0), save=False, study="pytest")
    assert result.source == DataSource.ASPEN and result.status.converged
    assert abs(result.balances.mass_closure_rel) < 1e-6
    assert abs(result.balances.energy_closure_rel) < 1e-5
    assert result.streams["S5"].temperature_C == pytest.approx(625.0, abs=1e-6)
