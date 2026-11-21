"""Independent Python process model mirroring the AmCraX Aspen flowsheet (source = python_model)."""
from .flowsheet import FlowsheetSpecError, pressure_profile, run_python_case


def compare_results(a, b):
    """See :func:`amcrax.process_model.compare.compare_results` (imported lazily so that
    ``python -m amcrax.process_model.compare`` runs without a runpy warning)."""
    from .compare import compare_results as _cmp

    return _cmp(a, b)


__all__ = ["run_python_case", "compare_results", "FlowsheetSpecError", "pressure_profile"]
