<!-- cites: -->

# 13 Python-Aspen automation

## 13.1 Architecture

Every Aspen Plus result in this report was produced by a Python program, not by interactive GUI work. The chain consists of six modules in `backend/amcrax/aspen`:

1. **Generator** (`inp_writer.py`): validates a typed `CaseInputs` object and writes a complete Aspen keyword input file (`.inp`) with explicit `IN-UNITS` (bar, °C, kW).
2. **COM session** (`session.py`, `AspenSession`): starts Aspen Plus V15 as an out-of-process COM server, opens the file, reads and writes variable-tree nodes, runs the engine and releases the server.
3. **Extraction** (`extract.py`): reads every stream and block and builds the run status.
4. **Typed result**: a pydantic `SimulationResult` (`amcrax.schemas`) with provenance `source = "aspen_plus_v15"`; KPIs and balance closures come from `amcrax.kpis`, the same functions applied to the Python process model.
5. **Storage** (`runner.py`): JSON in `results/simulations/`, CSV per study in `results/sensitivity/` and `results/validation/`, solved models as `.bkp`/`.apw`. Model files are referenced by project-relative paths (for example `aspen/models/baseline.bkp`), so no result embeds a machine-specific path.
6. **API worker** (`worker.py`): a separate process that the FastAPI backend launches for each on-demand run.

The batch scripts in `aspen/automation/` use the same chain: `run_baseline.py` (baseline and no-heat-integration models), `run_sensitivity.py` (Section 15), `run_equilibrium_grid.py` (Section 14), `run_scenarios.py` (named scenarios of `config/scenarios.json`), `verify_candidates.py` (re-solves the optimisation candidates in Aspen and compares them with the Python model, Section 18) and `capture_screenshots.py` (GUI figures).

<!-- data: backend/amcrax/aspen/runner.py _rel(); results/simulations/baseline.json model_file -->

## 13.2 COM interface used

Table: **Table 13.1.** COM members and variable-tree paths used by AmCraX (`<s>` stream, `<b>` block, `<c>` component). *Source: backend/amcrax/aspen/session.py, extract.py, runner.py; aspen/automation/run_baseline.py.*

| Purpose | Call or node | Notes |
|---|---|---|
| Start server | `win32com.client.DispatchEx("Apwn.Document.41.0")` | V15 ProgID; new process each time; its pids are recorded |
| Open model | `InitFromArchive2(<path>)` | `.inp`, `.bkp` and `.apw` |
| Headless operation | `SuppressDialogs = 1`, `Visible = 0` | set after opening |
| Reset | `Reinit()` | before each run, so no run inherits a previous solution |
| Run | `Engine.Run2()` (synchronous), then `Engine.IsRunning` check | returns after the results are loaded into the tree |
| Node access | `Tree.FindNode(path).Value`, `.UnitString`, `.Elements`, `.AttributeValue(12)` | attribute 12 = HAP_COMPSTATUS |
| Stream results | `\Data\Streams\<s>\Output\` `TEMP_OUT`, `PRES_OUT`, `MOLEFLMX`, `MASSFLMX`, `HMX_FLOW`, `VFRAC_OUT` (all `\MIXED`); `MOLEFLOW`, `MOLEFRAC`, `MASSFRAC` `\MIXED\<c>` | |
| Block results | `\Data\Blocks\<b>\Output\QCALC`, `B_TEMP`, `B_PRES`; Pump `WNET`, `BRAKE_POWER`; HeatX `HX_DUTY`, `HOT_TEMP`, `COLD_TEMP`, `HX_DTLM`, `HX_UA` | |
| Run messages | `\Data\Results Summary\Run-Status\Output\PER_ERROR` (children) | errors, warnings, input translation |
| Inputs changed in place | `\Data\Streams\FEED\Input\TOTFLOW\MIXED`, `FLOW\MIXED\<c>`; `\Data\Blocks\<b>\Input\TEMP`; `\Data\Blocks\PSA\Input\FRACS\H2PROD\MIXED\<c>`; `\Data\Blocks\FEHE\Input\VALUE` | |
| Native sensitivity | `\Data\Model Analysis Tools\Sensitivity\STEMP\Output\SENSVAR` | read by `run_baseline.py` |
| Save / release | `SaveAs(<path>)`; `Close()`, `Quit()`, `pythoncom.CoUninitialize()` | then process check (Section 13.4) |

## 13.3 Input changes, convergence and errors

Inputs that change the model structure (heat integration, reactor pressure, burner excess air, property method) cause a **new input file to be generated**. All others (reactor temperature, feed flow and water, FEHE approach, PSA fractions, PSA feed and stack temperatures) are **written in place** into the loaded model, followed by `Reinit` and a run. This avoids restarting Aspen for every point, keeps the generated file the only definition of the model and means a structural change can never leave stale specifications behind; one model load serves every point of a pressure level. Calculator TLINK, present only in the baseline models built for STEMP, overwrites the HEATER and FEHE temperatures from the reactor temperature, so `run_sensitivity.py` varies the FEHE approach in models generated without it.

The engine is run synchronously: `Run2()` returns only after the results are in the variable tree. An earlier asynchronous loop (`Run2(1)` and polling `IsRunning`) let one point of the equilibrium grid be read while results were still loading, which produced a stale heat duty at 600 °C and 30 bar (IDEAL). The validation matrix caught the defect (Section 14); the run call was corrected and the grid regenerated with every point re-initialised, plus a repeatability check of four points in independent sessions (maximum deviation 0 in conversion and duty) and a check that IDEAL duties do not vary with pressure at fixed temperature (maximum spread 3.25 × 10^−7^ kJ/mol).

<!-- data: backend/amcrax/aspen/session.py AspenSession.run; aspen/automation/run_equilibrium_grid.py REPEAT_CHECK; aspen/runs/equilibrium_rerun.log -->

A run is accepted only after three checks: the HAP_COMPSTATUS bit flags of every block (32 = results with errors, 2 = no results, 4 = warnings), the Run-Status messages, and the presence of results in every block. The baseline status records `converged = true` with no errors or warnings (Figure 13.1) and one information message from input translation (PRKBV binary parameters retrieved from the EOS-LIT databank). Any `AspenError` or validation error produces a result with `has_errors = true` and no extracted values; the next case forces a clean reload. Failed runs are recorded, never skipped.

<!-- data: results/simulations/baseline.json status; backend/amcrax/aspen/runner.py IN_PLACE_FIELDS, _structural_key -->

`get_quantity` compares each node's `UnitString` with the expected unit (°C, bar, kmol/hr, kg/hr, kW) and raises an error on a mismatch, so a hand-edited model cannot be mis-scaled silently. Quantities without a contract unit keep the Aspen unit, e.g. FEHE UA = 1590.96 `cal/sec-K` (Section 11.2).

![**Figure 13.1.** Aspen Plus run-status summary of the automated baseline run: completion status and the messages that the automation reads through `PER_ERROR` before any result is accepted. The user-name and host-computer fields are masked and labelled "(masked)". *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/15_run_status.png){width=95%}

## 13.4 Locking, time-outs and process isolation

A cross-process lock, `aspen_lock()` (`msvcrt.locking` on `aspen/runs/.aspen.lock`, waiting up to 900 s), guarantees one Aspen instance at a time for batch scripts and API requests alike. `AspenSession` records the pids of the `AspenPlus.exe` processes it starts in `aspen/runs/.session_pids`. On closing it calls `Close` and `Quit`, uninitialises COM and waits up to 15 s; a process still alive is terminated by pid. Because a holder of the lock knows that no automation session is alive, `aspen_lock()` terminates any recorded pid that still runs: an instance orphaned by a killed worker. Only instances started by the automation are ever terminated; other Aspen windows on the machine are not touched. A second `InitFromArchive2` on a live V15 document failed with "Unable to open file", so opening another file restarts the server.

The FastAPI backend never loads COM. It runs each case as `python -m amcrax.aspen.worker --inputs <json> --output <json> --timeout <s>`; exit code 0 means a result file was written (its status still has to be inspected), 1 an Aspen failure and 2 invalid inputs. Time-outs are enforced at the worker-process level: the API kills the worker's process tree after a wall-clock limit (default 600 s including the lock wait, `AMCRAX_ASPEN_TIMEOUT_S`) and reports the job as timed out; the next lock holder removes the orphaned Aspen instance. The session itself also rejects a solve that exceeds its limit (180 s by default). A COM fault or a hung engine therefore cannot block or crash the web server.

<!-- data: backend/amcrax/aspen/runner.py aspen_lock; backend/amcrax/aspen/session.py kill_orphaned_sessions, close; backend/amcrax/aspen/worker.py main; backend/amcrax/api/jobs.py ASPEN_TIMEOUT_S, ASPEN_SOLVE_TIMEOUT_S, _kill_tree -->

## 13.5 Performance, reproducibility and screenshots

The recorded engine times of the full flowsheet are 2.042 s (baseline, including the ten-point STEMP block) and 2.108 s (without FEHE). The regenerated equilibrium grid (168 single-reactor points, both property methods, every point re-initialised, plus repeatability runs) took from 16:14:57 to 16:23:40, i.e. 523 s including all Aspen start-ups. The model-open time is logged only to the console and is not quoted.

<!-- data: results/simulations/baseline.json status.engine_time_s; results/simulations/baseline_no_hi.json status.engine_time_s; aspen/runs/equilibrium_rerun.log (start 16:14:57, exit 16:23:40) -->

Reproducibility rests on the input file being the model: every case is regenerated from `CaseInputs` by `inp_writer.py`; working copies go to `aspen/runs/<study>/`, never to `aspen/models/`, where only `run_baseline.py` saves the reference models. Every result JSON carries its inputs, its model file (relative path), the Aspen messages and the engine time.

`capture_screenshots.py` opens the baseline model under the lock with the GUI visible, navigates the navigation pane through UI Automation (tree-item selection), opens each form by posting an Enter key to the Aspen window's own message queue, and captures the window with `PrintWindow`. It takes over neither mouse nor keyboard and never saves the model.

## 13.6 Lessons from surveyed repositories

Five public repositories were read (survey `docs/reference_projects/github_survey.md`); no code was copied:

- zwang1995/Aspen-Plus-Automation (MIT): `InitFromArchive2` and `Reinit` adopted; its asynchronous run with `IsRunning` polling was adopted first and later replaced (Section 13.3); its kill of every `AspenPlus.exe` was rejected in favour of pid-scoped clean-up.
- beykal-lab/aspen-python-automation (CC-BY-4.0): reads results without a convergence check, which motivated the mandatory status check.
- thirakorn-mokkawes-59/aspen-mcp (MIT): V15 evidence for ProgID 41.0 and `\MIXED` substream nodes.
- EPEL-SNU/Aspen_Plus_MCP (MIT): Run-Status `PER_ERROR` messages and single-threaded COM use.
- adk23333/py2aspen (BSD-3-Clause): not usable (V14 only).

The repositories disagree about the per-block `BLKSTAT` code, so AmCraX uses HAP_COMPSTATUS and Run-Status messages instead.

## 13.7 Limitations

The automation requires Windows, pywin32 and a licensed Aspen Plus V15; other versions need a different ProgID. Only one Aspen instance runs at a time, so API requests queue behind the lock. The node paths in Table 13.1 were verified on this model only.
