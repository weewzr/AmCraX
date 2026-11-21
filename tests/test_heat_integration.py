"""Tests for amcrax.heat_integration (problem table, composites, flowsheet analysis)."""
from __future__ import annotations

import json
import subprocess
import sys

import numpy as np
import pytest

from amcrax import paths
from amcrax.heat_integration import HeatIntegrationResult, analyse, composite, linear_curve, problem_table
from amcrax.schemas import CaseInputs, SimulationResult

C0 = 273.15


# ---------------------------------------------------------------- generic problem table
def four_stream():
    """Classic four-stream example (Linnhoff & Hindmarsh style; e.g. Kemp, Pinch Analysis and
    Process Integration, 2nd ed., ch. 2). Hand cascade at dT_min = 10 K (shifted T, degC):
    165-145: +60 | 145-140: +2.5 | 140-85: -82.5 | 85-55: +75 | 55-25: -15
    raw cascade 0, 60, 62.5, -20, 55, 40  ->  Qh = 20 kW, Qc = 60 kW, pinch shifted 85 (90 hot / 80 cold)."""
    K = lambda c: c + C0  # noqa: E731
    return [
        linear_curve("1", "cold", K(20), K(135), CP_kW_K=2.0),
        linear_curve("2", "hot", K(170), K(60), CP_kW_K=3.0),
        linear_curve("3", "cold", K(80), K(140), CP_kW_K=4.0),
        linear_curve("4", "hot", K(150), K(30), CP_kW_K=1.5),
    ]


def test_four_stream_textbook_targets():
    r = problem_table(four_stream(), 10.0)
    assert r.hot_utility_kW == pytest.approx(20.0, abs=1e-6)
    assert r.cold_utility_kW == pytest.approx(60.0, abs=1e-6)
    assert r.pinch_shifted_K - C0 == pytest.approx(85.0, abs=1e-6)
    assert r.pinch_hot_K - C0 == pytest.approx(90.0, abs=1e-6)
    assert r.pinch_cold_K - C0 == pytest.approx(80.0, abs=1e-6)
    assert not r.threshold


def test_two_stream_analytic():
    # hot 200->50 CP 1 (150 kW), cold 40->180 CP 1 (140 kW). Equal CPs: the hot-end constraint
    # (hot 200 must exceed cold 180 + ... by dT_min) binds; cold target 180 can be reached by heat
    # exchange only while 200 - dT >= 180, so Qh = max(0, dT - 20); Qc = Qh + (150 - 140).
    K = lambda c: c + C0  # noqa: E731
    s = [linear_curve("h", "hot", K(200), K(50), CP_kW_K=1.0), linear_curve("c", "cold", K(40), K(180), CP_kW_K=1.0)]
    for dT in (5.0, 10.0, 30.0, 40.0):
        r = problem_table(s, dT)
        qh_expect = max(0.0, dT - 20.0)
        assert r.hot_utility_kW == pytest.approx(qh_expect, abs=1e-6), dT
        assert r.cold_utility_kW == pytest.approx(qh_expect + 10.0, abs=1e-6), dT


def test_isothermal_duty_needs_hot_stream_above_it():
    K = lambda c: c + C0  # noqa: E731
    rxn = linear_curve("r", "cold", K(600), K(600), duty_kW=100.0)
    below = linear_curve("h", "hot", K(615), K(100), duty_kW=500.0)   # 615 < 600 + 20
    above = linear_curve("h", "hot", K(700), K(100), duty_kW=500.0)
    assert problem_table([rxn, below], 20.0).hot_utility_kW == pytest.approx(100.0, abs=1e-6)
    assert problem_table([rxn, above], 20.0).hot_utility_kW < 100.0


@pytest.mark.parametrize("dT", [1.0, 10.0, 26.0])
def test_problem_table_energy_conservation(dT):
    r = problem_table(four_stream(), dT)
    assert (r.hot_utility_kW - r.cold_utility_kW) == pytest.approx(r.total_cold_kW - r.total_hot_kW, abs=1e-9)
    assert np.all(r.cascade_kW >= -1e-9)


def test_dtmin_sensitivity_monotonic():
    qh = [problem_table(four_stream(), d).hot_utility_kW for d in np.linspace(0.5, 60, 40)]
    assert np.all(np.diff(qh) >= -1e-9)
    assert qh[-1] > qh[0]


def test_composite_monotonic():
    H, T = composite([c for c in four_stream() if c.kind == "hot"])
    assert np.all(np.diff(T) > 0) and np.all(np.diff(H) >= 0)
    assert H[-1] == pytest.approx(3.0 * 110 + 1.5 * 120)


# ---------------------------------------------------------------- flowsheet results
def _load_results() -> list[SimulationResult]:
    out = []
    p = paths.RESULTS_SIMULATIONS / "baseline.json"
    if p.exists():
        out.append(SimulationResult.model_validate_json(p.read_text(encoding="utf-8")))
    try:
        from amcrax.process_model import run_python_case
        out.append(run_python_case(CaseInputs(case_id="hi_test_python")))
    except Exception as exc:  # process model unavailable - fall back to whatever exists
        print("python process model not used:", exc)
    if not out:
        pytest.skip("no SimulationResult available (no Aspen baseline.json, no process model)")
    return out


RESULTS = None


def results():
    global RESULTS
    if RESULTS is None:
        RESULTS = [(r, analyse(r, 20.0)) for r in _load_results()]
    return RESULTS


def test_flowsheet_energy_balance_and_monotonic_composites():
    for res, h in results():
        for t in filter(None, (h.targets_process, h.targets_with_flue)):
            assert abs(t.energy_balance_residual_kW) < 1e-6 * max(1.0, t.total_cold_streams_kW)
            assert t.hot_utility_kW >= 0 and t.cold_utility_kW >= -1e-9
            for H, T in ((t.hot_composite_H_kW, t.hot_composite_T_C), (t.cold_composite_H_kW, t.cold_composite_T_C)):
                assert np.all(np.diff(T) > 0) and np.all(np.diff(H) >= -1e-9)
            assert min(t.gcc_H_kW) == pytest.approx(0.0, abs=1e-6)


def test_flowsheet_configuration_ordering_and_temperature_levels():
    for res, h in results():
        c = {r.id: r for r in h.configurations}
        assert c["a"].external_heating_kW >= c["b"].external_heating_kW >= c["d1"].external_heating_kW - 1e-6
        # reaction heat (isothermal at T_R) can only come from external heat or flue gas above T_R + dT_min
        rxn = next(s for s in h.streams if s.id == "REACTION").duty_kW
        assert c["d1"].external_heating_kW >= rxn - 1e-6
        if "d2" in c:
            assert c["d2"].external_heating_kW <= c["d1"].external_heating_kW + 1e-6
            assert c["d2"].external_heating_kW <= c["c"].external_heating_kW + 1e-6
            flue = next(s for s in h.streams if s.id == "FLUE")
            assert c["c"].tailgas_heat_used_kW <= flue.duty_kW + 1e-6


def test_flowsheet_dtmin_monotonic():
    res, _ = results()[0]
    qh = [analyse(res, d).targets_with_flue.hot_utility_kW for d in (5.0, 20.0, 50.0, 100.0)]
    assert np.all(np.diff(qh) >= -1e-6)


def test_fehe_assessment_and_model_consistency():
    for res, h in results():
        f = h.fehe
        assert f is not None and f.duty_kW > 0
        assert f.min_internal_approach_K <= min(f.hot_end_approach_K, f.cold_end_approach_K) + 1e-6
        if f.area_m2 is not None:
            assert f.area_range_m2[0] < f.area_m2 < f.area_range_m2[1]
        # independent hot-side curve vs simulated FEHE duty (reported deviation, generous bound)
        assert f.hot_side_duty_model_kW == pytest.approx(f.duty_kW, rel=0.05)


def test_result_json_roundtrip():
    _, h = results()[0]
    h2 = HeatIntegrationResult.model_validate_json(h.model_dump_json())
    assert h2.targets_process.hot_utility_kW == h.targets_process.hot_utility_kW
    json.loads(h.model_dump_json())


def test_script_runs(tmp_path):
    res, _ = results()[0]
    src = tmp_path / "r.json"
    src.write_text(res.model_dump_json(), encoding="utf-8")
    cp = subprocess.run([sys.executable, str(paths.ROOT / "scripts" / "run_heat_integration.py"), str(src),
                         "--out-dir", str(tmp_path)], capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr
    for name in ("heat_integration_{}.json", "hi_composite_{}.png", "hi_grand_composite_{}.png",
                 "hi_configuration_comparison_{}.png"):
        assert (tmp_path / name.format(res.case_id)).exists()
