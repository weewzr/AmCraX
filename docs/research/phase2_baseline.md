# Phase 2 baseline record

This file records the state of AmCraX immediately before Phase 2 work started. Phase 2 results are judged against it.

## Checkpoint

| Item | Value |
|---|---|
| Date and time of record | 23 November 2026, 16:30 SGT |
| Branch at checkpoint | `main` |
| Commit | `80444217297c486cf8ec983fb3a1c10824b0cb2f` (`8044421`) |
| Working tree | clean (no uncommitted changes) |
| Remote | `https://github.com/weewzr/AmCraX.git`; `origin/main` at the same commit |
| Tags before checkpoint | none |
| Checkpoint tag | `amcrax-research-expansion-2026-11-23` (annotated), pushed to GitHub, target `8044421` |
| Deployed GitHub Pages commit | `8044421` (workflow run of 2026-11-23T08:04:16Z, conclusion `success`) |
| Phase 2 branch | `feature/phase2-interactive-research`, created from `8044421` |

History was not rewritten and nothing was force-pushed.

## Preserved release of the technical report

The 178-page technical report of the research expansion is kept unchanged as a historical release.

| Item | Value |
|---|---|
| Location | `docs/technical_report/releases/2026-11-23/` |
| PDF | `AmCraX_Technical_Report_2026-11-23.pdf`, 10 806 889 bytes, 178 pages |
| PDF SHA-256 | `0B4D03A487E3B06E26B7A38A1502D17E7C687F21D6C3A5D46FBECA19DF8A8F51` |
| DOCX | `AmCraX_Technical_Report_2026-11-23.docx` |
| DOCX SHA-256 | `B5272013E9BCFC2A67748438FF77F1FBAF7D5D183230A9B47D7554C194660B14` |
| Generated | 23 November 2026, 15:54 SGT |
| Commit that contains it | `8044421` (also reachable through the tag above) |

## Preserved research outputs

`results/research_releases/2026-11-23/` is a copy of `results/research/` at the checkpoint (249 files) plus the
human-readable evidence matrix. The evidence matrix file `evidence_matrix.json` has SHA-256
`3C72F509EF02AE8FD59A12963F3CC89C0662D98D4E1992924B6B1F8CE2FBAA60`. The 31 Aspen Plus captures in
`docs/images/aspen_evidence/` and the reference library are unchanged and are also reachable through the tag.

## Baseline verification (run at commit `8044421`)

| Check | Result |
|---|---|
| Python tests (`python -m pytest tests`) | 513 passed, 1 skipped (opt-in live Aspen test), 0 failed |
| Frontend unit tests (`npm test`) | 107 passed in 19 files |
| Browser checks (`node scripts/site_check.mjs`, four viewports) | 689 passed, 0 failed, no HTTP status of 400 or above |
| Research validation (`results/research/validation/summary.json`) | 350 items: 295 pass, 10 fail, 45 informational |
| Core validation matrix | 137 items: 105 pass, 22 fail, 10 informational |
| Aspen kinetic runs | 162, all with status `ok` |

### Known failures carried into Phase 2

- Three kinetic RPlug checks are slightly above the Peng-Robinson equilibrium conversion (by at most 4.9e-4 against a tolerance of 1e-4).
- Five checks of the feed-effluent exchanger duty: the Python value is 3.6 to 4.4 % above the Aspen value against a tolerance of 3 %.
- Two prediction checks of the Takahashi rate laws (mirrored from the core validation matrix).

These counts describe numerical verification, comparison between two models and comparison with published values.
None of them is an independent experimental validation.

## Hypothesis verdicts at the checkpoint (evidence matrix version 1)

| Hypothesis | Verdict | Row outcomes |
|---|---|---|
| H1 End-use suitability | INCONCLUSIVE | H1-a, H1-c, H1-d inconclusive; H1-b contradicted |
| H2 Feedstock | INCONCLUSIVE | H2-a to H2-d supported; H2-e contradicted |
| H3 Catalyst and heat integration | INCONCLUSIVE | H3-a, H3-d supported; H3-b, H3-c, H3-e, H3-f inconclusive |
| H4 Purification | INCONCLUSIVE | H4-e supported; H4-c contradicted; H4-a, H4-b, H4-d inconclusive |

## Phase 2 final state (24 November 2026)

Recorded after the fix pass and the plain-answers layer, on branch `feature/phase2-interactive-research` (uncommitted
working tree at the time of the runs). Re-run the commands to confirm.

| Check | Result |
|---|---|
| Python tests (`python -m pytest tests -o addopts=""`) | 753 passed, 1 skipped (opt-in live Aspen test), 0 failed |
| Frontend unit tests (`npm test`) | 290 passed in 30 files |
| Browser checks (`node scripts/site_check.mjs`, all routes, four viewports) | 1037 passed, 0 failed, no HTTP status of 400 or above |
| Research validation (`results/research/validation/summary.json`) | 696 items: 607 pass, 12 fail, 76 informational, 1 not available |
| By evidence kind | numerical verification 464 (440 pass, 5 fail, 19 informational); Python against Aspen comparison 183 (156, 5, 22); comparison with published literature 48 (11, 2, 35); independent experimental validation: none (1 placeholder item, not available) |
| Technical report | `docs/technical_report/AmCraX_Technical_Report.pdf`, 243 pages, SHA-256 `2194C8CB1A23A42F1ED524755D25698536675C18F00D10D7A6946AAF7BF58B64`; quality report: no unresolved tokens, privacy scan PASS |
| Paper and executive summary | `docs/paper/build/AmCraX_Paper.pdf` 18 pages; `docs/paper/build/AmCraX_Executive_Summary.pdf` 2 pages |
| Baseline LCOH | 4.015461254695034 USD/kg (unchanged; fuel counted at 100 % of its lower heating value) |

Hypothesis verdicts (methodology version 2, with components; version 1 verdicts all INCONCLUSIVE):

| Hypothesis | Verdict | Components |
|---|---|---|
| H1 End-use suitability | INCONCLUSIVE | H1-P INCONCLUSIVE, H1-Q INCONCLUSIVE |
| H2 Feedstock | MIXED | H2-E PARTIALLY SUPPORTED, H2-C SUPPORTED, H2-X CONTRADICTED |
| H3 Catalyst and heat integration | PARTIALLY SUPPORTED, resting only on H3-T | H3-T PARTIALLY SUPPORTED, H3-H INCONCLUSIVE, H3-K INCONCLUSIVE |
| H4 Purification | INCONCLUSIVE | H4-B INCONCLUSIVE |

The evidence matrix also carries plain answers (Yes, No or Not established) to the claims inside each hypothesis. They
are a reading aid derived in code from the row verdicts and from the separately stored halves of rows H1-a and H3-d;
they change no verdict.
