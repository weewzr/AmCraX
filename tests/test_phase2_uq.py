"""Phase 2 task U1: uncertainty quantification (amcrax.uq). Deterministic, no network, no Aspen."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from amcrax.kinetics import rate_laws
from amcrax.reactor import pfr
from amcrax.uq import SEED
from amcrax.uq.kinetic_hook import kinetic_overrides, simulate_with
from amcrax.uq.mcmc import adaptive_metropolis, ess_bulk, rhat
from amcrax.uq.sobol import ab_matrix, indices_from_outputs, ishigami, ishigami_analytic, sobol_base

ROOT = Path(__file__).resolve().parents[1]
UQ = ROOT / "results" / "research" / "uq"


# ------------------------------------------------------------------ Sobol estimators
def test_ishigami_analytic_values_match_published_table():
    # S1 = 0.3139, 0.4424, 0 (Marrel et al. 2009; OpenTURNS Ishigami use case); ST from the same closed form
    an = ishigami_analytic()
    assert an["S"] == pytest.approx([0.3139, 0.4424, 0.0], abs=5e-5)
    assert an["ST"] == pytest.approx([0.5576, 0.4424, 0.2437], abs=5e-5)


def test_ishigami_estimator_within_002():
    A, B = sobol_base(2 ** 13, 3, SEED)
    to = lambda U: -math.pi + 2 * math.pi * U  # noqa: E731
    fA, fB = ishigami(to(A)), ishigami(to(B))
    fAB = np.stack([ishigami(to(ab_matrix(A, B, [i]))) for i in range(3)])
    S, ST, _ = indices_from_outputs(fA, fB, fAB)
    an = ishigami_analytic()
    assert np.max(np.abs(S - an["S"])) < 0.02
    assert np.max(np.abs(ST - an["ST"])) < 0.02


def test_linear_additive_within_001():
    c = np.array([1.0, 2.0, 3.0, 4.0])
    A, B = sobol_base(2 ** 13, 4, SEED)
    fAB = np.stack([ab_matrix(A, B, [i]) @ c for i in range(4)])
    S, ST, _ = indices_from_outputs(A @ c, B @ c, fAB)
    ref = c ** 2 / np.sum(c ** 2)
    assert np.max(np.abs(S - ref)) < 0.01 and np.max(np.abs(ST - ref)) < 0.01


def test_sobol_base_deterministic_and_power_of_two():
    a1, b1 = sobol_base(256, 2, SEED)
    a2, b2 = sobol_base(256, 2, SEED)
    assert np.array_equal(a1, a2) and np.array_equal(b1, b2)
    with pytest.raises(ValueError):
        sobol_base(100, 2, SEED)


# ------------------------------------------------------------------ MCMC
def test_adaptive_metropolis_2d_gaussian():
    mean = np.array([1.0, -2.0])
    cov = np.array([[1.0, 0.6], [0.6, 2.0]])
    P = np.linalg.inv(cov)
    logp = lambda x: -0.5 * (x - mean) @ P @ (x - mean)  # noqa: E731
    rng = np.random.default_rng(SEED)
    chains = [adaptive_metropolis(logp, c.normal(0, 3, 2), 30000, c)["chain"][5000:] for c in rng.spawn(4)]
    flat = np.vstack(chains)
    assert np.allclose(flat.mean(axis=0), mean, atol=0.05 * np.sqrt(np.diag(cov)).max())
    assert np.allclose(np.cov(flat.T), cov, rtol=0.05, atol=0.05)
    C = np.stack(chains)
    assert rhat(C[:, :, 0]) < 1.01 and ess_bulk(C[:, :, 0]) > 400


def test_rhat_detects_non_mixing():
    rng = np.random.default_rng(SEED)
    C = np.stack([rng.normal(m, 1, 2000) for m in (0, 0, 0, 3)])
    assert rhat(C) > 1.1


# ------------------------------------------------------------------ kinetic hook
def test_param_overrides_none_is_bit_identical():
    p = {"NH3": 0.6, "H2": 0.3, "N2": 0.1}
    for cid in ("ni_takahashi_microkinetic", "ru_takahashi_microkinetic", "nire_ceo2_5ni1ru_lucentini_lhhw", "ru_kum_temkin_pyzhev"):
        a = rate_laws.rate_mol_per_kgcat_s(cid, 773.15, p)
        b = rate_laws.rate_mol_per_kgcat_s(cid, 773.15, p, param_overrides=None)
        c = rate_laws.rate_mol_per_kgcat_s(cid, 773.15, p, param_overrides={})
        assert a == b == c


def test_param_overrides_changes_rate_and_registry_unchanged():
    before = rate_laws._p("nire_ceo2_5ni1ru_lucentini_lhhw")
    p = {"NH3": 0.9, "H2": 0.05, "N2": 0.05}
    r0 = rate_laws.rate_mol_per_kgcat_s("nire_ceo2_5ni1ru_lucentini_lhhw", 773.15, p)
    r1 = rate_laws.rate_mol_per_kgcat_s("nire_ceo2_5ni1ru_lucentini_lhhw", 773.15, p, param_overrides={"k0": 2 * before["k0"]})
    assert r1 == pytest.approx(2 * r0, rel=1e-12)
    assert rate_laws._p("nire_ceo2_5ni1ru_lucentini_lhhw") == before


def test_hook_nominal_reproduces_validation_file_and_restores():
    d = json.loads((ROOT / "results/research/kinetics/validation_5Ni1Ru_CeO2.json").read_text(encoding="utf-8"))
    n = 25.0 * 1e-3 * 60.0 / 22.414 / 1000.0
    feed = {"NH3": n / 2.2, "Ar": n * 1.2 / 2.2}
    nom = rate_laws._p("nire_ceo2_5ni1ru_lucentini_lhhw")
    orig = pfr.rate_mol_per_kgcat_s
    for pt in d["points"]:
        x = simulate_with("nire_ceo2_5ni1ru_lucentini_lhhw", {k: nom[k] for k in ("k0", "Ek", "K1", "K4")}, 1e-4,
                          T_in_C=float(pt["T_C"]), P_in_bar=1.01325, feed_kmol_h=feed, mode="isothermal", pressure_drop=False,
                          n_points=3).outlet["conversion"]
        assert x == pytest.approx(pt["X_python"], abs=1e-9)
    assert pfr.rate_mol_per_kgcat_s is orig
    with pytest.raises(RuntimeError):
        with kinetic_overrides("nire_ceo2_5ni1ru_lucentini_lhhw", {"k0": 1.0}):
            raise RuntimeError("x")
    assert pfr.rate_mol_per_kgcat_s is orig


def test_singapore_evaluate_default_unchanged():
    from amcrax.economics.singapore import evaluate, extract_summary
    s = extract_summary(json.loads((ROOT / "results/simulations/baseline.json").read_text(encoding="utf-8")))
    assert evaluate(s, "grey")["lcoh_USD_per_kg"] == pytest.approx(4.015, abs=5e-4)


# ------------------------------------------------------------------ stored outputs
def _load(name):
    p = UQ / name
    if not p.exists():
        pytest.skip(f"{name} not generated")
    return json.loads(p.read_text(encoding="utf-8"))


def test_gsa_outputs_labelled_and_consistent():
    d = _load("gsa_sobol.json")
    assert d["analysis_kind"] == "global_sensitivity" and "Not experimental validation" in d["label"]
    assert "reference_scenario" in d["provenance"]
    for key, cs in d["cases"].items():
        ix = cs["outputs"]["lcoh_USD_per_kg"]["indices"]
        assert sum(v["S1"] for v in ix.values()) <= 1.05
        assert all(v["ST"] >= v["S1"] - 0.02 for v in ix.values())
    g = d["cases"]["grey|heat_integration_on"]["outputs"]["lcoh_USD_per_kg"]
    assert max(g["indices"], key=lambda k: g["indices"][k]["ST"]) == "nh3_price_USD_per_t"


def test_validation_file_evidence_kinds():
    p = ROOT / "results/research/validation/uq.json"
    if not p.exists():
        pytest.skip("uq.json not generated")
    d = json.loads(p.read_text(encoding="utf-8"))
    kinds = {"numerical_verification", "python_vs_aspen", "literature_comparison", "experimental_validation"}
    assert all(it["evidence_kind"] in kinds for it in d["items"])
    assert not any(it["evidence_kind"] == "experimental_validation" for it in d["items"])


def test_t2a_extrapolation_flags():
    d = _load("kinetic_param_propagation.json")
    for c in d["catalysts"].values():
        for cs in c["cases"].values():
            for k, v in cs.items():
                if isinstance(v, dict) and v.get("P_bar") == 20.0:
                    assert v["extrapolation"] is True
