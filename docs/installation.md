# AmCraX installation guide

Target: Windows 10 or 11 with Windows PowerShell 5.1. No administrator rights are needed. If the project path contains spaces, quote it. Commands below assume that the current directory is the project root.

What needs what:

| You want to | Needed |
|---|---|
| Browse stored results in the dashboard, run the Python models, run the tests | Python 3.12, and Node 24 for the dashboard. No Aspen Plus. |
| Run a new Aspen Plus simulation from the dashboard or a script | The above, plus Aspen Plus V15 installed, COM-registered and licensed. |
| Rebuild the technical report or the pitch deck | The above, plus pandoc (report), Microsoft Word or PowerPoint (PDF export) and Node (deck). |
| Refresh dashboard screenshots | Microsoft Edge and `npm ci` done (`playwright-core`). |

## 1. Prerequisites

1. **Python 3.12.** A per-user install is enough. Check with `python --version`, which should print `Python 3.12.x`.
2. **Node.js 24 LTS.** A portable zip is fine. Put it on `PATH` or unpack it to `%LOCALAPPDATA%\AmCraX-tools\node`.
3. Optional: pandoc 3.x (`%LOCALAPPDATA%\AmCraX-tools\pandoc`), MinGit (`...\git`), Microsoft Office and Microsoft Edge.
4. Optional: **Aspen Plus V15** (section 5).

`scripts\env.ps1` puts the project toolchain (`.venv`, Node, git and pandoc from `%LOCALAPPDATA%\AmCraX-tools`) first on `PATH` for the current PowerShell command:

```powershell
. "<project root>\scripts\env.ps1"; python -m pytest tests -q
```

## 2. One-step setup

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

`scripts\setup.ps1` is idempotent: it is safe to re-run. It

1. finds Python 3.12 (`PATH`, `py -3.12`, `%LOCALAPPDATA%\AmCraX-tools\python*`, `%LOCALAPPDATA%\Programs\Python\Python312`) and Node (`PATH` or `%LOCALAPPDATA%\AmCraX-tools\node`),
2. creates `.venv` if it does not exist,
3. runs `pip install -r requirements.txt` (pinned top-level packages),
4. runs `pip install -e backend` (the `amcrax` package, editable) unless `amcrax` already resolves to `backend\`,
5. runs `npm ci` in `frontend` unless `frontend\node_modules` exists (`-Force` reinstalls; `-SkipFrontend` skips this step),
6. reports whether the Aspen COM ProgID is registered.

Manual equivalent:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e backend
cd frontend; npm ci
```

## 3. Verify

```powershell
. scripts\env.ps1; python -m pytest tests -q          # Aspen is never started by the tests
cd frontend; npm test; npm run build                   # vitest, then tsc and vite build
```

A default run reports one skipped test, the opt-in live Aspen test (see the [developer guide](developer_guide.md)).

## 4. Launch

```powershell
scripts\start_amcrax.ps1          # API on :8000 (reused if already answering) and dashboard on :5173; opens the browser
scripts\stop_amcrax.ps1           # stops only what start_amcrax.ps1 started (logs\amcrax_pids.json)
```

The dashboard is at <http://localhost:5173>. Interactive API documentation is at <http://127.0.0.1:8000/docs>. Logs are `logs\api_stdout.log`, `logs\api_stderr.log`, `logs\api.log` (JSON lines), `logs\frontend_dev.log`, `logs\frontend_dev.err.log` and `logs\jobs\<job_id>.json`. Options are `-NoBrowser`, `-ApiPort` and `-FrontendPort`. For development with automatic restart on backend edits, run `scripts\start_api_dev.ps1` (a detached supervisor; `scripts\stop_api_dev.ps1` stops it) and then `start_amcrax.ps1`, which reuses that API.

The dashboard header shows the data mode: LIVE (API reachable), SNAPSHOT (API down, exported results used) or DEMO (neither). See the [user guide](user_guide.md).

## 5. Aspen Plus V15 (optional, for live simulation)

* Aspen Plus V15 must be installed and licensed for the Windows user that runs the API. AmCraX needs **one licence seat** and never starts more than one Aspen instance (a cross-process lock, section 7).
* It is driven through the COM ProgID `Apwn.Document.41.0` (`amcrax.aspen.session.PROGID_V15`). Stored results do not need Aspen.
* Check the COM registration without starting Aspen (a registry lookup only):

  ```powershell
  Test-Path 'Registry::HKEY_CLASSES_ROOT\Apwn.Document.41.0'        # True means registered
  ```

  The API performs the same check: `GET http://127.0.0.1:8000/api/health` returns `aspen.com_registered`, `aspen.available` and `aspen.reason`, and the dashboard header shows "Aspen: available" or "Aspen: unavailable (reason)". Registration does not prove that a licence seat is free; only a real run shows that. If the ProgID is missing, simulations with `engine: "aspen"` answer HTTP 503 `aspen_unavailable`, and the API never substitutes the Python model for a requested Aspen run.
* Time-outs: `AMCRAX_ASPEN_TIMEOUT_S` (default 600 s, the whole job including the wait for the lock) and `AMCRAX_ASPEN_SOLVE_TIMEOUT_S` (default 180 s, the Aspen solve). Set them in the shell before starting the API.
* The solved `.bkp` files in `aspen/models/` are sanitised by `aspen\automation\sanitise_models.py`, and `.apw` documents are not version-controlled. The `.inp` and `.bkp` files reproduce the models.

## 6. Running without Aspen

* **LIVE without Aspen.** The API runs, the dashboard reads every stored Aspen result from `results\simulations\*.json` and offers the independent Python process model (`python_model`) for new cases and sweeps. The Aspen engine button reports "unavailable".
* **SNAPSHOT.** With no API at all, `python scripts\export_snapshot.py` copies the stored results to `frontend\public\snapshot\` (git-ignored). With the API down, the dashboard serves them read-only under the banner "SNAPSHOT MODE". Actions that need the API are disabled.
* **DEMO.** With neither API nor snapshot, illustrative placeholder values appear behind a permanent red banner. Never use these as results.

## 7. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `uvicorn --reload` ends the PowerShell window that launched it | On Windows the reloader signals its console group. Use `scripts\start_api_dev.ps1` (a supervisor, `scripts\dev_api_supervisor.py`, restarts uvicorn on changes under `backend\amcrax`; stop it with `scripts\stop_api_dev.ps1`) or run uvicorn without `--reload`, as `start_amcrax.ps1` does. With a reloading server, queued and running jobs are lost on every code save and are later reported as `failed` ("API process restarted ..."), so run Aspen jobs against a non-reloading server. |
| A simulation stays `queued` | Aspen jobs run one at a time (first in, first out) and also wait for the machine-wide lock `aspen\runs\.aspen.lock`. Another script or job holds it. Waiting counts toward the 600 s job time-out. |
| `Another Aspen Plus run holds the lock; timed out waiting for it` | A run is in progress, or a process that holds the lock is hung. Find python processes that run `amcrax.aspen.worker` or an `aspen\automation\*.py` script (`Get-CimInstance Win32_Process -Filter "Name='python.exe'" \| select ProcessId,CommandLine`) and end the stale one. The operating system releases the lock when its process ends; the `.aspen.lock` file itself is harmless. |
| An `AspenPlus.exe` stays in Task Manager after a time-out | The worker is killed with its process tree on time-out, which can leave Aspen behind. `amcrax.aspen.session.kill_orphaned_sessions()` runs each time the lock is acquired and kills only the `AspenPlus.exe` PIDs that AmCraX recorded in `aspen\runs\.session_pids`; instances you started yourself are never touched. The next AmCraX Aspen run cleans up, or end the process manually. |
| `Could not start Aspen Plus via COM ProgID ...` | Aspen is not registered for this user, a licence seat is not available, or an Aspen modal dialog is open on the desktop. Check section 5, close dialogs and retry. |
| `start_amcrax.ps1`: port 5173 already in use | The script starts Vite with `--strictPort` and reuses whatever already answers HTTP 200 on the port. Free the port or pass `-FrontendPort 5180`. |
| Dashboard says "API unreachable" or shows SNAPSHOT | The API is not running on `127.0.0.1:8000` (the Vite proxy target is `http://localhost:8000`, see `frontend\vite.config.ts`). Start it with `start_amcrax.ps1` and reload. CORS allows `localhost:5173` and `127.0.0.1:5173` only. |
| Port 8000 busy | Another API instance answers there, and `start_amcrax.ps1` reuses it. To run a second one, use `python -m uvicorn amcrax.api.main:app --port 8001`; the frontend proxy still points to 8000. |
| `python` not found or the wrong version | Run `. scripts\env.ps1` first, or call `.venv\Scripts\python.exe`. The Windows Store `python` alias is not a real interpreter. |
| `npm` errors about execution policy | Use `powershell -ExecutionPolicy Bypass -File ...` for the scripts, or call `npm.cmd`. |
| pytest reports failures in `tests/test_api.py` while result files are being rewritten | Those tests read live result files. Re-run after the producing script finishes. |

## 8. Uninstall

Delete the project folder and, to remove the toolchain, `%LOCALAPPDATA%\AmCraX-tools`. Nothing is written to the registry or outside the project and that folder.
