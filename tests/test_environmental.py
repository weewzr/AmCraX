"""Tests for amcrax.environmental (simplified carbon-intensity accounting, not an LCA)."""
from __future__ import annotations

import math

import pytest

from amcrax.environmental import (
    HEATING_OPTIONS, NH3_ROUTES, SYSTEM_BOUNDARY, carbon_intensity, compare_scenarios, load_factors,
    reference_lines,
)
from amcrax.schemas import KPIs, MOLAR_MASS, CaseInputs, DataSource, RunStatus, SimulationResult, StreamResult


def make_result(h2_kg_h=250.0, nh3_kmol_h=99.8, deficit_kW=800.0, pump_kW=2.0) -> SimulationResult:
    return SimulationResult(
        case_id="unit", source=DataSource.DEMO, inputs=CaseInputs(), status=RunStatus(converged=True),
        streams={"FEED": StreamResult(id="FEED", component_mole_flow_kmol_h={"NH3": nh3_kmol_h, "H2O": 0.2})},
        kpis=KPIs(h2_product_kg_h=h2_kg_h, net_fuel_heat_deficit_kW=deficit_kW, pump_power_kW=pump_kW),
    )


ZERO = dict(nh3_ef_kg_per_kg=0.0, grid_ef_kg_per_kWh=0.0, ship_ef_kg_per_tkm=0.0, ng_ef_kg_per_TJ=0.0)


def _sum(b):
    return b.upstream_ammonia + b.transport + b.electricity + b.external_heat


@pytest.mark.parametrize("route", NH3_ROUTES)
@pytest.mark.parametrize("heat", HEATING_OPTIONS)
def test_breakdown_sums_to_total(route, heat):
    r = carbon_intensity(make_result(), f"{route}/{heat}")
    assert math.isclose(_sum(r.breakdown_kgCO2e_per_kgH2), r.total_kgCO2e_per_kgH2, rel_tol=1e-12)
    assert r.total_kgCO2e_per_kgH2 >= 0


@pytest.mark.parametrize("heat", HEATING_OPTIONS)
def test_zero_emission_inputs_give_zero(heat):
    r = carbon_intensity(make_result(), "grey", heating=heat, **ZERO)
    assert r.total_kgCO2e_per_kgH2 == 0.0
    assert all(f.provenance == DataSource.ASSUMPTION for f in r.factors if f.note == "user override")


def test_upstream_scales_with_kg_nh3_per_kg_h2():
    a = carbon_intensity(make_result(h2_kg_h=250.0), "grey", heating="electric", grid_ef_kg_per_kWh=0.0)
    b = carbon_intensity(make_result(h2_kg_h=125.0), "grey", heating="electric", grid_ef_kg_per_kWh=0.0)
    assert math.isclose(b.kg_nh3_per_kg_h2, 2 * a.kg_nh3_per_kg_h2, rel_tol=1e-12)
    assert math.isclose(b.total_kgCO2e_per_kgH2, 2 * a.total_kgCO2e_per_kgH2, rel_tol=1e-12)
    # upstream term = kg NH3/kg H2 x factor (no self-firing, so all NH3 is feed)
    ef = load_factors()["upstream_ammonia"]["grey"]["value"]
    assert math.isclose(a.breakdown_kgCO2e_per_kgH2.upstream_ammonia, a.kg_nh3_per_kg_h2 * ef, rel_tol=1e-12)


def test_units_hand_calculation():
    res = make_result(h2_kg_h=200.0, nh3_kmol_h=100.0, deficit_kW=1000.0, pump_kW=10.0)
    r = carbon_intensity(res, "grey/natural_gas", nh3_ef_kg_per_kg=2.0, ship_ef_kg_per_tkm=0.01, distance_km=1000.0,
                         grid_ef_kg_per_kWh=0.5, ng_ef_kg_per_TJ=56100.0, fired_heater_efficiency=1.0)
    nh3 = 100.0 * MOLAR_MASS["NH3"]
    b = r.breakdown_kgCO2e_per_kgH2
    assert math.isclose(b.upstream_ammonia, nh3 * 2.0 / 200.0, rel_tol=1e-12)
    assert math.isclose(b.transport, nh3 / 1000.0 * 1000.0 * 0.01 / 200.0, rel_tol=1e-12)  # t x km x kg/(t km)
    assert math.isclose(b.electricity, 10.0 * 0.5 / 200.0, rel_tol=1e-12)                   # kW x 1 h x kg/kWh
    assert math.isclose(b.external_heat, 1000.0 * 3600.0 / 1e9 * 56100.0 / 200.0, rel_tol=1e-12)  # kJ/h -> TJ/h
    assert math.isclose(r.natural_gas_GJ_h, 3.6, rel_tol=1e-12)


def test_electric_heating_books_under_electricity():
    r = carbon_intensity(make_result(deficit_kW=500.0, pump_kW=0.0), "green/electric", grid_ef_kg_per_kWh=0.4)
    assert r.breakdown_kgCO2e_per_kgH2.external_heat == 0.0
    assert math.isclose(r.breakdown_kgCO2e_per_kgH2.electricity, 500.0 * 0.4 / 250.0, rel_tol=1e-12)


def test_self_firing_adds_nh3_and_no_direct_co2():
    res = make_result(deficit_kW=1000.0)
    r = carbon_intensity(res, "grey/self_firing", ship_ef_kg_per_tkm=0.0)
    assert r.nh3_fuel_kg_h > 0
    # extra NH3 x upstream factor only (transport zeroed)
    ef = load_factors()["upstream_ammonia"]["grey"]["value"]
    assert math.isclose(r.breakdown_kgCO2e_per_kgH2.external_heat, r.nh3_fuel_kg_h * ef / 250.0, rel_tol=1e-12)
    g = carbon_intensity(res, "green/self_firing", ship_ef_kg_per_tkm=0.0)
    assert g.breakdown_kgCO2e_per_kgH2.external_heat == 0.0


def test_no_deficit_means_no_heat_emissions():
    res = make_result(deficit_kW=-300.0)  # tail gas covers all heating
    for h in HEATING_OPTIONS:
        r = carbon_intensity(res, "grey", heating=h)
        assert r.heat_deficit_kW == 0.0
        assert r.breakdown_kgCO2e_per_kgH2.external_heat == 0.0


@pytest.mark.parametrize("heat", HEATING_OPTIONS)
def test_scenario_ordering_green_lt_blue_lt_grey(heat):
    cmp = compare_scenarios(make_result())
    t = {r.nh3_route: r.total_kgCO2e_per_kgH2 for r in cmp.rows if r.heating_option == heat}
    assert t["green"] < t["blue"] < t["grey"]
    assert len(cmp.rows) == len(NH3_ROUTES) * len(HEATING_OPTIONS)


def test_every_factor_sourced_or_labelled_assumption():
    f = load_factors()
    for sect in ("upstream_ammonia", "transport", "electricity"):
        for k, e in f[sect].items():
            assert e["provenance"] in ("literature", "assumption"), (sect, k)
            if e["provenance"] == "literature":
                assert e["source"]["citekey"] in f["references"] or e["source"]["citekey"].startswith("kum"), (sect, k)
            else:
                assert "ASSUMPTION" in e["note"], (sect, k)
    r = carbon_intensity(make_result(), "blue")
    assert r.system_boundary == SYSTEM_BOUNDARY and "NOT a life-cycle assessment" in r.method


def test_reference_lines():
    rl = {x.label: x.value_kgCO2e_per_kgH2 for x in reference_lines()}
    eu = [v for k, v in rl.items() if k.startswith("EU")][0]
    assert abs(eu - 3.38) < 0.01  # 94 g/MJ x 0.3 x 120 MJ/kg
    assert 4.0 in rl.values()


def test_bad_inputs():
    with pytest.raises(ValueError):
        carbon_intensity(make_result(), "purple")
    with pytest.raises(ValueError):
        carbon_intensity(make_result(), "grey/coal")
    with pytest.raises(ValueError):
        carbon_intensity(make_result(h2_kg_h=0.0), "grey")
    with pytest.raises(ValueError):
        carbon_intensity(make_result(), "grey", distance_km=-1.0)


def test_on_stored_baseline_if_present():
    from amcrax import paths
    p = paths.RESULTS_SIMULATIONS / "baseline.json"
    if not p.exists():
        p = paths.RESULTS_SIMULATIONS / "python_baseline.json"
    if not p.exists():
        pytest.skip("no stored baseline result")
    res = SimulationResult.model_validate_json(p.read_text(encoding="utf-8"))
    r = carbon_intensity(res, "grey/natural_gas")
    assert 6.0 < r.kg_nh3_per_kg_h2 < 8.0  # 99.8 kmol/h NH3 -> about 252 kg/h H2
    assert r.input_source == res.source
