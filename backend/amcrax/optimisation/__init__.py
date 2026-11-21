"""AmCraX process optimisation (P2.5) and multi-objective / Pareto analysis (P3.5).

Engine: the independent Python process model (source ``python_model``). Optima are candidates that the
coordinator re-solves in Aspen Plus V15 (results/optimisation/aspen_verification.json).

Public API
----------
evaluate_result(result, **options) -> dict      common evaluator for Aspen and Python results
evaluate_inputs(inputs, **options) -> dict      evaluate_result(run_python_case(inputs))
run(objective=..., bounds=..., constraints=..., method=...) -> dict   one single-objective optimisation
pareto(rows=None, pairs=None, ...) -> dict      conflict test + Pareto fronts on the design grid
"""
from .evaluate import (CI_HEATING, HEAT_SOURCES, compression_requirement, evaluate_inputs, evaluate_result,
                       psa_feed_pressure_requirement_bar)
from .pareto import DEFAULT_GRID, PARETO_OBJECTIVES, conflicts, design_grid, front, non_dominated, pareto
from .problems import (CONSTRAINT_DOCS, DEFAULT_CONSTRAINTS, MODEL_LIMITATIONS, OBJECTIVES, VARIABLES, Evaluator,
                       constraint_values, flatness, minimise, run)

__all__ = [
    "evaluate_result", "evaluate_inputs", "compression_requirement", "psa_feed_pressure_requirement_bar",
    "HEAT_SOURCES", "CI_HEATING",
    "run", "minimise", "flatness", "constraint_values", "Evaluator", "VARIABLES", "OBJECTIVES", "DEFAULT_CONSTRAINTS",
    "CONSTRAINT_DOCS", "MODEL_LIMITATIONS",
    "pareto", "design_grid", "conflicts", "front", "non_dominated", "PARETO_OBJECTIVES", "DEFAULT_GRID",
]
