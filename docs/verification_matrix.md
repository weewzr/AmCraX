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
| P2.1 Dashboard | yes: 11 pages in `frontend/src/pages` | yes: screenshots in `docs/screenshots` | partly: reads stored results; no own checks | yes: Vite proxy to API, snapshot mode | yes: `docs/user_guide.md` | yes: 96 vitest tests (shape, mapping) on 21 November 2026; 279 in 29 files on 24 November 2026 |
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
| Technical report | yes: `build_report.py`, 87 PDF pages on 21 November 2026 (version 2.0 has 218 pages) | yes: PDF built 2026-11-21 | partly: build log lists 3 unresolved in-text citations | yes: linked from site and README | yes: `docs/technical_report` | partly: build-log checks only |
| Pitch deck | yes: `build_deck.py`, 15 PDF pages | yes: PDF built 2026-11-21 | not verified: slide numbers not compared with results | yes: linked from README | yes: `speaker_script.md` | no: no automated test found |

## Research expansion (Singapore hypothesis tests)

Added 2026-11-23. Status values: complete and validated, complete but preliminary, partially complete, not completed. Each status is justified from the files named; pass and fail counts are those of the 23 November 2026 release (295 pass, 10 fail, 45 informational over 7 files, separate from the 137-item core matrix); the current counts (607 pass, 12 fail, 76 informational, 1 not available of 696 items in 11 files, 24 November 2026) are in `results/research/validation/summary.json`, and the per-file counts below are those of the release unless a current count is given in brackets. The full account is in [research/validation_and_limitations.md](research/validation_and_limitations.md). Test run on 2026-11-23: `python -m pytest tests -q` gave 513 passed, 1 skipped (final verification run). The frontend suite was not re-run for this entry.

| Deliverable | Status | Justification |
|---|---|---|
| Research validation summary (`scripts/research/build_research_validation.py`, `summary.json`, `docs/validation/research_validation.md`) | complete and validated | Deterministic aggregation of 7 files, 350 items (now 11 files, 696 items); failures listed with observed, expected, tolerance and recorded cause |
| Kinetics: Kum, 5Ni1Ru/CeO2, 2.5Ni0.5Ru/CeO2 (`results/research/kinetics`) | complete but preliminary | `kinetics.json` 8 pass, 2 fail, 3 informational (now 10 pass, 2 fail, 7 informational); Lucentini checks reproduce the fitting data, not independent data; extrapolated to 20 bar |
| Kinetics: Ni/MgO and Ru/MgO (Takahashi approximation) | complete but preliminary | Fitted approximation (RMS rate error 12 %, 20 bar only); the two inherited failures `KIN-NI-PRED` and `KIN-RU-PRED` are unresolved |
| Kinetics: Ni/CeO2, Ru/CeO2, Ru-K/CaO | not completed | No usable published rate law (Lucentini 2019); Sayas 2020 full text inaccessible |
| Aspen RPlug infrastructure and catalyst cases (`results/research/aspen_kinetic`) | complete and validated | 162 runs, all `ok`; `aspen_kinetic.json` 161 pass, 3 fail (strict below-equilibrium check, cause recorded, not tuned), 19 informational (now 163 pass, 5 fail, 22 informational) |
| Catalyst comparison and heat integration (`results/research/catalyst_comparison`) | complete but preliminary | `catalyst_comparison.json` 66 pass, 5 fail (FEHE property basis, 3.45 to 4.44 % against 3 %), 4 informational; proxy prices; CAPEX insensitive to temperature; no Aspen run at the Python optimum points |
| Singapore techno-economics (`results/research/singapore`) | complete but preliminary | `economics.json` 9 pass, 0 fail, 6 informational (E09, arithmetic on Cho's own numbers, reclassified as informational in the final verification); screening CAPEX; secondary web prices; several Singapore inputs not found |
| Purification (`results/research/purification`) | partially complete | `purification.json` 4 pass, 0 fail, 4 informational (now 10 pass, 0 fail, 7 informational); PSA recovery-purity trade-off has two data points only; membrane costs are lower bounds; not every ISO 14687 contaminant evaluated; Cechetto 4 bar comparison not done |
| End use (`results/research/enduse`) | complete but preliminary | `enduse.json` 40 pass, 0 fail, 5 informational (now 69 pass, 0 fail, 6 informational); interpolated blend efficiencies; no combustion simulation; Halim figures unverified |
| Life-cycle assessment (`results/research/lca`) | complete but preliminary | `lca.json` 7 pass, 0 fail, 4 informational; low-confidence factors and unsourced distances |
| Aspen evidence screenshots (`docs/images/aspen_evidence`) | complete but preliminary | All 31 inspected and marked publishable; `ci_luc5_T572_P20_W100_hi__08_reactor_results.png` was recaptured on 2026-11-23 after its first capture showed the Catalyst tab; some forms not captured |
| API and dashboard integration of the research results | complete but preliminary | Read-only router `backend/amcrax/api/routers/research.py` and the Hypotheses pages under `frontend/src/site/hyp/` show the stored result files (end use and life cycle included); the end-use and life-cycle Python packages are not exposed as live calculation endpoints |

## Phase 2 (23 November 2026)

Status values are as in the research section above. Counts come from the files named; where a count was not final at the time of writing the entry says "see" and names the file. Evidence kinds are kept apart: numerical verification (NV), Python against Aspen comparison (PA), comparison with published literature (PL). AmCraX has no independent experimental validation.

| Feature | Status | Evidence |
|---|---|---|
| Interactive simulator (first page of the site) | complete but preliminary | 227 frontend unit tests (25 files) reported on 23 November 2026, 279 (29 files) and 922 browser checks at the quality check of 24 November 2026 before the fix pass, 290 (30 files) and 1037 browser checks at the final check of Phase 2 on 24 November 2026; browser model against Python on 82 vectors to about 1e-7 (NV) and against stored Aspen kinetic cases (PA), `results/research/simulator/parity_report.json`; site check passed on four viewports. No membrane model, no IRR, flow animation only |
| Unified reference scenario | complete but preliminary | `tests/test_phase2_reference.py` (29 tests); baseline 4.015 USD/kg reproduced; CAPEX extrapolated, see `docs/research/unified_baseline.md` |
| Heat exchanger sizing and cost | complete but preliminary | `results/research/validation/heat_exchanger.json`: 40 items, 27 pass, 0 fail, 13 informational (24 November 2026); no sourced U at 20 bar |
| Kinetic validity classification | complete and validated for the classification itself | Every law classified; none validated at 20 bar |
| End-use thresholds (H1) | complete but preliminary | `tests/test_phase2_enduse.py` (12 tests); no sourced turbine efficiency for the fired-cracker fuel |
| Carbon pricing, modes A and B (H2) | complete but preliminary | `tests/test_phase2_carbon_pricing.py` (13 tests); Mode B is hypothetical |
| Purification, PSA against membrane (H4) | complete but preliminary | `tests/test_phase2_purification.py` (10 tests); PSA recovery is an input |
| Catalyst economics (H3) | complete but preliminary | `tests/test_phase2_catalyst_econ.py` (13 tests); derived catalyst prices |
| Uncertainty quantification | complete but preliminary | `results/research/validation/uq.json`: 78 checks pass, 6 informational, 0 fail; `tests/test_phase2_uq.py` (13 tests); model-form error of the Takahashi law reported |
| Evidence matrix version 2 | complete but preliminary | `results/research/evidence_matrix.json`; rule `docs/research/verdict_methodology_v2.md`; version 1 verdicts shown beside. Only the roles, components, aggregation and general row standard were fixed before the analyses; the row-by-row rules were written after the results and tested by an independent adversarial review, which moved H2-b, H3-d and H4-e to INCONCLUSIVE. Verdicts: H1 INCONCLUSIVE, H2 MIXED, H3 PARTIALLY SUPPORTED (resting only on H3-T), H4 INCONCLUSIVE. Plain answers (Yes / No / Not established, a reading aid derived in code from the row and half-row outcomes; `tests/test_phase2_evidence_matrix.py` checks the mapping) are printed beside the verdicts |
| Fix pass of 24 November 2026 | complete | `results/research/fix_pass_2026-11-24.json` (`scripts/research/record_fix_pass.py`): membrane annualised with the capital recovery factor, centred Sobol first-order estimator (total-effect indices unchanged), fuel-efficiency envelope of the baseline, three row verdicts |
| Research validation, by evidence kind | see `results/research/validation/summary.json` | 696 items: NV 464 (440 pass, 5 fail, 19 informational), PA 183 (156, 5, 22), PL 48 (11, 2, 35); experimental validation none (1 placeholder, not available) |
| Full Python suite | complete | 753 passed and 1 skipped at the final check of Phase 2 on 24 November 2026 (705 after the fix pass earlier that day; 618 passed in a run during Phase 2 on 23 November; 513 at the start of Phase 2, `docs/research/phase2_baseline.md`); re-run to confirm |