# AmCraX HTTP API

FastAPI application `amcrax.api.main:app`. Base URL `http://127.0.0.1:8000`, interactive docs at `/docs`,
OpenAPI at `/openapi.json`. All bodies are JSON unless stated; NaN/Inf are returned as `null`.
Units follow the [developer guide](developer_guide.md) (degC at interfaces, bar, kmol/h, kW). Every result carries its provenance
`source` (`aspen_plus_v15`, `python_model`, ...). For setup and launch commands see [installation.md](installation.md); for adding an endpoint see section 12 of the developer guide.

## Run

```powershell
. .\scripts\env.ps1                                                         # from the project root
python -m uvicorn amcrax.api.main:app --host 127.0.0.1 --port 8000          # or scripts\run_api.ps1 [--reload --reload-dir backend/amcrax]
python -m pytest tests/test_api.py -q                                       # Aspen is never started by the tests
python scripts\export_snapshot.py                                           # frontend/public/snapshot/ for SNAPSHOT mode (see reproducing.md)
python scripts\smoke_api.py                                                # live sweep of every body-less GET and the POSTs; exit 1 on any 5xx
```

Environment: `AMCRAX_ASPEN_TIMEOUT_S` (default 600) wall-clock limit of one Aspen job, including the wait for the
cross-process Aspen lock; `AMCRAX_ASPEN_SOLVE_TIMEOUT_S` (default 180) is passed to the worker as `--timeout`
(Aspen solve limit). `POST /api/simulation/run` accepts `timeout_s` to override the job limit per request; the worker solve limit then becomes `timeout_s - min(60, 0.25*timeout_s)` (at least 5 s).

Input checks (422, before anything is queued or written): `case_id` must match `^[A-Za-z0-9_-]{1,64}$` wherever it enters (run, sensitivity base, inline scenario inputs, `/cases/{id}`, export, delete); `property_method` must be one of `PENG-ROB, RK-SOAVE, RKS-BM, PR-BM, SRK, IDEAL` (`invalid_property_method`); for the aspen engine the flowsheet feasibility check of the input writer applies (`invalid_flowsheet_inputs`, e.g. `reactor_pressure_bar` below 3 bar). A worker result that carries `status.has_errors` and no streams makes the job `failed` (messages in `message`) and is not stored; in an aspen sensitivity job such points are reported per row with `error`. A worker result whose source is not `aspen_plus_v15` is rejected. Aspen records without streams are not protected (deletable, overwritable).
Logs: `logs/api.log` (JSON lines). Job records: `logs/jobs/<job_id>.json`.

With `--reload` every save under `backend/amcrax` restarts the process: in-memory queued/running jobs are
abandoned. Their records stay readable and are reported as `failed` ("API process restarted ..."). Run Aspen jobs
against a server started without `--reload` (for example on port 8001).

## Endpoints

| Method | Path | Purpose | Request | Response | Errors |
|---|---|---|---|---|---|
| GET | `/api/health` | Liveness, versions, Aspen availability, module import state, case counts | - | `{status, time_utc, versions, aspen{progid, com_registered, worker_module_present, available, reason, timeout_s}, modules{name: bool}, module_errors{name: msg}, cases{total, by_source, analysis_files}}`. `modules` is a real (cached) import attempt; failures are retried every 20 s | - |
| GET | `/api/flowsheet` | `config/flowsheet.json` | - | flowsheet JSON | 404 `flowsheet_not_found` |
| GET | `/api/cases` | Stored cases = files in `results/simulations` that validate as `SimulationResult` (validation cached by mtime+size) | - | `{count, cases[{case_id, valid, source, created_utc, converged, deletable, file, inputs, kpis}]}` | - |
| GET | `/api/cases/{case_id}` | Full `SimulationResult` | - | SimulationResult | 404 `case_not_found`, 422 `invalid_case_id` |
| GET | `/api/cases/{id}/streams` `/blocks` `/kpis` | Parts of a case | - | `{case_id, source, streams|blocks|kpis(+balances,status)}` | 404 |
| DELETE | `/api/cases/{case_id}` | Delete a user (python) case | - | `{deleted}` | 403 `protected_case` for Aspen results, 404 |
| GET | `/api/export/{case_id}?format=json\|csv\|xlsx` | Download a case (attachment) | query `format` | file | 404, 422 |
| GET | `/api/data/{category}` | List files of a category: `sensitivity` (results/sensitivity/*.csv), `validation` (results/validation/*.csv, *.json), `optimisation` (results/optimisation/*.csv, *.json), `analysis` (JSON files in results/simulations that are not cases, e.g. heat_integration_*.json, economics_*, environmental_*). Files with the same stem (pareto.csv, pareto.json) are listed separately, each with its extension | - | `{category, count, items[{name (stem), file, name_with_extension, kind, bytes, modified_utc, columns?, rows?}]}` | 404 `data_not_found` (unknown category) |
| GET | `/api/data/{category}/{name}` | One file. `name` with extension (`pareto.json`, `pareto.csv`) is exact; a bare stem (`pareto`) resolves to the JSON when both exist (the CSV otherwise). CSV -> `{name, category, columns, rows, count, source_note}` (numbers parsed, empty -> null); JSON returned as stored (NaN -> null). Path traversal is rejected | - | see left | 404 `data_not_found` |
| GET | `/api/sensitivity/datasets`, `/api/sensitivity/datasets/{name}` | Older sensitivity-only view of the same CSVs | - | `{datasets[]}` / `{name, columns, rows, count}` | 404 `dataset_not_found` |
| POST | `/api/sensitivity/run` | One-variable sweep. python engine: synchronous (<= 200 points, `source: python_model`), otherwise a job. aspen engine: always a job | `{variable (numeric CaseInputs field), values[], base_inputs?, engine}` | rows or 202 job | 422 `invalid_variable`, `value_out_of_range`, 503 `aspen_unavailable`, `module_unavailable` |
| POST | `/api/simulation/run` | Start a simulation job and store the result under `results/simulations/<case_id>.json` | `{inputs: CaseInputs, engine: "python"\|"aspen", timeout_s?}` | 202 job (`Location: /api/jobs/{id}`) | 422, 503 `aspen_unavailable` (never falls back to python), 503 `module_unavailable` |
| GET | `/api/jobs`, `/api/jobs/{job_id}` | Job list / one job | - | job object | 404 `job_not_found` |
| GET | `/api/thermo/equilibrium?T_C&P_bar&eos=ideal\|pr` | Equilibrium of pure NH3 plus reaction enthalpy and Gibbs energy at T | query | `{result{conversion,...}, reaction_enthalpy_kJ_mol, reaction_gibbs_kJ_mol, source, notes}` | 422 `invalid_eos` |
| GET | `/api/thermo/grid?T_min_C&T_max_C&n_T&P_bar=1,5,..&eos` | Equilibrium grid | query | `{eos, source, count, points[{T_C, P_bar, conversion, result}]}` | 422 `invalid_grid`, `invalid_P_bar`, `invalid_eos` |
| GET | `/api/kinetics/catalysts` | `list_catalysts()` metadata: rate-law text, parameters, validity range, limitations, source citation | - | `{count, source:"literature", catalysts[], notes}` | 503 |
| POST | `/api/reactor/pfr` | 1-D PFR (`simulate_pfr`). `catalyst_id` (validated against the registry) and `catalyst_mass_kg` (alias `W_kg`) required; `T_C, P_bar, feed{species:kmol/h} \| feed_nh3_kmol_h, mode isothermal\|adiabatic\|heated (needs T_wall_C, U_W_m2K), approach_factor, keq_basis amcrax_thermo\|published, pressure_drop, n_tubes, eps_b, dp_m, tube_inner_diameter_m, n_points` | body | `{provenance:"python_model", catalyst{source,validity}, profiles{W_kg,conversion,T_K,P_bar,y,...}, outlet_summary, equilibrium_limit, warnings[], limitations[], result}` | 422 `invalid_catalyst`, `missing_parameter`, `validation_error`, `calculation_error` |
| GET | `/api/reactor/catalyst-mass?catalyst_id&T_C&P_bar&target\|fraction_of_equilibrium&mode&pressure_drop&n_tubes` | `catalyst_mass_for_conversion`; `catalyst_mass_kg` is null with `reachable:false` and a warning when the target cannot be reached (for example the default single tube loses all pressure) | query | `{catalyst_mass_kg, reachable, warnings, notes, ...}` | 422 |
| GET | `/api/heat-integration/{case_id}?dT_min_K=20` | Pinch / FEHE analysis of a stored case (`amcrax.heat_integration.analyse`) | query | `{case_id, dT_min_K, result}` | 404, 422 |
| POST | `/api/economics/lcoh` | `compute_lcoh` of a stored case; `overrides` = `EconomicAssumptions` fields (unknown fields rejected) | `{case_id, overrides{}}` | `{result: LCOHResult, notes}` | 404, 422 `invalid_overrides` |
| GET | `/api/economics/defaults` | economics.yaml defaults with value, unit, source/citekey/page or assumption flag, alternatives, CAPEX references, literature LCOH | - | `{defaults, capex_references, literature_lcoh, assumption_fields}` | - |
| POST | `/api/economics/sensitivity` | LCOH tornado rows (`lcoh_sensitivity`), sorted by swing | `{case_id, overrides?}` | `{rows[{parameter, low_value, high_value, lcoh_at_low, lcoh_at_high, source_of_range}]}` | 404 |
| GET | `/api/economics/price-curve?case_id&min&max&n&target_lcoh` | LCOH vs ammonia price. `breakeven` (ammonia price at which LCOH = `target_lcoh`) is only computed when `target_lcoh` is passed; `amcrax.economics` defines no default target, so without it `breakeven` is `null` and `breakeven_note` says so | query | `{points[], breakeven[] \| null, breakeven_note?}` | 404, 422 |
| POST | `/api/environment/carbon-intensity` | `carbon_intensity(result, scenario, **overrides)` (`grey`, `blue`, `green`, optionally `route/heating`; see overrides in the module) | `{case_id, scenario, overrides{}}` | `{result: CarbonIntensityResult (breakdown, factors with sources, system_boundary, notes)}` | 404, 422 |
| GET | `/api/environment/scenarios?case_id` | `compare_scenarios` table (NH3 route x heating option) | query | `{result: {rows[], reference_lines[]}}` | 404 |
| GET | `/api/environment/factors` | emission-factor registry with sources and verification flags | - | `{factors}` | - |
| POST | `/api/separation/compare` | PSA vs membrane vs combined (`compare_purification`) on a stored case | `{case_id, membrane_recoveries?, membrane_T_K?, permeate_pressure_bar?, product_pressure_bar?, compressor_eta?}` | `{result}` | 404 |
| POST | `/api/separation/membrane` | Pd-Ag membrane (`membrane_separator`); give `area_m2` or `target_recovery` (then `area_for_recovery`) | `{feed_kmol_h, feed_pressure_bar, area_m2\|target_recovery, ...}` | `{area_m2, result}` | 422 |
| POST | `/api/separation/psa` | `psa_performance` operating point | `{feed_kmol_h, feed_pressure_bar, tailgas_pressure_bar?, target_purity?, basis?, h2_recovery?}` | `{result}` | 422 |
| POST | `/api/optimisation/run` | `amcrax.optimisation.run`: one single-objective optimisation on the Python model. `objective` in `min_lcoh, max_lhv_efficiency, min_specific_heat, max_h2_production, max_conversion` (default `min_lcoh`); `method` `de` (default) or `grid`, both about 5 s; `bounds{var:[lo,hi]}`, `constraints{}`, optional `case_id` (stored case that defines the base inputs). Runs in a worker thread with a 20 s limit | `{objective, method?, bounds?, constraints?, case_id?}` | `{source:"python_model", request, result}` | 422 `calculation_error` (unknown objective), 504 `timeout`, 503 |
| GET | `/api/optimisation/results` | Stored files of `results/optimisation`: `single_objective, pareto, objective_conflicts, candidates (candidates_for_aspen), aspen_verification` (each null when absent), plus `aspen_verification_summary{criterion, tolerance_relative, primary_metrics, candidates[{id, status, aspen_converged, max_relative_deviation_primary, tolerance}], counts}`, `design_grid{rows, columns, n_grid_points, n_feasible, data_endpoint}`, `files[]`, `available{}` | - | object | - |
| POST | `/api/scenarios/analyse` | `amcrax.scenarios.compare`: scenario table (stored Aspen result where converged, else Python model; Aspen-minus-Python columns; origin x heat-source overlays). Empty `scenario_ids` = all | `{scenario_ids[], nh3_origin grey\|blue\|green, heat_source ammonia\|natural_gas\|electric, grid, price_policy sourced\|base, prefer_aspen, include_overlays}` (all optional) | `{source, request, result{settings, provenance, notes, metric_names, rows[]}}` | 422 `calculation_error` (unknown scenario id) |
| GET | `/api/scenarios/comparison` | Stored `results/simulations/scenario_comparison.json` | - | JSON | 404 `scenario_comparison_not_found` |
| GET | `/api/scenarios/definitions` | `config/scenarios.json` (named process scenarios and overlays) | - | JSON | 404 |
| POST | `/api/scenarios/compare` | Compare stored cases (Aspen and Python mixed) and/or inline inputs run with the python engine; deltas vs the first case | `{case_ids[], inputs[]?, engine: "python"}` (>= 2 cases total) | `{cases[{case_id, source, converged}], reference_case, columns, table[{kpi, <id>, delta_<id>, delta_rel_<id>}], kpi_table, differences, changed_inputs}` | 404, 422 `too_few_cases`, 400 `inline_aspen_unsupported` |
| GET | `/api/scenarios/export?case_ids=a,b&format=csv` | KPI table as CSV | query | text/csv | 404, 422 |
| GET | `/api/validation`, `/api/validation/summary` | validation matrix; counts by status and by model component | - | JSON | 404 |
| GET | `/api/references`, `/api/traceability` | `research/references.json`, `research/traceability.json` | - | JSON | 404 |
| GET | `/api/reports` | Deliverables that exist (technical report, deck, validation docs, api.md, README, Aspen model files): `key, title, kind, bytes, modified_utc, url` | - | `{count, reports[]}` | - |
| GET | `/files/{key}` | Read-only download of a whitelisted deliverable (keys from `/api/reports`; no paths) | - | file | 404 `file_not_found` |
| GET | `/api/screenshots` | `{aspen[] (aspen/screenshots/manifest.json entries + url), dashboard[] (docs/screenshots)}`; images under static mounts `/aspen-screenshots/<file>` and `/dashboard-screenshots/<file>` | - | JSON | - |
| GET | `/api/figures`, `/figures/{file}` | PNG figures from `results/figures` | - | list | - |

## Job life-cycle

`POST /api/simulation/run` (or a sensitivity run that is a job) returns `202` and a job object:
`{job_id, kind, engine, label, state, message, created_utc, started_utc, finished_utc, queue_time_s, run_time_s, case_id, progress, result}`.

`queued -> running -> succeeded | failed | timeout`. A `succeeded` simulation job has `case_id` (the stored id;
if the requested id is held by an Aspen result the python result is stored as `<id>_py` and Aspen results are never
overwritten). `message` says `converged` or `finished but NOT converged: ...`; read `status` in the stored case.
Poll `GET /api/jobs/{job_id}`. Python jobs run in a 4-thread pool. Aspen jobs run strictly one at a time in a FIFO
queue; a second submitted job stays `queued` until the first finishes. Job records are mirrored to `logs/jobs/`.

## Process isolation of Aspen

The API process never imports COM. Each Aspen job starts a child process
`python -m amcrax.aspen.worker --inputs in.json --output out.json --timeout <solve s>` (temporary directory),
waits for it with the job time-out, and kills the whole process tree on time-out. Exit code 0 plus a valid
`SimulationResult` JSON means success; a non-zero exit code (stderr tail in `message`) or an invalid output file
means `failed`. The worker takes a cross-process lock (`aspen/runs/.aspen.lock`) so that only one Aspen instance exists
machine-wide, also against other scripts; waiting for that lock counts towards the job time-out. If COM is not
registered or the worker module is missing the API answers `503 aspen_unavailable`; it never substitutes the python
engine for a requested Aspen run.

## Error model

Every non-2xx response is `{"code": str, "message": str, "detail": any}`. Codes in use: `not_found`,
`method_not_allowed`, `validation_error` (422, `detail` = pydantic errors), `invalid_case_id`, `case_not_found`,
`protected_case`, `invalid_property_method`, `invalid_flowsheet_inputs`, `data_not_found`, `dataset_not_found`, `job_not_found`, `invalid_variable`, `value_out_of_range`,
`invalid_eos`, `invalid_grid`, `calculation_error` (422, domain ValueError), `calculation_failed` (500),
`too_few_cases`, `module_unavailable` (503, module not importable), `aspen_unavailable` (503),
`timeout` (504, optimisation run exceeded 20 s), `internal_error` (500). CORS allows `http://localhost:5173` and `http://127.0.0.1:5173` (Vite).
