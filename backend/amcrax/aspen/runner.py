"""High-level Aspen Plus runs: one case, many cases, equilibrium validation grid.

Strategy
--------
* Each topology / pressure level is generated as a fresh ``.inp`` working copy under
  ``aspen/runs/<study>/`` (never in ``aspen/models``), so no original model is ever modified.
* Within one loaded model, inputs that do not change the model structure (reactor temperature,
  feed flow and composition, FEHE approach, PSA split fractions, PSA feed and stack temperatures)
  are modified in place through the COM variable tree, followed by ``Reinit`` + ``Run``.
* A cross-process lock guarantees a single Aspen instance at a time.
"""
from __future__ import annotations

import logging
import msvcrt
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterable, Iterator, Optional, Sequence

from amcrax.aspen.extract import extract_result
from amcrax.aspen.inp_writer import build_equilibrium_input, build_flowsheet_input, validate_flowsheet_inputs
from amcrax.aspen.session import AspenError, AspenSession
from amcrax.paths import ASPEN_RUNS, RESULTS_SIMULATIONS, ROOT, ensure_dirs
from amcrax.schemas import CaseInputs, DataSource, RunStatus, SimulationResult

log = logging.getLogger("amcrax.aspen")

B = r"\Data\Blocks"
S = r"\Data\Streams"

#: CaseInputs fields that can be changed on a loaded model through COM (no regeneration needed).
IN_PLACE_FIELDS = frozenset({
    "case_id", "feed_total_kmol_h", "feed_h2o_mole_frac", "reactor_temperature_C",
    "fehe_hot_end_approach_K", "psa_feed_temperature_C", "psa_h2_recovery", "psa_n2_slip",
    "stack_temperature_C",
})


@contextmanager
def aspen_lock(timeout_s: float = 900.0) -> Iterator[None]:
    """Cross-process mutex: only one Aspen Plus automation session may exist at a time."""
    ensure_dirs()
    lock_path = ASPEN_RUNS / ".aspen.lock"
    fh = open(lock_path, "a+")
    t0 = time.time()
    while True:
        try:
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            break
        except OSError:
            if time.time() - t0 > timeout_s:
                fh.close()
                raise AspenError("Another Aspen Plus run holds the lock; timed out waiting for it")
            time.sleep(0.5)
    try:
        # holding the lock means no automation session is alive: anything recorded is an orphan
        from amcrax.aspen.session import kill_orphaned_sessions

        kill_orphaned_sessions()
        yield
    finally:
        try:
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            fh.close()


def _rel(path: Path | str) -> str:
    """Path relative to the project root (results must not embed machine-specific absolute paths)."""
    try:
        return Path(path).resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return Path(path).name


def _structural_key(i: CaseInputs) -> tuple:
    """Inputs that require a regenerated input file when they change."""
    return (i.heat_integration, round(i.reactor_pressure_bar, 9), round(i.burner_excess_air, 9), i.property_method)


def apply_inputs(s: AspenSession, i: CaseInputs) -> None:
    """Write the in-place adjustable inputs of ``i`` into the loaded Aspen model."""
    t = i.reactor_temperature_C
    values: list[tuple[str, float]] = [
        (rf"{S}\FEED\Input\TOTFLOW\MIXED", i.feed_total_kmol_h),
        (rf"{S}\FEED\Input\FLOW\MIXED\NH3", 1.0 - i.feed_h2o_mole_frac),
        (rf"{S}\FEED\Input\FLOW\MIXED\H2O", i.feed_h2o_mole_frac),
        (rf"{B}\HEATER\Input\TEMP", t),
        (rf"{B}\CRACKER\Input\TEMP", t),
        (rf"{B}\COOLER\Input\TEMP", i.psa_feed_temperature_C),
        (rf"{B}\PSA\Input\FRACS\H2PROD\MIXED\H2", i.psa_h2_recovery),
        (rf"{B}\PSA\Input\FRACS\H2PROD\MIXED\N2", i.psa_n2_slip),
        (rf"{B}\FLUEHX\Input\TEMP", i.stack_temperature_C),
    ]
    if i.heat_integration:
        values.append((rf"{B}\FEHE\Input\VALUE", t - i.fehe_hot_end_approach_K))
    s.set_many(values)


def _failed_result(inputs: CaseInputs, message: str) -> SimulationResult:
    return SimulationResult(
        case_id=inputs.case_id,
        source=DataSource.ASPEN,
        inputs=inputs,
        status=RunStatus(converged=False, has_errors=True, messages=[message]),
        notes=["Aspen Plus run failed; no results were extracted."],
    )


def run_cases(
    cases: Sequence[CaseInputs],
    *,
    study: str = "adhoc",
    visible: bool = False,
    timeout_s: float = 180.0,
    save_models_to: Optional[Path] = None,
    native_sensitivity: bool = False,
    on_result: Optional[Callable[[SimulationResult], None]] = None,
    session_hook: Optional[Callable[[AspenSession, CaseInputs], None]] = None,
) -> list[SimulationResult]:
    """Run several cases in one Aspen session. Failed cases yield a result with ``has_errors``.

    ``save_models_to``: directory in which the solved model of every case is saved as
    ``<case_id>.bkp`` and ``<case_id>.apw``. ``session_hook`` is called after each successful run
    with the live session (used for screenshots).
    """
    ensure_dirs()
    run_dir = ASPEN_RUNS / study
    run_dir.mkdir(parents=True, exist_ok=True)
    results: list[SimulationResult] = []
    with aspen_lock():
        with AspenSession(visible=visible) as s:
            loaded_key: Optional[tuple] = None
            model_file: Optional[str] = None
            for inputs in cases:
                try:
                    validate_flowsheet_inputs(inputs)
                    key = _structural_key(inputs)
                    # Every case gets its own input file (also when the loaded model is only modified
                    # in place), so that the file named in the result reproduces exactly that case.
                    inp = run_dir / f"{inputs.case_id}.inp"
                    if inp.resolve().parent != run_dir.resolve():
                        raise ValueError(f"case_id {inputs.case_id!r} does not map to a file inside the run directory")
                    inp.write_text(
                        build_flowsheet_input(inputs, native_sensitivity=native_sensitivity), encoding="ascii"
                    )
                    model_file = _rel(inp)
                    if key != loaded_key:
                        s.open(inp)
                        loaded_key = key
                    else:
                        apply_inputs(s, inputs)
                    elapsed = s.run(timeout_s=timeout_s, reinit=True)
                    result = extract_result(s, inputs, engine_time_s=round(elapsed, 3), model_file=model_file)
                    if save_models_to is not None:
                        for ext in (".bkp", ".apw"):
                            s.save_as(Path(save_models_to) / f"{inputs.case_id}{ext}")
                        result.model_file = _rel(Path(save_models_to) / f"{inputs.case_id}.bkp")
                    if session_hook is not None:
                        session_hook(s, inputs)
                except (AspenError, ValueError) as exc:
                    log.error("case %s failed: %s", inputs.case_id, exc)
                    result = _failed_result(inputs, str(exc))
                    loaded_key = None  # force a clean reload for the next case
                results.append(result)
                if on_result is not None:
                    on_result(result)
    return results


def run_case(
    inputs: CaseInputs,
    *,
    visible: bool = False,
    timeout_s: float = 180.0,
    save: bool = True,
    study: str = "adhoc",
) -> SimulationResult:
    """Generate, run and extract one case. With ``save`` the result is stored in results/simulations."""
    result = run_cases([inputs], study=study, visible=visible, timeout_s=timeout_s)[0]
    if save:
        save_result(result)
    return result


def save_result(result: SimulationResult, directory: Path = RESULTS_SIMULATIONS) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{result.case_id}.json"
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return path


def run_equilibrium_grid(
    temperatures_C: Iterable[float],
    pressures_bar: Iterable[float],
    *,
    property_method: str = "PENG-ROB",
    timeout_s: float = 120.0,
    reinit: bool = True,
    session_hook: Optional[Callable[[AspenSession], None]] = None,
) -> list[dict]:
    """Pure-NH3 isothermal RGibbs runs over a T x P grid (validation of the Python model).

    Returns rows with the columns of ``results/validation/equilibrium_aspen_grid.csv``.
    Every point is re-initialised (``reinit=True``) so that no value can be carried over from the
    previous point.
    """
    ensure_dirs()
    run_dir = ASPEN_RUNS / "equilibrium"
    run_dir.mkdir(parents=True, exist_ok=True)
    inp = run_dir / f"equilibrium_{property_method.lower().replace('-', '')}.inp"
    temps, press = list(temperatures_C), list(pressures_bar)
    inp.write_text(build_equilibrium_input(temps[0], press[0], property_method), encoding="ascii")
    rows: list[dict] = []
    o = rf"{S}\EQPROD\Output"
    with aspen_lock():
        with AspenSession() as s:
            s.open(inp)
            for p in press:
                for t in temps:
                    s.set_many([
                        (rf"{S}\EQFEED\Input\TEMP\MIXED", t),
                        (rf"{S}\EQFEED\Input\PRES\MIXED", p),
                        (rf"{B}\REQ\Input\TEMP", t),
                        (rf"{B}\REQ\Input\PRES", p),
                    ])
                    s.run(timeout_s=timeout_s, reinit=reinit)
                    n_nh3 = float(s.get(rf"{o}\MOLEFLOW\MIXED\NH3", 0.0))
                    n_feed = float(s.get(rf"{S}\EQFEED\Output\MOLEFLOW\MIXED\NH3"))
                    duty_kw = s.get_quantity(rf"{B}\REQ\Output\QCALC", "kW")
                    rows.append({
                        "T_C": t,
                        "P_bar": p,
                        "property_method": property_method,
                        "nh3_conversion": 1.0 - n_nh3 / n_feed,
                        "y_NH3": float(s.get(rf"{o}\MOLEFRAC\MIXED\NH3", 0.0)),
                        "y_H2": float(s.get(rf"{o}\MOLEFRAC\MIXED\H2", 0.0)),
                        "y_N2": float(s.get(rf"{o}\MOLEFRAC\MIXED\N2", 0.0)),
                        # kW per (kmol/h) -> kJ/mol : x 3600 / 1000
                        "heat_duty_kJ_per_mol_NH3_fed": duty_kw * 3.6 / n_feed,
                    })
            if session_hook is not None:
                session_hook(s)
            s.save_as(run_dir / f"equilibrium_{property_method.lower().replace('-', '')}.bkp")
    return rows


def aspen_available() -> bool:
    """True if the Aspen Plus V15 COM class is registered (does not start Aspen)."""
    if os.name != "nt":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "Apwn.Document"):
            return True
    except OSError:
        return False
