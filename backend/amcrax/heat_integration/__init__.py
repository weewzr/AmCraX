"""Heat-integration (pinch) analysis: problem table, composite / grand composite curves,
configuration comparison and FEHE feasibility for an AmCraX SimulationResult.

Relation to the KPIs ``net_fuel_heat_deficit_kW`` and ``lhv_efficiency`` (amcrax.kpis): those are
first-law, upper-bound metrics - external heat is counted 1:1 against LHV (a 100 %-efficient fired
heater), all flue heat released down to the stack temperature is credited even where it lies below
the reactor temperature, and a heat surplus earns no credit. This package adds the temperature-level
(second-law-feasible) view: configuration (c) and the pinch targets credit flue heat only where it can
reach the process duty across dT_min, so their external heating is normally larger than the KPI
deficit (the two use different duty sources - model H-T curves here, block duties in the KPIs - so
the comparison is not an exact inequality).
"""
from .analysis import U_ASSUMED_W_M2K, U_RANGE_W_M2K, analyse
from .models import (ConfigurationRow, ConsistencyCheck, FEHEAssessment, HeatIntegrationResult, HIStream,
                     PinchTargets, ProblemTableRow)
from .pinch import Curve, PinchResult, composite, linear_curve, make_curve, problem_table

__all__ = [
    "analyse", "HeatIntegrationResult", "PinchTargets", "ProblemTableRow", "ConfigurationRow", "FEHEAssessment",
    "ConsistencyCheck", "HIStream", "Curve", "PinchResult", "composite", "linear_curve", "make_curve",
    "problem_table", "U_ASSUMED_W_M2K", "U_RANGE_W_M2K",
]
