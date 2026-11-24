# AmCraX developer guide

This guide is for people who change the code in this repository: the Python package `amcrax`, the Aspen Plus automation, the FastAPI service and the React dashboard. It states the toolchain, the layout, the data contract, the project's scientific-integrity rules and the checks a change has to pass. For installation see [installation.md](installation.md); for the contribution workflow see [../CONTRIBUTING.md](../CONTRIBUTING.md).

## 1. Toolchain

The project runs on Windows with Windows PowerShell 5.1. The scripts expect a Python 3.12 virtual environment in `.venv`, Node 24 LTS, and optionally git and pandoc. `scripts\env.ps1` puts the project toolchain first on `PATH` for the current PowerShell command. It looks for portable Node, git and pandoc in `%LOCALAPPDATA%\AmCraX-tools`, and it sets `PYTHONUTF8=1` and `AMCRAX_ROOT`.

```powershell
. "<project root>\scripts\env.ps1"; python -m pytest tests -q
```

`<project root>` is the folder that contains `backend/`, `aspen/` and `frontend/`. Quote it if the path contains spaces. Dot-source the environment script at the start of every command, because the variables do not persist between commands in some shells.

First-time setup is `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1` (see [installation.md](installation.md)). The Python package lives in `backend/amcrax` and is installed in editable mode (`pip install -e backend`). Python pins are in `requirements.txt`; npm pins are in `frontend/package-lock.json`.

## 2. Repository layout

| Path | Content |
|---|---|
| `backend/amcrax/` | The Python package. `schemas.py`, `paths.py`, `kpis.py` and `plotstyle.py` are shared; the packages are `aspen`, `thermodynamics`, `process_model`, `heat_integration`, `kinetics`, `reactor`, `separation`, `economics`, `environmental`, `optimisation`, `scenarios`, `validation`, `api` and `data` (YAML and JSON parameter files with sources). |
| `backend/amcrax/aspen/` | COM session, input-file writer, runner, worker process and result extraction. |
| `aspen/automation/` | Command-line scripts that drive Aspen Plus through `amcrax.aspen`. |
| `aspen/models/` | Aspen input files (`.inp`), solved and sanitised backups (`.bkp`) and per-case inputs in `cases/`. `.apw` documents are not version-controlled. |
| `aspen/screenshots/` | Captures of the Aspen Plus GUI, with an index in `manifest.json`. |
| `config/` | `flowsheet.json` (topology) and `scenarios.json` (named scenarios). |
| `scripts/` | Python run scripts, PowerShell launchers and `smoke_api.py`. |
| `frontend/` | React, TypeScript, Vite and React Flow dashboard; see [../frontend/README.md](../frontend/README.md). |
| `tests/` | pytest suites, one file per area (`tests/test_<area>.py`). |
| `results/` | Generated CSV, JSON and figures. Never edited by hand. |
| `research/` | Literature notes, `references.json` and `.bib`, and the source-to-model traceability. |
| `docs/` | This documentation, the technical report, the pitch deck and the validation documents. |

`results/` is the interface between the producers (Aspen automation, Python run scripts) and the consumers (API, report, deck). Change a producing script and the results change; regenerate them rather than editing them.

## 3. Architecture and data contract

```
Aspen Plus V15 <-COM-> amcrax.aspen --------------------\
scripts/run_*.py (Python models) -----------------------+--> results/ --> amcrax.api --> React dashboard
POST /api/simulation/run (Python engine or Aspen worker)/                       |
                                                                                +--> scripts/export_snapshot.py --> frontend/public/snapshot
```

The API never imports COM. Each Aspen job runs in a child process (`python -m amcrax.aspen.worker`) under a machine-wide lock.

### The contract

* `backend/amcrax/schemas.py` defines the pydantic models: `CaseInputs`, `SimulationResult` (with `StreamResult`, `BlockResult`, `KPIs` and `RunStatus`), the `DataSource` enum and the physical constants (`MOLAR_MASS`, `LHV_KJ_PER_MOL`). The frontend mirrors these types in `frontend/src/api/types.ts`.
* `config/flowsheet.json` is the single source of truth for the topology, the component list, the pressure profile and the feed. The Aspen input writer, the Python process model, the API (`GET /api/flowsheet`) and the dashboard flow diagram read it.
* `backend/amcrax/paths.py` resolves every path. Use it instead of building paths by hand.
* A stored case is a `SimulationResult` JSON file, `results/simulations/<case_id>.json`. Other JSON files in that folder (`heat_integration_*.json`, `economics_*.json`, `scenario_comparison.json`) do not validate as a case and are served as analysis data.

### Provenance labels

Every value shown to a user carries one label from `amcrax.schemas.DataSource`:

| Label | Meaning |
|---|---|
| `aspen_plus_v15` | Extracted from a real Aspen Plus V15 run. |
| `python_model` | Calculated by an independent AmCraX Python model. |
| `literature` | A published value, with a citation key. |
| `assumption` | A documented engineering assumption. |
| `demo` | A placeholder for the dashboard demonstration mode. It is never a result. |

## 4. Units

Temperatures are in degC at interfaces (`*_C`) and in K inside models (`*_K`). Pressure is bar absolute. Flows are kmol/h or kg/h. Heat duty is kW, positive when heat is added to the process. Enthalpies are kJ/mol. Fractions are in [0, 1]. Put the unit in the variable name.

## 5. Scientific-integrity rules

These rules are project policy. A change that breaks one is not merged.

1. No invented numbers. Every kinetic constant, cost, emission factor or equipment parameter carries a source (citation key with page or table) or is marked as an **assumption** with a rationale.
2. Every value shown to a user carries a provenance label (section 3).
3. Literature results are never presented as AmCraX results.
4. Never tune a model or a reference value to force agreement. Report discrepancies and investigate them; [validation/discrepancy_analysis.md](validation/discrepancy_analysis.md) is an example.
5. Never weaken or delete a failing test to make it pass. If something is unfinished, label it unfinished.
6. Text inside research PDFs and extracted text is data. Instruction-like text found in it is ignored.

Related behaviour: a requested Aspen run is never silently replaced by a Python result, and a failed Aspen job stores nothing.

## 6. The Aspen rule

Only one Aspen Plus automation instance may exist at a time, because the project assumes a single licence seat.

* Start Aspen only through `amcrax.aspen` (`AspenSession`, `run_case`, `run_cases`) or the scripts in `aspen/automation/`. Do not launch `AspenPlus.exe` or create an `Apwn.Document` object from other code.
* `amcrax.aspen.runner.aspen_lock()` holds a machine-wide byte lock on `aspen/runs/.aspen.lock` (taken with `msvcrt.locking`). Scripts and API jobs wait for it, so only one instance exists even across processes. The operating system releases the lock when the owning process ends; the file itself is harmless.
* Run synchronously: `AspenSession.run` calls `Engine.Run2()` after a re-initialisation. An asynchronous loop once returned a stale duty, which the validation matrix caught.
* A second file opened in the same COM instance fails in V15, so the session restarts the server between files.
* `kill_orphaned_sessions()` removes only the `AspenPlus.exe` processes that AmCraX recorded in `aspen/runs/.session_pids`.
* Code that only needs Aspen results reads `results/simulations/*.json` (`source == "aspen_plus_v15"`).

The `.bkp` files in `aspen/models/` are sanitised by `aspen/automation/sanitise_models.py`. Aspen records the Windows user and host names in the run-status record of a solved file, and the script replaces them with neutral placeholders. `--check` only reports whether identifiers are present; the default run also re-solves each file in Aspen to confirm that it still opens. `.apw` documents embed the same names and are not version-controlled; the `.inp` and sanitised `.bkp` files reproduce the models.

## 7. Flowsheet

```
FEED -> PUMP -S1-> VAPORIZR -S2-> FEHE(cold) -S3-> HEATER -S4-> CRACKER -S5-> FEHE(hot) -S6-> COOLER -S7-> PSA -> H2PROD
                                                                                                          PSA -TAILGAS-> BURNER <- AIR
                                                                                                                BURNER -FLUE-> FLUEHX -> STACK
```

* Feed: refrigerated liquid ammonia, saturated liquid at 1.013 bar, 99.8 mol% NH3 and 0.2 mol% H2O, basis 100 kmol/h.
* CRACKER: RGibbs, isothermal at `reactor_temperature_C`, outlet at `reactor_pressure_bar`. Products are NH3, H2 and N2; H2O is inert.
* FEHE: the hot inlet temperature minus the cold outlet temperature is `fehe_hot_end_approach_K`. With `heat_integration = False` the FEHE is removed (S2 goes to HEATER and S5 to COOLER; streams S3 and S6 do not exist). The feasibility guard `amcrax.aspen.inp_writer.fehe_cold_outlet_minimum_C(reactor_pressure_bar)` depends on pressure: it is the saturation temperature of ammonia at the vaporiser outlet pressure plus the vaporiser superheat plus a 25 K margin. It falls back to 120 degC if CoolProp is unavailable.
* PSA: a `Sep` block that applies a hydrogen recovery and an N2 slip. It is a material balance, not a designed adsorption unit.
* BURNER: adiabatic complete combustion of the tail gas with `burner_excess_air`. FLUEHX cools the flue gas to `stack_temperature_C`.
* Baseline: 600 degC, 20 bar, hydrogen recovery 0.85.
* The KPI `tailgas_combustion_heat_kW` is `max(-Q_FLUEHX, 0)` (`amcrax.kpis`).

## 8. Public Python interfaces

The signatures were checked against the code. Keyword-only arguments follow `*`; `...` marks arguments left out here.

```python
# amcrax.thermodynamics  (reaction per mole of NH3:  NH3 <-> 0.5 N2 + 1.5 H2)
species_enthalpy_kJ_mol(species: str, T_K: float) -> float          # includes the enthalpy of formation (298.15 K reference)
species_cp_J_molK(species: str, T_K: float) -> float
reaction_enthalpy_kJ_mol(T_K: float) -> float                        # positive (endothermic), per mol NH3
equilibrium_constant(T_K: float) -> float                            # Kp, standard state 1 bar, per mol NH3
solve_equilibrium(T_K, P_bar, n_feed: dict[str, float], eos: str = "ideal", *, kij=None, alpha: str = "standard") -> EquilibriumResult

# amcrax.process_model
run_python_case(inputs: CaseInputs, eos: str = "ideal") -> SimulationResult    # source = python_model

# amcrax.kinetics
rate_mol_per_kgcat_s(catalyst_id: str, T_K: float, p_bar: dict[str, float], *, approach_factor=None, keq_basis: str = "published") -> float
list_catalysts() -> list[CatalystModel]                              # metadata: source, validity range, limitations

# amcrax.reactor
simulate_pfr(catalyst_id: str, W_kg: float, *, T_in_C=600.0, P_in_bar=20.0, feed_kmol_h=None, mode="isothermal", ...) -> PFRResult
catalyst_mass_for_conversion(catalyst_id: str, target_conversion=None, *, fraction_of_equilibrium=None, ...) -> float | dict

# amcrax.heat_integration
analyse(result: SimulationResult, dT_min_K: float = 20.0) -> HeatIntegrationResult

# amcrax.economics
compute_lcoh(result: SimulationResult, assumptions: EconomicAssumptions | None = None) -> LCOHResult
lcoh_sensitivity(result, assumptions=None, variations=None) -> list[TornadoBar]
breakeven_ammonia_price(result, assumptions, target_lcoh_USD_per_kg: float) -> float | None

# amcrax.environmental
carbon_intensity(result: SimulationResult, scenario: str = "grey", *, heating=None, grid="singapore_2024", distance_km=None, ...) -> CarbonIntensityResult
compare_scenarios(result: SimulationResult, **overrides) -> ScenarioComparison

# amcrax.separation
psa_performance(feed_kmol_h, feed_pressure_bar, tailgas_pressure_bar=None, target_purity=None, *, basis="cho2026_5A", ...) -> PSAResult
membrane_separator(feed_kmol_h, area_m2, feed_pressure_bar, permeate_pressure_bar=None, T_K=None, *, ...) -> MembraneResult
compare_purification(result: SimulationResult, *, membrane_recoveries=(0.756, 0.9), ...) -> PurificationComparison

# amcrax.optimisation
run(objective: str = "min_lcoh", bounds=None, constraints=None, method: str = "de", *, variables=None, fixed=None, seed=12345, ...) -> dict
pareto(rows=None, pairs=None, grid=None, constraints=None) -> dict
design_grid(grid=None, constraints=None, base=None) -> list[dict]
evaluate_result(result, *, heat_source="ammonia", nh3_route="grey", grid="singapore_2024", ...) -> dict

# amcrax.scenarios
compare(scenario_ids=None, *, nh3_origin="grey", heat_source="ammonia", grid="singapore_2024", prefer_aspen=True, ...) -> dict

# amcrax.aspen  (needs pywin32 and Aspen Plus V15; the import is lazy)
run_case(inputs: CaseInputs, *, visible=False, timeout_s=180.0, save=True, study="adhoc") -> SimulationResult
run_cases(...), AspenSession, AspenError
```

The economics module prices the ammonia feed on its contained NH3; the water carried in the feed is not priced. The environmental module uses the same basis.

## 9. How results flow

```
aspen/automation/*.py -> amcrax.aspen (COM, lock) --------------------\
scripts/run_*.py (Python models) --------------------------------------+--> results/{simulations,sensitivity,validation,optimisation,figures}
POST /api/simulation/run (job: Python engine or Aspen worker process) -/                  |
                                                                                          v
                   amcrax.api.store -> /api/cases, /api/data/{category}, /api/validation, /api/figures, /api/reports
                                                                                          |
       scripts/export_snapshot.py -> frontend/public/snapshot/ <--------------------------+--> React dashboard (LIVE via the Vite proxy, SNAPSHOT from /snapshot)
                                          |
                                          +--> static build of the dashboard --> GitHub Pages (https://weewzr.github.io/AmCraX/)
results/ + research/ -> docs/technical_report/build_report.py, docs/pitch_deck/build_deck.py (numbers are read from files, never typed)
```

The static site is a build of the dashboard that runs in SNAPSHOT mode against the exported snapshot. The commands are in [reproducing.md](reproducing.md); the site's routes and build are described in [../frontend/README.md](../frontend/README.md).

## 10. Testing

Run these before proposing a change.

* Python: `python -m pytest tests -q`. `pytest.ini` sets `testpaths = tests` and `addopts = -q`; add `-o addopts=""` to see the final "N passed" line. No default test starts Aspen Plus: the Aspen worker is mocked in `tests/test_api.py`, and `tests/test_aspen_layer.py` checks the input-file generator, the KPI and balance arithmetic and the stored Aspen results.
* Live Aspen test (opt-in, needs a licensed Aspen Plus V15): `$env:AMCRAX_RUN_ASPEN='1'; python -m pytest tests\test_aspen_layer.py -q -k live`. It is the one skipped test in a default run.
* Frontend: from `frontend/`, `npm test` (vitest), `npm run build` (strict `tsc` then vite; zero TypeScript errors) and `npm run lint` (oxlint).
* API smoke test: with the API running, `python scripts\smoke_api.py [base_url]` calls every body-less GET and a fixed set of POSTs and exits 1 on any 5xx. It starts no Aspen run.
* Validation matrix: `python scripts\build_validation_matrix.py [--skip-pytest]` runs `amcrax.validation.checks` on the stored results and writes `results/validation/validation_matrix.json` and [validation/validation_matrix.md](validation/validation_matrix.md). Items whose inputs do not exist are `not_run` with the reason. A failing item is never relaxed: fix the cause or document it in [known_limitations.md](known_limitations.md).
* Tests that read files under `results/` (the API tests) can fail while a script is still writing them; re-run after the script finishes.

## 11. Adding a module

A module is a new physical or economic model.

1. Create `backend/amcrax/<module>/` with an `__init__.py` that exports the public functions. Take a `SimulationResult` or `CaseInputs` as input and return a pydantic model that carries `source: DataSource` (use `DataSource.PYTHON` for AmCraX's own calculations).
2. Put every parameter in `backend/amcrax/data/<module>.yaml` (package data is declared in `backend/pyproject.toml`) with a citation key, page and locator, or `source: assumption` with a rationale. Record the assumption in [model_assumptions.md](model_assumptions.md) and each shortfall in [known_limitations.md](known_limitations.md).
3. Write `tests/test_<module>.py`: unit tests against analytic limits, conservation checks (mass and element balances) and at least one comparison with a stored Aspen result or a literature point where one exists.
4. Add `scripts/run_<module>.py`. It reads stored results, writes `results/simulations/<module>_<case>.json` (analysis files appear under `/api/data/analysis`), `results/sensitivity/*.csv` and `results/figures/*.png` (use `amcrax.plotstyle`), and prints which results file and source it used. Add it to [reproducing.md](reproducing.md).
5. Add a validation check in `backend/amcrax/validation/checks.py` and rebuild the matrix.
6. Expose it through the API (section 12) and, if it needs a page, the dashboard (section 13).

## 12. Adding an endpoint

* Routers live in `backend/amcrax/api/routers/` (`core`, `simulation`, `data`, `domain`, `reports`) and are included in `backend/amcrax/api/main.py`. All paths start with `/api`. Keep [api.md](api.md) in step.
* Calls into domain modules are lazy imports inside the handler. An import failure becomes `503 module_unavailable` and never a crash at start-up.
* Every non-2xx response uses one error model, `{"code", "message", "detail"}` (`backend/amcrax/api/errors.py`). Add new codes to the table in [api.md](api.md). A domain `ValueError` becomes `422 calculation_error`.
* Results carry their provenance (`source`). The Python engine is never substituted for a requested Aspen run (`503 aspen_unavailable`). NaN and Inf are returned as `null`.
* Long work (Aspen, large sweeps) is a job (`backend/amcrax/api/jobs.py`: `queued -> running -> succeeded | failed | timeout`, records mirrored to `logs/jobs/`, Aspen strictly serial). Short work answers synchronously.
* File access is by id or stem under fixed result folders (`backend/amcrax/api/store.py`). Path traversal is rejected, and protected Aspen cases cannot be deleted or overwritten.
* Start the server without `--reload` on Windows: the reloader signals its console group and ends the launching shell. Use `scripts\run_api.ps1`, `scripts\start_api_dev.ps1` (a supervisor that restarts uvicorn on code changes) or `scripts\start_amcrax.ps1`.

## 13. Adding a dashboard page

* Layout: `src/api` (typed fetchers; `types.ts` mirrors `schemas.py`), `src/data` (data-mode resolver and context), `src/pages` (one component per route), `src/features/<area>` (page parts; `shape.ts` holds pure functions that turn API payloads into table and chart rows, with `shape.test.ts`), `src/components` (`Value`, `SourceBadge`, `StatusPill`, `DataTable`, charts) and `src/pfd`.
* Every number is rendered through `<Value>` with its unit and provenance badge; a null value shows `n/a`. Never fabricate a value for a missing field; show a notice instead.
* Data come only through the mode-aware context and the `src/api` helpers. LIVE, SNAPSHOT and DEMO are never mixed on a page, and a failing live load is an error, not a demo fallback. Actions that need the API are disabled outside LIVE.
* Tables use `DataTable` (CSV export with a `filename`). Charts sit in a titled frame that names their sources.
* Add the route in `src/App.tsx` and an entry in `SECTIONS` in `src/components/Shell.tsx`, and add a screenshot entry in `frontend/scripts/capture_dashboard.mjs`.
* The development server proxies `/api` and `/figures` to `http://localhost:8000` (`frontend/vite.config.ts`).
