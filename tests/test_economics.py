"""Tests for amcrax.economics (LCOH)."""
from __future__ import annotations

import math

import pytest

from amcrax import paths
from amcrax.economics import (
    CATEGORIES,
    STOICHIOMETRIC_KG_NH3_PER_KG_H2,
    EconomicAssumptions,
    breakeven_ammonia_price,
    compute_lcoh,
    crf,
    lcoh_sensitivity,
    literature_benchmarks,
    load_economics_data,
)
from amcrax.schemas import KPIs, BlockResult, CaseInputs, DataSource, RunStatus, SimulationResult, StreamResult


def _synthetic(deficit_kW: float = 800.0) -> SimulationResult:
    """Hand-made result (round numbers) so every cost can be checked by hand."""
    return SimulationResult(
        case_id="synthetic", source=DataSource.DEMO, inputs=CaseInputs(), status=RunStatus(converged=True),
        streams={"FEED": StreamResult(id="FEED", mass_flow_kg_h=1700.0, component_mole_flow_kmol_h={"NH3": 99.8})},
        blocks={"PUMP": BlockResult(id="PUMP", power_kW=2.0)},
        kpis=KPIs(h2_product_kg_h=250.0, net_fuel_heat_deficit_kW=deficit_kW, cooling_duty_kW=300.0, pump_power_kW=2.0),
    )


@pytest.fixture(scope="module")
def baseline() -> SimulationResult:
    for name in ("baseline.json", "python_baseline.json"):
        p = paths.RESULTS_SIMULATIONS / name
        if p.exists():
            return SimulationResult.model_validate_json(p.read_text(encoding="utf-8"))
    return _synthetic()


def _zero_opex(**kw) -> EconomicAssumptions:
    base = dict(nh3_price_USD_per_t=0.0, electricity_price_USD_per_kWh=0.0, fired_heat_price_USD_per_kJ=0.0,
                heat_import_mode="fired_heat", cooling_water_price_USD_per_kJ=0.0, catalyst_price_USD_per_kg=0.0,
                maintenance_frac_capex_per_yr=0.0, insurance_frac_capex_per_yr=0.0, labour_USD_per_yr=0.0)
    base.update(kw)
    return EconomicAssumptions(**base)


# --------------------------------------------------------------------------------------------- CRF
def test_crf_hand_calculation():
    # i = 10 %, n = 25 yr: 1.1^25 = 10.834705943; CRF = 0.1*10.8347/(9.8347) = 0.1101681
    assert crf(0.10, 25) == pytest.approx(0.1101681, rel=1e-6)
    # i = 8.5 %, n = 25: ln(1.085)*25 = 2.03950 -> 1.085^25 = 7.68657; CRF = 0.085*7.68657/6.68657 = 0.0977117
    assert crf(0.085, 25) == pytest.approx(0.085 * 1.085 ** 25 / (1.085 ** 25 - 1), rel=1e-12)
    assert crf(0.085, 25) == pytest.approx(0.0977117, rel=1e-5)
    assert crf(0.0, 20) == pytest.approx(1 / 20)
    assert crf(1e-9, 20) == pytest.approx(1 / 20, rel=1e-6)


# --------------------------------------------------------------------------------------------- structure
def test_breakdown_sums_to_total(baseline):
    r = compute_lcoh(baseline)
    assert set(r.breakdown_USD_per_kg) == set(CATEGORIES)
    assert sum(r.breakdown_USD_per_kg.values()) == pytest.approx(r.lcoh_USD_per_kg, rel=1e-12)
    assert r.annual_costs_USD_per_yr["total"] / r.annual_h2_kg == pytest.approx(r.lcoh_USD_per_kg, rel=1e-12)
    fx = sum(v for k, v in r.annual_costs_USD_per_yr.items() if k.startswith("fixed_opex."))
    assert fx == pytest.approx(r.annual_costs_USD_per_yr["fixed_opex"], rel=1e-12)
    assert all(v >= 0 for v in r.breakdown_USD_per_kg.values())
    assert r.source == DataSource.PYTHON and r.input_source == baseline.source


@pytest.mark.parametrize("mode", ["fired_heat", "ammonia_fuel"])
def test_linear_in_ammonia_price_with_slope_kg_nh3_per_kg_h2(baseline, mode):
    a = EconomicAssumptions(heat_import_mode=mode)
    prices = [0.0, 300.0, 450.0, 1000.0]
    l = [compute_lcoh(baseline, a.model_copy(update={"nh3_price_USD_per_t": p})).lcoh_USD_per_kg for p in prices]
    r = compute_lcoh(baseline, a)
    kg_per_kg = r.kg_nh3_feed_per_kg_h2 + (r.kg_nh3_fuel_per_kg_h2 if mode == "ammonia_fuel" else 0.0)
    for p, li in zip(prices, l):
        assert li == pytest.approx(l[0] + kg_per_kg * p / 1000.0, rel=1e-10)
    if mode == "fired_heat":
        # the feed is priced on its contained NH3 (kmol/h x 17.0305 kg/kmol), not on the whole feed stream:
        # the 0.2 mol% water in commercial ammonia is not paid for at the ammonia price
        feed_nh3 = baseline.streams["FEED"].component_mole_flow_kmol_h["NH3"] * 17.0305
        assert feed_nh3 < baseline.streams["FEED"].mass_flow_kg_h
        assert r.kg_nh3_fuel_per_kg_h2 == 0.0
        assert (l[-1] - l[0]) / 1.0 == pytest.approx(feed_nh3 / baseline.kpis.h2_product_kg_h, rel=1e-10)


def test_stoichiometric_floor():
    assert STOICHIOMETRIC_KG_NH3_PER_KG_H2 == pytest.approx(5.632, abs=1e-3)
    r = compute_lcoh(_synthetic())
    assert r.kg_nh3_feed_per_kg_h2 >= r.stoichiometric_floor_kg_nh3_per_kg_h2


# --------------------------------------------------------------------------------------------- limits
def test_zero_capex_limit():
    res = _synthetic()
    a = EconomicAssumptions(capex_method="fixed", capex_fixed_USD=0.0)
    r = compute_lcoh(res, a)
    assert r.breakdown_USD_per_kg["capex"] == 0.0
    assert r.annual_costs_USD_per_yr["fixed_opex.maintenance"] == 0.0
    assert r.annual_costs_USD_per_yr["fixed_opex.insurance"] == 0.0
    exp_fixed = a.labour_USD_per_yr * (1 + a.plant_overhead_frac_labour_maint) * (1 + a.g_and_a_frac_fixed_opex)
    assert r.annual_costs_USD_per_yr["fixed_opex"] == pytest.approx(exp_fixed, rel=1e-12)


def test_zero_opex_limit():
    res = _synthetic()
    a = _zero_opex(capex_method="fixed", capex_fixed_USD=10e6)
    r = compute_lcoh(res, a)
    expected = 10e6 * crf(a.discount_rate, a.plant_life_yr) / (250.0 * a.operating_hours_h_per_yr)
    assert r.lcoh_USD_per_kg == pytest.approx(expected, rel=1e-12)
    assert r.lcoh_USD_per_kg == pytest.approx(r.breakdown_USD_per_kg["capex"], rel=1e-12)


def test_zero_everything_is_zero():
    r = compute_lcoh(_synthetic(), _zero_opex(capex_method="fixed", capex_fixed_USD=0.0))
    assert r.lcoh_USD_per_kg == 0.0


# --------------------------------------------------------------------------------------------- units
def test_unit_consistency_by_hand():
    res = _synthetic(deficit_kW=800.0)
    a = EconomicAssumptions(heat_import_mode="fired_heat")
    r = compute_lcoh(res, a)
    h = a.operating_hours_h_per_yr
    ann = r.annual_costs_USD_per_yr
    # contained NH3 only: 99.8 kmol/h * 17.0305 kg/kmol (the synthetic 1700 kg/h feed stream also carries water)
    assert ann["ammonia_feed"] == pytest.approx(99.8 * 17.0305 * a.nh3_price_USD_per_t / 1000 * h)   # kg/h * USD/kg * h
    assert ann["electricity"] == pytest.approx(2.0 * a.electricity_price_USD_per_kWh * h)            # kW * USD/kWh * h
    assert ann["cooling_water"] == pytest.approx(300.0 * 3600 * a.cooling_water_price_USD_per_kJ * h)  # kJ/s*s/h*USD/kJ*h
    assert ann["imported_heat"] == pytest.approx(800.0 * 3600 * a.fired_heat_price_USD_per_kJ * h)
    # catalyst: 99.8 kmol/h * 22.414 L/mol -> mL/h, / (mL/(g h)) -> g
    m = 99.8e3 * a.normal_molar_volume_L_per_mol * 1e3 / a.catalyst_space_velocity_mL_NH3_per_gcat_h / 1e3
    assert ann["catalyst"] == pytest.approx(m * a.resolved_catalyst_price_USD_per_kg() / a.catalyst_lifetime_yr)
    # ammonia fuel: kW / (kJ/mol) = mol/s
    r2 = compute_lcoh(res, EconomicAssumptions(heat_import_mode="ammonia_fuel"))
    assert r2.kg_nh3_fuel_per_kg_h2 * 250.0 == pytest.approx(800.0 / 316.80 * 3600 * 17.0305 / 1000, rel=1e-9)
    # CAPEX per kg scales with 1/hours; total CAPEX does not
    r3 = compute_lcoh(res, a.model_copy(update={"operating_hours_h_per_yr": h / 2}))
    assert r3.breakdown_USD_per_kg["capex"] == pytest.approx(2 * r.breakdown_USD_per_kg["capex"])
    assert r3.capex.total_capex_USD == pytest.approx(r.capex.total_capex_USD)


def test_heat_surplus_not_credited_unless_enabled():
    res = _synthetic(deficit_kW=-200.0)
    r = compute_lcoh(res)
    assert r.breakdown_USD_per_kg["imported_heat"] == 0.0 and r.kg_nh3_fuel_per_kg_h2 == 0.0
    r2 = compute_lcoh(res, EconomicAssumptions(credit_heat_surplus=True))
    assert r2.breakdown_USD_per_kg["imported_heat"] < 0.0


def test_missing_kpi_raises():
    res = _synthetic()
    res.kpis.net_fuel_heat_deficit_kW = None
    with pytest.raises(ValueError):
        compute_lcoh(res)


# --------------------------------------------------------------------------------------------- CAPEX
def test_capex_capacity_exponent_rule():
    a = EconomicAssumptions()
    r1 = compute_lcoh(_synthetic(), a)
    res2 = _synthetic()
    res2.kpis.h2_product_kg_h = 500.0
    r2 = compute_lcoh(res2, a)
    assert r2.capex.total_capex_USD / r1.capex.total_capex_USD == pytest.approx(2 ** 0.7451, rel=1e-9)
    # ahmad2025gtcc correlation at 0.25 t/h: 18.171 * 0.25^0.7451 MUSD
    assert r1.capex.total_capex_USD == pytest.approx(18.171e6 * 0.25 ** 0.7451, rel=1e-9)
    assert "class 4-5" in r1.capex.estimate_class and "NOT a detailed" in r1.capex.estimate_class
    assert sum(r1.capex.equipment_breakdown_USD.values()) == pytest.approx(r1.capex.total_capex_USD)
    assert {x.method for x in r1.capex.alternatives} == {"chopra2026_point", "farokhi2025_point"}


# --------------------------------------------------------------------------------------------- helpers
def test_breakeven_and_tornado(baseline):
    a = EconomicAssumptions()
    p = breakeven_ammonia_price(baseline, a, 5.0)
    assert p is not None and p > 0
    assert compute_lcoh(baseline, a.model_copy(update={"nh3_price_USD_per_t": p})).lcoh_USD_per_kg == pytest.approx(5.0)
    assert breakeven_ammonia_price(baseline, a, 0.01) is None
    bars = lcoh_sensitivity(baseline, a)
    assert bars[0].parameter == "nh3_price_USD_per_t"
    assert all(b.swing >= bars[i + 1].swing for i, b in enumerate(bars[:-1]))


# --------------------------------------------------------------------------------------------- provenance
def test_every_default_is_sourced_or_labelled():
    d = load_economics_data()["defaults"]
    for name, e in d.items():
        entries = [e[k] for k in ("Ni", "Ru")] if name == "catalyst_price_USD_per_kg" else [e]
        for x in entries:
            assert x["source"] in ("literature", "assumption"), name
            if x["source"] == "literature":
                assert x.get("citekey") and x.get("page") is not None and x.get("locator"), name
            else:
                assert x.get("rationale"), name


def test_citekeys_exist_in_references():
    import json
    refs = json.loads((paths.RESEARCH_DIR / "references.json").read_text(encoding="utf-8"))
    keys = {r.get("citekey") or r.get("id") for r in (refs if isinstance(refs, list) else refs.get("references", []))}
    d = load_economics_data()
    used = {e["citekey"] for e in d["defaults"].values() if isinstance(e, dict) and e.get("citekey")}
    used |= {b["citekey"] for b in d["literature_lcoh"]}
    used |= {v["citekey"] for v in d["capex_references"].values()}
    assert used <= keys, used - keys


def test_provenance_echoed(baseline):
    r = compute_lcoh(baseline, EconomicAssumptions(nh3_price_USD_per_t=777.0))
    assert r.provenance["nh3_price_USD_per_t"].source == DataSource.ASSUMPTION    # caller override
    r0 = compute_lcoh(baseline)
    assert r0.provenance["nh3_price_USD_per_t"].source == DataSource.LITERATURE
    assert r0.provenance["nh3_price_USD_per_t"].citekey == "cho2026nickel"
    assert r0.provenance["psa_h2_recovery"].source == DataSource.ASSUMPTION
    assert r0.provenance["process_data"].source == baseline.source


# --------------------------------------------------------------------------------------------- sanity (report only)
def test_sanity_vs_library_tea(baseline, capsys):
    """Report AmCraX LCOH next to the library TEA values at comparable NH3 prices. Not tuned, not forced: the
    assertion only checks the order of magnitude (same decade)."""
    bench = [b for b in literature_benchmarks() if b.get("nh3_price_USD_per_t") and b["unit"] == "USD/kg"]
    lines = []
    for b in bench:
        r = compute_lcoh(baseline, EconomicAssumptions(nh3_price_USD_per_t=b["nh3_price_USD_per_t"]))
        lines.append(f"NH3 {b['nh3_price_USD_per_t']:>5} USD/t: AmCraX {r.lcoh_USD_per_kg:5.2f} vs "
                     f"{b['label']} {b['value']:5.2f} USD/kg ({b['citekey']} p.{b['page']}) "
                     f"ratio {r.lcoh_USD_per_kg / b['value']:.2f}")
        assert 0.1 < r.lcoh_USD_per_kg / b["value"] < 10
    with capsys.disabled():
        print("\n[economics sanity, report only]\n  " + "\n  ".join(lines))
    assert math.isfinite(compute_lcoh(baseline).lcoh_USD_per_kg)
