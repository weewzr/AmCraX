<!-- cites: cho2026nickel, iso2019hydrogen, halim2025ammonia, sayas2020rukcao, abdoos2025psa -->

# 40 Four-hypothesis evidence matrix

This section brings the evidence of Sections 25 to 39 together. The evidence matrix is a single data file, `results/research/evidence_matrix.json`, with a human-readable version in `docs/research/evidence_matrix.md`. The tables of this section are generated from the JSON file when the report is built, so the verdicts and numbers shown here are those in the file and are never retyped.

## 40.1 Verdict methodology v2

The verdict rule is `docs/research/verdict_methodology_v2.md`. Only the row roles, the components, the aggregation rule and the general row standard were fixed in it before the Phase 2 analyses (commit f233509), and they have not been edited since. The row-by-row coded decision rules of the matrix builder were written after the results were known; they were then tested by an independent adversarial review, which moved three rows (H2-b, H3-d and H4-e) from SUPPORTED to INCONCLUSIVE (Section 31.4). Each hypothesis is stated as one primary hypothesis and split into components; each component has primary rows, which vote, and secondary rows, which are reported but do not vote. Each row is judged against its own claim by a rule stated in the row, with an envelope (the range of inputs in which the conclusion holds) and, where the outcome depends on an unsourced input, a threshold compared with the sourced values. A row whose sourced values straddle its threshold is INCONCLUSIVE. A result smaller than the demonstrated numerical resolution of the model cannot support or contradict a row, and a hypothetical scenario cannot change a row about actual policy. A component is SUPPORTED if every primary row is SUPPORTED, CONTRADICTED if no primary row is SUPPORTED and at least half are CONTRADICTED, MIXED if at least one is SUPPORTED and one CONTRADICTED, PARTIALLY SUPPORTED if at least one is SUPPORTED, none CONTRADICTED and at least one INCONCLUSIVE, and INCONCLUSIVE otherwise. Components combine into the hypothesis verdict by the same pattern, with PARTIALLY SUPPORTED components counting towards MIXED and PARTIALLY SUPPORTED; by the written rule a MIXED component counts for nothing at hypothesis level. A PARTIALLY SUPPORTED hypothesis is always printed with the components it rests on. The row standard itself is unchanged from version 1: a row is SUPPORTED only if the result is computed, does not restate a built-in assumption and survives its sensitivity or uncertainty analysis.

Version 1.0 of this report used a stricter combination rule (rule v1): a hypothesis was SUPPORTED only if every one of its rows was SUPPORTED, and CONTRADICTED only if none was SUPPORTED and at least half were CONTRADICTED. Under that rule all four hypotheses were INCONCLUSIVE. The v1 verdicts are shown next to the v2 verdicts in the tables below, together with the result of applying rule v1 to the current rows, so that a change of label can be traced to the rule or to the evidence. Row H2-e is judged in two carbon-pricing modes: the actual Singapore boundary (Mode A), which votes because the row is about actual policy, and a hypothetical life-cycle price (Mode B, not Singapore law), which is reported only.

The three row changes after the independent review applied the row standard more strictly, not less: each of those rows had a coded rule that could not fail or tested only half of its sub-claim. As a result, the only row verdicts that differ from version 1.0 are those of H2-b, H3-d and H4-e, which were SUPPORTED under rule v1 and are INCONCLUSIVE now. Where the coded rule of the matrix builder gives a different row verdict from the one decided from the result files, the matrix reports the difference instead of forcing a verdict.

Plain answers state what the model computes and under which assumptions; the formal classification applies a stricter rule fixed before the analysis, under which a result that rests on an untested assumption is not counted as supported; both are published. Elsewhere in this report each hypothesis is summarised by its headline answer and limitations first; this chapter keeps the formal classification. Each hypothesis section below opens with a table of plain answers: a reading aid that answers the claims inside the hypothesis with Yes, Yes under the stated assumption, No or Not established, derived in code from the formal outcomes. Yes under the stated assumption is given only where the result is computed with the claimed direction on every basis, the formal test is inconclusive solely because one named quantity is assumed and no sourced value of it exists, and the limitation names the assumption and its break-even value (in this edition: the fired-cracking half of H1-a, where the turbine efficiency is assumed). Yes is given only where the underlying test is SUPPORTED, either a row verdict or one half of a two-half row that is computed and stored separately (H1-a: cracking with PSA and fired cracking; H3-d: energy and cost); No only where it is CONTRADICTED; everything else is Not established. A plain answer for half a row is a finding, and the formal row verdict stays INCONCLUSIVE because the row needs both halves. No plain answer changes a row, component or hypothesis verdict. Secondary rows that test a published figure are listed after the table as reproduced, not reproduced or not established.

## 40.2 Verdicts

{{EVIDENCE_SUMMARY_TABLE}}

## 40.3 H1 End-use suitability

{{EVIDENCE_ROWS:H1}}

## 40.4 H2 Feedstock

{{EVIDENCE_ROWS:H2}}

## 40.5 H3 Catalyst and heat integration

{{EVIDENCE_ROWS:H3}}

## 40.6 H4 Purification

{{EVIDENCE_ROWS:H4}}

## 40.7 How to read the verdicts

A verdict states what the AmCraX models, with their stated boundaries, can show about a hypothesis; it is not a general statement about ammonia cracking.

**Support must not be built in.** Some results that look like support follow directly from model inputs and are not counted as evidence. The baseline hydrogen purity follows from the assumed PSA split fractions. The ranking of direct ammonia power above fired or purified cracking follows from the assumption of equal turbine efficiency; only the size of the gap and the efficiency threshold are computed results (Section 33). A share of an input, such as the feed share of the LCOH, is tested by a threshold against sourced ranges, not taken as evidence by itself (Section 34).

**Thresholds decide where sources are missing.** Where no source exists for a decisive input (the turbine efficiency on H~2~/N~2~ fuel, the overall heat-transfer coefficient at 20 bar, a catalyst quotation, the PSA recovery on cracked ammonia), the row gives the threshold at which its conclusion changes and compares it with whatever is sourced. If the sourced values straddle the threshold, the row is INCONCLUSIVE.

**Uncertainty is often larger than the effect.** The cost differences between catalysts are a few hundredths of a US dollar per kilogram, while the 90 % range of the LCOH from economic inputs alone spans 3.21 to 4.84 USD/kg in the Sobol sample, conditional on the assumed input distributions (Section 37). An effect smaller than the resolution of the model that produces it is not counted as support in either direction.

**Unverified literature is not evidence.** Essay values whose primary source could not be read are kept as leads and labelled unverified. No AmCraX result uses them as an input; where a row tests such a claim it does so with AmCraX's own calculation.

**Addendum: three papers read in full (24 November 2026).** Three papers that earlier could be seen only as abstracts or search summaries were read in full: Halim et al. (2025), Abdoos et al. (2025) and Sayas et al. (2020). No verdict moved: H1 {{VERDICT:H1}}, H2 {{VERDICT:H2}}, H3 {{VERDICT:H3}} and H4 {{VERDICT:H4}}, and every component and row verdict is unchanged; the baseline of 4.015 USD/kg stays frozen. The papers locate the Singapore plant figures quoted in the essay and show that its 40 % is a fuel-cost comparison, not a cost of power (Section 33.4); give the only published PSA purity-recovery front for this gas composition, a simulation, which is carried as a labelled case and a baseline sensitivity (Sections 32.4 and 36.4); and confirm the Ru-K/CaO orders and activation energy without supplying a rate constant (Section 35.2). Section 31.5 lists every correction.

**Essay statements that are not reproduced.** On the unified basis, direct NH~3~ power is 7.6 % cheaper than fired cracking and 16.5 % cheaper than cracking with PSA under the equal-efficiency assumption, not about 40 %, and 1.3 % dearer than exhaust-heated cracking ({{ROW_VERDICT:H1-b}}). The paper behind the 40 % computes no cost of power: its 39 to 44 % is a fuel cost at the turbine inlet, on which AmCraX gives 20 to 33 % (Section 33.4). The statement of Cho et al. (2026) that a Ru cracker needs no supplementary fuel while a Ni cracker does holds only for PSA recoveries of 0.7564 to 0.7813 ({{ROW_VERDICT:H3-e}}). Their 7.0 % lower reconversion cost for Ru becomes -16.2 to +1.6 % on AmCraX boundaries ({{ROW_VERDICT:H3-f}}). The published PSA point of 99.11 mol% H~2~ contains about 8,900 ppm N~2~ and meets neither the 99.9 % industrial grade nor ISO 14687:2019 grade D (International Organization for Standardization [ISO], 2019) ({{ROW_VERDICT:H4-c}}).
<!-- data: results/research/enduse/turbine_threshold.json; results/research/catalyst_economics/catalyst_economics.json row_evidence H3-e, H3-f; results/research/purification/purification_study.json PSA_CHO N2 8900 ppm; results/research/uq/gsa_sobol.json (90 % range 3.206-4.840) -->
