<!-- cites: cho2026nickel, cechetto2021fpt, sg_cpa2018 -->

# 31 Changes since the 23 November 2026 release

This is version 2.0 of the report (Phase 2). Version 1.0, the release of 23 November 2026 (178 pages), is preserved unchanged in `docs/technical_report/releases/2026-11-23/` and under the repository tag `amcrax-research-expansion-2026-11-23`; the result files it quotes are preserved in `results/research_releases/2026-11-23/`. Sections 1 to 30 keep their structure. Sections 31 to 39 and 43 are new, Section 40 replaces the former Section 31 (evidence matrix), and Sections 41 and 42 replace the former Sections 32 and 33.

## 31.1 What changed and why

Phase 2 put every research output on one techno-economic basis (Section 32), replaced assumed catalyst prices by prices derived from metal content (Section 35), added threshold analyses for the hypotheses whose outcome depends on an unsourced input (Sections 33 to 36), added variance-based sensitivity and Bayesian calibration diagnostics (Section 37), and applied a stricter verdict methodology that was fixed before the analysis (Section 40). The changes below are the ones a reader of version 1.0 needs to know. Several of them go against the preceding essay; they are stated as found.

Table: **Table 31.1.** Findings that changed between version 1.0 and version 2.0. Costs in USD/kg H~2~ unless stated; SGD values use 1.288444 SGD/USD (European Central Bank reference rates of 20 November 2026). *Source: docs/internal/phase2_decisions.md section 4; results/research/reference_scenario/supersession.json; result files named in Sections 32 to 40.*

| Finding | Version 1.0 (release of 23 Nov 2026) | Version 2.0 (Phase 2) |
|---|---|---|
| Baseline LCOH | 3.92 (legacy correlation) and 3.61 (equipment method), two bases | 4.015 (5.174 SGD/kg), one basis |
| Feed share of LCOH | 84 % of 3.61 | 76 % of 4.015 |
| Break-even NH~3~ price against the NE Asia SMR marker (3.06) | 375 USD/t | 320 USD/t (277 to 371 over the sourced CAPEX range) |
| CAPEX | 2.78 MUSD | 7.67 MUSD |
| NPV at 3.06 USD/kg | -10.1 MUSD | -17.5 MUSD |
| Direct NH~3~ power against fired cracking / cracking + PSA | 5 % / 15 % cheaper | 7.6 % / 16.5 % cheaper (equal-efficiency assumption) |
| Exhaust-heated full cracking against direct NH~3~ power | 4 % cheaper | 1.3 % cheaper; equal at 40 vol% H~2~ |
| H4 industrial ranking | raw membrane cheaper than PSA | depends on PSA recovery; parity near 0.80; not robust |
| Low-temperature energy saving (H3-a) | 17 % fired duty (unequal conversion) | about 5 % at equal conversion with heat integration; 163 kW without |
| Heat-integration saving | 0.21 gross | 0.214 gross; +0.067 to +0.095 net of the exchanger cost |
| Catalyst prices | Cho TEA values (Ru 542, Ni 33.4 USD/kg) | derived from metal content: Ru/Al~2~O~3~ 4791, Ru/MgO 3006, 5Ni1Ru 628, 2.5Ni0.5Ru 330, Ni/MgO 37 USD/kg (central) |
| Above-equilibrium Aspen failures | cause "plausible" | quantified (compressibility and fugacity parts); 20 bar passes in the partial-pressure form, 40 bar still fails |
| FEHE duty failures | "property-basis difference" | quantified: dew-point state +8.8 kW and NH~3~ residual enthalpy +12.1 kW; still failing, tolerance unchanged |
| Singapore carbon tax | 45 SGD/tCO~2~e "2026-27" | 45 SGD/tCO~2~e for 2026 and any later year (Carbon Pricing Act 2018; Singapore Statutes Online, 2026); N~2~O GWP 265 for the tax |
| Membrane selectivity | none in the library | 40,541 to 500,000 (ideal, single gas; Cechetto et al., 2021) against a requirement of 12,919 |
| Verdicts | all four INCONCLUSIVE (rule v1) | H1 INCONCLUSIVE, H2 MIXED, H3 PARTIALLY SUPPORTED, H4 PARTIALLY SUPPORTED (rule v2, fixed before analysis); v1 shown alongside |

<!-- data: results/research/reference_scenario/supersession.json rows (208); baseline.json lcoh_USD_per_kg 4.015461, lcoh_SGD_per_kg 5.173697, capex_total_USD 7666560, npv_USD -17455720; capex_audit.json methods_on_amcrax_baseline; carbon_pricing/feed_dominance.json; enduse/turbine_threshold.json; purification/phase2_comparison.json; catalyst_economics/catalyst_economics.json; heat_exchanger/heat_exchanger_study.json; kinetics/equilibrium_consistency.json; heat_exchanger/fehe_duty_diagnosis.json -->

The verdict row is the one that matters most and the one most easily misread. Version 2.0 applies a different rule (methodology v2, `docs/research/verdict_methodology_v2.md`), which judges each row against its own primary claim and then combines rows into components and components into a hypothesis verdict. The rule was written before the Phase 2 analysis and has not been edited since. Version 1.0 required every row of a hypothesis to be SUPPORTED. The v1 verdicts are shown next to the v2 verdicts in Section 40, so a reader can see that the change in label comes from the rule as well as from new evidence. No row verdict was moved to make a hypothesis look better: H1 stays INCONCLUSIVE.

## 31.2 Where the superseded numbers still appear

The core stored results of Sections 1 to 23 (`results/simulations`, `results/sensitivity`, `results/optimisation`, `results/validation`) are not changed by Phase 2. Where those sections quote the legacy LCOH of 3.919 USD/kg or the electricity price of 0.084 USD/kWh, the number is correct for the stored core result and is marked "legacy core result, superseded for research outputs". Sections 26 to 30 report the Phase 1 research studies; where they quote a Phase 1 research number that Phase 2 superseded, the text now gives the unified value or points to the section that does. The full list of 208 changed quantities, with the old value, the new value, the file and the reason, is `results/research/reference_scenario/supersession.json`.

## 31.3 Two findings against the essay

Two Phase 2 findings go against the preceding essay and are repeated wherever H1 and H3 are discussed. First, on the reference basis, power from exhaust-heated full cracking is about 1.3 % cheaper than direct ammonia power (Section 33); direct ammonia is cheaper only against the fired and purified cracking pathways, and only under the equal-efficiency assumption. Second, at ruthenium catalyst prices derived from metal content, the low-temperature catalysts do not pay for themselves at equal conversion (Section 35); the Phase 1 figure of a 17 % fired-duty reduction was mostly an artefact of unequal conversion (Cho et al., 2026, used the published TEA price of 542 USD/kg for Ru-K/CaO, which lies below the ruthenium metal value).
