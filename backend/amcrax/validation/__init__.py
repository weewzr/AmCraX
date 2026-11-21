"""AmCraX model-validation library: reusable checks returning :class:`CheckResult` objects.

The validation matrix itself is assembled by ``scripts/build_validation_matrix.py``.
"""
from .checks import (
    ELEMENTS,
    FAIL,
    INFO,
    NOT_RUN,
    PASS,
    CheckResult,
    check_aspen_verification,
    check_converged,
    check_single_objective_feasibility,
    check_economic_consistency,
    check_element_closure,
    check_mass_closure,
    check_nonnegative,
    check_optimisation_feasibility,
    check_reaction_stoichiometry,
    check_unit_sanity,
    check_value,
    check_vant_hoff,
    check_vant_hoff_data,
    element_totals,
    judge,
    not_run,
    simulation_closures,
)

__all__ = [
    "ELEMENTS", "FAIL", "INFO", "NOT_RUN", "PASS", "CheckResult", "check_aspen_verification",
    "check_single_objective_feasibility", "check_converged", "check_economic_consistency",
    "check_element_closure", "check_mass_closure", "check_nonnegative", "check_optimisation_feasibility",
    "check_reaction_stoichiometry", "check_unit_sanity", "check_value", "check_vant_hoff", "check_vant_hoff_data",
    "element_totals", "judge", "not_run", "simulation_closures",
]
