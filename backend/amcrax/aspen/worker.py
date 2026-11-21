"""Process-isolated Aspen Plus worker.

The FastAPI backend never loads COM in its own process. It launches::

    python -m amcrax.aspen.worker --inputs <CaseInputs.json> --output <SimulationResult.json>

Contract: reads a ``CaseInputs`` JSON file, runs the case in Aspen Plus V15, writes a
``SimulationResult`` JSON file. Exit code 0 = a result file was written (inspect ``status`` for
convergence); non-zero = failure, with the reason on stderr.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from amcrax.schemas import CaseInputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one AmCraX case in Aspen Plus V15")
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--visible", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s", stream=sys.stderr)

    try:
        inputs = CaseInputs.model_validate_json(args.inputs.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"invalid inputs file: {exc}", file=sys.stderr)
        return 2
    try:
        from amcrax.aspen.runner import run_case

        result = run_case(inputs, visible=args.visible, timeout_s=args.timeout, save=False, study="api")
    except Exception as exc:  # AspenError, COM failures, ...
        print(f"Aspen Plus run failed: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
