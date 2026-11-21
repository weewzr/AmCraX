"""Aspen Plus V15 COM session wrapper.

Responsibilities: start Aspen Plus as an out-of-process COM server, open a model, read and write
variable-tree nodes, run the engine with a timeout, report status, save, and always release the
COM server (killing only the process this session started if it refuses to exit).
"""
from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Iterable, Optional

log = logging.getLogger("amcrax.aspen")

#: Aspen Plus V15.0 registers the version-specific ProgID ``Apwn.Document.41.0``.
PROGID_V15 = "Apwn.Document.41.0"
ASPEN_IMAGE = "AspenPlus.exe"

# HAP_COMPSTATUS attribute (IHNode.AttributeValue(12)) bit flags.
HAP_COMPSTATUS = 12
HAP_RESULTS_SUCCESS = 1
HAP_NO_RESULTS = 2
HAP_RESULTS_WARNINGS = 4
HAP_RESULTS_INACCESS = 8
HAP_RESULTS_INCOMPAT = 16
HAP_RESULTS_ERRORS = 32
HAP_INPUT_INCOMPLETE = 64
HAP_INPUT_COMPLETE = 128


class AspenError(RuntimeError):
    """Raised for COM start-up failures, missing nodes, engine time-outs and failed runs."""


def _aspen_pids() -> set[int]:
    """PIDs of running AspenPlus.exe processes (empty set if the query fails)."""
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {ASPEN_IMAGE}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=20, check=False,
        ).stdout
    except Exception:  # pragma: no cover - diagnostic helper only
        return set()
    pids: set[int] = set()
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) >= 2 and parts[0].lower().strip('"') == ASPEN_IMAGE.lower():
            try:
                pids.add(int(parts[1]))
            except ValueError:
                pass
    return pids


def _pid_file() -> Path:
    from amcrax.paths import ASPEN_RUNS

    ASPEN_RUNS.mkdir(parents=True, exist_ok=True)
    return ASPEN_RUNS / ".session_pids"


def _record_session_pids(pids: set[int]) -> None:
    """Remember which Aspen processes the live automation session started (for orphan cleanup)."""
    try:
        _pid_file().write_text(" ".join(str(p) for p in sorted(pids)), encoding="ascii")
    except OSError:  # pragma: no cover
        pass


def kill_orphaned_sessions() -> list[int]:
    """Terminate Aspen instances left behind by an automation session that died (e.g. a worker
    process killed on time-out).

    Must only be called while holding ``aspen_lock`` (then no automation session can be alive, so
    every recorded pid that is still an ``AspenPlus.exe`` process is an orphan). Aspen instances
    started by the user are never recorded and therefore never touched.
    """
    try:
        recorded = {int(tok) for tok in _pid_file().read_text(encoding="ascii").split()}
    except (OSError, ValueError):
        return []
    killed = []
    for pid in sorted(recorded & _aspen_pids()):
        log.warning("terminating orphaned Aspen Plus automation instance pid %s", pid)
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, check=False)
        killed.append(pid)
    _record_session_pids(set())
    return killed


class AspenSession:
    """Context manager around one Aspen Plus COM instance.

    >>> with AspenSession() as s:                      # doctest: +SKIP
    ...     s.open("aspen/models/amcrax_baseline.bkp")
    ...     s.set(r"\\Data\\Blocks\\CRACKER\\Input\\TEMP", 650.0)
    ...     s.run()
    ...     t = s.get(r"\\Data\\Streams\\S5\\Output\\TEMP_OUT\\MIXED")
    """

    def __init__(self, *, visible: bool = False, progid: str = PROGID_V15) -> None:
        self.visible = visible
        self.progid = progid
        self.app: Any = None
        self.model_path: Optional[Path] = None
        self._own_pids: set[int] = set()
        self._com_initialised = False

    # ------------------------------------------------------------------ lifecycle
    def __enter__(self) -> "AspenSession":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def start(self) -> None:
        try:
            import pythoncom
            import win32com.client as win32
        except ImportError as exc:  # pragma: no cover
            raise AspenError("pywin32 is not installed; Aspen Plus automation requires Windows + pywin32") from exc
        pythoncom.CoInitialize()
        self._com_initialised = True
        before = _aspen_pids()
        t0 = time.time()
        try:
            self.app = win32.DispatchEx(self.progid)
        except Exception as exc:
            raise AspenError(f"Could not start Aspen Plus via COM ProgID {self.progid}: {exc}") from exc
        self._own_pids = _aspen_pids() - before
        _record_session_pids(self._own_pids)
        log.info("Aspen Plus started in %.1f s (pids %s)", time.time() - t0, sorted(self._own_pids))

    def open(self, path: str | Path) -> None:
        """Open an Aspen file (.inp input file, .bkp backup or .apw document).

        One COM instance holds one document: opening a second file restarts the server, which is
        the only sequence found to be reliable with Aspen Plus V15 (a second ``InitFromArchive2``
        on a live document fails with "Unable to open file").
        """
        p = Path(path).resolve()
        if not p.exists():
            raise AspenError(f"Aspen model not found: {p}")
        if self.model_path is not None:
            self.close()
            self.start()
        t0 = time.time()
        try:
            self.app.InitFromArchive2(str(p))
        except Exception as exc:
            raise AspenError(f"Aspen Plus could not open {p.name}: {exc}") from exc
        self.model_path = p
        try:  # these properties only exist once a document is initialised
            self.app.SuppressDialogs = 1
            self.app.Visible = bool(self.visible)
        except Exception as exc:  # pragma: no cover
            log.warning("could not set SuppressDialogs/Visible: %s", exc)
        log.info("opened %s in %.1f s", p.name, time.time() - t0)

    def close(self) -> None:
        app, self.app = self.app, None
        self.model_path = None
        if app is not None:
            for call in ("Close", "Quit"):
                try:
                    getattr(app, call)()
                except Exception:
                    pass  # the server disconnects during Quit; that is expected
            del app
        if self._com_initialised:
            try:
                import pythoncom

                pythoncom.CoUninitialize()
            except Exception:  # pragma: no cover
                pass
            self._com_initialised = False
        # make sure the instance we started is really gone (never touch other Aspen processes)
        if self._own_pids:
            deadline = time.time() + 15
            while time.time() < deadline and (_aspen_pids() & self._own_pids):
                time.sleep(0.5)
            for pid in _aspen_pids() & self._own_pids:
                log.warning("Aspen Plus pid %s did not exit - terminating it", pid)
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, check=False)
            self._own_pids = set()
            _record_session_pids(set())

    # ------------------------------------------------------------------ tree access
    def node(self, path: str):
        n = self.app.Tree.FindNode(path)
        if n is None:
            raise AspenError(f"Aspen variable-tree node not found: {path}")
        return n

    def has(self, path: str) -> bool:
        try:
            return self.app.Tree.FindNode(path) is not None
        except Exception:
            return False

    def get(self, path: str, default: Any = None) -> Any:
        """Value of a leaf node; ``default`` if the node does not exist or holds no value."""
        try:
            n = self.app.Tree.FindNode(path)
        except Exception:
            return default
        if n is None:
            return default
        try:
            v = n.Value
        except Exception:
            return default
        return default if v is None else v

    def get_with_unit(self, path: str) -> tuple[Any, Optional[str]]:
        n = self.app.Tree.FindNode(path)
        if n is None:
            return None, None
        try:
            unit = n.UnitString
        except Exception:
            unit = None
        return n.Value, (unit or None)

    def get_quantity(self, path: str, expected_unit: str) -> Optional[float]:
        """Numeric value of a node, verifying that Aspen reports it in ``expected_unit``.

        The model is generated with explicit IN-UNITS, so a unit mismatch means the model was
        changed by hand; fail loudly instead of silently mis-scaling a result.
        """
        value, unit = self.get_with_unit(path)
        if value is None:
            return None
        if unit is not None and unit.strip().lower() != expected_unit.lower():
            raise AspenError(f"{path}: expected unit '{expected_unit}' but Aspen reports '{unit}'")
        return float(value)

    def set(self, path: str, value: Any) -> None:
        self.node(path).Value = value

    def children(self, path: str) -> list[str]:
        try:
            return [e.Name for e in self.node(path).Elements]
        except AspenError:
            return []
        except Exception:
            return []

    def comp_status(self, path: str) -> int:
        try:
            return int(self.node(path).AttributeValue(HAP_COMPSTATUS))
        except Exception:
            return 0

    # ------------------------------------------------------------------ execution
    def run(self, *, timeout_s: float = 180.0, reinit: bool = True) -> float:
        """Run the simulation; returns the wall-clock engine time in seconds.

        ``reinit=True`` purges previous results first so that each run starts from the same state
        and cannot inherit a previous solution.
        """
        if reinit:
            try:
                self.app.Reinit()
            except Exception as exc:
                raise AspenError(f"Aspen Reinit failed: {exc}") from exc
        t0 = time.time()
        # Synchronous run: Run2() returns only after the engine has finished AND the results have
        # been loaded into the variable tree. An earlier asynchronous implementation (Run2(1) +
        # polling Engine.IsRunning) could read the tree while results were still being loaded and
        # returned one stale block duty in a no-reinit sweep (found by the validation matrix).
        # A hung engine is handled one level up: the API runs each case in a worker process that
        # is killed on time-out, and aspen_lock() then removes the orphaned Aspen instance.
        try:
            self.app.Engine.Run2()
        except Exception as exc:
            raise AspenError(f"Aspen engine run failed: {exc}") from exc
        # Defensive: make sure the engine really is idle before results are read.
        while True:
            try:
                running = bool(self.app.Engine.IsRunning)
            except Exception as exc:
                raise AspenError(f"Lost connection to Aspen Plus after the run: {exc}") from exc
            if not running:
                break
            if time.time() - t0 > timeout_s:
                try:
                    self.app.Engine.Stop()
                except Exception:
                    pass
                raise AspenError(f"Aspen run exceeded the time-out of {timeout_s:.0f} s and was stopped")
            time.sleep(0.05)
        elapsed = time.time() - t0
        if elapsed > timeout_s:
            # The run completed and its results are valid: keep them. (Discarding a converged run
            # after the fact would only lose work; a genuinely hung engine never reaches this line
            # and is handled by the worker-process time-out.)
            log.warning("Aspen run took %.0f s, longer than the requested time-out of %.0f s; results kept",
                        elapsed, timeout_s)
        return elapsed

    def run_messages(self) -> list[str]:
        """Text of the run-status summary (errors, warnings, input-translation messages)."""
        base = r"\Data\Results Summary\Run-Status\Output\PER_ERROR"
        lines: list[str] = []
        for name in self.children(base):
            v = self.get(base + "\\" + name)
            if isinstance(v, str) and v.strip():
                lines.append(v.rstrip())
        return lines

    def block_ids(self) -> list[str]:
        return self.children(r"\Data\Blocks")

    def stream_ids(self) -> list[str]:
        return self.children(r"\Data\Streams")

    def save_as(self, path: str | Path) -> Path:
        p = Path(path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.app.SaveAs(str(p))
        except Exception as exc:
            raise AspenError(f"Aspen SaveAs failed for {p}: {exc}") from exc
        return p

    def set_many(self, values: Iterable[tuple[str, Any]]) -> None:
        for path, value in values:
            self.set(path, value)
