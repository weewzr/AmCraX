"""Tests for amcrax.optimisation (evaluator, optimiser, constraints, Pareto)."""
from __future__ import annotations

import numpy as np
import pytest

from amcrax import paths
from amcrax.economics import EconomicAssumptions, compute_lcoh
from amcrax.environmental import carbon_intensity, load_factors
from amcrax.optimisation import (constraint_values, design_grid, evaluate_inputs, evaluate_result, front, minimise,
                                 non_dominated, run)
from amcrax.process_model import run_python_case
from amcrax.schemas import CaseInputs, SimulationResult


@pytest.fixture(scope="module")
def py_base():
    return run_python_case(CaseInputs())


def test_evaluate_matches_economics_and_environment(py_base):
    m = evaluate_result(py_base)
    assert m["compression_power_kW"] == 0.0  # 20 bar: PSA feed 19.5 bar >= 7 bar
    assert m["lcoh_USD_per_kg"] == pytest.approx(compute_lcoh(py_base, EconomicAssumptions()).lcoh_USD_per_kg, rel=1e-12)
    ci = carbon_intensity(py_base, "grey/self_firing")
    assert m["carbon_intensity_kgCO2e_per_kgH2"] == pytest.approx(ci.total_kgCO2e_per_kgH2, rel=1e-12)
    assert "grey/self_firing" in m["ci_scenario"]
    assert m["lhv_efficiency"] == py_base.kpis.lhv_efficiency
    parts = sum(v for k, v in m.items() if k.startswith("lcoh_") and k.endswith("_USD_per_kg") and k != "lcoh_USD_per_kg")
    assert parts == pytest.approx(m["lcoh_USD_per_kg"], rel=1e-10)


def test_evaluate_aspen_baseline():
    p = paths.RESULTS_SIMULATIONS / "baseline.json"
    if not p.exists():
        pytest.skip("no Aspen baseline")
    r = SimulationResult.model_validate_json(p.read_text(encoding="utf-8"))
    m = evaluate_result(r)
    assert m["source"] == "aspen_plus_v15"
    assert m["lcoh_USD_per_kg"] == pytest.approx(compute_lcoh(r).lcoh_USD_per_kg, rel=1e-12)


def test_compression_added_consistently():
    m = evaluate_inputs(CaseInputs(reactor_pressure_bar=5.0))
    assert m["compression_power_kW"] > 0
    res = run_python_case(CaseInputs(reactor_pressure_bar=5.0))
    a = EconomicAssumptions(compression_power_kW=m["compression_power_kW"])
    assert m["lcoh_USD_per_kg"] == pytest.approx(compute_lcoh(res, a).lcoh_USD_per_kg, rel=1e-12)
    ef = load_factors()["electricity"]["singapore_2024"]["value"]
    ci0 = carbon_intensity(res, "grey/self_firing").total_kgCO2e_per_kgH2
    assert m["carbon_intensity_kgCO2e_per_kgH2"] == pytest.approx(
        ci0 + m["compression_power_kW"] * ef / res.kpis.h2_product_kg_h, rel=1e-12)


def test_minimise_analytic():
    f = lambda x: (x[0] - 1.3) ** 2 + 2 * (x[1] + 0.7) ** 2 + 0.5  # noqa: E731
    r = minimise(f, [(-3, 3), (-3, 3)], seed=1)
    assert r["x"] == pytest.approx([1.3, -0.7], abs=1e-4)
    assert r["fun"] == pytest.approx(0.5, abs=1e-7)
    # constrained: x0 + x1 >= 1 -> optimum on the line
    rc = minimise(lambda x: x[0] ** 2 + x[1] ** 2, [(-2, 2), (-2, 2)], lambda x: np.array([x[0] + x[1] - 1.0]), seed=1)
    assert rc["x"] == pytest.approx([0.5, 0.5], abs=1e-3)
    assert rc["feasible"]


def test_minimise_deterministic():
    f = lambda x: np.sin(3 * x[0]) + (x[0] - 0.2) ** 2  # noqa: E731
    a = minimise(f, [(-2, 2)], seed=7)
    b = minimise(f, [(-2, 2)], seed=7)
    assert a["x"][0] == b["x"][0] and a["fun"] == b["fun"]


@pytest.fixture(scope="module")
def lcoh_run():
    return run("min_lcoh", variables=["reactor_temperature_C", "reactor_pressure_bar"], popsize=6, maxiter=12,
               flatness_points=9)


def test_run_respects_constraints_and_bounds(lcoh_run):
    r = lcoh_run
    assert all(g >= -1e-7 for g in r["constraints"]["values_at_optimum"].values())
    for n, d in r["decision_variables"].items():
        assert d["lower"] - 1e-9 <= d["optimum"] <= d["upper"] + 1e-9
    assert r["optimum_inputs"]["reactor_pressure_bar"] >= 3.0
    assert r["optimum_metrics"]["lcoh_USD_per_kg"] <= r["baseline_metrics"]["lcoh_USD_per_kg"] + 1e-9
    m = evaluate_inputs(CaseInputs(**r["optimum_inputs"]))
    assert m["lcoh_USD_per_kg"] == pytest.approx(r["optimum_metrics"]["lcoh_USD_per_kg"], rel=1e-12)
    assert r["engine"] == "python_model" and "driver" in r and "flatness" in r


def test_run_deterministic(lcoh_run):
    r2 = run("min_lcoh", variables=["reactor_temperature_C", "reactor_pressure_bar"], popsize=6, maxiter=12,
             flatness_points=0)
    assert r2["optimum_inputs"] == lcoh_run["optimum_inputs"]


def test_constraint_conversion_enforced():
    r = run("min_lcoh", constraints={"min_nh3_conversion": 0.99}, variables=["reactor_temperature_C", "reactor_pressure_bar"],
            popsize=6, maxiter=12, flatness_points=0)
    assert r["optimum_metrics"]["nh3_conversion"] >= 0.99 - 1e-7


def test_bound_flag_for_conversion():
    r = run("max_conversion", variables=["reactor_temperature_C", "reactor_pressure_bar"], popsize=6, maxiter=10,
            flatness_points=0)
    # equilibrium conversion rises with T and falls with P: both bounds active, reported as such
    assert r["decision_variables"]["reactor_temperature_C"]["at_bound"] == "upper"
    assert r["decision_variables"]["reactor_pressure_bar"]["at_bound"] == "lower"
    assert r["bound_active"] and r["model_limitation"]


def test_non_dominated_simple():
    F = np.array([[1, 5], [2, 3], [3, 4], [4, 1], [2, 3]], float)
    assert non_dominated(F).tolist() == [True, True, False, True, True]


def test_pareto_front_non_dominated():
    g = {"reactor_temperature_C": [500.0, 600.0, 700.0], "reactor_pressure_bar": [10.0, 20.0, 40.0],
         "psa_h2_recovery": [0.75, 0.9], "fehe_hot_end_approach_K": [50.0]}
    rows = design_grid(g)
    assert len(rows) == 18
    pts = front(rows, ["lcoh_USD_per_kg", "carbon_intensity_kgCO2e_per_kgH2"], ["min", "min"])
    assert pts and all(p["feasible"] for p in pts)
    feas = [r for r in rows if r["feasible"]]
    for p in pts:
        for q in feas:
            dom = (q["lcoh_USD_per_kg"] <= p["lcoh_USD_per_kg"] and q["carbon_intensity_kgCO2e_per_kgH2"] <= p["carbon_intensity_kgCO2e_per_kgH2"]
                   and (q["lcoh_USD_per_kg"] < p["lcoh_USD_per_kg"] or q["carbon_intensity_kgCO2e_per_kgH2"] < p["carbon_intensity_kgCO2e_per_kgH2"]))
            assert not dom


def test_constraint_values_infeasible_model():
    g = constraint_values(None, {"fehe_min_internal_dT_K": 0, "min_nh3_conversion": 0.95})
    assert all(v < 0 for v in g.values())
