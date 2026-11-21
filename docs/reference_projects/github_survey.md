# Third-party repository survey (Aspen automation and numerical stack)

Survey date: 2026-11-21. Method: one unauthenticated GitHub REST call per repository (header `User-Agent: generic-client`), plus `git clone --depth 1` and a read of the code for the five small Aspen repositories (clones in `docs/reference_projects/_clones/survey/`, scratch, not committed). No code was copied. No Aspen/COM call was made by this survey; every node path below is **as used by the repository, not verified against our V15 model** until the coordinator tests it.

## 1. Summary table

| Repository | Exists | Licence (API SPDX) | Last push | Stars | What it is | Reuse decision | Licence compatible |
|---|---|---|---|---|---|---|---|
| pywin32/pywin32 (redirects to mhammond/pywin32) | yes | API returned none (project licence is PSF-style; not machine-verified) | 2026-11-12 | 5637 | Python bindings for Windows APIs, incl. `win32com.client` | dependency (already installed, 312) | yes (permissive, PSF-style - verify text before redistribution) |
| Cantera/cantera | yes | API: NOASSERTION (project states BSD-3-Clause; not machine-verified) | 2026-11-01 | 888 | Chemical kinetics, thermodynamics, transport | dependency, optional cross-check of thermo/equilibrium (installed 3.2.0) | yes (BSD-3) |
| scipy/scipy | yes | BSD-3-Clause | 2026-11-20 | 15231 | Scientific computing (ODE, optimise, root finding) | dependency (installed 1.18.1) | yes |
| pyomo/pyomo (now Pyomo/pyomo) | yes | API: NOASSERTION (project states BSD-3-Clause; not machine-verified) | 2026-11-21 | 2563 | Algebraic modelling language for optimisation | dependency, optional (installed 6.11.0) | yes (BSD-3) |
| plotly/plotly.py | yes | MIT | 2026-11-19 | 18916 | Interactive plotting library | dependency (installed 7.1.0) | yes |
| xyflow/xyflow | yes | MIT | 2026-11-19 | 39101 | React Flow / Svelte Flow monorepo (npm `@xyflow/react`) | dependency (npm, frontend) | yes |
| EPEL-SNU/Aspen_Plus_MCP | yes | MIT | 2026-10-07 | 8 | MCP server, very large (about 259 KB single server file) with flowsheet builder, EO, TEA | pattern reference only | MIT; patterns only, nothing copied |
| beykal-lab/aspen-python-automation | yes | CC-BY-4.0 | 2026-04-12 | 7 | Two scripts: LHS sampling and optimiser callback | pattern reference only | CC-BY-4.0 needs attribution for copied material; we copy nothing |
| zwang1995/Aspen-Plus-Automation | yes | MIT | 2024-10-17 | 37 | Small pywin32 class + parametric sweep of a distillation column | pattern reference only | MIT; patterns only |
| adk23333/py2aspen | yes | BSD-3-Clause | 2026-08-21 | 13 | comtypes wrapper (typed blocks/streams), V14 only | not used (pattern reference for ExportType enum) | BSD-3; no code taken |
| thirakorn-mokkawes-59/aspen-mcp | yes | MIT | 2026-06-07 | 2 | MCP server, 85 tools, explicitly Aspen V15 (41.0) | pattern reference only (best V15 evidence) | MIT; patterns only |

Notes on licence column: GitHub's detector returned `NOASSERTION` or nothing for pywin32, Cantera and Pyomo. The BSD-3 / PSF statements for these three come from general knowledge of the projects, not from this survey's API call, so label them "unverified by survey". All three are already installed in the venv and used as ordinary libraries; no source is vendored.

## 2. Per-repository notes

### pywin32 (dependency)
Provides `win32com.client.Dispatch`, `pythoncom` (COM apartments). The three COM repositories that use it (zwang, beykal, aspen-mcp, EPEL) all go through `win32com.client.Dispatch("Apwn.Document")`. Installed version 312 in our venv. Risk: COM objects are apartment-threaded; use one thread for all Aspen calls (aspen-mcp and EPEL both built a single-thread funnel for this reason).

### Cantera (optional cross-check)
Installed 3.2.0. Not a dependency of the AmCraX thermodynamics module (which must be independent); usable only as a validation cross-check, labelled `python_model` / `literature` as appropriate. Must not tune our module to match it.

### SciPy / Pyomo / plotly.py / xyflow
Standard libraries, all alive (pushed within the last two weeks). SciPy and plotly are BSD/MIT. xyflow is the upstream of React Flow; consume via npm, not by cloning.

### zwang1995/Aspen-Plus-Automation (pattern reference; 5 small files, V12 then generic)
- ProgID: v1 `Dispatch("Apwn.Document.38.0")` (comment maps V10=36.0, V11=37.0, V12=38.0), v2 `Dispatch("Apwn.Document")` (version-independent). Our V15 is `Apwn.Document.41.0`.
- Open: `Application.InitFromArchive2(abspath)` for both `.bkp` and `.apw` (the README claims both).
- Visibility and dialogs: set **after** open: `Application.Visible = 0/1`, `Application.SuppressDialogs = 0/1`. Defaults in the wrapper are Visible=0, SuppressDialogs=0 (dialogs NOT suppressed by default; the example passes 1).
- Run: v1 `Engine.Run()` (asynchronous, hence the poll loop on `Engine.IsRunning == 1` with `Engine.Stop`), v2 `Engine.Run2()` (synchronous; the poll code is commented out).
- Reset between runs: `Application.Reinit()`.
- Inputs: `Tree.FindNode(r"\Data\Blocks\ED\Input\NSTAGE").Value = n`, `...\Input\BASIS_RR`, `\Data\Streams\SOLVENT\Input\TOTFLOW\MIXED`, `\Data\Blocks\ED\Input\FEED_STAGE\FEED`.
- Outputs: `\Data\Streams\DIST1\Output\MOLEFRAC\MIXED\C4H8`, `\Data\Blocks\ED\Output\REB_DUTY`.
- Convergence/errors: v2 reads `\Data\Results Summary\Run-Status\Output\UOSSTAT` as a whole-flowsheet error flag (stored in a column named `hasERROR`, but UOSSTAT is a status integer, not a boolean; 0 = no unit-operation error). v1 also had a `.his` history-file scan for the string "ERROR" using `\Data\Results Summary\Run-Status\Output\RUNID` to build the filename (relative path `../simulation/<RUNID>.his`).
- Enumerate: `Tree.FindNode(r"\Data\Streams").Elements` / `\Data\Blocks`, iterate and read `.Name`.
- Close: `Application.Quit()`; plus a WMI `taskkill` of `AspenPlus.exe` (kills every Aspen process of the user - do NOT copy this pattern on a shared machine).
- Bugs/risks: `SuppressDialogs` default 0 can hang headless runs; `taskkill` is indiscriminate; `hasERROR` naming misleading; no timeout on `Run2`; the v1 history path is hard-coded relative. `time.sleep(2)` after open is a guess.
- Decision: pattern reference only. MIT, compatible.

### beykal-lab/aspen-python-automation (pattern reference; 2 scripts)
- ProgID `Dispatch('Apwn.Document')`; open with `InitFromArchive2(abspath('X.bkp'))`; run with `Engine.Run2()`. No `Visible`, no `SuppressDialogs`, no `Reinit`, no explicit quit (the `Close` line is commented out), so Aspen is left running; no convergence check at all.
- Inputs: `\Data\Streams\S1\Input\TOTFLOW\MIXED`, `\Data\Blocks\B14\Input\TEMP`, `\Data\Blocks\B17\Input\PRES`.
- Outputs: `\Data\Streams\S3\Output\TEMP_OUT\MIXED`, `\Data\Streams\S60\Output\MASSFRAC\MIXED\NA+`, `\Data\Streams\S60\Output\MASSFLOW\MIXED\NA+`, `\Data\Blocks\B<n>\Output\QNET` (summed over positive values only for total energy).
- Bugs/risks: `main.py` references undefined `S1` (script does not run as shipped); loop `range(0, num-1)` drops the last sample; non-raw strings like `"\Data\Streams\S60\Output\MASSFRAC\MIXED\CL-"` work only because `\D`, `\S`, `\O`, `\M`, `\C` are not escape sequences (a `\t`-style segment such as `\TEMP...` after a backslash would break; use raw strings); output file handle never closed; results are read even when the run failed. Nodes read without a convergence check, so failed runs return stale numbers.
- Decision: pattern reference only. CC-BY-4.0 requires attribution if any material were copied; we copy none.

### adk23333/py2aspen (not used; V14, comtypes)
- Library built on `comtypes` (`client.CreateObject(progid)` then late-bound `lazybind`); ships a type library `tlb/v14/happ.tlb`. Only `AspenVersionCode.V14 = "40.0"` is defined and `version` property does `AspenVersionCode(code)` on the app name, so on V15 (41.0) it would raise `ValueError`. Not V15 ready.
- Open: `InitFromArchive2` (bkp), `InitFromFile` (apw, not `InitFromFile2`), `InitNew2`, `Restore2`; save `Save`, `SaveAs`, `WriteArchive2`; `Export(type, path)` with an `ExportType` enum (BACKUP=1, REPORT=2, SUMMARY=3, INPUT=4, ... RUN_MSG=6, INPUT_WITH_GRAPHICS=18) useful as documentation of `Export`.
- Run: `app.Run2()` (on the Application object; others use `Engine.Run2()`), `Engine.Stop()`, `Reinit()`. `Visible`, `SuppressDialogs` as app attributes.
- Tree access through `Tree.Elements("Data").Elements("Blocks")` / `("Streams")` and `node.Elements("Input").Elements(alias)`; `AttributeValue[...]` calls for unit handling via the `Unit Table` node (`Elements.Label(0, col)`).
- Close: `app.Close()` (not `Quit()`), which leaves the AspenPlus process alive in some builds (not verified here).
- Decision: not used as a dependency (V14 only, heavy abstraction, comtypes path differs from our pywin32 plan). The HAP attribute IDs in `aspen_type.py` (e.g. HAP_UNITROW=2, HAP_BASIS=13, HAP_OUTVAR=18, HAP_FULLNAME=65) are documentation-grade reference only. BSD-3, compatible.

### thirakorn-mokkawes-59/aspen-mcp (pattern reference; the only V15-explicit source)
- ProgID `win32com.client.Dispatch("Apwn.Document")`, comment says connected as "v15 / 41.0". Sets `SuppressDialogs = True` immediately after Dispatch and reads `app.Name` as a liveness check.
- Single dedicated COM apartment thread (`pythoncom.CoInitialize()` plus `PumpWaitingMessages`), 55 s call timeout, 3 retries with back-off, reconnect on HRESULTs 0x800706BA / 0x800706BE / 0x80010108 / 0x800706BF / 0x80004005.
- Root access: `app.RootModel("")` then `.FindNode(path)` or `.Elements(name)` walks; its README claims `Tree` equivalence. Others use `app.Tree.FindNode` directly.
- Open: `InitFromFile(path)` for `.apw`; close `app.Close()`; save `Save()` / `SaveAs(path)`; blank-template copied to `%TEMP%` with PID suffix instead of `InitNew` ("COM references unstable").
- Run: `app.Run2()` (synchronous). `reinit_and_run`: `app.Engine.Reinit()` then `app.Run2()`. Async option `Engine.Run()`. `Engine.Stop()`, `Engine.IsRunning`, `Engine.Ready`.
- Other app-level members used: `Visible`, `RefreshOff` (batch refresh), `RunScript(file)`, `Generate(file, mode)`, `Readback(file, mode)`.
- Results nodes: stream `\Data\Streams\<s>\Output\RES_TEMP`, `RES_PRES`, `RES_VFRAC`, `RES_MASSFLOW`, `RES_MOLEFLOW`, `RES_VOLFLOW`, `MW`, `PRES_OUT`; block `\Data\Blocks\<b>\Output\BLKSTAT`, `BLKMSG`, `PER_ERROR`, `PROPSTAT`; tear streams `\Data\Convergence\Tear\...`.
- Inputs: **stream inputs need the MIXED substream child**: `\Data\Streams\<s>\Input\TEMP\MIXED`, `\PRES\MIXED`, `\FLOW\MIXED\<comp>`, `\TOTAL\MIXED`; writing the parent node gives an under-specified error (AE_UNDERSPEC). `HEATER` default `HEATOPT=CONST-DUTY`; set `\Data\Blocks\<b>\Input\HEATOPT = "CONST-TEMP"` before specifying temperature. `node.SetValue(0, value)` is used in place of `.Value =`. Node-attribute writes go through `AttributeValue` property-put.
- Convergence: per block `BLKSTAT`. The repository's own comment: "In Aspen v15 (41.0), BLKSTAT=0 means converged, not uncalculated; BLKSTAT=2 means not converged; BLKMSG holds the error text". Pre-run feed completeness check (TEMP, PRES, FLOW or TOTAL on every feed stream). Warning that an incomplete `\Data\Utilities\<name>\Input` marks the whole simulation as input-incomplete.
- Bugs/risks: (1) BLKSTAT mapping disagrees with EPEL (below) - must be tested; (2) the `stat_map` it prints ({0 OK, 1 converged, 2 not converged, 3 warning}) is inconsistent with its own docstring; (3) `close_file` uses `Close()` and drops the reference without `Quit()`; (4) a 45-55 s timeout on a synchronous `Run2` can leave Aspen busy after the Python side gave up; (5) README comments are Chinese with mojibake on a default Windows console; (6) 2 stars, young project.
- Decision: pattern reference only. MIT, compatible.

### EPEL-SNU/Aspen_Plus_MCP (pattern reference; large research code)
- ProgID `win32.Dispatch('Apwn.Document')`; `SuppressDialogs = True` set **before** `InitFromArchive2(abspath)`; no `Visible` by default (an explicit tool sets `Visible = bool(visible)`).
- Run: `Engine.Reinit()` then `Engine.Run2()`. Their note: on that Aspen build `Engine.Run2()` is synchronous, `Engine.IsRunning` stayed False, and block statuses were final as soon as it returned (observed 1.7 s and 3.8 s on two flowsheets). No polling or `sleep` needed.
- Single-thread executor (`ComFunnel`) because Apwn.Document is STA.
- Close: `global_aspen.Close()`; process-level fallback kills `AspenPlus.exe` via psutil (indiscriminate; avoid).
- Run status: `\Data\Results Summary\Run-Status\Output` children `TOTSTAT`, `PER_ERROR`, `CVSTAT`, `ITSTAT`, `UOSSTAT`, `RSTAT`, `UOSSTAT2`; messages: `...\Run-Status\Output\PER_ERROR` (iterate `.Elements`, read `.Value`). Per block `\Data\Blocks\<b>\Output\BLKSTAT`, `...\Output\PER_ERROR`.
- Stream reads: `\Data\Streams\<s>\Output\STR_MAIN\TEMP\MIXED`, `...\STR_MAIN\PRES\MIXED`, `...\STR_MAIN\MOLEFLOW\MIXED\<cid>`, `...\STR_MAIN\MOLEFRAC\MIXED\<cid>`, total `...\Output\MOLEFLMX\MIXED`; fall back to `...\Input` if `STR_MAIN` is missing. Stream writes through `...\Input\TEMP\MIXED`, `PRES\MIXED`, `BASIS\MIXED` (= "MOLE-FLOW"), `FLOW\MIXED\<comp>`.
- Block reads: `QCALC`, `QNET`, `B_VFRAC` (outlet vapour fraction) under `\Data\Blocks\<b>\Output\`.
- Slash-form paths also work: `Tree.FindNode("Data/Blocks/<b>/<tag>")`.
- Bugs/risks: `simulation_success()` treats `BLKSTAT == 1` as **failed**, while the other server's `get_simulation_status` treats anything `!= 0` as failed and the aspen-mcp repository says 2 = not converged; the three sources disagree. We must establish BLKSTAT semantics ourselves on our own model (run a deliberately infeasible case) and not rely on any of them. Also the server file is 259 KB (hard to audit); it embeds LLM/evaluation code irrelevant to AmCraX.
- Decision: pattern reference only. MIT, compatible; the `vendor/` code is under the same root licence, nothing taken.

## 3. Aspen COM node path cheat-sheet (from the repos; to be verified on our V15 model by the coordinator)

ProgID and lifecycle
- `win32com.client.Dispatch("Apwn.Document")` (version-independent) or `"Apwn.Document.41.0"` (V15, explicit). Repos using the independent ID: zwang v2, beykal, EPEL, aspen-mcp.
- Open: `app.InitFromArchive2(abs_path)` (.bkp, used by 3 repos); `app.InitFromFile(abs_path)` (.apw, aspen-mcp and py2aspen; `InitFromFile2` is used by none of the five). Always pass absolute paths.
- Dialogs: `app.SuppressDialogs = True` (set before open in EPEL, right after Dispatch in aspen-mcp; set after open in zwang). `app.Visible = False/True`. aspen-mcp also exposes `app.RefreshOff`.
- Run: `app.Engine.Reinit()` then `app.Engine.Run2()` (synchronous per EPEL's observation; zwang v1 used the async `Engine.Run()` with `Engine.IsRunning` polling). `app.Run2()` on the Application is used by aspen-mcp and py2aspen. Stop: `Engine.Stop()`. Status flags: `Engine.IsRunning`, `Engine.Ready`.
- Close: `app.Quit()` (zwang) or `app.Close()` (aspen-mcp, EPEL, py2aspen). Which one releases the AspenPlus process is not established by these repos; test it.
- All COM calls from one thread (STA); initialise with `pythoncom.CoInitialize()` on any non-main thread.

Tree access
- `app.Tree.FindNode(r"\Data\...").Value` (zwang, beykal, EPEL); `app.RootModel("")` entry point in aspen-mcp. Use raw strings for paths.
- `node.Elements` iterates children (`.Name`, `.Value`); `node.Elements(i)` or `node.Elements("Name")`; `node.Elements.Count`.
- Write: `node.Value = x` or `node.SetValue(0, x)`.

Stream paths (`<s>` = stream id, `<c>` = component id)
- Inputs: `\Data\Streams\<s>\Input\TEMP\MIXED`, `\PRES\MIXED`, `\TOTFLOW\MIXED` (zwang/beykal) or `\TOTAL\MIXED` (aspen-mcp), `\FLOW\MIXED\<c>`, `\BASIS\MIXED`. Parent without `\MIXED` raises AE_UNDERSPEC.
- Results (two families seen): `\Data\Streams\<s>\Output\TEMP_OUT\MIXED`, `\PRES_OUT\MIXED`, `\MOLEFRAC\MIXED\<c>`, `\MASSFRAC\MIXED\<c>`, `\MASSFLOW\MIXED\<c>`, `\MOLEFLMX\MIXED` (total mole flow); and the summary family `\Output\STR_MAIN\TEMP\MIXED`, `\STR_MAIN\PRES\MIXED`, `\STR_MAIN\MOLEFLOW\MIXED\<c>`, `\STR_MAIN\MOLEFRAC\MIXED\<c>`; and `\Output\RES_TEMP`, `RES_PRES`, `RES_VFRAC`, `RES_MASSFLOW`, `RES_MOLEFLOW`, `MW`. Units are those set in the model (check `HAP_UNITROW`/unit set; METCBAR gives bar, C, kmol/hr); do not assume.

Block paths (`<b>` = block id)
- Inputs: `\Data\Blocks\<b>\Input\TEMP`, `\PRES`, `\NSTAGE`, `\BASIS_RR`, `\HEATOPT` (set `CONST-TEMP` before TEMP on HEATER).
- Results: `\Data\Blocks\<b>\Output\QNET`, `QCALC`, `REB_DUTY` (RadFrac), `B_VFRAC`.
- Enumerate: `\Data\Streams` and `\Data\Blocks` via `.Elements`.

Convergence and errors
- Per block: `\Data\Blocks\<b>\Output\BLKSTAT` (value meaning is DISPUTED between repos: aspen-mcp says 0 = OK, 2 = not converged; EPEL treats 1 as failed), `...\Output\BLKMSG`, `...\Output\PER_ERROR` (list of messages), `...\Output\PROPSTAT`.
- Whole run: `\Data\Results Summary\Run-Status\Output\` with `UOSSTAT` (unit-operation status, 0 = normal), `PER_ERROR` (error messages list), `TOTSTAT`, `CVSTAT`, `ITSTAT`, `RSTAT`, `UOSSTAT2`, `RUNID` (name of history file `<RUNID>.his`).
- Tear streams: `\Data\Convergence\Tear\...` (aspen-mcp).
- Recommended for AmCraX (suggestion, not copied): after `Run2`, require `UOSSTAT == 0`, no entries in `Run-Status\Output\PER_ERROR`, and all per-block `PER_ERROR` empty; determine BLKSTAT semantics experimentally; record the raw codes in the result JSON.

## 4. Risks to flag to the coordinator
1. BLKSTAT semantics conflict across three sources; do not hard-code until tested on our model.
2. `Engine.Run2()` is asserted synchronous by two repos but one older repo used async `Run()`; add our own timeout and check `Engine.IsRunning` after return.
3. Indiscriminate process kills (`taskkill`, `psutil`) in two repos: never copy; clean up our own instance only.
4. `Close()` versus `Quit()` unresolved; test that no orphan `AspenPlus.exe` remains.
5. Stream input nodes need `\MIXED`; HEATER needs `HEATOPT=CONST-TEMP` before a TEMP spec; an incomplete utility definition blocks the whole run.
6. Unit sets: node values come in model units; our contract needs degC, bar, kmol/h, kW; read the unit set and convert explicitly.
7. None of the five repos was run; all path/behaviour statements are from reading source, with the repositories' own claims attributed to them.
