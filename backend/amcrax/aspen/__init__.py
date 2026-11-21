"""Aspen Plus V15 automation layer (Windows COM).

Public entry points::

    from amcrax.aspen import run_case, AspenSession
    result = run_case(CaseInputs())            # -> amcrax.schemas.SimulationResult

Only one Aspen instance may run at a time; :func:`run_case` holds a cross-process file lock.
"""
from __future__ import annotations

__all__ = ["AspenSession", "AspenError", "run_case", "run_cases"]


def __getattr__(name: str):  # lazy: importing amcrax.aspen must not require pywin32
    if name in {"AspenSession", "AspenError"}:
        from amcrax.aspen import session

        return getattr(session, name)
    if name in {"run_case", "run_cases"}:
        from amcrax.aspen import runner

        return getattr(runner, name)
    raise AttributeError(name)
