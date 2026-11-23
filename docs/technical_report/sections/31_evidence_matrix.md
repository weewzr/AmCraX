<!-- cites: cho2026nickel, cechetto2023membrane, iso2019hydrogen, sayas2020high -->

# 31 Four-hypothesis evidence matrix

This section brings the evidence of Sections 25 to 30 together. The evidence matrix is a single data file, `results/research/evidence_matrix.json`, with a human-readable version in `docs/research/evidence_matrix.md`. Each hypothesis is split into rows, one per sub-claim; each row records the Singapore scenario, the Aspen Plus and Python models, the case identifiers, the input assumptions, the literature, the validation method, the numerical findings with their origin and source file, the uncertainty range, the limitations, and a conclusion with the conditions under which it holds. The tables of this section are generated from the JSON file when the report is built, so the verdicts and numbers shown here are those in the file and are never retyped.

Each row receives its own verdict from a rule stated in the row (for example, a cost difference smaller than the Monte Carlo band of the LCOH gives INCONCLUSIVE). A hypothesis is SUPPORTED only if every one of its rows is SUPPORTED, CONTRADICTED if none of its rows is SUPPORTED and at least half are CONTRADICTED, and INCONCLUSIVE otherwise. This rule is strict on purpose: a hypothesis with several parts is supported only if every part is.

## 31.1 Verdicts

{{EVIDENCE_SUMMARY_TABLE}}

## 31.2 H1 End-use suitability

{{EVIDENCE_ROWS:H1}}

## 31.3 H2 Feedstock

{{EVIDENCE_ROWS:H2}}

## 31.4 H3 Catalyst and heat integration

{{EVIDENCE_ROWS:H3}}

## 31.5 H4 Purification

{{EVIDENCE_ROWS:H4}}

## 31.6 What the verdicts mean

A verdict states what the AmCraX models, with their stated boundaries, can show about a hypothesis; it is not a general statement about ammonia cracking. Three points govern how the verdicts should be read.

**Support must not be built in.** Some results that look like support follow directly from model inputs and are not counted as evidence. The baseline hydrogen purity follows from the assumed PSA split fractions, and the PSA recovery-purity relation used in Section 28 is flat by construction between the two published points, so neither says anything about the size of the purity penalty. For the same reason the ordering of purification cost by end use (row H4-b) is not counted as support: it is set by the assumed recoveries and by the added purification and compression steps. The end-use pathways apply the direct-NH~3~ turbine efficiency to hydrogen-rich fuel (an assumption), so a fired or purified cracker in front of a turbine can only add ammonia burn and capital; the ranking of direct use above those pathways (rows H1-a and H1-d) therefore follows from that assumption, and only the size of the gap is a computed result. Where a row is supported by a computed share of an input, such as the ammonia feed share of the LCOH, the row conclusion states this and the conditions under which it holds.

**Uncertainty is often larger than the effect.** The cost differences that H3 rests on are at most a few hundredths of a US dollar per kilogram, while the Monte Carlo range of the LCOH from economic inputs alone spans about 1.6 USD/kg (Sections 26.6 and 27). Where an effect is smaller than the uncertainty of the model that produces it, the matrix does not count it as support in either direction.

**Unverified literature is not evidence.** Essay values whose primary source could not be read (the Singapore plant figures quoted from Halim and co-authors, whose full text could not be accessed, the Ru-K/CaO kinetic values quoted from Sayas et al. (2020), and a capacity scale effect quoted from Deka and co-authors, whose paper was not obtained) are kept as leads and labelled unverified; no AmCraX result uses them as an input, and where a row tests such a claim it does so with AmCraX's own calculation.

## 31.7 Essay statements that are not reproduced

The following essay statements, most of them quoted from the literature, are not reproduced by the AmCraX evidence under the conditions stated in the sections cited. Not reproduced does not always mean contradicted: the matrix row and its verdict are given with each statement, and a statement is contradicted only where its row says so. They are reported because the study was set up to find them.

* **Direct ammonia is about 40 % cheaper than cracking-based power.** On the AmCraX price basis, direct NH~3~ power is 5.1 % cheaper than power from fully cracked, fired-heated gas and 15.0 % cheaper than power from cracked and purified hydrogen, and it is 4.3 % dearer than power from cracked gas heated by turbine exhaust. The direction for fired or purified cracking follows from the assumed equal turbine efficiency; the computed magnitude is several times smaller than 40 % (Section 29; {{ROW_VERDICT:H1-b}}).
* **A Ru cracker needs no supplementary fuel while a Ni cracker does** (Cho et al., 2026). On AmCraX boundaries both designs need supplementary NH~3~ at a PSA recovery of 0.85 (161 and 152 kg/h) and neither needs more than the thermal-loss allowance at 0.756; the PSA recovery, not the catalyst, decides (Section 26.7; {{ROW_VERDICT:H3-e}}).
* **Ru lowers the reconversion cost by 7.0 %** (Cho et al., 2026). AmCraX gives at most 2.6 % in the same direction, and the opposite sign with Cho's own catalyst inventory or PSA recovery (Section 26.7; {{ROW_VERDICT:H3-f}}, because the differences lie inside the cost uncertainty).
* **A low-temperature catalyst can outweigh its higher price.** This is shown only against a nickel cracker forced to about 735 °C. Against a nickel design optimised on its own kinetics the break-even ruthenium price, 75-498 USD/kg against the 542 USD/kg proxy, lies inside the resolution of the cost model, so the model can neither confirm nor reject the statement (Section 26.4). Heat integration reduces the benefit of a low reactor temperature rather than adding to it (Section 26.2; {{ROW_VERDICT:H3-c}} and {{ROW_VERDICT:H3-d}}).
* **The published PSA operating point delivers usable hydrogen.** The Cho et al. (2026) point of 75.6 % recovery at 99.11 mol% H~2~ contains about 8900 ppm N~2~ and fails both the 99.9 % industrial grade and ISO 14687:2019 grade D (International Organization for Standardization [ISO], 2019) (Section 28; {{ROW_VERDICT:H4-c}}).

The membrane-reactor result of Cechetto et al. (2023) could not be tested, because the library has no module area or permeation parameters for that membrane; it remains a literature value.
<!-- data: results/research/enduse/enduse_results.json halim_claim_check.computed (AmCraX price set: full_fired 5.104 %, full_purified 14.954 %, full_exhaust -4.303 %); results/research/catalyst_comparison/catalyst_cho_comparison.json summary (Ni_supp_nh3_kg_h 161.08, Ru 151.98; 0.756: 7.11/6.94; rec_Ru_lower_by_pct 2.562 max); catalyst_comparison.json findings.breakeven_price; results/research/purification/purification_study.json cases.20bar_baseline.configs[PSA_CHO].product_ppm.N2 8900.0, spec_evaluation; results/research/singapore/monte_carlo.json results.grey (p5 2.849, p95 4.432); results/research/validation/purification.json -->
