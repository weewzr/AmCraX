"""Tests for amcrax.separation (reduced-order PSA / membrane / NH3 slip / compression models)."""
from __future__ import annotations

import math

import pytest

from amcrax import paths
from amcrax.schemas import SimulationResult
from amcrax.separation import (MODEL_LABEL, ammonia_slip, compare_purification, compression_power_kW,
                               default_stages, membrane_separator, params, permeance, psa_performance,
                               sieverts_flux)

# Cracked gas of the Aspen baseline (S7, 600 degC / 20 bar case), kmol/h - test input only
FEED = {"NH3": 1.91512572, "H2": 146.827311, "N2": 48.9424371, "H2O": 0.2}


def _close_h2(feed, a, b):
    return feed["H2"] - (a.get("H2", 0.0) + b.get("H2", 0.0))


def test_parameters_have_sources():
    P = params()
    for p in P["psa"]["operating_points"]:
        assert p["citekey"] and p["page"] and p["locator"]
    for s in P["membrane"]["permeability_sets"]:
        assert s["citekey"] and s["page"]
    assert P["ammonia_slip"]["fuel_cell_limit_ppm"]["value"] == 0.1
    assert P["psa"]["amcrax_baseline"]["source"] == "assumption"


@pytest.mark.parametrize("basis", ["cho2026_5A", "hansen2024_cha_AC", "kum2026_lumped", "hansen2024_lee", "amcrax_baseline"])
def test_psa_balances_and_bounds(basis):
    r = psa_performance(FEED, 19.5, basis=basis)
    assert r.model == MODEL_LABEL
    for k in FEED:
        assert FEED[k] == pytest.approx(r.product_kmol_h.get(k, 0.0) + r.tailgas_kmol_h.get(k, 0.0), abs=1e-10)
    assert abs(_close_h2(FEED, r.product_kmol_h, r.tailgas_kmol_h)) < 1e-10
    assert 0 <= r.h2_recovery <= 1
    assert 0 < r.h2_purity_mole_frac <= 1
    assert r.compression_power_kW == 0.0  # 19.5 bar is above every requirement


def test_psa_reproduces_literature_point():
    r = psa_performance(FEED, 19.5, basis="cho2026_5A")
    assert r.h2_recovery == 0.756
    assert r.h2_purity_mole_frac == pytest.approx(0.9911, abs=1e-12)
    assert r.required_feed_pressure_bar == 7.0


def test_psa_compression_when_below_requirement():
    r = psa_performance(FEED, 2.0, basis="cho2026_5A")
    assert r.compression_power_kW > 0
    assert r.compression_stages == default_stages(2.0, 7.0) == 1  # 3.5 = max stage ratio
    assert r.specific_energy_kWh_per_kgH2 > 0


def test_compression_single_stage_hand_calc():
    # ideal gas, constant cp 29.1 J/mol/K, 100 kmol/h, 300 K, 1 -> 5 bar, eta 1:
    # T2s = 300 * 5**(8.314462618/29.1) ; W = (100/3.6 mol/s) * 29.1 * (T2s - 300) / 1000 kW
    R = 8.314462618
    T2s = 300.0 * 5.0 ** (R / 29.1)
    W = (100.0 / 3.6) * 29.1 * (T2s - 300.0) / 1000.0
    assert W == pytest.approx(141.58, abs=0.05)  # hand value
    r = compression_power_kW(100.0, {"N2": 1.0}, 300.0, 1.0, 5.0, stages=1, eta=1.0, cp_J_molK=29.1)
    assert r["power_kW"] == pytest.approx(W, rel=1e-9)
    r75 = compression_power_kW(100.0, {"N2": 1.0}, 300.0, 1.0, 5.0, stages=1, eta=0.75, cp_J_molK=29.1)
    assert r75["power_kW"] == pytest.approx(W / 0.75, rel=1e-9)
    # NASA-7 cp(T) for N2 near 300-480 K is ~29.1-29.4 J/mol/K -> within 1 %
    rT = compression_power_kW(100.0, {"N2": 1.0}, 300.0, 1.0, 5.0, stages=1, eta=1.0)
    assert rT["power_kW"] == pytest.approx(W, rel=0.01)


def test_compression_intercooling_reduces_power():
    w1 = compression_power_kW(100.0, FEED, 313.15, 2.0, 20.0, stages=1, eta=0.75)["power_kW"]
    w3 = compression_power_kW(100.0, FEED, 313.15, 2.0, 20.0, stages=3, eta=0.75)["power_kW"]
    assert 0 < w3 < w1
    assert compression_power_kW(100.0, FEED, 313.15, 20.0, 10.0)["power_kW"] == 0.0


def test_flux_zero_at_equal_partial_pressure():
    k = permeance(673.15)
    assert sieverts_flux(1e5, 1e5, k) == 0.0
    assert sieverts_flux(5e5, 1e5, k) > 0
    assert sieverts_flux(1e5, 5e5, k) == 0.0  # no back-permeation
    # pure H2 feed at the permeate pressure: nothing permeates
    m = membrane_separator({"H2": 10.0, "N2": 0.0}, 50.0, 1.0, 1.0)
    assert m.h2_recovery == pytest.approx(0.0, abs=1e-12)


def test_flux_matches_formula():
    s = next(p for p in params()["membrane"]["permeability_sets"] if p["id"] == "richard_ref53")
    T = 673.15
    k = s["Pe0_mol_m_s_Pa05"] * math.exp(-s["Ea_kJ_mol"] * 1000 / (8.314462618 * T)) / (s["thickness_um"] * 1e-6)
    assert permeance(T) == pytest.approx(k, rel=1e-6)
    assert sieverts_flux(1.0e6, 1.0e5, k) == pytest.approx(k * (1e3 - 1e5 ** 0.5), rel=1e-12)


def test_unusable_permeability_rejected():
    with pytest.raises(ValueError):
        permeance(673.15, "richard_ref52")


def test_membrane_balance_and_profile():
    m = membrane_separator(FEED, 40.0, 19.5, 1.0)
    assert m.model == MODEL_LABEL
    assert abs(_close_h2(FEED, m.permeate_kmol_h, m.retentate_kmol_h)) < 1e-9
    for k in ("NH3", "N2", "H2O"):
        assert m.retentate_kmol_h[k] == FEED[k]
    assert 0 <= m.h2_recovery <= m.max_recovery_at_pinch <= 1
    rec = [p.recovery for p in m.profile]
    assert all(b >= a - 1e-12 for a, b in zip(rec, rec[1:]))
    # retentate H2 partial pressure never drops below the permeate pressure
    assert min(p.y_h2_retentate for p in m.profile) * 19.5 >= 1.0 - 1e-6


def test_membrane_monotonic_in_area_and_pressure_ratio():
    areas = [0, 5, 10, 20, 40, 80, 160]
    r = [membrane_separator(FEED, a, 19.5, 1.0, n_profile=2).h2_recovery for a in areas]
    assert r[0] == 0.0
    assert all(b > a for a, b in zip(r, r[1:]))
    assert all(0 <= x <= 1 for x in r)
    rp = [membrane_separator(FEED, 30.0, pf, 1.0, n_profile=2).h2_recovery for pf in (3, 5, 10, 20, 30)]
    assert all(b > a for a, b in zip(rp, rp[1:]))
    rq = [membrane_separator(FEED, 30.0, 19.5, pp, n_profile=2).h2_recovery for pp in (4.0, 2.0, 1.0, 0.5)]
    assert all(b > a for a, b in zip(rq, rq[1:]))
    # approaches the pinch limit for very large area
    big = membrane_separator(FEED, 5000.0, 19.5, 1.0, n_profile=2)
    assert big.h2_recovery == pytest.approx(big.max_recovery_at_pinch, abs=1e-3)


def test_membrane_temperature_window_flag():
    assert membrane_separator(FEED, 10.0, 19.5, 1.0, T_K=873.15).in_pd_window is False
    assert membrane_separator(FEED, 10.0, 19.5, 1.0).in_pd_window is True


def test_ammonia_slip_requirement():
    s = ammonia_slip(FEED)
    assert s.limit_ppm == 0.1
    assert s.nh3_cracked_gas_ppm == pytest.approx(1e6 * FEED["NH3"] / sum(FEED.values()))
    allowed = 0.1e-6 * FEED["H2"]
    assert s.required_nh3_removal_factor == pytest.approx(1 - allowed / FEED["NH3"])
    assert not s.meets_limit_without_removal
    assert ammonia_slip({"H2": 10.0, "N2": 3.0}).required_nh3_removal_factor == 0.0


@pytest.mark.skipif(not (paths.RESULTS_SIMULATIONS / "baseline.json").exists(), reason="no baseline result")
def test_compare_on_baseline_result():
    res = SimulationResult.model_validate_json((paths.RESULTS_SIMULATIONS / "baseline.json").read_text(encoding="utf-8"))
    c = compare_purification(res)
    assert c.model == MODEL_LABEL
    assert any(r.option.startswith("PSA") for r in c.rows) and any("membrane" in r.option for r in c.rows)
    for r in c.rows:
        assert 0 <= r.h2_recovery <= 1
        assert r.h2_loss_fraction == pytest.approx(1 - r.h2_recovery, abs=1e-9)
