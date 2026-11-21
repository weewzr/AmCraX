<!-- cites: -->

# 12 Python-Aspen automation

## 12.1 Architecture

Every Aspen Plus result in this report was produced by a Python program, not by work in the GUI. The chain in `backend/amcrax/aspen` has six links:

1. **Generator** (`inp_writer.py`): validates a typed `CaseInputs` object and writes a complete Aspen input file (`.inp`) with explicit units (bar, °C, kW); the file is a pure function of the case.
2. **COM session** (`session.py`): starts Aspen Plus V15 as an out-of-process COM server, opens the file, reads and writes variable-tree nodes, runs the engine and releases the server.
3. **Extraction** (`extract.py`): reads every stream and block, checks units and builds the run status.
4. **Typed result**: a `SimulationResult` labelled `aspen_plus_v15`, with KPIs and balances from `amcrax.kpis`, the functions the Python process model also uses.
5. **Store** (`runner.py`): JSON per case and CSV per study under `results/`, with project-relative model paths.
6. **Isolated worker** (`worker.py`): a separate process that the API starts for each on-demand Aspen run (Section 22).

The scripts in `aspen/automation/` use the same chain, among them `run_sensitivity.py` (Section 17), `run_equilibrium_grid.py` (Section 13) and `verify_candidates.py`, which re-solves the optimisation candidates (Section 20).

## 12.2 COM interface used

Table: **Table 12.1.** COM members and variable-tree paths used by AmCraX (`<s>` stream, `<b>` block, `<c>` component). *Source: backend/amcrax/aspen/session.py, extract.py, runner.py; aspen/automation/run_baseline.py, run_equilibrium_grid.py, sanitise_models.py.*

| Purpose | Call or node | Notes |
|---|---|---|
| Start server | `win32com.client.DispatchEx("Apwn.Document.41.0")` | V15 ProgID; new process each time; its process ids are recorded |
| Open model | `InitFromArchive2(<path>)` | `.inp`, `.bkp` and `.apw`; a second file restarts the server |
| Headless operation | `SuppressDialogs = 1`, `Visible = 0` | set after opening |
| Reset and run | `Reinit()`, then `Engine.Run2()`; `Engine.IsRunning`, `Engine.Stop()` | synchronous; idle check after return |
| Node access | `Tree.FindNode(path)`: `.Value`, `.UnitString`, `.Elements`, `.AttributeValue(12)` | attribute 12 = HAP_COMPSTATUS |
| Stream results | `\Data\Streams\<s>\Output\` `TEMP_OUT`, `PRES_OUT`, `MOLEFLMX`, `MASSFLMX`, `HMX_FLOW`, `VFRAC_OUT` (each `\MIXED`); `MOLEFLOW`, `MOLEFRAC`, `MASSFRAC` `\MIXED\<c>`; `SOURCE`, `DESTINATION` | |
| Block results | `\Data\Blocks\<b>\Output\` `QCALC`, `B_TEMP`, `B_PRES`; Pump `WNET`, `FLUID_POWER`, `BRAKE_POWER`, `CEFF`, `HEAD_CAL`, `PDRP`; HeatX `HX_DUTY`, `HOTINT`, `HOT_TEMP`, `COLDINT`, `COLD_TEMP`, `HX_DTLM`, `HX_UA`, `HX_AREAC`, `HX_FMTD` | |
| Run messages | `\Data\Results Summary\Run-Status\Output\PER_ERROR` (children) | errors, warnings, input translation |
| Inputs changed in place | `\Data\Streams\FEED\Input\TOTFLOW\MIXED`, `FLOW\MIXED\<c>`; `\Data\Blocks\<b>\Input\TEMP` (HEATER, CRACKER, COOLER, FLUEHX); `\Data\Blocks\PSA\Input\FRACS\H2PROD\MIXED\<c>`; `\Data\Blocks\FEHE\Input\VALUE` | Section 12.3 |
| Equilibrium grid | `\Data\Streams\EQFEED\Input\TEMP\MIXED`, `PRES\MIXED`; `\Data\Blocks\REQ\Input\TEMP`, `PRES` | single-RGibbs validation model |
| Native sensitivity | `\Data\Model Analysis Tools\Sensitivity\STEMP\Output\SENSVAR` | read by `run_baseline.py` |
| Binary parameters | `\Data\Properties\Parameters\Binary Interaction\<form>\Input` | raw dump; the PRKBV form holds no values (Section 13) |
| Save and release | `SaveAs(<path>)`; `Close()`, `Quit()`, `pythoncom.CoUninitialize()` | then a process check (Section 12.5) |

## 12.3 In-place input changes and per-case input files

Inputs that change the model structure (heat integration, reactor pressure, burner excess air, property method) make the runner open a freshly generated input file. All others (reactor temperature, feed flow and water, FEHE approach, PSA fractions, PSA feed and stack temperatures) are written in place into the loaded model, followed by `Reinit` and a run, so one model load serves, for example, a whole pressure level.

An independent code review found that cases solved in place had named the input file of the first case of their group. The runner now writes an input file for every case, and `write_case_inputs.py` writes `aspen/models/cases/<case_id>.inp` for each stored Aspen case and records it as `model_file`, so the named file reproduces exactly that case. The two baseline results point to the solved backups in `aspen/models/`.

<!-- data: backend/amcrax/aspen/runner.py IN_PLACE_FIELDS, _structural_key, run_cases; aspen/automation/write_case_inputs.py; results/simulations/*.json model_file (18 cases -> aspen/models/cases/*.inp, baseline pair -> aspen/models/*.bkp) -->

## 12.4 Synchronous runs and the stale-duty defect

The engine runs synchronously: `Run2()` returns only after the results are in the variable tree, and the session then confirms that `IsRunning` is false. An earlier loop started the engine asynchronously (`Run2(1)` and polling `IsRunning`). In the equilibrium sweep, then run without re-initialisation, one IDEAL point (600 °C, 30 bar) was read while results were still loading and carried the previous point's duty, 1.24 kJ/mol off. The validation matrix caught it, because an ideal-gas duty per mole converted cannot depend on pressure (Section 16). The fix: synchronous runs, re-initialisation at every grid point, a repeatability check of four points in independent sessions (deviation 0 for both methods) and a stale-value check (spread of the IDEAL duty per mole converted over pressure 3.25 × 10^-7^ kJ/mol, limit 10^-3^). Flowsheet runs had always re-initialised and were unaffected.

<!-- data: backend/amcrax/aspen/session.py AspenSession.run; aspen/automation/run_equilibrium_grid.py REPEAT_CHECK; aspen/runs/equilibrium_rerun.log (repeatability 0.00e+00, spread 3.25e-07 kJ/mol); results/validation/validation_matrix.json EQ-DH-ASPEN, EQ-GRID-STALE; docs/validation/discrepancy_analysis.md section 6 -->

## 12.5 Run acceptance, unit checks and process isolation

A run is accepted only after three checks: the HAP_COMPSTATUS bit flags of every block (32 = errors, 2 = no results, 4 = warnings), the Run-Status messages, and results in every block. The baseline records `converged = true`, no errors or warnings, and one input-translation message: PRKBV binary parameters retrieved from the EOS-LIT databank (run-status form in Section 6). A failed case yields a result with `has_errors = true` and no streams, the next case forces a clean reload, and the API stores nothing. `get_quantity` compares each node's `UnitString` with the expected unit (C, bar, kmol/hr, kg/hr, kW) and raises an error on a mismatch, so a hand-edited model cannot be mis-scaled silently; other quantities keep their Aspen unit, such as the FEHE UA in cal/(s K) (Section 10).

<!-- data: backend/amcrax/aspen/extract.py extract_status, extract_block; backend/amcrax/aspen/session.py get_quantity; results/simulations/baseline.json status -->

`aspen_lock()` holds a machine-wide byte lock on `aspen/runs/.aspen.lock` (waiting up to 900 s), so scripts and API jobs never run two Aspen instances. The session records the process ids of the `AspenPlus.exe` instances it starts; on closing it calls `Close` and `Quit`, releases COM, waits up to 15 s and terminates a surviving instance by its id. Aspen runs as a COM server, not as a child of the Python process, so a new lock holder, knowing that no session is alive, terminates any recorded instance still running: orphans of a killed worker. Other Aspen windows are never touched.

Time-outs act at worker level. The API runs each case as `python -m amcrax.aspen.worker` (exit code 0: result written, 1: Aspen failure, 2: invalid inputs) and kills the worker's process tree after a wall-clock limit that includes the lock wait (default 600 s), reporting the job as `timeout`. The solve limit passed to the worker (default 180 s) cannot interrupt a synchronous `Run2`: a late run keeps its results with a warning, and a hung engine ends only through the worker kill and the orphan clean-up. The web server never loads COM.

<!-- data: backend/amcrax/aspen/runner.py aspen_lock (timeout_s=900); backend/amcrax/aspen/session.py close, kill_orphaned_sessions, run; backend/amcrax/aspen/worker.py main; backend/amcrax/api/jobs.py ASPEN_TIMEOUT_S 600, ASPEN_SOLVE_TIMEOUT_S 180, solve_timeout_for, _kill_tree -->

## 12.6 Input validation

Everything that reaches a file name or the input file is validated in the case schema and again in the API. The case id must match `^[A-Za-z0-9_-]{1,64}$`, and the runner checks that the input path stays inside the run directory. The property method must be one of PENG-ROB, RK-SOAVE, RKS-BM, PR-BM, SRK and IDEAL. `validate_flowsheet_inputs` rejects reactor pressures below 3 bar and FEHE cold outlets below a pressure-dependent minimum: the ammonia saturation temperature at the vaporiser pressure plus the 10 K superheat and a 25 K margin, 85.9 °C at the baseline. The former fixed 120 °C threshold was too low above about 65 bar. The API answers 422; an infeasible sensitivity point is reported without starting Aspen.

<!-- data: backend/amcrax/schemas.py CaseInputs.case_id pattern, PROPERTY_METHODS; backend/amcrax/api/store.py check_id; backend/amcrax/api/jobs.py check_inputs, ALLOWED_PROPERTY_METHODS; backend/amcrax/aspen/inp_writer.py MIN_FLOWSHEET_PRESSURE_BAR 3.0, FEHE_GUARD_MARGIN_K 25, fehe_cold_outlet_minimum_C (CoolProp T_sat at 20.8 bar 50.88 degC + 10 + 25 = 85.9 degC; fallback 120 degC) -->

## 12.7 Run times and reproducibility

Table: **Table 12.2.** Measured Aspen run times. *Source: results/simulations/*.json status.engine_time_s; results/sensitivity/aspen_*.csv engine_time_s; aspen/runs/studies.log and equilibrium_rerun.log.*

| Runs | Number | Time |
|---|---|---|
| Baseline flowsheet incl. ten-point native sensitivity STEMP | 1 | 2.042 s engine |
| Flowsheet without FEHE | 1 | 2.108 s engine |
| All stored flowsheet cases | 20 | 1.34-2.64 s engine, median 1.52 s |
| Sensitivity studies (8 studies) | 91 | 1.34-2.69 s engine, median 1.51 s; 1061 s wall clock incl. start-ups and model loads |
| Equilibrium grid (both methods) and repeatability runs | 168 + 8 | 523 s wall clock |

<!-- data: results/simulations/baseline.json, baseline_no_hi.json status.engine_time_s; 20 aspen_plus_v15 cases min 1.34, median 1.519, max 2.637 s; results/sensitivity/aspen_*.csv (91 rows, all converged) min 1.343, median 1.514, max 2.691 s; aspen/runs/studies.log study times sum 1061.3 s; aspen/runs/equilibrium_rerun.log 16:14:57-16:23:40 -->

Table 12.2 shows that engine time is small; start-ups and model loads dominate the wall clock. Every result carries its inputs, model file, Aspen messages and engine time. `sanitise_models.py` replaces the Windows user and host names in the run-status record of solved `.bkp` files and re-solves each file to confirm that it opens; `.apw` documents embed the same names and are not version-controlled. `capture_screenshots.py` drives the GUI through UI Automation and messages to the Aspen window's own queue, captures it with `PrintWindow` and never saves the model.

## 12.8 Lessons from surveyed repositories

Five public repositories were read (`docs/reference_projects/github_survey.md`); no code was copied. zwang1995/Aspen-Plus-Automation (MIT) confirmed `InitFromArchive2` and `Reinit`; its kill of every `AspenPlus.exe` was rejected, and its first version used the asynchronous run-and-poll pattern that later caused the AmCraX stale-duty defect. beykal-lab/aspen-python-automation (CC-BY-4.0) reads results without a convergence check, which motivated the mandatory status checks. thirakorn-mokkawes-59/aspen-mcp (MIT), the only V15-explicit source, documented ProgID 41.0, `\MIXED` input nodes and single-thread COM use. EPEL-SNU/Aspen_Plus_MCP (MIT) showed the Run-Status messages and a synchronous `Run2()`. adk23333/py2aspen (BSD-3-Clause) supports V14 only. The repositories disagree on the `BLKSTAT` code, so AmCraX uses HAP_COMPSTATUS instead.

## 12.9 Limits

The automation needs Windows, pywin32 and a licensed Aspen Plus V15; another version needs another ProgID. One instance runs at a time, so API requests queue behind the lock. Opening a second file restarts the COM server, which adds start-up time to every structural change. The node paths of Table 12.1 were verified on this model only, and a hung engine is stopped only by killing the worker process.
