# Reproducing the results

This page lists, in order, the commands that regenerate every stored result, figure and deliverable. Run them from the project root in Windows PowerShell 5.1 after `. scripts\env.ps1` (see [installation.md](installation.md)).

Each step carries one of these requirements:

| Marker | Needs |
|---|---|
| **[Python only]** | The Python environment. No Aspen Plus, Word or PowerPoint. |
| **[needs Aspen Plus V15]** | A licensed Aspen Plus V15 installation with COM registered. One Aspen instance runs at a time (see the Aspen rule in the [developer guide](developer_guide.md)). |
| **[needs Word or PowerPoint]** | Microsoft Word (report) or PowerPoint (deck) for the PDF export. |

Phase 2 (23 November 2026) added a master script and steps for the unified reference scenario, the evidence matrix version 2, the simulator data and the website. They are in [section 9](#9-phase-2-regenerate-everything-in-order). The check of the preserved release is in [section 10](#10-verify-the-preserved-release). Sections 1 to 8 describe the earlier steps, which remain valid. Where an earlier step writes a result that Phase 2 regenerates (everything under `results\research\`), run the Phase 2 steps afterwards.

The stored files in `results/` already hold the outputs. Reproduce them only when you change a model, a parameter or a script, or when you want to confirm them. Run times are given where a script or a document records them; where none is recorded the entry says so. They depend on the machine.

The Aspen steps need a seat that is free for the whole run. A single converged flowsheet solve takes a few seconds (the engine time recorded for the baseline is about 2 s). Scripts that solve many points take correspondingly longer.

## 1. Check the environment

**[Python only]**

```powershell
. scripts\env.ps1
python -m pytest tests -q
```

Expected: all tests pass, and one test (the opt-in live Aspen test) is skipped. Aspen is never started. The count at the start of Phase 2 (513 passed, 1 skipped) is recorded in [research/phase2_baseline.md](research/phase2_baseline.md). Phase 2 adds tests (`tests\test_phase2_*.py`), so the number is higher on the Phase 2 branch: read it from your own run. Tests that read result files can fail while a script is rewriting them, so do not run the suite during step 9.2.

## 2. Aspen Plus results

**[needs Aspen Plus V15]**

```powershell
python aspen\automation\run_baseline.py [--visible]
```

Builds and solves the heat-integrated baseline and the variant without the feed/effluent exchanger. Writes `results\simulations\baseline.json`, `results\simulations\baseline_no_hi.json`, `results\sensitivity\aspen_native_STEMP_<case_id>.csv` and `aspen\models\baseline*.inp` / `.bkp` (and `.apw`, which is not version-controlled). `--visible` shows the Aspen window.

```powershell
python aspen\automation\run_equilibrium_grid.py
```

Solves an isothermal RGibbs reactor with pure ammonia over a temperature-pressure grid for the PENG-ROB and IDEAL property methods, with repeatability checks. Writes `results\validation\equilibrium_aspen_grid.csv` and `results\validation\aspen_binary_parameters.json`. Run time: not recorded.

```powershell
python aspen\automation\run_sensitivity.py [study ...]
```

Runs the Aspen parameter studies on the full flowsheet. Every row of every CSV is an Aspen run. Without arguments it runs all studies: `temperature`, `pressure`, `tp_map`, `feed_rate`, `feed_water`, `psa_recovery`, `fehe_approach` and `no_hi_temperature`. Writes `results\sensitivity\aspen_<study>.csv`. Run time: not recorded.

```powershell
python aspen\automation\run_scenarios.py [--force] [id ...]
```

Solves the named scenarios of `config\scenarios.json` and writes `results\simulations\<id>.json`. A scenario whose result already exists and converged is skipped unless `--force` is given.

```powershell
python aspen\automation\write_case_inputs.py
```

Writes `aspen\models\cases\<case_id>.inp` for every converged stored Aspen case and records the file in the result. This step needs no Aspen run, because the input file is a function of the stored inputs.

```powershell
python aspen\automation\sanitise_models.py [--no-verify] [--check]
```

Replaces the Windows user and host names that Aspen writes into the `.bkp` files with placeholders. Run it after any step that rewrites a `.bkp`. **[needs Aspen Plus V15]** unless `--check` or `--no-verify` is given; with `--no-verify` the files are edited without re-solving them. `--check` only reports and exits 1 if identifiers are present.

## 3. Equilibrium validation

**[Python only]**

```powershell
python scripts\generate_equilibrium_figures.py
python scripts\validate_equilibrium.py
python scripts\analyse_equilibrium_discrepancy.py
```

The first script writes the Python equilibrium grid `results\validation\equilibrium_python_grid.csv` and the equilibrium figures. The second compares it with the Aspen grid from section 2 and writes `results\validation\equilibrium_comparison.csv` and parity figures; it exits with a message and writes nothing if the Aspen CSV is missing. The third decomposes the difference into thermochemical-data and equation-of-state effects and writes `results\validation\equilibrium_discrepancy*.{csv,json}` and figures. The written discussion is [validation/discrepancy_analysis.md](validation/discrepancy_analysis.md).

## 4. Python models and analyses

**[Python only]**, unless marked otherwise. The scripts that take a result file default to `results\simulations\baseline.json` and fall back to the Python baseline if it is missing; the source is recorded in each output.

```powershell
python scripts\run_python_baseline.py [--eos ideal|pr]
```

Writes `results\simulations\python_baseline.json` and `python_baseline_no_hi.json` (with `--eos pr`, files with the suffix `_pr`) and prints the KPI table.

```powershell
python scripts\run_heat_integration.py results\simulations\baseline.json [--dtmin 20]
python scripts\run_heat_integration.py results\simulations\baseline_no_hi.json
```

Writes `results\simulations\heat_integration_<case_id>.json` and the composite-curve figures.

```powershell
python scripts\run_kinetics_study.py
```

Kinetics validation and the Ni versus Ru packed-bed study. Writes `results\validation\kinetics_validation.csv`, `results\simulations\pfr_baseline.json`, `results\sensitivity\pfr_temperature_sweep.csv` and figures. `--validation-only` skips the reactor part.

```powershell
python scripts\run_economics.py [results\simulations\baseline.json] [--target-lcoh 5.0]
python scripts\run_environmental.py [results\simulations\baseline.json] [--grid singapore_2024] [--distance-km 5000]
python scripts\run_separation_study.py [results\simulations\baseline.json]
```

Economics writes `results\simulations\economics_<case_id>.json`, the LCOH tornado and price-curve CSVs under `results\sensitivity\` and figures. Without `--target-lcoh` no break-even price is computed. The carbon-intensity script writes `results\simulations\environmental_<case_id>.json` and figures. The separation study writes `results\simulations\separation_<case_id>.json`, the membrane and PSA CSVs and figures.

```powershell
python scripts\run_optimisation.py [--candidates-only]
```

Single-objective optimisation, design grid, objective conflicts, Pareto fronts and the candidates for Aspen verification. Writes under `results\optimisation\` (`single_objective.json`, `design_grid.csv`, `pareto.json`, `pareto.csv`, `objective_conflicts.json`, `candidates_for_aspen.json`) and `results\figures\opt_*.png`. With `--candidates-only` only the candidate file is regenerated. The optimiser is seeded, so the result is repeatable. Run time: about 5 s per single-objective run, as quoted for the API endpoint; the whole script takes longer.

```powershell
python aspen\automation\verify_candidates.py [--tolerance 0.03] [--reuse]
```

**[needs Aspen Plus V15]**. Re-solves each candidate from `candidates_for_aspen.json` in Aspen, stores `results\simulations\opt_<id>.json`, compares the Python and Aspen metrics and writes `results\optimisation\aspen_verification.json` and `.csv`. `--reuse` keeps stored Aspen results whose inputs are identical; `--tolerance` overrides the default relative tolerance.

```powershell
python scripts\run_scenarios_analysis.py
python scripts\plot_aspen_sensitivity.py
```

The first writes `results\simulations\scenario_comparison.json`, `results\optimisation\scenario_comparison.csv` and scenario figures. The second draws figures from the Aspen sensitivity CSVs of section 2.

## 5. Validation matrix

**[Python only]**

```powershell
python scripts\build_validation_matrix.py [--skip-pytest]
```

Runs every check in `amcrax.validation` on the stored results and, unless `--skip-pytest` is given, the test suite. Writes `results\validation\validation_matrix.json`, three supporting CSVs and [validation/validation_matrix.md](validation/validation_matrix.md). Run it last, after all results above exist, so that no item is `not_run` for a missing input.

## 6. Dashboard data, static site and screenshots

```powershell
python scripts\export_snapshot.py
```

**[Python only]**. Copies the stored results, and the API responses derived from them, into `frontend\public\snapshot\` for SNAPSHOT mode. The script calls the API in process through a test client, so no server needs to be running. It writes nothing synthetic.

```powershell
cd frontend
npm run build:pages
```

**[Node only]**. Builds the static GitHub Pages site into `frontend\dist` with base path `/AmCraX/`. In this mode the site never contacts an API and reads the bundled snapshot, so run the snapshot export above first. The same command runs in `.github\workflows\deploy-pages.yml` on every push to `main`. To check the built site locally, run `node scripts\serve_pages.mjs` in one terminal and `node scripts\site_check.mjs` in another (the check needs Microsoft Edge).

```powershell
scripts\start_amcrax.ps1 -NoBrowser
node frontend\scripts\capture_dashboard.mjs --base http://localhost:5173
```

Captures the dashboard pages to `docs\screenshots\dashboard_*.png`. It needs Microsoft Edge and the API and dashboard running; without `--base` the script starts its own Vite server on port 5176 and needs the API on port 8000. The SNAPSHOT-mode images use `--query ?mode=snapshot --prefix snapshot`. The public-site images (`docs\screenshots\site_*.png`) come from `frontend\scripts\capture_site.mjs`, run against the locally served Pages build. Stop the servers with `scripts\stop_amcrax.ps1`.

```powershell
python aspen\automation\capture_screenshots.py [--only NAME ...]
```

**[needs Aspen Plus V15]**. Captures the baseline model in the Aspen Plus window through UI Automation into `aspen\screenshots\` and writes `manifest.json`. The Aspen window must be visible and in the foreground. The run-status image shows the Windows user and host names, so mask them before publishing.

## 7. Technical report and pitch deck

```powershell
python docs\technical_report\build_report.py [--no-pdf]
```

**[needs Word or PowerPoint]** for the PDF (Word); with `--no-pdf` only the `.docx` is built and Word is not needed. It also needs pandoc. It writes `docs\technical_report\AmCraX_Technical_Report.docx` and `.pdf` and a build log. The report build takes the section titled "Reproducing" into an appendix.

```powershell
python docs\pitch_deck\build_deck.py
```

**[needs Word or PowerPoint]** (PowerPoint). Reads every number from `results\`, lays out the slides with `pptxgenjs` (run `npm ci` in `docs\pitch_deck` once) and exports `docs\pitch_deck\AmCraX_Pitch_Deck.pptx` and `.pdf`. `--no-tests` and `--no-export` skip the test collection and the PowerPoint export.

## 8. Research expansion (Singapore hypothesis tests)

The index, with the meaning of every result folder, is [research/README.md](research/README.md). Run from the repository root after `. scripts\env.ps1`. Steps are **[Python only]** unless marked **[needs Aspen Plus V15]**. The stored Aspen results in `results\research\aspen_kinetic` allow all Python-only steps to run without Aspen Plus.

```powershell
python scripts\research\kinetics_validation.py
python scripts\research\kinetics_studies.py
python scripts\research\kinetics_aspen_spec.py
python scripts\research\economics_singapore.py
python scripts\research\catalyst_comparison.py
python scripts\research\purification_study.py
python scripts\research\lca_run.py
python scripts\research\enduse_run.py
```

**[Python only]**. Write the kinetics, economics, catalyst comparison, purification, life-cycle and end-use results under `results\research\<area>\`, the figures under `results\figures\research\` and one validation file per area under `results\research\validation\`. `lca_run.py` must run before `enduse_run.py`. `catalyst_comparison.py` takes about five minutes.

```powershell
python aspen\automation\make_catalyst_study_cases.py
python aspen\automation\run_kinetic_cases.py aspen\automation\cases\kinetic_validation_cases.json
python aspen\automation\run_kinetic_cases.py aspen\automation\cases\kinetic_lhhw_check_cases.json
python aspen\automation\run_kinetic_cases.py aspen\automation\cases\catalyst_validation_cases.json
python aspen\automation\run_kinetic_cases.py aspen\automation\cases\catalyst_study_cases.json
python aspen\automation\run_kinetic_cases.py aspen\automation\cases\catalyst_integrated_cases.json
python aspen\automation\sanitise_models.py --check
```

**[needs Aspen Plus V15]**. Runs the kinetic RPlug cases (standalone and integrated flowsheet) one at a time through the existing session and lock code (`aspen\runs\.aspen.lock`) and writes `results\research\aspen_kinetic\<case_id>.json` and `run_status.json`; cases already marked `ok` are skipped (`--force` re-runs). The sanitising check confirms that no user name, host name or user path remains in the research `.bkp` files.

```powershell
python aspen\automation\validate_kinetic_vs_python.py
python aspen\automation\summarise_catalyst_studies.py
```

**[Python only]**. Compare the stored Aspen results with the Python PFR and summarise the catalyst studies. Run in this order: the second step replaces the validation items with ids starting `cat_` and keeps the others.

```powershell
python aspen\automation\capture_kinetic_screenshots.py CASE_ID [CASE_ID ...] [--only 01 04 ...]
```

**[needs Aspen Plus V15]**. Captures the Aspen window of a case into `docs\images\aspen_evidence\` and updates `manifest.json`; user name, host name and user paths are masked before saving. Open every new PNG and record the result (`visually_verified`, `inspection_note`, `publish`) before using it.

```powershell
python scripts\research\build_research_validation.py
```

**[Python only]**. Aggregates `results\research\validation\*.json` into `results\research\validation\summary.json` and `docs\validation\research_validation.md`. Deterministic. It does not read or change the core validation matrix. Run it last.

## 9. Phase 2: regenerate everything, in order

Run from the repository root after `. scripts\env.ps1`. Nothing in 9.1 to 9.8 needs Aspen Plus, Word or PowerPoint, except where marked. The stored Aspen kinetic results (`results\research\aspen_kinetic`) are inputs, not outputs, of these steps.

| Step | What | Needs |
|---|---|---|
| 9.1 | Environment | Python 3.12 venv, Node 24 (`scripts\setup.ps1`) |
| 9.2 | All research results (master script) | Python only |
| 9.3 | Evidence matrix, version 2 | Python only |
| 9.4 | Test suite | Python only |
| 9.5 | Snapshot for the website | Python only |
| 9.6 | Frontend tests and the Pages build | Node only |
| 9.7 | Browser check of the built site | Node and Microsoft Edge |
| 9.8 | Technical report and paper | pandoc; Word for the PDF of the report |
| 9.9 | New Aspen runs (only if the Aspen model changes) | Aspen Plus V15 |

### 9.1 Environment

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
. scripts\env.ps1
```

### 9.2 All research results

```powershell
python scripts\research\run_all_phase2.py
python scripts\research\run_all_phase2.py --from uq     # resume at the first step whose path contains "uq"
```

The script runs 17 steps in dependency order and stops at the first failure. In order: the unified reference scenario (`economics_reference_scenario.py`), Singapore economics, life-cycle assessment, end-use pathways, end-use turbine thresholds, purification and the PSA against membrane study, catalyst comparison, heat exchanger study, catalyst economics, carbon pricing (modes A and B), the three uncertainty-quantification scripts and their acceptance checks, the simulator data export (`export_simulator_data.py`) and the research validation summary. The whole run takes about 20 to 30 minutes on the machine used for Phase 2. It never starts Aspen Plus. It rewrites `results\research\**` and the figures in `results\figures\research\`. Only a provenance hash changes when the inputs are unchanged.

### 9.3 Evidence matrix, version 2

```powershell
python scripts\research\build_evidence_matrix.py
```

Reads the result files and writes `results\research\evidence_matrix.json` and `docs\research\evidence_matrix.md`. The verdict rule is [research/verdict_methodology_v2.md](research/verdict_methodology_v2.md), fixed before the Phase 2 analyses. The matrix shows the version 1 verdict beside each version 2 verdict. If a coded rule gives a verdict that differs from the one recorded in the project notes, the builder reports it and does not force it.

### 9.4 Tests

```powershell
python -m pytest tests -q
```

Run it after 9.2 and 9.3 have finished. The expected result is zero failures and one skipped test (the opt-in live Aspen test). The failing items inside the validation files (exchanger duty, 40 bar kinetic check, two Takahashi prediction checks) are recorded results, not test failures.

### 9.5 Snapshot for the website

```powershell
python scripts\export_snapshot.py
```

Copies the stored results, the API responses derived from them and the three simulator files (`model.json`, `aspen_anchors.json`, `test_vectors.json`) into `frontend\public\snapshot\`. Run it after 9.2 and 9.3. It writes nothing synthetic.

### 9.6 Frontend tests and the Pages build

```powershell
cd frontend
npm test
npm run build:pages
```

`npm test` runs the unit tests, including the tests that compare the browser model with the Python test vectors. `npm run build:pages` writes the static site to `frontend\dist` with base path `/AmCraX/`. The site never contacts an API.

### 9.7 Browser check

```powershell
cd frontend
node scripts\serve_pages.mjs        # terminal 1, serves the built site locally
node scripts\site_check.mjs         # terminal 2, needs Microsoft Edge
node scripts\site_check.mjs --routes home     # optional: one route only ("home" is the simulator at "/")
```

The check opens every route at four viewport widths (390, 820, 1440 and 1920 px), and reports failed assertions and any HTTP status of 400 or above. It checks that pages load and that required elements and downloads exist. It does not judge whether a diagram is well drawn: look at the screenshots in `docs\screenshots\` for that. Screenshots are regenerated with `node scripts\capture_site.mjs` against the locally served build. By default the check also writes screenshots to `docs\screenshots\`; pass `--no-shots` to avoid that. `node scripts\e2e_sim_run.mjs` is a separate check of the live Simulation page of the platform (Python engine, API running); it is not part of the static site check.

### 9.8 Technical report and paper

```powershell
python docs\technical_report\build_report.py [--no-pdf]
```

Builds `docs\technical_report\AmCraX_Technical_Report.docx` and, with Word, the PDF. It reads every number from the result files. The short paper is built from its own folder under `docs\paper\`: follow the build instructions in that folder, which are kept with the paper. The 23 November 2026 release of the report in `docs\technical_report\releases\2026-11-23\` is not rebuilt and must not be edited.

### 9.9 Steps that need Aspen Plus V15

Only these need a licence. They are not needed to reproduce anything in 9.1 to 9.8.

- The baseline and sensitivity runs of section 2 (`aspen\automation\run_baseline.py`, `run_sensitivity.py`, `run_scenarios.py`, `run_equilibrium_grid.py`).
- The kinetic RPlug runs of section 8 (`aspen\automation\run_kinetic_cases.py`).
- `aspen\automation\verify_candidates.py` and `capture_screenshots.py`, `capture_kinetic_screenshots.py`.

Phase 2 made no new Aspen runs. All Aspen numbers in Phase 2 results are the stored values.

## 10. Verify the preserved release

The report and the research outputs of 23 November 2026 are kept unchanged. To check them:

```powershell
git rev-parse amcrax-research-expansion-2026-11-23^{commit}      # expect 80444217297c486cf8ec983fb3a1c10824b0cb2f
Get-FileHash docs\technical_report\releases\2026-11-23\AmCraX_Technical_Report_2026-11-23.pdf  -Algorithm SHA256
Get-FileHash docs\technical_report\releases\2026-11-23\AmCraX_Technical_Report_2026-11-23.docx -Algorithm SHA256
Get-FileHash results\research_releases\2026-11-23\evidence_matrix.json -Algorithm SHA256
```

The expected hashes are in [research/phase2_baseline.md](research/phase2_baseline.md):

| File | SHA-256 |
|---|---|
| Report PDF (10 806 889 bytes, 178 pages) | `0B4D03A487E3B06E26B7A38A1502D17E7C687F21D6C3A5D46FBECA19DF8A8F51` |
| Report DOCX | `B5272013E9BCFC2A67748438FF77F1FBAF7D5D183230A9B47D7554C194660B14` |
| Evidence matrix (version 1) | `3C72F509EF02AE8FD59A12963F3CC89C0662D98D4E1992924B6B1F8CE2FBAA60` |

To see the whole release as it was, use `git checkout amcrax-research-expansion-2026-11-23` in a separate clone. Do not run the Phase 2 scripts in that checkout, because they overwrite `results\research\`.

## 11. What the steps do and do not show

A passing run reproduces the stored numbers. It is numerical verification only. Comparisons of Python with Aspen, and with published values, are separate evidence kinds and have their own files under `results\research\validation\`. AmCraX has no independent experimental validation.
