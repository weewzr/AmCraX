# Research expansion: Singapore-specific hypothesis tests

This folder indexes the research expansion of AmCraX. It tests four hypotheses from the author's CN5190 essay computationally, using Jurong Island as a representative industrial setting for Singapore (no claim is made that a facility exists).

| Id | Hypothesis |
|---|---|
| H1 | End-use suitability: cracking is most justified when the end use needs molecular hydrogen, not where ammonia can be used directly. |
| H2 | Feedstock: affordable, low-carbon ammonia is essential to economic and environmental competitiveness. |
| H3 | Catalyst and heat integration: low-temperature, high-activity catalysts with effective heat integration reduce energy use and can outweigh higher catalyst cost. |
| H4 | Purification: must balance purity requirements against recovery losses, energy and equipment cost. |

Allowed verdicts are SUPPORTED, CONTRADICTED and INCONCLUSIVE. They are held only in the evidence matrix and are not repeated in these pages:

- [evidence_matrix.md](evidence_matrix.md), generated from `results/research/evidence_matrix.json` (rows per sub-claim with the Aspen model, Python model, case ids, assumptions, literature, validation method, numerical findings, uncertainty, limitations and links to data, figures and screenshots).
- [validation_and_limitations.md](validation_and_limitations.md): what was validated against what, what is preliminary or assumed, what failed and why, and inaccessible sources.
- [../validation/research_validation.md](../validation/research_validation.md): aggregated research validation items, including every failure.

Every value is labelled `aspen` (Aspen Plus V15 run), `python` (independent model), `literature` or `assumption` in its result file. Ni/CeO2, Ru/CeO2 and Ru-K/CaO are not modelled because no usable published rate law was available (see [validation_and_limitations.md](validation_and_limitations.md), section 3.1).

## Where each result lives

Paths are relative to the repository root. Figures are in `results/figures/research/`, written with a CSV of the plotted data next to the result JSON.

| Workstream | Result folder | Script | Figures | Validation file |
|---|---|---|---|---|
| Kinetics (catalyst rate laws, studies) | `results/research/kinetics` | `scripts/research/kinetics_validation.py`, `kinetics_studies.py`, `kinetics_aspen_spec.py` (helpers in `kinetics_common.py`) | `kinetics_*.png` | `results/research/validation/kinetics.json` |
| Aspen Plus RPlug (kinetic reactor, catalyst cases) | `results/research/aspen_kinetic` | `aspen/automation/run_kinetic_cases.py`, `make_catalyst_study_cases.py`, `summarise_catalyst_studies.py`, `validate_kinetic_vs_python.py`, `capture_kinetic_screenshots.py` | `aspen_kinetic_*.png` | `results/research/validation/aspen_kinetic.json` |
| Catalyst comparison and heat integration (H3) | `results/research/catalyst_comparison` | `scripts/research/catalyst_comparison.py` | `catalyst_*.png` | `results/research/validation/catalyst_comparison.json` |
| Singapore techno-economics (H2) | `results/research/singapore` | `scripts/research/economics_singapore.py` | `singapore_*.png` | `results/research/validation/economics.json` |
| Purification (H4) | `results/research/purification` | `scripts/research/purification_study.py` | `purification_*.png` | `results/research/validation/purification.json` |
| End use (H1) | `results/research/enduse` | `scripts/research/enduse_run.py` (run `lca_run.py` first) | `enduse_*.png` | `results/research/validation/enduse.json` |
| Life-cycle assessment (H1, H2) | `results/research/lca` | `scripts/research/lca_run.py` | `lca_*.png` | `results/research/validation/lca.json` |
| Validation summary | `results/research/validation/summary.json` | `scripts/research/build_research_validation.py` | none | all of the above |

Code added for the research expansion (additive; existing behaviour is unchanged): `backend/amcrax/kinetics` (research catalysts), `backend/amcrax/aspen/kinetic.py` (kinetic RPLUG builder and runner), `backend/amcrax/research/catalyst_comparison.py`, `backend/amcrax/economics/singapore.py` with `backend/amcrax/data/singapore.yaml`, `backend/amcrax/separation/purification.py`, `backend/amcrax/enduse` and `backend/amcrax/environmental/lca.py`. Tests: `tests/test_research_*.py`. New references: `research/reference_additions/*.json` (the library `research/references.json` is not edited). Each workstream also writes `assumptions.json` (name, value, unit, source type, source, applicability note) in its result folder.

### Aspen models and screenshots

- Models: `aspen/models/research/` holds one input file (`.inp`) and one sanitised backup (`.bkp`) per case. The case id prefix gives the study: `kv_` and `kl_` (kinetic validation and LHHW checks), `ki_` (integrated validation), `cv_` (catalyst validation points), `cs_` (catalyst studies), `ci_` (catalyst, integrated flowsheet). Case lists are in `aspen/automation/cases/`.
- Run status: `results/research/aspen_kinetic/run_status.json` (one entry per case).
- Screenshots: `docs/images/aspen_evidence/` with `manifest.json`. Each capture records its case id, model file, navigation path, inspection result (`visually_verified`, `inspection_note`) and `publish`. A capture with `publish: false` must not be used in the website or report.

## Reproducing the research results

Run from the repository root after loading the environment (`. scripts\env.ps1`). Steps marked **[Aspen Plus V15]** need a licensed Aspen Plus V15 installation on Windows and take a machine-wide lock (`aspen/runs/.aspen.lock`); one instance at a time. Steps marked **[Python only]** do not need Aspen Plus. The stored results in `results/research/aspen_kinetic` allow every Python-only step to be re-run without Aspen.

### Python only

```powershell
python scripts\research\kinetics_validation.py
python scripts\research\kinetics_studies.py
python scripts\research\kinetics_aspen_spec.py
python scripts\research\economics_singapore.py
python scripts\research\catalyst_comparison.py
python scripts\research\purification_study.py
python scripts\research\lca_run.py
python scripts\research\enduse_run.py
python scripts\research\build_research_validation.py
```

Notes: `lca_run.py` must precede `enduse_run.py`; `catalyst_comparison.py` takes about five minutes and reads the stored Aspen results; `build_research_validation.py` must be last because it aggregates the other validation files. The Aspen-side validation and summary steps below are also Python only but read Aspen results:

```powershell
python aspen\automation\validate_kinetic_vs_python.py
python aspen\automation\summarise_catalyst_studies.py
```

`validate_kinetic_vs_python.py` writes `results/research/validation/aspen_kinetic.json`; `summarise_catalyst_studies.py` then replaces the items with ids starting `cat_` and keeps the others, so run them in this order.

### Needs Aspen Plus V15

```powershell
python aspen\automation\make_catalyst_study_cases.py
python aspen\automation\run_kinetic_cases.py aspen\automation\cases\kinetic_validation_cases.json
python aspen\automation\run_kinetic_cases.py aspen\automation\cases\kinetic_lhhw_check_cases.json
python aspen\automation\run_kinetic_cases.py aspen\automation\cases\catalyst_validation_cases.json
python aspen\automation\run_kinetic_cases.py aspen\automation\cases\catalyst_study_cases.json
python aspen\automation\run_kinetic_cases.py aspen\automation\cases\catalyst_integrated_cases.json
python aspen\automation\sanitise_models.py --check
python aspen\automation\capture_kinetic_screenshots.py CASE_ID [CASE_ID ...] [--only 01 04 ...]
```

`run_kinetic_cases.py` skips cases already marked `ok` (use `--force` to re-run). Each run goes through the existing session and lock code in `backend/amcrax/aspen`. `capture_kinetic_screenshots.py` opens a copy of a saved `.bkp` in a visible Aspen window, re-runs it, captures the Aspen window only and masks the user name, host name and any user path before saving; after capture, every PNG must be opened and inspected before `visually_verified` is trusted.

### Tests

```powershell
python -m pytest tests -q
```

The research tests are `tests/test_research_*.py`. The live-Aspen test is opt-in and skipped by default.

## Reading the numbers

- A pass in a validation file means the stated check was met, not that the physical claim is established; several kinetic passes are consistency checks against the fitting data.
- All rate laws are used at 20 bar although fitted at 1 atm (Takahashi, Lucentini) or up to 10 bar (Kum); Aspen agreeing with Python validates the implementation, not the rate law.
- The CAPEX model does not respond to temperature, reactor volume or exchanger area.
- No product is called fuel-cell grade; purity claims name the ISO 14687 contaminants that were evaluated and list those that were not.
