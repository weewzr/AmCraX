# AmCraX verification matrix

This matrix records, for each feature of the P1 to P3 scope, whether it is implemented, executes, produces valid results, is integrated, is documented and is tested. It is a feature-level view. The check-level evidence is in the [validation matrix](validation/validation_matrix.md), which lists 137 items (105 pass, 22 fail, 0 not run, 10 informational). Known limits are in [known_limitations.md](known_limitations.md).

Cell values: `yes`, `partly` or `no`, followed by the evidence. "not verified" means no evidence was found.

## How it was verified

Verified on 2026-11-21 by reading the code, the tests, `results/validation/validation_matrix.json` and `docs/api.md`, and by running these commands from the repository root:

- `python -m pytest tests -q -p no:warnings`: all tests passed, 1 skipped (the opt-in live-Aspen test). The repository configuration adds `-q`, which hides the summary line, so the count was read from the same run without the extra `-q`: `391 passed, 1 skipped in 58.19s`.
- `npx vitest run` in `frontend`: `Test Files  18 passed (18)` and `Tests  96 passed (96)`.

Aspen Plus was not started. "Executes" for Aspen-based features rests on the stored results of earlier runs (279 runs, all converged) and was not re-run today. The public site URL https://weewzr.github.io/AmCraX/ answered HTTP 404 when fetched on 2026-11-21.

## P1: core simulation

| Feature | Implemented | Executes | Produces valid results | Integrated | Documented | Tested |
|---|---|---|---|---|---|---|
| P1.1 Aspen automation | yes: `backend/amcrax/aspen`, `aspen/automation` | yes: stored runs; not re-run today | yes: `BAL-ASPEN` 20/20, `SENS` 8/8, `STEMP` 2/2 | yes: API worker process, `docs/api.md` | yes: `docs/installation.md` section 5 | partly: `test_aspen_layer.py`; live test skipped |
| P1.2 Baseline flowsheet | yes: `config/flowsheet.json`, input writer | yes: `results/simulations/baseline.json` converged | yes: closures, `PHYS` 4 pass, 1 informational; reduced-order PSA | yes: dashboard, API, report | yes: `docs/model_assumptions.md` | partly: `test_aspen_layer.py` on stored results; no live test |
| P1.3 Equilibrium model | yes: `amcrax.thermodynamics` | yes: `/api/thermo/equilibrium` | yes: `EQ` 8 pass, 3 informational; JANAF checks | yes: API, site calculator | yes: `validation/discrepancy_analysis.md` | yes: `test_thermodynamics.py` |
| P1.4 Sensitivity analysis | yes: 8 Aspen studies, Python sweeps | yes: 91 Aspen runs stored | yes: `SENS` 8/8, `STEMP` 2/2 | yes: `/api/sensitivity/run`, dashboard page | yes: `docs/user_guide.md` | partly: `sensitivity/shape.test.ts`, `test_api.py` |
| P1.5 Interactive PFD | yes: `frontend/src/pfd` | yes: `docs/screenshots/dashboard_pfd.png` | partly: shows stored values; routing hand-coded for baseline | yes: dashboard and public site | yes: `docs/user_guide.md` | yes: `pfd/mapping.test.ts`, `panels.test.tsx` |

## P2: analysis and platform

| Feature | Implemented | Executes | Produces valid results | Integrated | Documented | Tested |
|---|---|---|---|---|---|---|
| P2.1 Dashboard | yes: 11 pages in `frontend/src/pages` | yes: screenshots in `docs/screenshots` | partly: reads stored results; no own checks | yes: Vite proxy to API, snapshot mode | yes: `docs/user_guide.md` | yes: 96 vitest tests (shape, mapping) |
| P2.2 FastAPI backend | yes: `amcrax.api` | yes: `scripts/smoke_api.py`, tests | yes: `PYTEST-test_api` pass | yes: serves dashboard and export | yes: `docs/api.md` | yes: `test_api.py` |
| P2.3 Heat integration | yes: `amcrax.heat_integration` | yes: `heat_integration_baseline.json` | partly: no matrix family; U assumed | yes: `/api/heat-integration`, Heat page | yes: `docs/model_assumptions.md` | yes: `test_heat_integration.py` |
| P2.4 Techno-economics | yes: `amcrax.economics` | yes: `economics_baseline.json` | partly: `ECON` 6/6 sums; costs preliminary | yes: `/api/economics/*`, Economics page | yes: `known_limitations.md` section 6 | yes: `test_economics.py` |
| P2.5 Optimisation | yes: `amcrax.optimisation` | yes: `results/optimisation/*.json` | yes: `OPT-ASPEN`, `OPT-FEAS`; 10 of 10 re-solved in Aspen | yes: `/api/optimisation/*`, Optimisation page | yes: `known_limitations.md` section 8 | yes: `test_optimisation.py` |
| P2.6 Scenario analysis | yes: `amcrax.scenarios`, `config/scenarios.json` | yes: 8 `scn_*` Aspen results | partly: Aspen converged, `FS-PRIMARY` pass; overlays assumed | yes: `/api/scenarios/*` | yes: `docs/api.md` | yes: `test_scenarios.py` |

## P3: extensions

| Feature | Implemented | Executes | Produces valid results | Integrated | Documented | Tested |
|---|---|---|---|---|---|---|
| P3.1 Kinetics | yes: `amcrax.kinetics`, 3 catalyst models | yes: `/api/kinetics/catalysts` | partly: `KIN` 1 pass, 2 fail, 1 informational | partly: API and Reactor page; not in Aspen | yes: `known_limitations.md` section 5 | yes: `test_kinetics.py` |
| P3.2 Plug-flow reactor | yes: `amcrax.reactor` | yes: `results/simulations/pfr_baseline.json` | partly: 1 atm kinetics extrapolated to 20 bar | partly: `/api/reactor/pfr`; not in Aspen | yes: `results/validation/pfr_fix_note.md` | yes: `test_reactor.py` |
| P3.3 Purification | yes: `amcrax.separation`: PSA, membrane | yes: `separation_baseline.json` | partly: reduced-order, not validated | partly: `/api/separation/*`; no polishing in flowsheet | yes: `known_limitations.md` section 4 | yes: `test_separation.py` |
| P3.4 Environmental assessment | yes: `amcrax.environmental` | yes: `environmental_baseline.json` | partly: `ENV` 3/3 sums; carbon accounting simplified | yes: `/api/environment/*`, Environment page | yes: `known_limitations.md` section 7 | yes: `test_environmental.py` |
| P3.5 Multi-objective analysis | yes: Pareto in `amcrax.optimisation` | yes: `pareto.json`, `objective_conflicts.json` | partly: 4 Pareto points re-solved in Aspen; objectives mostly agree | yes: Optimisation page | yes: `docs/api.md` | yes: `test_pareto_front_non_dominated` |

## Delivery

| Feature | Implemented | Executes | Produces valid results | Integrated | Documented | Tested |
|---|---|---|---|---|---|---|
| Public website | yes: `frontend/src/site`, 9 sections | partly: not built today; site tests pass | not verified: site build not inspected | no: live URL answered 404 today | yes: `frontend/README.md` | yes: `site/*.test.ts` |
| Validation matrix | yes: `scripts/build_validation_matrix.py` | yes: JSON generated 2026-11-21 | yes: 22 failures kept and explained | yes: dashboard page, `/api/validation` | yes: `docs/validation` | yes: `test_validation_checks.py` |
| Technical report | yes: `build_report.py`, 87 PDF pages | yes: PDF built 2026-11-21 | partly: build log lists 3 unresolved in-text citations | yes: linked from site and README | yes: `docs/technical_report` | partly: build-log checks only |
| Pitch deck | yes: `build_deck.py`, 15 PDF pages | yes: PDF built 2026-11-21 | not verified: slide numbers not compared with results | yes: linked from README | yes: `speaker_script.md` | no: no automated test found |
