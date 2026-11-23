"""Workstream A part 2: catalyst-specific RPLUG cases (no Aspen needed)."""
from __future__ import annotations

import importlib.util
import json
import math

import pytest

from amcrax.aspen.kinetic import (
    APPROXIMATION_PRESSURE_BAR,
    AspenLHHWSpec,
    KineticReactorInputs,
    build_kinetic_reactor_input,
    resolve_spec,
)
from amcrax.paths import ROOT

SPEC = ROOT / "results" / "research" / "kinetics" / "aspen_kinetics_spec.json"
needs_spec = pytest.mark.skipif(not SPEC.exists(), reason="kinetics workstream spec not present")


def _load(name):
    p = ROOT / "aspen" / "automation" / f"{name}.py"
    s = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


@needs_spec
@pytest.mark.parametrize("cat", ["ni_takahashi_microkinetic", "ru_takahashi_microkinetic"])
def test_approximation_spec_is_mole_fraction_lhhw(cat):
    e = {c["catalyst_id"]: c for c in json.loads(SPEC.read_text(encoding="utf-8"))["catalysts"]}[cat]
    s = resolve_spec(cat, "lhhw_approximation")
    assert isinstance(s, AspenLHHWSpec)
    assert s.cbasis == "MOLEFRAC"
    kf = e["best_native_approximation"]["kinetic_factor"]
    assert s.k_kmol_kgcat_s == pytest.approx(kf["k"])
    assert s.activation_energy_kJ_mol == pytest.approx(kf["E_J_per_mol"] / 1000.0)
    assert s.provenance.startswith("python")
    text = build_kinetic_reactor_input(KineticReactorInputs(
        catalyst_id=cat, kinetic_form="lhhw_approximation", temperature_C=500, pressure_bar=20,
        catalyst_mass_kg=100, n_tubes=50, feed_kmol_h={"NH3": 100.0}))
    assert "CBASIS=MOLEFRAC" in text and "REAC-CLASS=LHHW" in text and "PRES-UNIT" not in text


@needs_spec
def test_microkinetic_still_refused_without_approximation_form():
    with pytest.raises(ValueError):
        resolve_spec("ni_takahashi_microkinetic", "auto")


def test_approximation_only_at_its_pressure():
    with pytest.raises(ValueError):
        KineticReactorInputs(catalyst_id="ni_takahashi_microkinetic", kinetic_form="lhhw_approximation",
                             pressure_bar=APPROXIMATION_PRESSURE_BAR - 10, catalyst_mass_kg=10)


@needs_spec
def test_case_lists_respect_approximation_pressure(tmp_path, monkeypatch):
    m = _load("make_catalyst_study_cases")
    monkeypatch.setattr(m, "CASES", tmp_path)
    m.main()
    for name in ("catalyst_validation_cases", "catalyst_study_cases", "catalyst_integrated_cases"):
        cases = json.loads((tmp_path / f"{name}.json").read_text(encoding="utf-8"))
        assert len({c["case_id"] for c in cases}) == len(cases)
        for c in cases:
            KineticReactorInputs(**{k: v for k, v in c.items() if k not in ("configuration", "flowsheet")})
            if c["kinetic_form"] == "lhhw_approximation":
                assert c["pressure_bar"] == APPROXIMATION_PRESSURE_BAR
    rows = json.loads((ROOT / "results/research/kinetics/study_temperature_for_target_conversion.json")
                      .read_text(encoding="utf-8"))["rows"]
    t_op = m.operating_temperatures()
    for r in rows:
        if r["P_bar"] == 20.0 and r["W_cat_kg"] == 100.0 and r["X_target"] == 0.95:
            assert t_op[r["catalyst_id"]] == math.ceil(r["T_required_C"])


def test_log_interpolation_of_catalyst_mass():
    m = _load("summarise_catalyst_studies")
    w = m.interp_w_for_fraction([(10.0, 0.5), (100.0, 0.9), (1000.0, 1.0)], 0.95)
    assert w == pytest.approx(math.exp(math.log(100) + 0.5 * math.log(10)))
    assert m.interp_w_for_fraction([(10.0, 0.5), (100.0, 0.9)], 0.99) is None
