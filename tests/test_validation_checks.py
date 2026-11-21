"""Tests of the reusable validation checks (amcrax.validation)."""
from __future__ import annotations

import math

import pytest

from amcrax import paths
from amcrax.process_model import run_python_case
from amcrax.schemas import CaseInputs, SimulationResult
from amcrax.thermodynamics import NU, equilibrium_constant, reaction_enthalpy_kJ_mol
from amcrax.validation import (FAIL, NOT_RUN, PASS, CheckResult, check_economic_consistency, check_element_closure,
                               check_mass_closure, check_nonnegative, check_optimisation_feasibility,
                               check_reaction_stoichiometry, check_unit_sanity, check_vant_hoff, check_vant_hoff_data,
                               judge, simulation_closures)


def test_pass_requires_metric_and_tolerance():
    with pytest.raises(ValueError):
        CheckResult("x", "x", PASS)
    with pytest.raises(ValueError):
        CheckResult("x", "x", PASS, value=0.0)
    with pytest.raises(ValueError):
        CheckResult("x", "x", "maybe")


def test_judge():
    assert judge(0.5, 1.0) == PASS
    assert judge(-1.5, 1.0) == FAIL
    assert judge(float("nan"), 1.0) == FAIL
    assert judge(None, 1.0) == NOT_RUN


def test_stoichiometry():
    assert check_reaction_stoichiometry(NU).status == PASS
    assert check_reaction_stoichiometry({"NH3": -1, "N2": 0.5, "H2": 1.0}).status == FAIL


def test_element_and_mass_closure():
    n_in = {"NH3": 1.0}
    assert check_element_closure(n_in, {"NH3": 0.2, "N2": 0.4, "H2": 1.2}).status == PASS
    assert check_element_closure(n_in, {"NH3": 0.2, "N2": 0.4, "H2": 1.0}).status == FAIL
    assert check_mass_closure(100.0, 100.0).status == PASS
    assert check_mass_closure(100.0, 101.0).status == FAIL


def test_vant_hoff_python_thermo_and_synthetic():
    T = [600.0, 700.0, 800.0, 900.0]
    assert check_vant_hoff(lambda t: math.log(equilibrium_constant(t)), reaction_enthalpy_kJ_mol, T).status == PASS
    # inconsistent pair: dH doubled
    bad = check_vant_hoff(lambda t: math.log(equilibrium_constant(t)), lambda t: 2 * reaction_enthalpy_kJ_mol(t), T)
    assert bad.status == FAIL
    # tabulated data: constant dH -> lnK = a - dH/(R T) exactly; the linear-dH integration is exact here
    R = 8.314462618
    Ts = [500.0 + 25 * i for i in range(10)]
    assert check_vant_hoff_data(Ts, [5 - 50e3 / (R * t) for t in Ts], [50.0] * 10, tol=1e-9).status == PASS
    assert check_vant_hoff_data(Ts, [5 - 50e3 / (R * t) for t in Ts], [55.0] * 10, tol=1e-3).status == FAIL


@pytest.fixture(scope="module")
def py_base() -> SimulationResult:
    return run_python_case(CaseInputs())


def test_python_flowsheet_closes(py_base):
    res = simulation_closures(py_base, "py")
    assert [r.status for r in res] == [PASS, PASS, PASS]
    assert check_nonnegative(py_base).status == PASS
    assert check_unit_sanity(py_base).status == PASS


def test_negative_flow_and_bad_fraction_detected(py_base):
    bad = py_base.model_copy(deep=True)
    bad.streams["S5"].component_mole_flow_kmol_h["NH3"] = -1.0
    assert check_nonnegative(bad).status == FAIL
    bad.streams["S5"].mole_frac["H2"] = 1.5
    assert check_unit_sanity(bad).status == FAIL


@pytest.mark.skipif(not (paths.RESULTS_SIMULATIONS / "baseline.json").exists(), reason="Aspen baseline not exported")
def test_aspen_baseline_closures():
    r = SimulationResult.model_validate_json((paths.RESULTS_SIMULATIONS / "baseline.json").read_text(encoding="utf-8"))
    for c in simulation_closures(r, "aspen"):
        assert c.status == PASS, c
    assert check_nonnegative(r).status == PASS


def test_hooks():
    ok = check_optimisation_feasibility({"T": 600.0, "P": 20.0}, {"T": (250, 1000), "P": (1, 100)},
                                        {"purity": (0.9996, ">=", 0.999)})
    assert ok.status == PASS
    bad = check_optimisation_feasibility({"T": 1200.0}, {"T": (250, 1000)})
    assert bad.status == FAIL and bad.value == pytest.approx(200.0)
    assert check_economic_consistency({"capex": 1.0, "feed": 3.0}, 4.0).status == PASS
    assert check_economic_consistency({"capex": 1.0, "feed": 3.0}, 4.5).status == FAIL


def test_independent_physics_recalculations_on_python_result(py_base):
    """The independent recalculations (Cantera, CoolProp, LMTD) reproduce the Python model, which uses the same
    GRI-Mech data and the same pump formula - a check of the recalculation code, run without Aspen."""
    pytest.importorskip("cantera")
    from amcrax.validation import physics as ph
    f = ph.flame_temperature_cantera(py_base)
    assert f["dT_complete_minus_aspen_K"] == pytest.approx(0.0, abs=0.05)       # here 'aspen' = the Python result
    assert f["max_abs_product_flow_dev_vs_aspen_flue_kmol_h"] < 1e-9
    assert -5.0 < f["dT_equilibrium_minus_complete_K"] < 0.0                    # dissociation lowers T_ad
    q = ph.fluehx_duty_cantera(py_base)
    assert abs(q["rel_dev"]) < 1e-5
    w = ph.pump_power_hand(py_base)
    assert w["rel_dev"] == pytest.approx(0.0, abs=1e-12)
    assert ph.fehe_ua_lmtd(py_base) is None                                      # no UA in a Python result


def test_fehe_ua_lmtd_unit_and_relation():
    from amcrax.schemas import BlockResult
    from amcrax.validation import physics as ph
    r = run_python_case(CaseInputs()).model_copy(deep=True)
    d1, d2 = 50.0, 150.0
    lm = (d2 - d1) / math.log(d2 / d1)
    q = 600.0
    r.blocks["FEHE"] = BlockResult(id="FEHE", duty_kW=q, details={
        "hot_inlet_temperature_C": 600.0, "cold_outlet_temperature_C": 550.0, "hot_outlet_temperature_C": 225.0,
        "cold_inlet_temperature_C": 75.0, "UA": q / lm * 1000.0 / ph.CAL_IT_J, "UA_unit": "cal/sec-K"})
    u = ph.fehe_ua_lmtd(r)
    assert u["rel_dev"] == pytest.approx(0.0, abs=1e-12) and u["LMTD_K"] == pytest.approx(lm)
    assert u["rel_dev_if_thermochemical_cal"] == pytest.approx(ph.CAL_TH_J / ph.CAL_IT_J - 1, rel=1e-9)
    r.blocks["FEHE"].details["UA_unit"] = "W/K"
    with pytest.raises(ValueError):
        ph.fehe_ua_lmtd(r)


def _cand(id, p, s, conv=True, status="pass"):
    return {"id": id, "aspen_converged": conv, "max_relative_deviation_primary": p,
            "max_relative_deviation_primary_metric": "m1", "max_relative_deviation_secondary": s,
            "max_relative_deviation_secondary_metric": "m2", "tolerance": 0.02, "status": status}


def test_aspen_verification_follows_file_criterion():
    from amcrax.validation import check_aspen_verification
    doc = {"tolerance_relative": 0.02, "primary_metrics": ["m1"],
           "candidates": [_cand("a", 0.012, 0.10), _cand("b", -0.005, 0.03)]}
    r = check_aspen_verification(doc)
    assert r.status == PASS and r.value == pytest.approx(0.012) and r.tolerance == 0.02
    assert "0.1" in r.detail  # secondary deviation reported, not judged
    doc["candidates"].append(_cand("c", 0.025, 0.0, status="fail"))
    assert check_aspen_verification(doc).status == FAIL           # primary outside tolerance
    doc["candidates"][-1] = _cand("c", 0.001, 0.0, conv=False, status="fail")
    assert check_aspen_verification(doc).status == FAIL           # not converged
    doc["candidates"][-1] = _cand("c", 0.001, 0.0, status="fail")
    assert check_aspen_verification(doc).status == FAIL           # file status inconsistent with recomputation
    assert check_aspen_verification({"candidates": []}).status == NOT_RUN


def _res(opt, g, feasible=True, at_bound=None):
    return {"id": "r", "feasible": feasible,
            "decision_variables": {"T": {"lower": 400.0, "upper": 800.0, "optimum": opt, "at_bound": at_bound}},
            "constraints": {"values_at_optimum": g}}


def test_single_objective_feasibility():
    from amcrax.validation import check_single_objective_feasibility as chk
    assert chk({"results": [_res(600.0, {"x": 0.1}), _res(800.0, {"x": -1e-9}, at_bound="upper")]}).status == PASS
    assert chk({"results": [_res(600.0, {"x": -0.01})]}).status == FAIL              # flagged feasible, violated
    assert chk({"results": [_res(850.0, {"x": 0.1})]}).status == FAIL                # outside bounds
    assert chk({"results": [_res(800.0, {"x": 0.1})]}).status == FAIL                # missing at_bound flag
    assert chk({"results": [_res(600.0, {"x": -0.05}, feasible=False)]}).status == PASS  # honestly labelled infeasible
    assert chk({"results": [_res(600.0, {"x": 0.05}, feasible=False)]}).status == FAIL   # infeasible flag unsupported
    assert chk({}).status == NOT_RUN
