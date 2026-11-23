"""Uncertainty quantification utilities (Phase 2, task U1). numpy/scipy only.

Modules
    sobol         Saltelli (2010) first-order and Jansen (1999) total-effect estimators, grouped indices, bootstrap CIs,
                  Ishigami and linear test functions.
    kinetic_hook  temporary kinetic parameter overrides for amcrax.reactor.pfr (uses the additive
                  ``param_overrides`` keyword of amcrax.kinetics.rate_laws.rate_mol_per_kgcat_s).
    mcmc          adaptive Metropolis (Haario et al. 2001), rank-normalised split R-hat and bulk ESS (Vehtari et al. 2021).

Every result built on these is an uncertainty or sensitivity analysis of a model under stated input ranges.
It is not experimental validation.
"""
SEED = 20261123

LABEL = "Uncertainty of a model given its stated input ranges. Not experimental validation."
