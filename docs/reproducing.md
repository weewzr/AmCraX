# Reproducing the results

This page lists, in order, the commands that regenerate every stored result, figure and deliverable. Run them from the project root in Windows PowerShell 5.1 after `. scripts\env.ps1` (see [installation.md](installation.md)).

Each step carries one of these requirements:

| Marker | Needs |
|---|---|
| **[Python only]** | The Python environment. No Aspen Plus, Word or PowerPoint. |
| **[needs Aspen Plus V15]** | A licensed Aspen Plus V15 installation with COM registered. One Aspen instance runs at a time (see the Aspen rule in the [developer guide](developer_guide.md)). |
| **[needs Word or PowerPoint]** | Microsoft Word (report) or PowerPoint (deck) for the PDF export. |

The stored files in `results/` already hold the outputs. Reproduce them only when you change a model, a parameter or a script, or when you want to confirm them. Run times are given where a script or a document records them; where none is recorded the entry says so. They depend on the machine.

The Aspen steps need a seat that is free for the whole run. A single converged flowsheet solve takes a few seconds (the engine time recorded for the baseline is about 2 s). Scripts that solve many points take correspondingly longer.

## 1. Check the environment

**[Python only]**

```powershell
. scripts\env.ps1
python -m pytest tests -q
```

Expected: all tests pass, and one test (the opt-in live Aspen test) is skipped. Aspen is never started.

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

**[Python only]** Placeholder: the static-site build for GitHub Pages. The command and its options are to be confirmed by the website maintainer; see [../frontend/README.md](../frontend/README.md).

```powershell
scripts\start_amcrax.ps1 -NoBrowser
node frontend\scripts\capture_dashboard.mjs --base http://localhost:5173
```

Captures the dashboard pages to `docs\screenshots\dashboard_*.png`. It needs Microsoft Edge and the API and dashboard running; without `--base` the script starts its own Vite server on port 5176 and needs the API on port 8000. The SNAPSHOT-mode images use `--query ?mode=snapshot --prefix snapshot`. Placeholder: the website maintainer will confirm the capture script and options for the static site. Stop the servers with `scripts\stop_amcrax.ps1`.

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
