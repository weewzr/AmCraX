"""Tests for amcrax.environmental.lca (workstream U)."""
from __future__ import annotations

import pytest

from amcrax.environmental import lca


def test_blue_reproduces_lee():
    assert lca.blue_nh3_ef(1, 0) == pytest.approx(1.16, abs=1e-9)
    assert lca.blue_nh3_ef(1, 1) == pytest.approx(0.77, abs=1e-9)
    assert lca.blue_nh3_ef(0, 0) == pytest.approx(2.60, abs=1e-9)


def test_capture_and_leak_monotonic():
    assert lca.blue_nh3_ef(0.9) > lca.blue_nh3_ef(1.0)
    assert lca.blue_nh3_ef(1.0, 0, 0.03) > lca.blue_nh3_ef(1.0, 0, 0.0)


def test_bad_parameters():
    with pytest.raises(ValueError):
        lca.blue_nh3_ef(1.2)
    with pytest.raises(ValueError):
        lca.delivered_nh3_ef(1.0, 1000.0, boil_off=1.0)


def test_shipping_and_boil_off():
    assert lca.ship_kg_per_kg_nh3(5000.0) == pytest.approx(0.055)
    assert lca.delivered_nh3_ef(1.0, 0.0, boil_off=0.1) == pytest.approx(1.0 / 0.9)


def test_ccgt_and_leakage():
    base = lca.ccgt_ci_kg_per_MWh()
    assert base == pytest.approx(3.6 / 0.55 * 56.1, rel=1e-9)
    assert lca.ccgt_ci_kg_per_MWh(leak_frac=0.015) > base


def test_n2o_nox_separate():
    d = lca.n2o_noX_per_MWh()
    assert d["N2O_kgCO2e_per_MWh"] == pytest.approx(d["N2O_kg_per_MWh"] * 273.0)
    assert d["NO_kg_per_MWh"] > d["N2O_kg_per_MWh"]


def test_every_factor_has_source():
    for k, v in lca.FACTORS.items():
        assert v["source"] and v["source_type"] in ("literature", "assumption"), k


def test_green_range_ordering():
    assert lca.green_nh3_ef("low") < lca.green_nh3_ef("mid") < lca.green_nh3_ef("high")
    assert lca.green_nh3_ef("lee") == 0.0
