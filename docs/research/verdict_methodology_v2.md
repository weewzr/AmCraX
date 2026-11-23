# Verdict methodology, version 2 (fixed before the Phase 2 analyses)

Written on 23 November 2026 and committed before any Phase 2 analysis was run, so that the rule cannot be shaped by the
new results. Version 1 of the rule and its verdicts are kept (see `docs/research/phase2_baseline.md` and
`results/research_releases/2026-11-23/evidence_matrix.json`), and every hypothesis in the version 2 matrix also shows
its version 1 verdict.

## Why the rule is changed

Version 1 called a hypothesis SUPPORTED only if every one of its rows was SUPPORTED. Three properties of that rule make
the overall verdict less informative than the rows:

1. **Rows of different kinds were given the same vote.** Some rows test the hypothesis itself. Others test whether a
   specific number quoted in the essay from another paper can be reproduced on AmCraX boundaries (for example the
   40 % cost advantage attributed to Halim et al., or the fuel and cost findings of Cho et al.). A failure to reproduce
   a quoted number is a finding about that number. It is not evidence against the hypothesis.
2. **A hypothesis with several components had only one verdict.** H2 and H3 each join two or three separable claims
   (economic and environmental; energy and cost). One unresolved component hid the supported ones.
3. **The conditions of a supported row were not part of the verdict.** A model result holds inside the range of
   conditions that were computed. That range should be stated with the verdict, not left in a limitations list.

The row-level standard is not relaxed. A row is still SUPPORTED only if the result is computed, is not a restatement of
an assumption built into the model, and survives its sensitivity or uncertainty analysis.

## Structure

Each hypothesis is split into:

- **Primary hypothesis**: the statement itself.
- **Components**: the separable claims inside the statement. Each component has its own verdict.
- **Rows (sub-claims)**: each row belongs to one component and has a role:
  - `primary`: tests the component directly.
  - `secondary`: reproduction of a specific published or essay number, or a technology comparison that the
    hypothesis statement does not contain. Secondary rows are reported in full but do not vote.
- For every row: numerical conclusions, assumptions, uncertainty, validation status, and the **envelope** (the range of
  conditions inside which the row verdict holds, with computed thresholds where they exist).

## Row roles (fixed here)

| Hypothesis | Component | Primary rows | Secondary rows |
|---|---|---|---|
| H1 | H1-P Direct use is preferable where ammonia can be burned directly | H1-a (standalone cracking for power), H1-c (cracking integrated with the turbine exhaust) | H1-b (the 40 % figure) |
| H1 | H1-Q Cracking is justified where molecular hydrogen is the product | H1-d | |
| H2 | H2-E Affordable ammonia is essential to economic competitiveness | H2-a, H2-b | |
| H2 | H2-C Low-carbon ammonia is essential to environmental competitiveness | H2-c, H2-d | |
| H2 | H2-X Cross-claim: low carbon intensity is rewarded economically | H2-e (reported under the actual Singapore carbon-tax boundary and, separately, under a hypothetical life-cycle carbon price) | |
| H3 | H3-T Lower-temperature operation reduces energy use | H3-a, H3-b | |
| H3 | H3-H Heat integration reduces energy use | H3-d | |
| H3 | H3-K The savings can outweigh a higher catalyst cost | H3-c | H3-e, H3-f (reproduction of Cho et al.) |
| H4 | H4-B Purity must be balanced against recovery, energy and cost | H4-a, H4-b, H4-e | H4-c (published PSA point), H4-d (membrane against PSA) |

New rows added in Phase 2 must be given a component and a role when they are defined, before their result is computed.

The cross-claim H2-X is kept as its own component because the hypothesis statement can be read in two ways. Under the
first reading, affordability serves the economic claim and low carbon intensity serves the environmental claim. Under
the second, low carbon intensity is also claimed to help the economics. Version 1 used the second reading. Version 2
reports both: H2-E and H2-C carry the first reading and H2-X carries the second, and the H2 verdict text must always
state the H2-X outcome.

## Rules

**Row verdict** (unchanged vocabulary): SUPPORTED, CONTRADICTED or INCONCLUSIVE.

- SUPPORTED requires a computed result that does not follow from a built-in assumption, that holds across the stated
  sensitivity or uncertainty range, and whose envelope is stated.
- A row whose direction follows from an assumption can become SUPPORTED only through evidence that is independent of
  that assumption. One accepted form is a threshold analysis: compute the value of the assumed quantity at which the
  conclusion reverses, and compare that threshold with sourced values of the quantity. If sourced values lie clearly on
  one side of the threshold, the row is SUPPORTED inside the envelope they define. If no adequate source exists, or
  sourced values straddle the threshold, the row stays INCONCLUSIVE and the threshold is reported as the finding.
- A result smaller than the demonstrated numerical resolution of the model (for example the Python against Aspen
  offset) cannot support or contradict a row.
- A hypothetical scenario (for example a carbon price applied to embodied emissions) can only support a row that is
  explicitly conditional on that scenario. It cannot change a row about actual policy.

**Component verdict**, from its primary rows:

- SUPPORTED: every primary row is SUPPORTED.
- CONTRADICTED: no primary row is SUPPORTED and at least half are CONTRADICTED.
- MIXED: at least one primary row is SUPPORTED and at least one is CONTRADICTED.
- PARTIALLY SUPPORTED: at least one primary row is SUPPORTED, none is CONTRADICTED and at least one is INCONCLUSIVE.
- INCONCLUSIVE: otherwise.

**Hypothesis verdict**, from its components (the cross-claim H2-X is reported beside the verdict and is counted as a
component):

- SUPPORTED: every component is SUPPORTED.
- CONTRADICTED: no component is SUPPORTED or PARTIALLY SUPPORTED and at least half are CONTRADICTED.
- MIXED: at least one component is SUPPORTED or PARTIALLY SUPPORTED and at least one is CONTRADICTED.
- PARTIALLY SUPPORTED: at least one component is SUPPORTED or PARTIALLY SUPPORTED, none is CONTRADICTED, and not all
  are SUPPORTED.
- INCONCLUSIVE: otherwise.

Every hypothesis verdict is printed with its component verdicts, the envelope of each supported component, the
secondary-row findings and the version 1 verdict. A verdict of SUPPORTED never appears without its envelope.

## What the rule does not allow

- Changing a row's role or component after its Phase 2 result is known.
- Counting a secondary row as support.
- Calling a model result validated outside the range in which it was checked.
- Describing agreement between two models, or with a published number, as experimental validation.
