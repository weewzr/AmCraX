# AmCraX dashboard user guide

Start the dashboard with `scripts\start_amcrax.ps1` and open <http://localhost:5173> (see [installation.md](installation.md)). The navigation lists eleven
sections, described below. The endpoint reference is [api.md](api.md); the limitations that apply to the results shown are in [known_limitations.md](known_limitations.md).

The page addresses (routes) and the way the dashboard is served, including the public static site, are described in [../frontend/README.md](../frontend/README.md). This guide
refers to pages by name only.

## 1. Data modes and provenance

### Data modes (badge in the header, banner under it)

| Mode | When | What you can do |
|---|---|---|
| **LIVE** (green "LIVE - API") | `GET /api/health` answers | everything: browse stored cases, run Python-model simulations and sweeps, run Aspen jobs if "Aspen: available", what-if calculations (economics, carbon intensity, heat integration), exports |
| **SNAPSHOT** (blue, with the export time) | API unreachable, `frontend/public/snapshot/manifest.json` exists (`python scripts/export_snapshot.py`) | read-only browsing of real stored results; every action that needs the API is disabled |
| **DEMO** (red banner "DEMONSTRATION DATA") | neither | illustrative placeholders (`source: demo`); never results |

A reachable API or snapshot that fails to load shows an error; it never falls back to demo data. Modes are never mixed on a page.

### Provenance badges

Every number is rendered with its unit and a badge (`frontend/src/components/ui.tsx`, labels from `amcrax.schemas.DataSource`):

| Badge | Meaning |
|---|---|
| `aspen_plus_v15` | extracted from a real Aspen Plus V15 run (stored in `results/simulations/<id>.json`) |
| `python_model` | independent AmCraX Python calculation (equilibrium, process model, pinch, PFR, economics, carbon intensity, optimisation) |
| `literature` | published value, always with a citation key (never presented as an AmCraX result) |
| `assumption` | engineering assumption, documented in `docs/model_assumptions.md` |
| `demo` | placeholder |

`n/a` means "not available"; no value is ever guessed. A "not converged" case is flagged and must not be relied on. The case selector in the
header chooses the **active case** used by the Process Flow Diagram, Reactor Analysis, Heat Integration, Techno-Economics and Environment pages.

## 2. Sections

For each section: *shows* what the page displays; *data* where it comes from (endpoint -> results file; provenance); *change* what you can vary;
*export* how to take data away. Every table built with `DataTable` has a CSV export button; every chart sits in a titled frame with its source badge.

### Overview
* Shows: process summary of the active case (KPI tiles), validation summary (counts from the validation matrix), explanation of the data modes, links to the sections.
* Data: `/api/cases`, `/api/cases/{id}`, `/api/validation` -> `results/simulations/*.json` (`aspen_plus_v15` / `python_model`), `results/validation/validation_matrix.json`.
* Change: the active case (header).

### Process Flow Diagram
* Shows: the flowsheet of `config/flowsheet.json` drawn with React Flow (pump, vaporiser, FEHE, trim heater, cracker, cooler, PSA, burner, flue-gas cooler), streams coloured by dominant
  component or temperature, optional overlays (T, P, molar flow, mass flow, main composition), flow animation, and side panels for the clicked equipment (duty, role) or stream (all properties).
  With heat integration off the FEHE and streams S3 / S6 are re-routed out.
* Data: `/api/flowsheet`, `/api/cases/{id}` of the active case; one provenance badge in the diagram header.
* Change: colour mode, overlays, selection; the active case.
* Export: use the Simulation section's tables for numbers; the diagram itself is captured as a screenshot (`docs/screenshots/dashboard_pfd*.png`).

### Simulation
* Shows: operating-conditions form (all `CaseInputs` fields with bounds and help text), engine choice, a job panel, results of the selected case (streams, blocks, KPIs, balance closures, engine messages),
  and a scenario comparison (2-4 cases, KPI deltas versus the first, changed inputs, mixed-engine warnings) with economic / carbon overlays from `config/scenarios.json`.
* Data: `POST /api/simulation/run` -> job -> `results/simulations/<case_id>.json`; `GET /api/jobs/{id}`; `GET /api/scenarios/definitions`; `POST /api/scenarios/compare`; scenario comparison file
  `results/simulations/scenario_comparison.json` (produced by `scripts/run_scenarios_analysis.py`).
* Change: every input; engine `Python model` (immediate, `python_model`) or `Aspen Plus V15` (rigorous, about 15 s to several minutes). The Aspen button is disabled with the reason when the API reports Aspen unavailable.
* Running Aspen from the UI: submit with engine Aspen; the **job states** are `queued -> running -> succeeded | failed | timeout`. Aspen jobs run strictly one at a time (one licence seat, machine-wide lock):
  a second job waits as `queued`. The whole job (including waiting for the lock) is limited to 600 s by default (`AMCRAX_ASPEN_TIMEOUT_S`; the Aspen solve itself to 180 s, `AMCRAX_ASPEN_SOLVE_TIMEOUT_S`).
  A failed or timed-out job stores nothing and never shows a substitute result. The cracker outlet pressure must be at least 3 bar for the full flowsheet. A succeeded job is stored as a new case and selectable in the header;
  an Aspen result is never overwritten (a Python result for an Aspen case id is stored as `<id>_py`).
* Export: per case JSON, CSV or XLSX (`GET /api/export/{case_id}?format=json|csv|xlsx`), streams and blocks tables as CSV, comparison table as CSV.

### Reactor Analysis
* Shows: (1) equilibrium explorer - conversion and composition versus temperature at selectable pressures, ideal gas versus Peng-Robinson; (2) the cracker of the active case; (3) kinetics - catalyst list with validity ranges,
  and packed-bed PFR profiles for a chosen catalyst, with the kinetics-extrapolation warning.
* Data: `/api/thermo/equilibrium`, `/api/thermo/grid` (`python_model`, independent equilibrium); `/api/kinetics/catalysts` (`literature` constants); `POST /api/reactor/pfr` (`python_model` on literature kinetics);
  stored: `results/simulations/pfr_baseline.json`, `results/sensitivity/pfr_temperature_sweep.csv`, `results/validation/equilibrium_*.csv`.
* Change: T range, pressures, EOS, catalyst, PFR inputs.
* Limits: kinetics measured at 1 atm are extrapolated to 20 bar (`docs/known_limitations.md`).

### Heat Integration
* Shows: pinch targets at the chosen dT_min (process streams only, and with tail-gas flue gas), composite and grand composite curves, stream table, FEHE profile and area (assumed U), configuration comparison (a-d)
  of external heating, with/without heat integration comparison (needs both `baseline` and `baseline_no_hi`), and a consistency table of the Python H-T curves against Aspen block duties.
* Data: `GET /api/heat-integration/{case_id}?dT_min_K=20` (`amcrax.heat_integration`, `python_model` applied to the stored case); stored `results/simulations/heat_integration_<case>.json`.
* Change: dT_min (live mode only).
* Export: CSV from each table (`heat_consistency.csv`, `heat_configurations.csv`, `duties_<case>.csv`).

### Sensitivity Analysis
* Shows: the available sweep datasets (Aspen studies `results/sensitivity/aspen_*.csv`, LCOH tornado and price curves, PFR and membrane sweeps), selectable x variable and y series, heat map for the T-P map, a table
  (selected or all columns, non-converged rows flagged) and, in live mode, a Python-model overlay for the same points and new sweeps.
* Data: `/api/sensitivity/datasets[/{name}]`, `POST /api/sensitivity/run` (Python engine synchronous up to 200 points; Aspen engine as a job) -> `aspen_plus_v15` rows from CSV, `python_model` for new sweeps.
* Change: x / y variables; new sweep variable, range, engine.
* Export: CSV of the displayed table (`sweep_<variable>.csv` for new sweeps).

### Optimisation
* Shows: stored single-objective results with model limitations, the Aspen verification of the optimum candidates, a design-landscape map from the design grid, objective-conflict table,
  Pareto fronts, and a form to run a new optimisation.
* Data: `/api/data/optimisation/*` -> `results/optimisation/single_objective.json`, `design_grid.csv`, `pareto.json`, `objective_conflicts.json`, `aspen_verification.json`; `POST /api/optimisation/run` (Python model).
  Files are produced by `scripts/run_optimisation.py` and `aspen/automation/verify_candidates.py`. Badge `python_model`; verified rows `aspen_plus_v15`.
  `results/optimisation/` holds `single_objective.json`, `design_grid.csv`, `pareto.*`, `objective_conflicts.json`, `candidates_for_aspen.json`, `aspen_verification.json|csv` and `scenario_comparison.csv`.
  The Aspen verification card lists the candidates re-solved in Aspen Plus (the exact optima plus Pareto points), the primary metrics judged, the tolerance and the per-candidate maximum primary and secondary deviations;
  the values are in `results/optimisation/aspen_verification.json`. If that file is missing the page shows a "not yet verified" notice instead.
* Change: objective, variables and bounds of a new run; landscape axes, metric, feasibility filter.
* Note: a run started from the page is not written to `results/optimisation`.

### Techno-Economics
* Shows: LCOH headline and stacked breakdown (CAPEX annuity, fixed OPEX, ammonia, imported heat, electricity), specific ammonia consumption versus the stoichiometric floor (the ammonia feed is priced on its contained NH3; the feed water is not priced), LCOH versus ammonia price curve,
  tornado, break-even target, assumptions with their literature / assumption labels, published literature LCOH (reference only), and a preliminary-estimate warning (class 4-5 CAPEX).
* Data: `POST /api/economics/lcoh` (`amcrax.economics`, `python_model` on the stored case); stored `results/simulations/economics_<case>.json`, `results/sensitivity/lcoh_*`; parameters `backend/amcrax/data/economics.yaml`.
* Change: ammonia price, discount rate, plant life, operating hours, CAPEX multiplier, catalyst (Ni / Ru); a banner says when what-if values are active (tornado and literature table stay at defaults).
* Export: CSV of breakdown and tornado tables.

### Environment
* Shows: carbon intensity (kg CO2e per kg H2) for ammonia route (grey / blue / green) x heating option (natural gas / self-firing / electric), breakdown by contribution, emission-factor table with citation and provenance,
  system boundary, reference lines (EU RFNBO, IEA 4 kg). A permanent notice says this is simplified accounting, not an LCA; factors taken from secondary extracts are flagged "to be verified against primary source".
* Data: `POST /api/environment/carbon-intensity` (`amcrax.environmental`); stored `results/simulations/environmental_<case>.json`; factors `backend/amcrax/data/environmental.yaml`.
* Change: shipping distance, grid factor (overrides are labelled `assumption`).
* Export: CSV (`carbon_intensity.csv`, `emission_factors.csv`).

### Validation
* Shows: the validation matrix (status pass / fail / not_run / informational, filter by status, component, text; evidence files), a "what is not validated" list, the Aspen RGibbs versus Python equilibrium comparison
  (selectable quantity and pressure, deviation summary), and the flowsheet cross-check Aspen versus Python.
* Data: `/api/validation` -> `results/validation/validation_matrix.json`; `/api/data/validation/*` -> `equilibrium_comparison.csv`, `aspen_vs_python_flowsheet.csv`, ... (labels `aspen_plus_v15` vs `python_model`).
* Export: CSV of the matrix and comparison tables. Rebuild with `python scripts/build_validation_matrix.py`.

### Reports
* Shows: downloadable deliverables (technical report PDF / DOCX, pitch deck PPTX / PDF), the genuine Aspen Plus GUI screenshots, a figure gallery (`results/figures`), model traceability, references and a "how to reproduce" panel.
* Data: `/api/reports`, `/api/figures`, `/api/screenshots`, `/api/references`, `/api/traceability`.
* Export: the deliverable files themselves.

## 3. Typical workflows

* **Inspect the baseline**: Overview -> PFD -> Simulation (streams / blocks) -> Heat Integration. The active case should be `baseline` (`aspen_plus_v15`).
* **Run a Python what-if**: Simulation -> change inputs -> engine "Python model" -> result stored as a `python_model` case, visible in every page that accepts a case.
* **Run Aspen** (needs the licence): Simulation -> engine "Aspen Plus V15" -> watch the job panel. Only one Aspen job at a time.
* **Compare scenarios**: Simulation -> scenario comparison -> select 2-4 cases -> export CSV.
* **Trace a number**: badge -> endpoint in the section above -> results file -> script in [reproducing.md](reproducing.md).

## 4. Command-line equivalents

```powershell
. scripts\env.ps1
python scripts\run_python_baseline.py                    # Python model, writes results\simulations\python_baseline*.json
python aspen\automation\run_baseline.py                  # needs Aspen
python aspen\automation\run_scenarios.py                 # needs Aspen
python scripts\run_optimisation.py                       # Python model optimisation
python aspen\automation\verify_candidates.py             # needs Aspen: re-solve the optimum candidates
```

Full ordered list: [reproducing.md](reproducing.md).

## 5. Screenshots

Captured with `frontend/scripts/capture_dashboard.mjs` (Microsoft Edge, headless); the `snapshot_*` files with `--query ?mode=snapshot --prefix snapshot`. Files in `docs/screenshots/`:

All eleven pages in LIVE mode (1600x1000), plus the PFD side panels and SNAPSHOT-mode examples:

| Section | Screenshot |
|---|---|
| Overview | ![Overview](screenshots/dashboard_overview.png) |
| Process Flow Diagram | ![Process Flow Diagram](screenshots/dashboard_pfd.png) |
| PFD, equipment panel | ![PFD equipment panel](screenshots/dashboard_pfd_equipment_panel.png) |
| PFD, stream panel | ![PFD stream panel](screenshots/dashboard_pfd_stream_panel.png) |
| Simulation | ![Simulation](screenshots/dashboard_simulation.png) |
| Simulation, after a run | ![Simulation run](screenshots/dashboard_simulation_run.png) |
| Reactor Analysis | ![Reactor Analysis](screenshots/dashboard_reactor.png) |
| Heat Integration | ![Heat Integration](screenshots/dashboard_heat.png) |
| Sensitivity Analysis | ![Sensitivity Analysis](screenshots/dashboard_sensitivity.png) |
| Optimisation | ![Optimisation](screenshots/dashboard_optimisation.png) |
| Techno-Economics | ![Techno-Economics](screenshots/dashboard_economics.png) |
| Environment | ![Environment](screenshots/dashboard_environment.png) |
| Validation | ![Validation](screenshots/dashboard_validation.png) |
| Reports | ![Reports](screenshots/dashboard_reports.png) |
| SNAPSHOT mode: Overview | ![Snapshot Overview](screenshots/snapshot_overview.png) |
| SNAPSHOT mode: PFD | ![Snapshot PFD](screenshots/snapshot_pfd.png) |
| SNAPSHOT mode: Sensitivity | ![Snapshot Sensitivity](screenshots/snapshot_sensitivity.png) |

## 6. Refreshing screenshots

```powershell
. scripts\env.ps1
scripts\start_amcrax.ps1 -NoBrowser
node frontend\scripts\capture_dashboard.mjs --base http://localhost:5173
```
(without `--base` the script starts its own Vite server on port 5176 and needs the API on port 8000.)
