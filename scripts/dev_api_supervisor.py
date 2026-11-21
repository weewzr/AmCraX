"""Development supervisor for the AmCraX API (Windows-safe replacement for ``uvicorn --reload``).

``uvicorn --reload`` on Windows signals its console group on every reload, which also terminates
the shell that launched it. This supervisor runs uvicorn *without* reload in its own process
group, restarts it when a Python file under backend/amcrax changes (debounced) or when it exits,
and keeps running until the file ``logs/api_supervisor.stop`` appears.

Start detached:   scripts/start_api_dev.ps1
Stop:             New-Item logs/api_supervisor.stop   (or scripts/stop_api_dev.ps1)
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WATCH = ROOT / "backend" / "amcrax"
LOGS = ROOT / "logs"
STOP = LOGS / "api_supervisor.stop"
PORT = "8000"


def snapshot() -> dict[str, float]:
    state: dict[str, float] = {}
    for p in WATCH.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        try:
            state[str(p)] = p.stat().st_mtime
        except OSError:
            pass
    return state


def start(log) -> subprocess.Popen:
    flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "amcrax.api.main:app", "--host", "127.0.0.1", "--port", PORT],
        cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, creationflags=flags,
    )


def stop(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> int:
    LOGS.mkdir(exist_ok=True)
    STOP.unlink(missing_ok=True)
    with open(LOGS / "uvicorn_dev.log", "a", encoding="utf-8", buffering=1) as log:
        def note(msg: str) -> None:
            log.write(f"[supervisor {time.strftime('%H:%M:%S')}] {msg}\n")

        state = snapshot()
        proc = start(log)
        note(f"started uvicorn pid {proc.pid}")
        changed_at = None
        while not STOP.exists():
            time.sleep(1.0)
            new = snapshot()
            if new != state:
                state, changed_at = new, time.time()
            if changed_at is not None and time.time() - changed_at > 2.0:  # debounce: wait for saves to settle
                note("source change detected - restarting")
                stop(proc)
                proc = start(log)
                note(f"restarted uvicorn pid {proc.pid}")
                changed_at = None
            elif proc.poll() is not None:
                note(f"uvicorn exited with code {proc.returncode} - restarting in 3 s")
                time.sleep(3.0)
                proc = start(log)
                note(f"restarted uvicorn pid {proc.pid}")
        note("stop file found - shutting down")
        stop(proc)
    STOP.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
