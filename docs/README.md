# AmCraX documentation

This folder holds the documentation of AmCraX, the Ammonia Cracking Simulation and Optimisation Platform. The project README is [../README.md](../README.md). The documents are grouped by purpose.

## Getting started

| Document | Contents |
|---|---|
| [installation.md](installation.md) | Prerequisites, one-step setup, verification, launching the API and dashboard, running without Aspen Plus, troubleshooting. |
| [user_guide.md](user_guide.md) | The dashboard: data modes, provenance badges, each page, typical workflows. |

## Explanation

| Document | Contents |
|---|---|
| [model_assumptions.md](model_assumptions.md) | Assumption register for each model layer, with value, source and expected impact. |
| [validation/validation_matrix.md](validation/validation_matrix.md) | The validation matrix: every check, its status and its evidence. |
| [validation/discrepancy_analysis.md](validation/discrepancy_analysis.md) | Why the Aspen Plus and independent Python equilibrium results differ. |
| [known_limitations.md](known_limitations.md) | Limitations by layer, with consequences and remedies. |
| [technical_report/AmCraX_Technical_Report.pdf](technical_report/AmCraX_Technical_Report.pdf) | The technical report: methods, results, validation and discussion (a `.docx` copy sits beside it). |

## How-to

| Document | Contents |
|---|---|
| [reproducing.md](reproducing.md) | The ordered commands that regenerate every result, with the software each step needs. |
| [reproducing.md](reproducing.md#2-aspen-plus-results) | Running the Aspen Plus cases, sensitivity studies and scenarios. |
| [reproducing.md](reproducing.md#6-dashboard-data-static-site-and-screenshots) | Exporting the snapshot, building the static site and capturing screenshots. |
| [reproducing.md](reproducing.md#7-technical-report-and-pitch-deck) | Rebuilding the technical report and the pitch deck. |

## Reference

| Document | Contents |
|---|---|
| [api.md](api.md) | The HTTP API: endpoints, job life-cycle, process isolation of Aspen, error model. |
| [developer_guide.md](developer_guide.md) | Toolchain, layout, data contract, integrity rules, Python interfaces, tests, extension points. |
| [dependencies.md](dependencies.md) | Python and npm packages and external tools, with versions and licences. |
| [reference_projects/github_survey.md](reference_projects/github_survey.md) | Third-party software survey: public projects that were read for context, none vendored. A machine-readable copy is in [reference_projects/github_survey.json](reference_projects/github_survey.json). |

The screenshots used by the user guide are in `screenshots/`. The pitch deck and its speaker script are in `pitch_deck/`.
