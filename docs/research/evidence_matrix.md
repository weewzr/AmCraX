# Research evidence matrix (H1-H4), methodology version 2

Generated from `results/research/evidence_matrix.json` by `scripts/research/build_evidence_matrix.py` (2026-11-24T05:28:59Z). Do not edit by hand; re-run the script.

Verdict rule: `docs/research/verdict_methodology_v2.md` (version 2, fixed before the Phase 2 analyses). Row verdicts: SUPPORTED, CONTRADICTED, INCONCLUSIVE. Component and hypothesis verdicts add MIXED and PARTIALLY SUPPORTED. Every row verdict is derived in code from the result files by the rule printed with the row. The version 1 verdict of the 23 November 2026 release is shown beside every verdict.

Component verdict from its primary rows (methodology v2): SUPPORTED if every primary row is SUPPORTED; CONTRADICTED if no primary row is SUPPORTED and at least half are CONTRADICTED; MIXED if at least one is SUPPORTED and at least one CONTRADICTED; PARTIALLY SUPPORTED if at least one is SUPPORTED, none is CONTRADICTED and at least one is INCONCLUSIVE; otherwise INCONCLUSIVE. Secondary rows are reported but do not vote.

Hypothesis verdict from its components (methodology v2; the cross-claim H2-X counts as a component): SUPPORTED if every component is SUPPORTED; CONTRADICTED if no component is SUPPORTED or PARTIALLY SUPPORTED and at least half are CONTRADICTED; MIXED if at least one component is SUPPORTED or PARTIALLY SUPPORTED and at least one is CONTRADICTED; PARTIALLY SUPPORTED if at least one component is SUPPORTED or PARTIALLY SUPPORTED, none is CONTRADICTED and not all are SUPPORTED; otherwise INCONCLUSIVE.

Evidence kinds are kept apart: numerical verification, Python against Aspen comparison, comparison with published literature, and independent experimental validation. AmCraX has no independent experimental validation. No row lists it as an evidence kind.

Currency: calculations in USD; SGD values use 1.288444 SGD/USD (2026-11-20).

## Verdict table

| Hypothesis | Component or row | Role | Verdict (v2) | Verdict (v1) | Statement |
|---|---|---|---|---|---|
| **H1** | | | **INCONCLUSIVE** | INCONCLUSIVE | End-use suitability: cracking is most justified when the end use needs molecular hydrogen, not where ammonia can be used directly. |
| | **H1-P** | component | **INCONCLUSIVE** | | Direct use is preferable where ammonia can be burned directly |
| | H1-a | primary | INCONCLUSIVE | INCONCLUSIVE | Where ammonia can be burned directly (power), direct NH3 combustion is cheaper than power from a standalone (fired) cracker or from cracked and purified hydrogen. |
| | H1-c | primary | INCONCLUSIVE | INCONCLUSIVE | Cracking is not justified where ammonia can be used directly: partial or full cracking in front of a turbine does not pay. |
| | H1-b | secondary | CONTRADICTED | CONTRADICTED | Direct NH3 combustion is about 40 % cheaper than cracking-based power (essay, citing Halim et al. 2025). |
| | **H1-Q** | component | **INCONCLUSIVE** | | Cracking is justified where molecular hydrogen is the product |
| | H1-d | primary | INCONCLUSIVE | INCONCLUSIVE | Cracking is most justified when the end use needs molecular hydrogen: the conversion loss is small when H2 is the product and larger when H2 is only an intermediate fuel. |
| **H2** | | | **MIXED** | INCONCLUSIVE | Feedstock: affordable, low-carbon ammonia is essential to economic and environmental competitiveness. |
| | **H2-E** | component | **SUPPORTED** | | Affordable ammonia is essential to economic competitiveness |
| | H2-a | primary | SUPPORTED | SUPPORTED | Ammonia feed cost dominates the cost of cracked hydrogen, so affordable ammonia is essential to economic competitiveness. |
| | H2-b | primary | SUPPORTED | SUPPORTED | Only affordable ammonia keeps cracked hydrogen competitive with the hydrogen benchmarks relevant to Singapore. |
| | **H2-C** | component | **SUPPORTED** | | Low-carbon ammonia is essential to environmental competitiveness |
| | H2-c | primary | SUPPORTED | SUPPORTED | Low-carbon ammonia is essential for environmental competitiveness of ammonia-based power in Singapore. |
| | H2-d | primary | SUPPORTED | SUPPORTED | Low-carbon ammonia is essential for cracked hydrogen to have lower carbon intensity than fossil hydrogen. |
| | **H2-X** | component | **CONTRADICTED** | | Cross-claim: low carbon intensity is rewarded economically |
| | H2-e | primary | CONTRADICTED | CONTRADICTED | Low-carbon ammonia is essential to economic competitiveness (that is, low carbon intensity is rewarded in the Singapore cost of hydrogen). |
| **H3** | | | **PARTIALLY SUPPORTED** | INCONCLUSIVE | Catalyst and heat integration: low-temperature, high-activity catalysts with effective heat integration reduce energy use and can outweigh higher catalyst cost. |
| | **H3-T** | component | **PARTIALLY SUPPORTED** | | Lower-temperature operation reduces energy use |
| | H3-a | primary | SUPPORTED | SUPPORTED | Energy half of the catalyst claim: at equal conversion, running the cracker at the lower temperature that a more active catalyst allows reduces energy use. |
| | H3-b | primary | INCONCLUSIVE | INCONCLUSIVE | Low-temperature, high-activity catalysts allow the cracker to run at a lower temperature for the same duty. |
| | **H3-H** | component | **SUPPORTED** | | Heat integration reduces energy use |
| | H3-d | primary | SUPPORTED | SUPPORTED | Effective heat integration reduces energy use (and cost) of the cracker, and matters more than the catalyst's temperature. |
| | **H3-K** | component | **INCONCLUSIVE** | | The savings can outweigh a higher catalyst cost |
| | H3-c | primary | INCONCLUSIVE | INCONCLUSIVE | The energy saved by a low-temperature, high-activity catalyst can outweigh its higher catalyst cost. |
| | H3-e | secondary | INCONCLUSIVE | INCONCLUSIVE | Cho et al. (2026): the Ru process at 567 degC needs no supplementary fuel while the Ni process at 736 degC burns supplementary NH3. |
| | H3-f | secondary | INCONCLUSIVE | INCONCLUSIVE | Cho et al. (2026): the Ru process has a 7.0 % lower relative economic cost (REC) than the Ni process. |
| **H4** | | | **PARTIALLY SUPPORTED** | INCONCLUSIVE | Purification: must balance purity requirements against recovery losses, energy and equipment cost. |
| | **H4-B** | component | **PARTIALLY SUPPORTED** | | Purity must be balanced against recovery, energy and cost |
| | H4-a | primary | INCONCLUSIVE | INCONCLUSIVE | Higher hydrogen purity from PSA costs hydrogen recovery (purity-recovery trade-off). |
| | H4-b | primary | INCONCLUSIVE | INCONCLUSIVE | Purification must be matched to the end use: stricter purity requirements raise the cost per kg of usable hydrogen. |
| | H4-e | primary | SUPPORTED | SUPPORTED | Recovery losses trade against energy: hydrogen not recovered by purification returns as fuel for the cracker, up to the furnace demand. |
| | H4-c | secondary | CONTRADICTED | CONTRADICTED | A published PSA operating point (Cho: 75.6 % recovery at 99.11 % H2) is sufficient for hydrogen end uses with ISO 14687 grades. |
| | H4-d | secondary | INCONCLUSIVE | INCONCLUSIVE | A Pd-Ag membrane balances purity, recovery and cost better than PSA for fuel-cell hydrogen. |

## H1: INCONCLUSIVE

**Primary hypothesis.** End-use suitability: cracking is most justified when the end use needs molecular hydrogen, not where ammonia can be used directly.

**Verdict.** INCONCLUSIVE (methodology v2). Version 1 verdict of the 23 November release: INCONCLUSIVE. Version 1 rule applied to the current rows: INCONCLUSIVE.

**Strongest defensible statement.** Under the modelled operating conditions, direct ammonia combustion produces electricity at a lower cost than the standalone cracking pathways, with a calculated cost advantage of approximately 8 to 17 % (5 to 15 % on the earlier cost basis). This comparison assumes that the hydrogen-rich turbine operates at the same 49.64 % efficiency as the direct-ammonia turbine. The actual economic advantage depends on fuel-specific turbine performance. The advantage over cracking + PSA survives the threshold test on every basis; the advantage over fired cracking cannot be tested because no turbine efficiency for its fuel is sourced.

**Findings against the essay.**

- Exhaust-heated full cracking (255.6 USD/MWh) is 1.3 % cheaper than direct use (258.9) on the reference basis.
- The essay's 40 % cost advantage of direct use is not reproduced (at most 16.6 %).

**Components.**

| Component | Verdict | Primary rows | Secondary rows | Envelope |
|---|---|---|---|---|
| H1-P Direct use is preferable where ammonia can be burned directly | INCONCLUSIVE | H1-a, H1-c | H1-b | none (no primary row is SUPPORTED) |
| H1-Q Cracking is justified where molecular hydrogen is the product | INCONCLUSIVE | H1-d | - | none (no primary row is SUPPORTED) |

**Verdict conditions.** Hypothesis verdict from its components (methodology v2; the cross-claim H2-X counts as a component): SUPPORTED if every component is SUPPORTED; CONTRADICTED if no component is SUPPORTED or PARTIALLY SUPPORTED and at least half are CONTRADICTED; MIXED if at least one component is SUPPORTED or PARTIALLY SUPPORTED and at least one is CONTRADICTED; PARTIALLY SUPPORTED if at least one component is SUPPORTED or PARTIALLY SUPPORTED, none is CONTRADICTED and not all are SUPPORTED; otherwise INCONCLUSIVE. Components: H1-P INCONCLUSIVE; H1-Q INCONCLUSIVE. Component verdict from its primary rows (methodology v2): SUPPORTED if every primary row is SUPPORTED; CONTRADICTED if no primary row is SUPPORTED and at least half are CONTRADICTED; MIXED if at least one is SUPPORTED and at least one CONTRADICTED; PARTIALLY SUPPORTED if at least one is SUPPORTED, none is CONTRADICTED and at least one is INCONCLUSIVE; otherwise INCONCLUSIVE. Secondary rows are reported but do not vote. Row outcomes: CONTRADICTED: H1-b; INCONCLUSIVE: H1-a, H1-c, H1-d.

### H1-a: INCONCLUSIVE

Role: primary (H1-P). Version 1 verdict: INCONCLUSIVE.

**Sub-claim.** Where ammonia can be burned directly (power), direct NH3 combustion is cheaper than power from a standalone (fired) cracker or from cracked and purified hydrogen.

**Numerical conclusions.**

- Direct NH3 258.9 USD/MWh against fired cracking 280.1 (7.6 % cheaper) and cracking + PSA 310.2 (16.5 % cheaper), at the equal-efficiency assumption 49.64 %.
- Fired cracking needs +5.16 pp (range 3.29 to 8.79 over 11 bases); no turbine efficiency on fired-cracker H2/N2 fuel is sourced.
- Cracking + PSA needs +12.55 pp (range 9.68 to 18.10), above the only sourced gain (6.08 to 7.30 pp, NETL pure H2, an upper bound) on every basis.

**Conclusion.** Under the modelled operating conditions direct NH3 combustion is cheaper than both standalone cracking pathways (7.6 % and 16.5 %), at an assumed equal turbine efficiency of 49.64 %. The cracking + PSA half survives the threshold test on every basis; the fired half cannot be tested because no efficiency is sourced, so the row is not SUPPORTED.

**Rule and outcome.** Threshold rule (methodology v2): the direction rests on the assumed H2-rich-fuel turbine efficiency, so for each half (fired cracking, cracking + PSA) the efficiency gain at which cracking equals direct use is computed on every cost basis and compared with sourced gains. SUPPORTED if sourced gains lie below the threshold on every basis for both halves; CONTRADICTED if above on every basis for both; otherwise INCONCLUSIVE. Here: fired half 'no_source', cracking + PSA half 'below'.

**Envelope.** AmCraX boundary, grey 450 USD/t (300-1000 checked), 5000-8000 h, capex x0.5-x2 and Ahmad correlation. The cracking + PSA half holds on all 11 bases; the fired half has no sourced turbine efficiency.

**Threshold.** gain in combined-cycle efficiency on the H2-rich fuel needed for cracking to equal direct use (percentage points): 5.165, 6.274, 5.570, 3.346, 8.786, 6.630, 3.954, 3.290, 6.891, 5.293, 5.713, 12.551, 12.551, 11.702, 9.759, 18.103, 14.791, 10.695, 9.677, 15.193, 12.749, 11.869. Sourced: NETL pure-H2 minus NH3 combined-cycle efficiency, as a ratio on the AmCraX turbine 6.080, NETL pure-H2 minus NH3 combined-cycle efficiency, absolute (upper bound) 7.300. Comparison: {"fired": "no_source", "purified": "below"}.

**Assumptions.**

- H2-rich-fuel turbine at the direct-NH3 efficiency 49.64 % (fired and purified rows only).
- eta_h2_fuel = 49.64 % (copy of direct) for fired and purified; fired cracker heat from NH3 at 100 % transfer efficiency; Cho-itemised cracker capex extrapolated about 30-fold; Ahmad plant capital scaled ^0.67; 8000 h (not sourced).

**Uncertainty.** fired threshold over bases 3.29 to 8.79 pp; purified 9.68 to 18.10 pp

**Validation status.** Energy balance closure of every power pathway; Ahmad Case 2a LCOE reproduced; Aspen LHV efficiency reproduced (results/research/validation/enduse.json). Validation status of the underlying models: results/research/validation/enduse.json: 69 pass, 0 fail, 6 informational.

**Evidence kinds.** numerical verification, literature comparison.

**Key uncertainty (what would change the verdict).** Outside this envelope the verdict may change: AmCraX boundary, grey 450 USD/t (300-1000 checked), 5000-8000 h, capex x0.5-x2 and Ahmad correlation. The cracking + PSA half holds on all 11 bases; the fired half has no sourced turbine efficiency.

**Uncertainty range.** fired threshold over bases 3.29 to 8.79 pp; purified 9.68 to 18.10 pp

- Singapore scenario: Jurong Island representative power plant burning imported NH3; common reference NH3 price from the Singapore price set (grey), operating hours, Singapore electricity and carbon tax inputs as in price_set of enduse_results.json
- Aspen model: Stored Aspen Plus V15 baseline (results/simulations/baseline.json): cracker reactor and pre-heater duty, PSA heat deficit used as cracker heat; no Aspen combustion model.
- Python model: amcrax.enduse.pathways power pathways (energy balance, Ahmad-scaled plant capital, amcrax.economics).
- Case ids: baseline (stored Aspen), direct, full_fired, full_purified
- Validation: Energy balance closure of every power pathway; Ahmad Case 2a LCOE reproduced; Aspen LHV efficiency reproduced (results/research/validation/enduse.json). Validation status of the underlying models: results/research/validation/enduse.json: 69 pass, 0 fail, 6 informational.
- Input assumptions: Fired variants apply the direct-NH3 turbine efficiency to H2-rich fuel (assumption).; PSA recovery of the stored baseline (assumption) for the purified route.; Plant capital outside the cracker: Ahmad Case 2a scaled with plant power.; No NOx abatement cost; no combustion simulated.
- Literature: `ahmad2025gtcc` (Ahmad et al. 2025: NH3 and cracked-NH3 GTCC efficiencies and Case 2a cost basis); `halim2025ammoniapower` (Halim et al. 2025 (abstract only): direct use preferred to cracking for power)
- Limitations: Efficiencies of intermediate blends are a linear interpolation of Ahmad's two end points (assumption).; Fired and purified variants apply the direct-NH3 turbine efficiency to H2-rich fuel (assumption); the threshold at which each conclusion reverses is in turbine_threshold.json (scripts/research/enduse_threshold.py). Exhaust-heated variants use Ahmad's system efficiency instead (implied 47.8 % on cracked-gas LHV).; Plant capital outside the cracker is Ahmad's Case 2a scaled with power^0.67; no NOx abatement cost.; Fuel-cell candidate cost excludes NH3 polishing and other ISO 14687 contaminant control.; Halim et al. (2025) full text was not accessible; only the abstract and bibliographic data were checked.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| LCOE direct NH3 CCGT | 258.9 | USD/MWh | python | `results/research/enduse/enduse_results.json` | `power_pathways/[id=direct]/cost_USD_per_MWh_at_450` |
| LCOE full cracking, fired cracker | 280.1 | USD/MWh | python | `results/research/enduse/enduse_results.json` | `power_pathways/[id=full_fired]/cost_USD_per_MWh_at_450` |
| LCOE full cracking + PSA H2 | 310.2 | USD/MWh | python | `results/research/enduse/enduse_results.json` | `power_pathways/[id=full_purified]/cost_USD_per_MWh_at_450` |
| NH3 LHV to electricity, direct | 0.4964 | fraction | literature | `results/research/enduse/enduse_results.json` | `power_pathways/[id=direct]/efficiency_NH3_LHV_to_electricity` |
| NH3 LHV to electricity, cracked + PSA H2 | 0.4356 | fraction | python | `results/research/enduse/enduse_results.json` | `power_pathways/[id=full_purified]/efficiency_NH3_LHV_to_electricity` |
| direct cheaper than fired cracking, 1 - direct/cracking | 7.554 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=AmCraX price set (450 USD~1t, 8000 h);cracking_pathway=full_fired]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| direct cheaper than cracking + PSA, 1 - direct/cracking | 16.523 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=AmCraX price set (450 USD~1t, 8000 h);cracking_pathway=full_purified]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| same, Ahmad basis | 16.634 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=Ahmad basis (480 USD~1t, 7200 h);cracking_pathway=full_purified]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| same, renewable NH3 at today's price | 14.646 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=renewable NH3 today (1000 USD~1t);cracking_pathway=full_purified]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| turbine efficiency on H2-rich fuel (copy of direct case) | 0.4964 | fraction | assumption | `results/research/enduse/assumptions.json` | `[name=eta_gt_gas]/value` |
| LCOE direct NH3 (unified basis) | 258.9 | USD/MWh | python | `results/research/enduse/turbine_threshold.json` | `row_evidence/H1-a/numbers/LCOE_direct` |
| LCOE fired cracking (unified basis) | 280.1 | USD/MWh | python | `results/research/enduse/turbine_threshold.json` | `row_evidence/H1-a/numbers/LCOE_full_fired` |
| LCOE cracking + PSA (unified basis) | 310.2 | USD/MWh | python | `results/research/enduse/turbine_threshold.json` | `row_evidence/H1-a/numbers/LCOE_full_purified` |
| direct cheaper than fired cracking, 1 - d/c | 7.554 | % | python | `results/research/enduse/turbine_threshold.json` | `row_evidence/H1-a/numbers/direct_cheaper_pct_fired` |
| direct cheaper than cracking + PSA, 1 - d/c | 16.523 | % | python | `results/research/enduse/turbine_threshold.json` | `row_evidence/H1-a/numbers/direct_cheaper_pct_purified` |
| turbine efficiency assumed on H2-rich fuel (copy of direct NH3) | 0.4964 | fraction | assumption | `results/research/enduse/assumptions.json` | `[name=eta_gt_gas]/value` |
| threshold, fired cracking (reference basis) | 5.165 | pp | python | `results/research/enduse/turbine_threshold.json` | `thresholds/full_fired/threshold_delta_pp_reference` |
| threshold, cracking + PSA (reference basis) | 12.551 | pp | python | `results/research/enduse/turbine_threshold.json` | `thresholds/full_purified/threshold_delta_pp_reference` |

Figures: `results/figures/research/enduse_power_cost_vs_ci.png`, `results/figures/research/enduse_power_cost_vs_price.png`, `results/figures/research/enduse_power_efficiency.png`
Data: `results/research/enduse/assumptions.json`, `results/research/enduse/enduse_results.json`, `results/research/enduse/pathway_table_power.csv`, `results/research/enduse/price_sweep.csv`, `results/research/enduse/turbine_threshold.json`

### H1-c: INCONCLUSIVE

Role: primary (H1-P). Version 1 verdict: INCONCLUSIVE.

**Sub-claim.** Cracking is not justified where ammonia can be used directly: partial or full cracking in front of a turbine does not pay.

**Numerical conclusions.**

- Exhaust-heated full cracking 255.6 USD/MWh against direct 258.9: 1.3 % cheaper than direct on the reference basis (against the essay).
- Partial 40 vol% exhaust-heated cracking 258.93 USD/MWh, equal to direct within 0.002 USD/MWh.
- Threshold +4.04 pp on the reference basis against sourced 4.9 to 5.5 pp; thresholds range 1.97 to 11.70 pp over bases and blends.

**Conclusion.** On the reference basis exhaust-heated cracking is slightly cheaper than direct use, which goes against the essay; across CAPEX, price and operating-hour bases the threshold moves across the sourced range, so the row is INCONCLUSIVE.

**Rule and outcome.** Threshold rule (methodology v2): the row says cracking in front of the turbine does not pay. The exhaust-heat system-efficiency gain at which each exhaust-heated pathway equals direct use is computed on every basis and compared with the supported sourced gain. SUPPORTED if sourced gains lie below every threshold (direct cheaper everywhere); CONTRADICTED if above every threshold (cracking cheaper everywhere); otherwise INCONCLUSIVE. Here: 'straddle' over 7 pathways and all bases; reference basis, full cracking: 'above'.

**Envelope.** small or mid-size machines (Ahmad 43 MW class, PR 8); no F/H-class source The sign flips with the cost basis: cracker CAPEX x1.22 removes the cracking advantage.

**Threshold.** exhaust-heat system-efficiency gain needed for cracking to equal direct use (pp, full-cracking equivalent): 4.040, 5.265, 4.448, 2.031, 8.039, 5.656, 2.703, 1.970, 5.945, 4.182, 4.605, 5.861, 7.647, 7.144, 2.939, 11.699, 8.227, 3.916, 2.852, 8.655, 6.069, 7.398, 5.318, 6.937, 6.312, 2.668, 10.610, 7.462, 3.554, 2.589, 7.849, 5.507, 6.535, 4.933, 6.434, 5.735, 2.476, 9.837, 6.919, 3.298, 2.402, 7.277, 5.108, 5.938, 4.628, 6.034, 5.287, 2.323, 9.222, 6.487, 3.094, 2.254, 6.822, 4.791, 5.474, 4.367, 5.694, 4.911, 2.194, 8.699, 6.119, 2.921, 2.128, 6.434, 4.521, 5.084, 4.134, 5.389, 4.580, 2.078, 8.229, 5.790, 2.766, 2.016, 6.086, 4.280, 4.742. Sourced: supported exhaust-heated system gain, low 4.900, supported exhaust-heated system gain, high 5.500. Comparison: {"all_bases": "straddle", "reference_full_exhaust": "above"}.

**Assumptions.**

- Ahmad system end points (54 % 'about'), linear interpolation for partial cracking, reference cracker capex, 8000 h

**Uncertainty.** full-exhaust threshold over bases 1.97 to 8.04 pp

**Validation status.** Ahmad bypass table reproduced by stoichiometry; N and H atom balance and blend round trip (enduse.json). Validation status of the underlying models: results/research/validation/enduse.json: 69 pass, 0 fail, 6 informational.

**Evidence kinds.** numerical verification, literature comparison.

**Key uncertainty (what would change the verdict).** Outside this envelope the verdict may change: small or mid-size machines (Ahmad 43 MW class, PR 8); no F/H-class source The sign flips with the cost basis: cracker CAPEX x1.22 removes the cracking advantage.

**Uncertainty range.** full-exhaust threshold over bases 1.97 to 8.04 pp

- Singapore scenario: Jurong Island representative power plant burning imported NH3; common reference NH3 price from the Singapore price set (grey), operating hours, Singapore electricity and carbon tax inputs as in price_set of enduse_results.json
- Aspen model: Partial-cracking heat is the stored Aspen baseline reactor + pre-heater duty scaled with the cracked share; no Aspen combustion or exhaust-heated reactor model.
- Python model: amcrax.enduse.pathways partial-cracking scan and break-even efficiency gain.
- Case ids: direct, partial_exhaust_40, partial_fired_40, full_exhaust
- Validation: Ahmad bypass table reproduced by stoichiometry; N and H atom balance and blend round trip (enduse.json). Validation status of the underlying models: results/research/validation/enduse.json: 69 pass, 0 fail, 6 informational.
- Input assumptions: Exhaust-heated cracker efficiency taken from Ahmad's two end points (literature).; Efficiency of intermediate blends linearly interpolated between Ahmad's end points (assumption).; Fired variants: direct-NH3 turbine efficiency (assumption).
- Literature: `ahmad2025gtcc` (Ahmad et al. 2025: NH3 and cracked-NH3 GTCC efficiencies and Case 2a cost basis); `halim2025ammoniapower` (Halim et al. 2025 (abstract only): direct use preferred to cracking for power)
- Limitations: No combustion simulation; NOx not quantified for blends and cracked fuels.; Turbine H2 tolerance ranges are flags only (Ahmad p. 2; brief value unverified).

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| LCOE full cracking, exhaust-heated, unpurified | 255.6 | USD/MWh | python | `results/research/enduse/enduse_results.json` | `power_pathways/[id=full_exhaust]/cost_USD_per_MWh_at_450` |
| LCOE partial cracking 40 vol% H2, exhaust-heated | 258.9 | USD/MWh | python | `results/research/enduse/enduse_results.json` | `power_pathways/[id=partial_exhaust_40]/cost_USD_per_MWh_at_450` |
| LCOE partial cracking 40 vol% H2, fired | 268.6 | USD/MWh | python | `results/research/enduse/enduse_results.json` | `power_pathways/[id=partial_fired_40]/cost_USD_per_MWh_at_450` |
| LCOE direct NH3 | 258.9 | USD/MWh | python | `results/research/enduse/enduse_results.json` | `power_pathways/[id=direct]/cost_USD_per_MWh_at_450` |
| exhaust-heated efficiency (literature end point) | 0.5458 | fraction | literature | `results/research/enduse/enduse_results.json` | `power_pathways/[id=full_exhaust]/efficiency_NH3_LHV_to_electricity` |
| share of Ahmad's efficiency gain needed for 40 vol% partial cracking to match direct, 450 USD/t | 1.000 | fraction | python | `results/research/enduse/enduse_results.json` | `partial_cracking/breakeven_efficiency_gain/[NH3_price_USD_t=450]/gain_scale_where_partial_40vol_equals_direct` |
| NH3 price above which exhaust-heated full cracking beats direct | 355.1 | USD/t | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/crossover_prices/full_exhaust_vs_direct_NH3_price_USD_t` |
| H2 fraction of the partial-cracking case | 0.4 | vol fraction | assumption | `results/research/enduse/enduse_results.json` | `power_pathways/[id=partial_exhaust_40]/H2_vol_fraction_in_fuel` |
| LCOE exhaust-heated full cracking | 255.6 | USD/MWh | python | `results/research/enduse/turbine_threshold.json` | `row_evidence/H1-c/numbers/LCOE_full_exhaust` |
| LCOE exhaust-heated partial cracking, 40 vol% H2 | 258.9 | USD/MWh | python | `results/research/enduse/turbine_threshold.json` | `row_evidence/H1-c/numbers/LCOE_partial_exhaust_40` |
| LCOE direct NH3 | 258.9 | USD/MWh | python | `results/research/enduse/turbine_threshold.json` | `row_evidence/H1-c/numbers/LCOE_direct` |
| threshold system gain, exhaust-heated full cracking (reference basis) | 4.040 | pp | python | `results/research/enduse/turbine_threshold.json` | `row_evidence/H1-c/numbers/threshold_delta_system_pp_full_exhaust` |
| cracker CAPEX factor at which exhaust-heated full cracking equals direct | 1.222 | - | python | `results/research/enduse/turbine_threshold.json` | `row_evidence/H1-c/numbers/capex_factor_where_full_exhaust_equals_direct` |

Figures: `results/figures/research/enduse_partial_cracking_cost.png`
Data: `results/research/enduse/enduse_results.json`, `results/research/enduse/partial_cracking_scan.csv`, `results/research/enduse/turbine_threshold.json`

### H1-d: INCONCLUSIVE

Role: primary (H1-Q). Version 1 verdict: INCONCLUSIVE.

**Sub-claim.** Cracking is most justified when the end use needs molecular hydrogen: the conversion loss is small when H2 is the product and larger when H2 is only an intermediate fuel.

**Numerical conclusions.**

- H2 as product keeps 87.7 % of the NH3 LHV (Aspen).
- Electricity per kg NH3: direct 2.565; cracking + PSA 2.251 at the efficiency copy, 2.526 to 2.582 at the NETL gains (straddles direct).
- Cracked H2 costs 4.015 USD/kg (5.174 SGD/kg), above the 3.06 USD/kg NE Asia SMR marker.

**Conclusion.** The conversion loss for power depends on the H2 turbine efficiency: at sourced gains cracking + PSA gives about the same electricity as direct combustion, so the energy half is unresolved; cracked H2 is also dearer than the benchmark it was compared with.

**Rule and outcome.** Energy rule (methodology v2): the 'larger loss when H2 is an intermediate fuel' half is tested at sourced H2-turbine efficiencies, not at the assumed copy. SUPPORTED if cracking + PSA gives less electricity per kg NH3 than direct combustion at every sourced efficiency; CONTRADICTED if more at every sourced efficiency; otherwise INCONCLUSIVE. Here the sourced range gives 'straddle' relative to direct.

**Envelope.** Jurong Island cracker, plant-gate 19.5 bar H2

**Threshold.** electricity per kg NH3 of cracking + PSA at sourced turbine gains, against direct combustion: 2.565. Sourced: electricity per kg NH3, cracking + PSA at NETL gain as a ratio 2.526, electricity per kg NH3, cracking + PSA at NETL gain absolute 2.582. Comparison: "straddle".

**Assumptions.**

- stored Aspen PSA split; reference capex; benchmarks of mixed basis and grade

**Uncertainty.** benchmarks 3.0-10 USD/kg straddle the computed LCOH range 4.0-8.1

**Validation status.** Aspen LHV efficiency matched within tolerance; stored LCOH reproduced; purification mass closure (enduse.json, purification.json). Validation status of the underlying models: results/research/validation/enduse.json: 69 pass, 0 fail, 6 informational; results/research/validation/purification.json: 10 pass, 0 fail, 7 informational.

**Evidence kinds.** python vs aspen, numerical verification, literature comparison.

**Key uncertainty (what would change the verdict).** Outside this envelope the verdict may change: Jurong Island cracker, plant-gate 19.5 bar H2

**Uncertainty range.** benchmarks 3.0-10 USD/kg straddle the computed LCOH range 4.0-8.1

- Singapore scenario: Jurong Island cracker supplying industrial or fuel-cell hydrogen from imported grey NH3 (Singapore price set).
- Aspen model: Stored Aspen Plus V15 baseline flowsheet (RGibbs cracker, FEHE, PSA split block) for the LHV efficiency.
- Python model: amcrax.enduse hydrogen pathways with amcrax.economics; purification workstream PSA_D_MB for Grade D.
- Case ids: baseline (stored Aspen), scn_fuel_cell_grade (stored Aspen), PSA_D_MB
- Validation: Aspen LHV efficiency matched within tolerance; stored LCOH reproduced; purification mass closure (enduse.json, purification.json). Validation status of the underlying models: results/research/validation/enduse.json: 69 pass, 0 fail, 6 informational; results/research/validation/purification.json: 10 pass, 0 fail, 7 informational.
- Input assumptions: PSA purity and recovery of the stored Aspen baseline are set by an assumed split (they support no purity claim).; Grade D cost is a lower bound: NH3 polishing and contaminants other than NH3, N2 and H2O not evaluated.
- Literature: `iso14687_2019` (ISO 14687:2019 grade limits); `ahmad2025gtcc` (turbine efficiencies)
- Limitations: No route other than cracking is evaluated for producing H2 from NH3; the comparison is between end uses, not between H2 sources (see H2 for SMR comparators).

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| NH3 LHV to H2 LHV, cracker + PSA | 0.8774 | fraction | aspen | `results/research/enduse/enduse_results.json` | `hydrogen_pathways/[id=h2_industrial]/efficiency_NH3_LHV_to_H2` |
| cost industrial H2 (99.9 %), stored Aspen baseline | 4.015 | USD/kg H2 | python | `results/research/enduse/enduse_results.json` | `hydrogen_pathways/[id=h2_industrial]/cost_USD_per_kg_at_grey_450` |
| cost Grade D candidate, PSA_D_MB at 350 bar (lower bound) | 4.463 | USD/kg H2 | python | `results/research/enduse/enduse_results.json` | `hydrogen_pathways/[id=h2_fuelcell_gradeD_purif_study]/cost_USD_per_kg_at_grey_450` |
| electricity per kg NH3, direct combustion | 2.565 | kWh/kg NH3 | python | `results/research/enduse/enduse_results.json` | `detour/kWh_electricity_per_kg_NH3_direct` |
| electricity per kg NH3, cracked + purified H2 | 2.251 | kWh/kg NH3 | python | `results/research/enduse/enduse_results.json` | `detour/kWh_electricity_per_kg_NH3_cracked_purified` |
| turbine efficiency on H2-rich fuel (copy of direct case) | 0.4964 | fraction | assumption | `results/research/enduse/assumptions.json` | `[name=eta_gt_gas]/value` |
| NH3 LHV to H2 LHV, cracker + PSA (Aspen) | 0.8772 | fraction | aspen | `results/research/enduse/turbine_threshold.json` | `row_evidence/H1-d/numbers/eta_H2_product` |
| LCOH grey NH3 450 USD/t | 4.015 | USD/kg H2 | python | `results/research/enduse/turbine_threshold.json` | `row_evidence/H1-d/numbers/LCOH_grey_USD` |
| LCOH grey NH3 450 USD/t | 5.174 | SGD/kg H2 | python | `results/research/enduse/turbine_threshold.json` | `row_evidence/H1-d/numbers/LCOH_grey_SGD` |
| NE Asia SMR production-cost marker | 3.060 | USD/kg H2 | literature | `results/research/enduse/turbine_threshold.json` | `row_evidence/H1-d/numbers/benchmarks/ne_asia_smr_production_cost` |
| electricity per kg NH3, direct | 2.565 | kWh/kg NH3 | python | `results/research/enduse/turbine_threshold.json` | `row_evidence/H1-d/numbers/kWh_per_kg_NH3/direct` |
| electricity per kg NH3, cracking + PSA at the efficiency copy | 2.251 | kWh/kg NH3 | python | `results/research/enduse/turbine_threshold.json` | `row_evidence/H1-d/numbers/kWh_per_kg_NH3/cracked_purified_at_eta_copy` |

Figures: `results/figures/research/enduse_hydrogen_cost_ci.png`, `results/figures/research/enduse_power_efficiency.png`
Data: `results/research/enduse/assumptions.json`, `results/research/enduse/enduse_results.json`, `results/research/enduse/pathway_table_hydrogen.csv`, `results/research/enduse/turbine_threshold.json`

### H1-b: CONTRADICTED

Role: secondary (H1-P). Version 1 verdict: CONTRADICTED.

**Sub-claim.** Direct NH3 combustion is about 40 % cheaper than cracking-based power (essay, citing Halim et al. 2025).

**Numerical conclusions.**

- Largest computed gap 16.6 % (smallest -5.0 %) against the quoted 40 %; 27.3 % at most in any sensitivity.
- The quoted figure would need a cracker CAPEX x6.3 (cracking + PSA) or x11.1 (fired).

**Conclusion.** The 40 % figure is not reproduced on AmCraX boundaries (at most 16.6 %). Halim et al. full text was not accessible.

**Rule and outcome.** Reproduction rule (unchanged from version 1): CONTRADICTED if the largest computed gap on any stored basis is below half the quoted figure; otherwise INCONCLUSIVE. Secondary row: does not vote.

**Envelope.** AmCraX boundaries and the three stored price and hour bases; does not show that Halim et al.'s own calculation is wrong.

**Threshold.** half the quoted figure: 40. Sourced: none sourced. Comparison: "largest computed gap below half".

**Assumptions.**

- As H1-a; three stored price and operating-hour bases.

**Uncertainty.** Halim's inputs unknown (full text not accessible)

**Validation status.** Claim check against computed 1 - direct/cracking on three bases (validation item EU-halim-claim, informational because Halim's inputs were not accessed). Validation status of the underlying models: results/research/validation/enduse.json: 69 pass, 0 fail, 6 informational.

**Evidence kinds.** numerical verification, literature comparison.

**Key uncertainty (what would change the verdict).** Outside this envelope the verdict may change: AmCraX boundaries and the three stored price and hour bases; does not show that Halim et al.'s own calculation is wrong.

**Uncertainty range.** Halim's inputs unknown (full text not accessible)

- Singapore scenario: Jurong Island representative power plant burning imported NH3; common reference NH3 price from the Singapore price set (grey), operating hours, Singapore electricity and carbon tax inputs as in price_set of enduse_results.json
- Aspen model: No Aspen combustion model; cracker duties from the stored Aspen baseline.
- Python model: amcrax.enduse.pathways (halim_claim_check).
- Case ids: direct, full_exhaust, full_fired, full_purified
- Validation: Claim check against computed 1 - direct/cracking on three bases (validation item EU-halim-claim, informational because Halim's inputs were not accessed). Validation status of the underlying models: results/research/validation/enduse.json: 69 pass, 0 fail, 6 informational.
- Input assumptions: Same as H1-a; three price and operating-hour bases (AmCraX, Ahmad, renewable NH3 today).
- Literature: `ahmad2025gtcc` (Ahmad et al. 2025: NH3 and cracked-NH3 GTCC efficiencies and Case 2a cost basis); `halim2025ammoniapower` (Halim et al. 2025 (abstract only): direct use preferred to cracking for power)
- Limitations: Halim et al. (2025) full text not accessible; the claimed figure is from the essay and the abstract-level record.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| essay/Halim claim: direct cheaper than cracking-based power | 40 | % | literature | `results/research/validation/enduse.json` | `[id=EU-halim-claim]/expected` |
| computed gap, AmCraX price set, full_exhaust | -1.308 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=AmCraX price set (450 USD~1t, 8000 h);cracking_pathway=full_exhaust]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| computed gap, AmCraX price set, full_fired | 7.554 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=AmCraX price set (450 USD~1t, 8000 h);cracking_pathway=full_fired]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| computed gap, AmCraX price set, full_purified | 16.523 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=AmCraX price set (450 USD~1t, 8000 h);cracking_pathway=full_purified]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| computed gap, Ahmad basis, full_exhaust | -1.089 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=Ahmad basis (480 USD~1t, 7200 h);cracking_pathway=full_exhaust]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| computed gap, Ahmad basis, full_fired | 7.674 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=Ahmad basis (480 USD~1t, 7200 h);cracking_pathway=full_fired]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| computed gap, Ahmad basis, full_purified | 16.634 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=Ahmad basis (480 USD~1t, 7200 h);cracking_pathway=full_purified]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| computed gap, renewable NH3 today, full_exhaust | -5.042 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=renewable NH3 today (1000 USD~1t);cracking_pathway=full_exhaust]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| computed gap, renewable NH3 today, full_fired | 5.522 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=renewable NH3 today (1000 USD~1t);cracking_pathway=full_fired]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| computed gap, renewable NH3 today, full_purified | 14.646 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=renewable NH3 today (1000 USD~1t);cracking_pathway=full_purified]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| essay figure: direct cheaper than cracking-based power | 40 | % | literature | `results/research/enduse/turbine_threshold.json` | `row_evidence/H1-b/numbers/claim_pct` |
| largest computed gap, stored bases | 16.634 | % | python | `results/research/enduse/turbine_threshold.json` | `forty_percent_figure/largest_computed_pct` |
| smallest computed gap, stored bases | -5.042 | % | python | `results/research/enduse/turbine_threshold.json` | `forty_percent_figure/smallest_computed_pct` |
| largest gap in any sensitivity | 27.296 | % | python | `results/research/enduse/turbine_threshold.json` | `forty_percent_figure/largest_in_sensitivities_pct` |
| cracker CAPEX factor needed for the essay figure, cracking + PSA | 6.281 | - | python | `results/research/enduse/turbine_threshold.json` | `forty_percent_figure/cracker_capex_factor_for_40pct_purified` |
| cracker CAPEX factor needed for the essay figure, fired cracking | 11.137 | - | python | `results/research/enduse/turbine_threshold.json` | `forty_percent_figure/cracker_capex_factor_for_40pct_fired` |

Figures: `results/figures/research/enduse_power_cost_vs_price.png`
Data: `results/research/enduse/claim_check_direct_vs_cracking.csv`, `results/research/enduse/enduse_results.json`, `results/research/enduse/turbine_threshold.json`, `results/research/validation/enduse.json`

## H2: MIXED

**Primary hypothesis.** Feedstock: affordable, low-carbon ammonia is essential to economic and environmental competitiveness.

**Verdict.** MIXED (methodology v2). Version 1 verdict of the 23 November release: INCONCLUSIVE. Version 1 rule applied to the current rows: INCONCLUSIVE.

**Strongest defensible statement.** Ammonia price dominates the cost of cracked hydrogen (feed 76 % of LCOH on the reference basis, on every sourced price and CAPEX basis), and competitiveness with the SMR marker needs ammonia at or below about 320 USD/t. Low-carbon ammonia is necessary for lower emissions than fossil alternatives. Under the actual Singapore carbon tax, low carbon intensity is not rewarded (cross-claim H2-X CONTRADICTED); under a hypothetical life-cycle price, not Singapore law, blue overtakes grey near 33 SGD/t with a wide range.

**Cross-claim.** Cross-claim H2-X (low carbon intensity is rewarded economically): CONTRADICTED under the actual Singapore carbon-tax boundary. Under a hypothetical life-cycle carbon price (not Singapore law): INCONCLUSIVE.

**Findings against the essay.**

- Grey ammonia at the central price is not cheap enough: P(LCOH < 3.06 USD/kg) = 0.014.
- Under the actual Singapore carbon tax the tax is zero for every ammonia route, so low-carbon ammonia earns no cost advantage.

**Components.**

| Component | Verdict | Primary rows | Secondary rows | Envelope |
|---|---|---|---|---|
| H2-E Affordable ammonia is essential to economic competitiveness | SUPPORTED | H2-a, H2-b | - | H2-a: NH3 price above the 50 %-feed-share threshold (see numbers) at capacity scale 1, both heat-integration cases, reference CAPEX with multiplier up to 1.5 and PSA recovery down to 0.756 H2-b: against the NE Asia SMR marker and the Singapore willingness-to-pay figure; plant gate; CAPEX multiplier 0.41-1.5 One benchmark only. |
| H2-C Low-carbon ammonia is essential to environmental competitiveness | SUPPORTED | H2-c, H2-d | - | H2-c: Singapore power against NG CCGT or the grid average, GWP100, sourced gate-factor ranges H2-d: cracked H2 at the PSA outlet vs fossil H2 comparators, GWP100, sourced EF ranges |
| H2-X Cross-claim: low carbon intensity is rewarded economically | CONTRADICTED | H2-e | - | none (no primary row is SUPPORTED) |

**Verdict conditions.** Hypothesis verdict from its components (methodology v2; the cross-claim H2-X counts as a component): SUPPORTED if every component is SUPPORTED; CONTRADICTED if no component is SUPPORTED or PARTIALLY SUPPORTED and at least half are CONTRADICTED; MIXED if at least one component is SUPPORTED or PARTIALLY SUPPORTED and at least one is CONTRADICTED; PARTIALLY SUPPORTED if at least one component is SUPPORTED or PARTIALLY SUPPORTED, none is CONTRADICTED and not all are SUPPORTED; otherwise INCONCLUSIVE. Components: H2-E SUPPORTED; H2-C SUPPORTED; H2-X CONTRADICTED. Component verdict from its primary rows (methodology v2): SUPPORTED if every primary row is SUPPORTED; CONTRADICTED if no primary row is SUPPORTED and at least half are CONTRADICTED; MIXED if at least one is SUPPORTED and at least one CONTRADICTED; PARTIALLY SUPPORTED if at least one is SUPPORTED, none is CONTRADICTED and at least one is INCONCLUSIVE; otherwise INCONCLUSIVE. Secondary rows are reported but do not vote. Row outcomes: SUPPORTED: H2-a, H2-b, H2-c, H2-d; CONTRADICTED: H2-e.

### H2-a: SUPPORTED

Role: primary (H2-E). Version 1 verdict: SUPPORTED.

**Sub-claim.** Ammonia feed cost dominates the cost of cracked hydrogen, so affordable ammonia is essential to economic competitiveness.

**Numerical conclusions.**

- Feed is 75.7 % of LCOH 4.015 USD/kg.
- Feed stays above half of LCOH down to 115 USD/t (174 with adverse non-feed inputs, 125 without heat integration); the lowest sourced price is 300 USD/t.
- Capital + fixed opex reach the feed cost only at CAPEX x4.70 (x3.09 at 300 USD/t); sourced multipliers reach x1.50.
- Sobol total-effect index of the NH3 price 0.896 [0.875, 0.917].

**Conclusion.** Ammonia price dominates the cost of cracked hydrogen on every sourced price and CAPEX basis. Caveat: the cost excluding feed (REC) is driven by CAPEX and PSA recovery, not by the NH3 price.

**Rule and outcome.** Threshold rule (methodology v2): the feed share follows from assumed prices, so the NH3 price at which feed falls to half of LCOH (base, adverse non-feed inputs, heat integration off) is compared with the lowest sourced NH3 price, and the CAPEX multiple at which capital plus fixed opex equal feed (at the lowest sourced price) with the largest sourced CAPEX multiplier. SUPPORTED if every sourced value lies on the feed-dominant side of both thresholds; otherwise INCONCLUSIVE. Here: price test passed, CAPEX test passed. The Sobol index is reported as supporting evidence, not as the basis.

**Envelope.** NH3 price above the 50 %-feed-share threshold (see numbers) at capacity scale 1, both heat-integration cases, reference CAPEX with multiplier up to 1.5 and PSA recovery down to 0.756

**Threshold.** NH3 price for a 50 % feed share; CAPEX multiple at which capital + fixed opex equal feed: 114.9, 174.3, 3.094. Sourced: lowest sourced NH3 price 300, largest sourced CAPEX multiplier 1.500. Comparison: {"price": "sourced above threshold", "capex": "sourced below threshold"}.

**Assumptions.**

- NH3 price scenarios are inputs (Cho Table 8 300-610 USD/t; others data/singapore.yaml)
- reference CAPEX cho2026_itemised_v1 (at or above the independent published range)
- stored Aspen activity 6.756 kg NH3 feed + 0.595 kg NH3 fuel per kg H2
- NH3 price ranges are scenario inputs (data/singapore.yaml; Cho 2026 Table 8 and secondary web), not Singapore transaction prices
- the feed share is accounting at fixed stoichiometry of the stored Aspen baseline; the Sobol indices depend on the stated input ranges
- CAPEX cho2026_itemised_v1 with multiplier 0.5-1.5; no Singapore location factor

**Uncertainty.** Sobol ST of the NH3 price: grey 0.896 [0.875, 0.917], blue 0.726, green_current 0.636, green_2030 0.944 (95 % bootstrap CI in gsa_sobol.json); S1 CIs are wide (Saltelli 2010 estimator variance), ST CIs narrow; top-3 ranking unchanged under a right-skewed lognormal CAPEX MC (n=5000) feed share p5-p95 0.694-0.802; feed is the largest item in 1.0000 of draws

**Validation status.** Stored LCOH reproduced exactly; cost-share closure; NH3 feed per kg H2 above the stoichiometric floor (economics.json). Validation status of the underlying models: results/research/validation/carbon_pricing.json: 27 pass, 0 fail, 0 informational, 1 not available; results/research/validation/economics.json: 9 pass, 0 fail, 6 informational; results/research/validation/uq.json: 78 pass, 0 fail, 6 informational.

**Evidence kinds.** numerical verification, literature comparison.

**Key uncertainty (what would change the verdict).** Outside this envelope the verdict may change: NH3 price above the 50 %-feed-share threshold (see numbers) at capacity scale 1, both heat-integration cases, reference CAPEX with multiplier up to 1.5 and PSA recovery down to 0.756

**Uncertainty range.** Sobol ST of the NH3 price: grey 0.896 [0.875, 0.917], blue 0.726, green_current 0.636, green_2030 0.944 (95 % bootstrap CI in gsa_sobol.json); S1 CIs are wide (Saltelli 2010 estimator variance), ST CIs narrow; top-3 ranking unchanged under a right-skewed lognormal CAPEX MC (n=5000) feed share p5-p95 0.694-0.802; feed is the largest item in 1.0000 of draws

- Singapore scenario: Jurong Island cracker (stored Aspen baseline capacity), imported NH3 at the Singapore price scenarios (grey, blue, green 2050, green 2030, green current), heat integration on.
- Aspen model: Stored Aspen Plus V15 baseline (results/simulations/baseline.json): NH3 feed and fuel per kg H2.
- Python model: amcrax.economics.singapore.evaluate (equipment-level CAPEX screening estimate), tornado sensitivity.
- Case ids: baseline (stored Aspen), grey|heat_integration_on
- Validation: Stored LCOH reproduced exactly; cost-share closure; NH3 feed per kg H2 above the stoichiometric floor (economics.json). Validation status of the underlying models: results/research/validation/carbon_pricing.json: 27 pass, 0 fail, 0 informational, 1 not available; results/research/validation/economics.json: 9 pass, 0 fail, 6 informational; results/research/validation/uq.json: 78 pass, 0 fail, 6 informational.
- Input assumptions: NH3 price scenarios and the 300-610 USD/t tornado range are inputs (Cho Table 8 and secondary web prices); the feed share is computed but scales with these assumed prices.; Equipment-level CAPEX is a feed-scaled screening estimate and probably optimistic, which raises the feed share.
- Literature: `cho2026nickel` (Cho et al. 2026: NH3 price range for sensitivity (Table 8) and feed share of LCOH); `sp_blue_ammonia_2025` (S&P Global 2025: blue ammonia prices (search-result text)); `argus_h2_markers` (Argus 2026: NE Asia SMR hydrogen cost marker (sample report issue 26-01, p. 2, incl. capex)); `sp_singapore_h2_2025` (S&P Global 2025: Singapore willingness to pay (search-result text)); `saltelli2010sobol` (Sobol estimator)
- Limitations: Benchmark and price inputs partly from search-result text (secondary_web).; No product compression, NOx treatment or storage in the plant boundary.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| LCOH grey, HI on | 4.015 | USD/kg H2 | python | `results/research/singapore/scenario_results.json` | `results/grey\|heat_integration_on/lcoh_USD_per_kg` |
| feed NH3 cost component, grey | 3.040 | USD/kg H2 | python | `results/research/singapore/scenario_results.json` | `results/grey\|heat_integration_on/breakdown_USD_per_kg/ammonia_feed` |
| NH3 feed per kg H2 (Aspen activity) | 6.756 | kg/kg | aspen | `results/research/singapore/scenario_results.json` | `results/grey\|heat_integration_on/kg_nh3_feed_per_kg_h2` |
| tornado swing, NH3 price 300-610 USD/t | 2.279 | USD/kg H2 | python | `results/research/singapore/tornado.json` | `bars/[parameter=nh3_price_USD_per_t]/swing` |
| next-largest tornado swing (capacity x0.25-x4) | 0.6257 | USD/kg H2 | python | `results/research/singapore/tornado.json` | `bars/[parameter=capacity_scale]/swing` |
| feed share of LCOH (grey, HI on) | 0.7571 | fraction | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-a/numbers/feed_share` |
| LCOH grey (reference scenario) | 4.015 | USD/kg H2 | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-a/numbers/lcoh_USD_per_kg` |
| NH3 price at which feed is half of LCOH (base) | 114.9 | USD/t | python | `results/research/uq/row_evidence.json` | `row_evidence/H2-a/numbers/nh3_price_threshold_feed_share_50pct_USD_per_t/base` |
| same, adverse non-feed inputs | 174.3 | USD/t | python | `results/research/uq/row_evidence.json` | `row_evidence/H2-a/numbers/nh3_price_threshold_feed_share_50pct_USD_per_t/adverse_capex1.5_psa0.756_cat_life1_price2x_hours7000` |
| same, heat integration off | 124.7 | USD/t | python | `results/research/uq/row_evidence.json` | `row_evidence/H2-a/numbers/nh3_price_threshold_feed_share_50pct_USD_per_t/heat_integration_off_base` |
| lowest sourced NH3 price | 300 | USD/t | literature | `results/research/uq/row_evidence.json` | `row_evidence/H2-a/numbers/lowest_sourced_nh3_price_USD_per_t` |
| CAPEX multiple at which capital + fixed opex equal feed, 300 USD/t | 3.094 | - | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-a/threshold/capex_multiple_capital_plus_fixed_equals_feed_at_300` |
| same, 450 USD/t | 4.699 | - | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-a/threshold/capex_multiple_capital_plus_fixed_equals_feed_at_450` |
| largest sourced CAPEX multiplier | 1.500 | - | literature | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-a/threshold/sourced_capex_multiplier_max` |
| Sobol total-effect index of NH3 price on LCOH (grey) | 0.8957 | - | python | `results/research/uq/row_evidence.json` | `row_evidence/H2-a/numbers/sobol_nh3_price_lcoh_HIon/grey/ST` |
| lower 95 % bound of that index | 0.8753 | - | python | `results/research/uq/row_evidence.json` | `row_evidence/H2-a/numbers/sobol_nh3_price_lcoh_HIon/grey/ST_ci/0` |
| upper 95 % bound of that index | 0.9172 | - | python | `results/research/uq/row_evidence.json` | `row_evidence/H2-a/numbers/sobol_nh3_price_lcoh_HIon/grey/ST_ci/1` |

Figures: `results/figures/research/singapore_tornado.png`, `results/figures/research/singapore_cost_breakdown.png`, `results/figures/research/singapore_monte_carlo.png`
Data: `results/research/carbon_pricing/row_evidence.json`, `results/research/singapore/scenario_breakdown.csv`, `results/research/singapore/scenario_results.json`, `results/research/singapore/tornado.csv`, `results/research/singapore/tornado.json`, `results/research/uq/row_evidence.json`

### H2-b: SUPPORTED

Role: primary (H2-E). Version 1 verdict: SUPPORTED.

**Sub-claim.** Only affordable ammonia keeps cracked hydrogen competitive with the hydrogen benchmarks relevant to Singapore.

**Numerical conclusions.**

- Break-even NH3 price 320 USD/t (277 to 371 over the CAPEX range); every central sourced price is 450 USD/t or more.
- Adverse finding: grey NH3 at the central price is not cheap enough; P(LCOH < 3.06) = 0.014. Only the low ends of the sourced ranges (300 USD/t) reach the break-even.

**Conclusion.** Competitiveness with the SMR marker requires NH3 at or below about 320 USD/t; this holds across the sourced CAPEX range. It is a necessity statement: at central sourced prices, grey ammonia included, cracked hydrogen is not competitive.

**Rule and outcome.** Necessity rule (methodology v2 threshold form, row read as 'only affordable ammonia keeps it competitive'): the break-even NH3 price against the benchmark is computed over the sourced CAPEX range. SUPPORTED if it exists on every basis and lies below every central sourced NH3 price, so that competitiveness requires ammonia cheaper than any central scenario; otherwise INCONCLUSIVE. Under the other reading ('is competitiveness achieved at sourced prices', proposed by the UQ workstream) the full sourced ranges straddle the threshold and the row would be INCONCLUSIVE; the adversarial review must test this choice of reading.

**Envelope.** against the NE Asia SMR marker and the Singapore willingness-to-pay figure; plant gate; CAPEX multiplier 0.41-1.5 One benchmark only.

**Threshold.** NH3 price at which LCOH equals the 3.06 USD/kg benchmark: 363.0, 371.0, 333.1, 320.0, 277.0. Sourced: central sourced NH3 price, grey 450, central sourced NH3 price, blue 487, central sourced NH3 price, green_current 1000, central sourced NH3 price, green_2030 709, central sourced NH3 price, green_2050 463. Comparison: "all central prices above every break-even".

**Assumptions.**

- benchmark 3.06 USD/kg NE Asia SMR incl. capex (Argus, production-cost marker, not a Singapore price)
- plant-gate LCOH, no compression or delivery
- reference CAPEX

**Uncertainty.** break-even 277-371 USD/t over CAPEX x0.41-1.5; grey MC P(LCOH < 3.06) = 0.0140

**Validation status.** Break-even consistency check (LCOH at the break-even price equals the benchmark) in economics.json. Validation status of the underlying models: results/research/validation/carbon_pricing.json: 27 pass, 0 fail, 0 informational, 1 not available; results/research/validation/economics.json: 9 pass, 0 fail, 6 informational; results/research/validation/uq.json: 78 pass, 0 fail, 6 informational.

**Evidence kinds.** numerical verification, literature comparison.

**Key uncertainty (what would change the verdict).** Outside this envelope the verdict may change: against the NE Asia SMR marker and the Singapore willingness-to-pay figure; plant gate; CAPEX multiplier 0.41-1.5 One benchmark only.

**Uncertainty range.** break-even 277-371 USD/t over CAPEX x0.41-1.5; grey MC P(LCOH < 3.06) = 0.0140

- Singapore scenario: Jurong Island cracker (stored Aspen baseline capacity), imported NH3 at the Singapore price scenarios (grey, blue, green 2050, green 2030, green current), heat integration on.
- Aspen model: Stored Aspen Plus V15 baseline activities.
- Python model: amcrax.economics.singapore.breakeven_nh3_price and Monte Carlo (n and seed in monte_carlo.json).
- Case ids: grey|heat_integration_on, green_2030|heat_integration_on, green_current|heat_integration_on
- Validation: Break-even consistency check (LCOH at the break-even price equals the benchmark) in economics.json. Validation status of the underlying models: results/research/validation/carbon_pricing.json: 27 pass, 0 fail, 0 informational, 1 not available; results/research/validation/economics.json: 9 pass, 0 fail, 6 informational; results/research/validation/uq.json: 78 pass, 0 fail, 6 informational.
- Input assumptions: Hydrogen benchmarks in breakeven_ammonia_price.json have different bases and source qualities (listed per benchmark there); none is a Singapore transaction price.; NH3 price scenarios are inputs (data/singapore.yaml).
- Literature: `cho2026nickel` (Cho et al. 2026: NH3 price range for sensitivity (Table 8) and feed share of LCOH); `sp_blue_ammonia_2025` (S&P Global 2025: blue ammonia prices (search-result text)); `argus_h2_markers` (Argus 2026: NE Asia SMR hydrogen cost marker (sample report issue 26-01, p. 2, incl. capex)); `sp_singapore_h2_2025` (S&P Global 2025: Singapore willingness to pay (search-result text)); `ace_h2_delivered` (ASEAN Centre for Energy: delivered blue/green H2 cost to East Asia (search-result text))
- Limitations: Break-even is for the cracker gate; landed cost and product compression excluded.; Constant prices, pre-tax NPV.; Benchmarks are read from breakeven_ammonia_price.json as stored at build time; their sources are listed there.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| break-even NH3 price vs NE Asia SMR benchmark | 320.0 | USD/t | python | `results/research/singapore/breakeven_ammonia_price.json` | `results/heat_integration_on/ne_asia_smr_production_cost/breakeven_nh3_USD_per_t` |
| NE Asia SMR benchmark | 3.060 | USD/kg H2 | literature | `results/research/singapore/breakeven_ammonia_price.json` | `results/heat_integration_on/ne_asia_smr_production_cost/h2_price_USD_per_kg` |
| break-even NH3 price vs Singapore willingness to pay | 311.8 | USD/t | python | `results/research/singapore/breakeven_ammonia_price.json` | `results/heat_integration_on/sg_low_carbon_willingness_to_pay/breakeven_nh3_USD_per_t` |
| break-even NH3 price vs blue H2 delivered East Asia | 720.0 | USD/t | python | `results/research/singapore/breakeven_ammonia_price.json` | `results/heat_integration_on/blue_delivered_east_asia/breakeven_nh3_USD_per_t` |
| grey NH3 price | 450 | USD/t | assumption | `results/research/singapore/scenario_results.json` | `results/grey\|heat_integration_on/nh3_price_USD_per_t` |
| green 2030 NH3 price | 709 | USD/t | assumption | `results/research/singapore/scenario_results.json` | `results/green_2030\|heat_integration_on/nh3_price_USD_per_t` |
| green current NH3 price | 1000 | USD/t | assumption | `results/research/singapore/scenario_results.json` | `results/green_current\|heat_integration_on/nh3_price_USD_per_t` |
| LCOH green current | 8.058 | USD/kg H2 | python | `results/research/singapore/scenario_results.json` | `results/green_current\|heat_integration_on/lcoh_USD_per_kg` |
| Monte Carlo LCOH p95, grey | 4.882 | USD/kg H2 | python | `results/research/singapore/monte_carlo.json` | `results/grey/lcoh_p95` |
| Monte Carlo LCOH p5, green current | 7.426 | USD/kg H2 | python | `results/research/singapore/monte_carlo.json` | `results/green_current/lcoh_p5` |
| Monte Carlo LCOH p5, grey | 3.253 | USD/kg H2 | python | `results/research/singapore/monte_carlo.json` | `results/grey/lcoh_p5` |
| Monte Carlo LCOH p5, green 2030 | 4.707 | USD/kg H2 | python | `results/research/singapore/monte_carlo.json` | `results/green_2030/lcoh_p5` |
| break-even NH3 price against NE Asia SMR 3.06 USD/kg | 320.0 | USD/t | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-b/numbers/breakeven_vs_ne_asia_smr_USD_per_t` |
| Monte Carlo P(LCOH < 3.06), grey | 0.014 | probability | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-b/numbers/mc_P_lcoh_below_3p06_grey` |

Figures: `results/figures/research/singapore_breakeven.png`, `results/figures/research/singapore_monte_carlo.png`
Data: `results/research/carbon_pricing/row_evidence.json`, `results/research/singapore/breakeven_ammonia_price.json`, `results/research/singapore/monte_carlo.json`, `results/research/singapore/scenario_results.json`

### H2-c: SUPPORTED

Role: primary (H2-C). Version 1 verdict: SUPPORTED.

**Sub-claim.** Low-carbon ammonia is essential for environmental competitiveness of ammonia-based power in Singapore.

**Numerical conclusions.**

- Break-even gate factor 0.81 to 1.33 kg CO2e/kg NH3; lowest sourced grey value 2.00; green at most 0.48.
- Not sufficient: blue (Lee v1, central 1.16) passes only in part of its range.

**Conclusion.** Low-carbon ammonia is necessary for ammonia power to cut emissions against Singapore alternatives; grey ammonia cannot.

**Rule and outcome.** Necessity rule (methodology v2 threshold form): SUPPORTED if the lowest sourced grey gate factor lies above the highest computed break-even (grey can never cut power-sector emissions) and a low-carbon route lies below the lowest break-even over its whole sourced range; otherwise INCONCLUSIVE.

**Envelope.** Singapore power against NG CCGT or the grid average, GWP100, sourced gate-factor ranges

**Threshold.** gate emission factor of NH3 at which NH3 power equals the fossil comparator: 0.8079, 1.331. Sourced: grey low 2, green high 0.4794. Comparison: "grey above, green below".

**Assumptions.**

- direct NH3 CCGT activity and efficiency from results/research/lca (Ahmad-calibrated)
- CCGT efficiency 0.50-0.60 (assumption range)
- NG upstream leakage 0-3 % (low-confidence scenario values)
- 5000 km shipping

**Uncertainty.** break-even gate EF 0.81-1.33 kg/kg over CCGT efficiency and leakage; grey sourced range 2.0-4.6

**Validation status.** Lee v1 and v2 factors reproduced exactly; existing environmental baseline reproduced; breakdown sums (lca.json). Validation status of the underlying models: results/research/validation/carbon_pricing.json: 27 pass, 0 fail, 0 informational, 1 not available; results/research/validation/lca.json: 7 pass, 0 fail, 4 informational.

**Evidence kinds.** numerical verification, literature comparison.

**Key uncertainty (what would change the verdict).** Outside this envelope the verdict may change: Singapore power against NG CCGT or the grid average, GWP100, sourced gate-factor ranges

**Uncertainty range.** break-even gate EF 0.81-1.33 kg/kg over CCGT efficiency and leakage; grey sourced range 2.0-4.6

- Singapore scenario: Imported NH3 shipped 5000 km (scenario distance) and burned in a Jurong Island CCGT; comparators NG CCGT and the EMA grid average.
- Aspen model: No Aspen model for combustion: Python/literature only (NH3 per MWh from Ahmad-calibrated efficiency).
- Python model: amcrax.environmental.lca (GWP100 AR6) and its Monte Carlo (uniform over stated ranges).
- Case ids: routes: green, blue, blue_v2, grey, direct_NH3_CCGT
- Validation: Lee v1 and v2 factors reproduced exactly; existing environmental baseline reproduced; breakdown sums (lca.json). Validation status of the underlying models: results/research/validation/carbon_pricing.json: 27 pass, 0 fail, 0 informational, 1 not available; results/research/validation/lca.json: 7 pass, 0 fail, 4 informational.
- Input assumptions: NG CCGT efficiency (central value and range in results/research/lca/assumptions.json) is an assumption.; Sea distance is a scenario value, not a sourced route length.; Blue capture and methane leakage are scenario parameters.
- Literature: `lee2022ammonia` (Lee et al. 2022: blue and grey NH3 cradle-to-gate factors); `iea2024ghr` (IEA Global Hydrogen Review 2024 (highlights): green NH3 range); `ema2025ses` (EMA Singapore Energy Statistics: grid emission factor (not verified at source; third-party listing)); `ipcc2021ar6wg1ch7` (IPCC AR6 WG1 Ch. 7: GWP100)
- Limitations: Coal-based NH3 factor is low confidence (abstract-level).; Blue-NH3 leakage and capture are scenario parameters, not measured values.; Boil-off and terminal losses excluded (no sourced value).; Green NH3 central value includes embedded renewable-asset emissions from the IEA range; Lee's boundary gives zero.; Distances are scenario values, not sourced route lengths.; NOx and N2O are simulated values from one paper.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| baseline sea distance (scenario value) | 5000 | km | assumption | `results/research/lca/lca_results.json` | `distance_km_baseline` |
| break-even NH3 gate EF, direct NH3 CCGT vs NG CCGT (baseline distance) | 0.8864 | kg CO2e/kg NH3 | python | `results/research/lca/lca_results.json` | `breakeven/[comparison=direct NH3 CCGT vs NG CCGT;distance_km=5000]/breakeven_NH3_gate_EF_kgCO2e_per_kgNH3` |
| break-even NH3 gate EF, direct NH3 CCGT vs grid average | 0.9756 | kg CO2e/kg NH3 | python | `results/research/lca/lca_results.json` | `breakeven/[comparison=direct NH3 CCGT vs grid average;distance_km=5000]/breakeven_NH3_gate_EF_kgCO2e_per_kgNH3` |
| green NH3 gate EF | 0.2752 | kg CO2e/kg NH3 | literature | `results/research/lca/lca_results.json` | `routes/[route=green]/gate_kgCO2e_per_kgNH3` |
| blue NH3 gate EF (Lee v1) | 1.160 | kg CO2e/kg NH3 | literature | `results/research/lca/lca_results.json` | `routes/[route=blue]/gate_kgCO2e_per_kgNH3` |
| blue NH3 gate EF (Lee v2) | 0.77 | kg CO2e/kg NH3 | literature | `results/research/lca/lca_results.json` | `routes/[route=blue_v2]/gate_kgCO2e_per_kgNH3` |
| grey NH3 gate EF | 2.600 | kg CO2e/kg NH3 | literature | `results/research/lca/lca_results.json` | `routes/[route=grey]/gate_kgCO2e_per_kgNH3` |
| CI direct NH3 power, green | 128.9 | kg CO2e/MWh | python | `results/research/lca/lca_results.json` | `routes/[route=green]/direct_NH3_CCGT_kgCO2e_per_MWh` |
| CI direct NH3 power, blue | 473.9 | kg CO2e/MWh | python | `results/research/lca/lca_results.json` | `routes/[route=blue]/direct_NH3_CCGT_kgCO2e_per_MWh` |
| CI NG CCGT | 367.2 | kg CO2e/MWh | assumption | `results/research/lca/lca_results.json` | `alternatives/ccgt_ng_kgCO2e_per_MWh/central` |
| CI Singapore grid average (EMA 2024) | 402 | kg CO2e/MWh | literature | `results/research/lca/lca_results.json` | `alternatives/grid_average_kgCO2e_per_MWh/central` |
| Monte Carlo P(blue direct power below NG CCGT) | 0.00215 | probability | python | `results/research/lca/lca_results.json` | `monte_carlo/blue_direct_NH3_power/P_cuts_emissions_vs_NG_CCGT` |
| highest break-even gate emission factor (power, against NG CCGT or grid) | 1.331 | kg CO2e/kg NH3 | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-c/threshold/breakeven_gate_ef_max` |
| lowest break-even gate emission factor | 0.8079 | kg CO2e/kg NH3 | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-c/numbers/power_breakeven_gate_ef_range_kgCO2e_per_kgNH3/0` |
| lowest sourced grey gate emission factor | 2 | kg CO2e/kg NH3 | literature | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-c/threshold/grey_gate_ef_min` |
| green NH3 gate emission factor, high | 0.4794 | kg CO2e/kg NH3 | literature | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-c/numbers/green/high` |
| blue NH3 (Lee v1) gate emission factor, central | 1.160 | kg CO2e/kg NH3 | literature | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-c/numbers/blue_v1/central` |

Figures: `results/figures/research/lca_power_by_route.png`, `results/figures/research/lca_breakeven_power.png`, `results/figures/research/lca_sensitivity_blue_power.png`
Data: `results/research/carbon_pricing/row_evidence.json`, `results/research/lca/lca_breakeven.csv`, `results/research/lca/lca_results.json`, `results/research/lca/lca_routes.csv`

### H2-d: SUPPORTED

Role: primary (H2-C). Version 1 verdict: SUPPORTED.

**Sub-claim.** Low-carbon ammonia is essential for cracked hydrogen to have lower carbon intensity than fossil hydrogen.

**Numerical conclusions.**

- Break-even gate factor 1.31 to 1.58; lowest grey 2.00.
- Grey cracked H2 is at least 15.1 kg CO2e/kg H2; green central 2.43.

**Conclusion.** Low-carbon ammonia is necessary for cracked hydrogen to be less carbon-intensive than unabated fossil hydrogen.

**Rule and outcome.** Necessity rule (methodology v2 threshold form): SUPPORTED if the lowest sourced grey gate factor lies above the highest break-even against unabated SMR and a low-carbon route lies below the lowest break-even over its whole sourced range; otherwise INCONCLUSIVE. Against SMR with CCS only green passes (reported, not voted).

**Envelope.** cracked H2 at the PSA outlet vs fossil H2 comparators, GWP100, sourced EF ranges

**Threshold.** gate factor at which cracked H2 equals unabated SMR: 1.305, 1.441, 1.577. Sourced: grey low 2, green high 0.4794. Comparison: "grey above, green below".

**Assumptions.**

- SMR unabated 10-12 kg/kg (IEA GHR 2024 highlights)
- SMR+CCS 3.4-3.6 (low confidence), 5.3 high
- self-firing NH3 heat, 5000 km, Singapore grid

**Uncertainty.** grey H2 CI 15.1-34.2 kg/kg, always above unabated SMR 10-12

**Validation status.** As H2-c (lca.json). Validation status of the underlying models: results/research/validation/carbon_pricing.json: 27 pass, 0 fail, 0 informational, 1 not available; results/research/validation/lca.json: 7 pass, 0 fail, 4 informational.

**Evidence kinds.** numerical verification, literature comparison.

**Key uncertainty (what would change the verdict).** Outside this envelope the verdict may change: cracked H2 at the PSA outlet vs fossil H2 comparators, GWP100, sourced EF ranges

**Uncertainty range.** grey H2 CI 15.1-34.2 kg/kg, always above unabated SMR 10-12

- Singapore scenario: Industrial H2 from a Jurong Island cracker fed with imported NH3 (5000 km), compared with SMR hydrogen.
- Aspen model: Stored Aspen Plus V15 baseline: NH3 per kg H2 and process electricity.
- Python model: amcrax.environmental.lca and Monte Carlo.
- Case ids: baseline (stored Aspen), routes: green, blue, grey
- Validation: As H2-c (lca.json). Validation status of the underlying models: results/research/validation/carbon_pricing.json: 27 pass, 0 fail, 0 informational, 1 not available; results/research/validation/lca.json: 7 pass, 0 fail, 4 informational.
- Input assumptions: SMR + CCS factor is low confidence (search extracts).; Leakage and capture are scenario parameters.
- Literature: `lee2022ammonia` (Lee et al. 2022 NH3 factors); `frontiers2024smrccs` (Elgowainy et al. 2024: SMR + CCS literature range quoted from other studies (secondary, low confidence)); `arxiv2206.10689smr` (SMR hydrogen emissions (search extract))
- Limitations: Coal-based NH3 factor is low confidence (abstract-level).; Blue-NH3 leakage and capture are scenario parameters, not measured values.; Boil-off and terminal losses excluded (no sourced value).; Green NH3 central value includes embedded renewable-asset emissions from the IEA range; Lee's boundary gives zero.; Distances are scenario values, not sourced route lengths.; NOx and N2O are simulated values from one paper.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| CI industrial H2, green NH3 | 2.430 | kg CO2e/kg H2 | python | `results/research/lca/lca_results.json` | `routes/[route=green]/H2_kgCO2e_per_kg` |
| CI industrial H2, blue NH3 (Lee v1) | 8.933 | kg CO2e/kg H2 | python | `results/research/lca/lca_results.json` | `routes/[route=blue]/H2_kgCO2e_per_kg` |
| CI industrial H2, grey NH3 | 19.518 | kg CO2e/kg H2 | python | `results/research/lca/lca_results.json` | `routes/[route=grey]/H2_kgCO2e_per_kg` |
| CI SMR unabated (central) | 11 | kg CO2e/kg H2 | literature | `results/research/lca/lca_results.json` | `alternatives/smr_h2_unabated_kgCO2e_per_kgH2/central` |
| CI SMR + CCS (central, low confidence) | 3.500 | kg CO2e/kg H2 | literature | `results/research/lca/lca_results.json` | `alternatives/smr_h2_ccs_kgCO2e_per_kgH2/central` |
| Monte Carlo P(blue H2 below SMR unabated) | 0.251 | probability | python | `results/research/lca/lca_results.json` | `monte_carlo/blue_industrial_H2/P_below_SMR_unabated` |
| Monte Carlo P(blue H2 below SMR + CCS) | 0 | probability | python | `results/research/lca/lca_results.json` | `monte_carlo/blue_industrial_H2/P_below_SMR_CCS` |
| break-even NH3 gate EF vs SMR unabated (5000 km) | 1.441 | kg CO2e/kg NH3 | python | `results/research/lca/lca_results.json` | `breakeven/[comparison=industrial H2 vs SMR unabated;distance_km=5000]/breakeven_NH3_gate_EF_kgCO2e_per_kgNH3` |
| break-even NH3 gate EF vs SMR + CCS (5000 km) | 0.4208 | kg CO2e/kg NH3 | python | `results/research/lca/lca_results.json` | `breakeven/[comparison=industrial H2 vs SMR + CCS;distance_km=5000]/breakeven_NH3_gate_EF_kgCO2e_per_kgNH3` |
| highest break-even gate factor against unabated SMR | 1.577 | kg CO2e/kg NH3 | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-d/threshold/breakeven_gate_ef_vs_smr_unabated_max` |
| lowest sourced grey gate factor | 2 | kg CO2e/kg NH3 | literature | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-d/threshold/grey_gate_ef_min` |
| green NH3 gate factor, high | 0.4794 | kg CO2e/kg NH3 | literature | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-c/numbers/green/high` |
| cracked H2 carbon intensity, grey, low end | 15.108 | kg CO2e/kg H2 | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-d/numbers/ci_kgCO2e_per_kgH2/grey/low` |
| cracked H2 carbon intensity, green, central | 2.430 | kg CO2e/kg H2 | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-d/numbers/ci_kgCO2e_per_kgH2/green/central` |

Figures: `results/figures/research/lca_h2_by_route.png`
Data: `results/research/carbon_pricing/row_evidence.json`, `results/research/lca/lca_breakeven.csv`, `results/research/lca/lca_results.json`

### H2-e: CONTRADICTED

Role: primary (H2-X). Version 1 verdict: CONTRADICTED. By mode: actual Singapore boundary CONTRADICTED (votes); hypothetical life-cycle price, not Singapore law, INCONCLUSIVE (does not vote).

**Sub-claim.** Low-carbon ammonia is essential to economic competitiveness (that is, low carbon intensity is rewarded in the Singapore cost of hydrogen).

**Numerical conclusions.**

- Actual Singapore boundary: carbon tax 0.000 USD/kg for every route; LCOH grey 4.015, blue 4.287, green (current price) 8.058 USD/kg.
- Hypothetical life-cycle price, not Singapore law: blue overtakes grey at 33 SGD/t (range 12 to 605); green at current prices needs 305 (156 to 466). The legislated rate is 45 SGD/t for 2026 and any later year.

**Conclusion.** Under the actual Singapore carbon tax low carbon intensity earns no cost advantage. Under a hypothetical life-cycle price (not Singapore law) the outcome depends on the price and the carbon-intensity range.

**Rule and outcome.** Policy rule (methodology v2: a hypothetical scenario cannot change a row about actual policy). Mode A, actual Singapore boundary (votes): CONTRADICTED if the carbon cost is zero for every NH3 route while low-carbon NH3 raises LCOH; otherwise INCONCLUSIVE. Mode B, HYPOTHETICAL life-cycle carbon price, not Singapore law (reported separately, does not vote): SUPPORTED if the price at which low-carbon NH3 overtakes grey lies at or below the legislated rate over its whole range; CONTRADICTED if blue and green both need more than that rate over their whole ranges; otherwise INCONCLUSIVE. Here Mode A CONTRADICTED, Mode B INCONCLUSIVE (blue range 'straddle' the legislated rate).

**Envelope.** current Singapore law; any plant size for the ammonia-route question (upstream emissions are outside the Act at every size)

**Threshold.** HYPOTHETICAL life-cycle carbon price at which low-carbon NH3 overtakes grey (not Singapore law): 12.447, 605.4, 156.5, 466.0. Sourced: legislated rate 45. Comparison: "straddle".

**Assumptions.**

- Carbon Pricing Act 2018 text as at 23 Nov 2026 (rate 45 from 2026, threshold 25,000 tCO2e, direct emissions only)
- single-site facility, no other emitters on site
- NH3 self-firing (no CO2)
- Mode B: life-cycle price on the full CI (no such instrument exists in Singapore)
- Mode B: NH3 price scenarios (central)
- Mode B: CI gate-factor ranges (lca.route_spec), 5000 km

**Uncertainty.** N2O factor not sourced; the threshold needs about 5 % of the fuel nitrogen to leave as N2O (about 1500 ppmv), far above the 0.15 ppmv simulated for an NH3 turbine. EITE allowances and future amendments not read. Mode B: threshold ranges from CI ranges and a joint Monte Carlo with NH3 price ranges (thresholds.json)

**Validation status.** Zero tax on NH3-fired heat and gas-fired heat below the threshold (economics.json). Validation status of the underlying models: results/research/validation/carbon_pricing.json: 27 pass, 0 fail, 0 informational, 1 not available; results/research/validation/economics.json: 9 pass, 0 fail, 6 informational; results/research/validation/lca.json: 7 pass, 0 fail, 4 informational.

**Evidence kinds.** numerical verification, literature comparison.

**Key uncertainty (what would change the verdict).** Outside this envelope the verdict may change: current Singapore law; any plant size for the ammonia-route question (upstream emissions are outside the Act at every size)

**Uncertainty range.** N2O factor not sourced; the threshold needs about 5 % of the fuel nitrogen to leave as N2O (about 1500 ppmv), far above the 0.15 ppmv simulated for an NH3 turbine. EITE allowances and future amendments not read. Mode B: threshold ranges from CI ranges and a joint Monte Carlo with NH3 price ranges (thresholds.json)

- Singapore scenario: Jurong Island cracker (stored Aspen baseline capacity), imported NH3 at the Singapore price scenarios (grey, blue, green 2050, green 2030, green current), heat integration on. Singapore carbon tax at the current legislated rate, Scope 1 only, with the NEA facility threshold.
- Aspen model: Stored Aspen Plus V15 baseline: direct emissions of the NH3-fired cracker (no CO2).
- Python model: amcrax.economics.singapore carbon-tax treatment; amcrax.environmental.lca carbon_tax_sg.
- Case ids: grey|heat_integration_on, green_2030|heat_integration_on
- Validation: Zero tax on NH3-fired heat and gas-fired heat below the threshold (economics.json). Validation status of the underlying models: results/research/validation/carbon_pricing.json: 27 pass, 0 fail, 0 informational, 1 not available; results/research/validation/economics.json: 9 pass, 0 fail, 6 informational; results/research/validation/lca.json: 7 pass, 0 fail, 4 informational.
- Input assumptions: Upstream and shipping emissions are outside Singapore's carbon-tax base (NEA rules).; N2O factor from one simulated source (Ahmad).
- Literature: `nea_carbon_tax` (NEA carbon tax rates, threshold and covered gases)
- Limitations: Only current, legislated Singapore carbon-tax rules; no low-carbon premium or contract-for-difference modelled.; The 'hypothetical' gas-heat carbon-tax heatmap ignores the threshold and is not used here.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| Singapore carbon tax rate used | 45 | SGD/t CO2e | literature | `results/research/lca/lca_results.json` | `carbon_tax_sg/rate_SGD_per_t` |
| carbon tax in LCOH, grey, NH3-fired heat | 0 | USD/kg H2 | python | `results/research/singapore/scenario_results.json` | `results/grey\|heat_integration_on/breakdown_USD_per_kg/carbon_tax` |
| tornado swing, carbon tax | 0 | USD/kg H2 | python | `results/research/singapore/tornado.json` | `bars/[parameter=carbon_tax_SGD_per_t]/swing` |
| LCOH grey | 4.015 | USD/kg H2 | python | `results/research/singapore/scenario_results.json` | `results/grey\|heat_integration_on/lcoh_USD_per_kg` |
| LCOH green 2030 | 5.919 | USD/kg H2 | python | `results/research/singapore/scenario_results.json` | `results/green_2030\|heat_integration_on/lcoh_USD_per_kg` |
| carbon tax, every NH3 route (actual Singapore boundary) | 0 | USD/kg H2 | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-e_mode_A_actual_policy/numbers/carbon_tax_USD_per_kg_all_routes` |
| LCOH grey | 4.015 | USD/kg H2 | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-e_mode_A_actual_policy/numbers/lcoh_by_route_USD_per_kg/grey` |
| LCOH blue | 4.287 | USD/kg H2 | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-e_mode_A_actual_policy/numbers/lcoh_by_route_USD_per_kg/blue` |
| LCOH green, current price | 8.058 | USD/kg H2 | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-e_mode_A_actual_policy/numbers/lcoh_by_route_USD_per_kg/green_current` |
| hypothetical life-cycle price at which blue overtakes grey, central | 33.106 | SGD/tCO2e | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-e_mode_B_hypothetical_conditional/numbers/blue_over_grey/central` |
| same, low | 12.447 | SGD/tCO2e | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-e_mode_B_hypothetical_conditional/numbers/blue_over_grey/range/0` |
| same, high | 605.4 | SGD/tCO2e | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-e_mode_B_hypothetical_conditional/numbers/blue_over_grey/range/1` |
| hypothetical price at which green (current) overtakes grey, central | 304.8 | SGD/tCO2e | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-e_mode_B_hypothetical_conditional/numbers/green_current_over_grey/central` |
| same, low | 156.5 | SGD/tCO2e | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-e_mode_B_hypothetical_conditional/numbers/green_current_over_grey/range/0` |
| same, high | 466.0 | SGD/tCO2e | python | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-e_mode_B_hypothetical_conditional/numbers/green_current_over_grey/range/1` |
| legislated Singapore carbon tax, 2026 onward | 45 | SGD/tCO2e | literature | `results/research/carbon_pricing/row_evidence.json` | `row_evidence/H2-e_mode_B_hypothetical_conditional/numbers/reference_prices/singapore_legislated_2026_onward` |

Figures: `results/figures/research/singapore_heatmap_nh3_price_carbon_tax.png`
Data: `results/research/carbon_pricing/row_evidence.json`, `results/research/lca/lca_results.json`, `results/research/singapore/heatmap_nh3_price_x_carbon_tax_nh3_heat.csv`, `results/research/singapore/scenario_results.json`, `results/research/singapore/tornado.json`

## H3: PARTIALLY SUPPORTED

**Primary hypothesis.** Catalyst and heat integration: low-temperature, high-activity catalysts with effective heat integration reduce energy use and can outweigh higher catalyst cost.

**Verdict.** PARTIALLY SUPPORTED (methodology v2). Version 1 verdict of the 23 November release: INCONCLUSIVE. Version 1 rule applied to the current rows: INCONCLUSIVE.

**Strongest defensible statement.** Heat integration reduces energy use substantially (Aspen) and saves 0.214 USD/kg gross, 0.067 to 0.095 net of the exchanger cost on the reference basis. Lower-temperature operation reduces fired duty at equal conversion only modestly (at most 25 kW with heat integration) and only resolved for the Ru catalysts. Whether the savings outweigh a higher catalyst cost is unresolved; at derived ruthenium prices they do not at equal conversion.

**Findings against the essay.**

- At ruthenium prices derived from metal content, the low-temperature catalysts do not pay at equal conversion.
- The Phase 1 figure of a 17 % fired-duty reduction came from unequal conversion and is withdrawn.

**Components.**

| Component | Verdict | Primary rows | Secondary rows | Envelope |
|---|---|---|---|---|
| H3-T Lower-temperature operation reduces energy use | PARTIALLY SUPPORTED | H3-a, H3-b | - | H3-a: 20 bar, conversion 0.95, PSA 0.85. Resolved for Ru/Al2O3, Ru/MgO (operating temperature 499, 522 degC against 594 degC for Ni/MgO), that is only for temperature differences of 72 K or more; unresolved for 5Ni1Ru/CeO2, 2.5Ni0.5Ru/CeO2. 20 bar, X 0.95 (equal conversion), 499-594 degC, with and without FEHE. With FEHE the saving is about 0.26 kW per K (25 kW from 594 to 499 degC, about 5 % of fired duty); it exceeds the absolute Python-Aspen offset (15 kW) only for a temperature drop of about 60 K or more (Ru/Al2O3, Ru/MgO against Ni; not the NiRu/CeO2 catalysts, 4-5 kW). Without FEHE 31-163 kW. The direction is kinetics-independent; WHICH catalyst reaches which T rests on extrapolated laws. |
| H3-H Heat integration reduces energy use | SUPPORTED | H3-d | - | H3-d: 20 bar, 499-625 degC reactor, FEHE hot-end approach 20-200 K (python), U >= break-even U Cost: the net saving is negative only below the break-even U, for NH3 near the low end of the price range or a high capital recovery factor. |
| H3-K The savings can outweigh a higher catalyst cost | INCONCLUSIVE | H3-c | H3-e, H3-f | none (no primary row is SUPPORTED) |

**Verdict conditions.** Hypothesis verdict from its components (methodology v2; the cross-claim H2-X counts as a component): SUPPORTED if every component is SUPPORTED; CONTRADICTED if no component is SUPPORTED or PARTIALLY SUPPORTED and at least half are CONTRADICTED; MIXED if at least one component is SUPPORTED or PARTIALLY SUPPORTED and at least one is CONTRADICTED; PARTIALLY SUPPORTED if at least one component is SUPPORTED or PARTIALLY SUPPORTED, none is CONTRADICTED and not all are SUPPORTED; otherwise INCONCLUSIVE. Components: H3-T PARTIALLY SUPPORTED; H3-H SUPPORTED; H3-K INCONCLUSIVE. Component verdict from its primary rows (methodology v2): SUPPORTED if every primary row is SUPPORTED; CONTRADICTED if no primary row is SUPPORTED and at least half are CONTRADICTED; MIXED if at least one is SUPPORTED and at least one CONTRADICTED; PARTIALLY SUPPORTED if at least one is SUPPORTED, none is CONTRADICTED and at least one is INCONCLUSIVE; otherwise INCONCLUSIVE. Secondary rows are reported but do not vote. Row outcomes: SUPPORTED: H3-a, H3-d; INCONCLUSIVE: H3-b, H3-c, H3-e, H3-f.

### H3-a: SUPPORTED

Role: primary (H3-T). Version 1 verdict: SUPPORTED.

**Sub-claim.** Energy half of the catalyst claim: at equal conversion, running the cracker at the lower temperature that a more active catalyst allows reduces energy use.

**Numerical conclusions.**

- Saving with heat integration: Ru/Al2O3 25.1 kW, Ru/MgO 18.6 kW, 5Ni1Ru/CeO2 5.4 kW, 2.5Ni0.5Ru/CeO2 4.4 kW; resolution 15.2 kW.
- Saving without heat integration: Ru/Al2O3 162.6 kW, Ru/MgO 123.4 kW, 5Ni1Ru/CeO2 37.8 kW, 2.5Ni0.5Ru/CeO2 31.0 kW.
- The Phase 1 figure of 17 % fired duty came from unequal conversion and is withdrawn.

**Conclusion.** At equal conversion lower-temperature operation reduces fired duty, by a few per cent with heat integration and more without; the result is resolved only for the two Ru catalysts with the largest temperature difference.

**Rule and outcome.** Resolution rule (methodology v2): at equal conversion the fired-duty saving of each low-temperature catalyst against Ni/MgO is compared with the largest Aspen minus Python fired-duty offset at the same T and X (15.2 kW). SUPPORTED if no catalyst shows a reversal beyond that offset and at least one saving exceeds it with and without heat integration; the envelope is limited to the resolved catalysts. Otherwise INCONCLUSIVE.

**Envelope.** 20 bar, conversion 0.95, PSA 0.85. Resolved for Ru/Al2O3, Ru/MgO (operating temperature 499, 522 degC against 594 degC for Ni/MgO), that is only for temperature differences of 72 K or more; unresolved for 5Ni1Ru/CeO2, 2.5Ni0.5Ru/CeO2. 20 bar, X 0.95 (equal conversion), 499-594 degC, with and without FEHE. With FEHE the saving is about 0.26 kW per K (25 kW from 594 to 499 degC, about 5 % of fired duty); it exceeds the absolute Python-Aspen offset (15 kW) only for a temperature drop of about 60 K or more (Ru/Al2O3, Ru/MgO against Ni; not the NiRu/CeO2 catalysts, 4-5 kW). Without FEHE 31-163 kW. The direction is kinetics-independent; WHICH catalyst reaches which T rests on extrapolated laws.

**Assumptions.**

- fixed 95 % conversion, 20 bar, PSA 0.85
- furnace efficiency 0.85 and 2 % loss (assumptions)
- fired duty = temperature-feasible import after FEHE and tail-gas firing

**Uncertainty.** Python fired duty is 13.8-15.2 kW below Aspen at the same T and X for all five catalysts (spread 1.4 kW, so the T-dependence is reproduced within 1.4 kW over 95 K); FEHE duty offset +20.8 kW (model form, task X1).

**Validation status.** Aspen RPLUG vs Python PFR (|dX| below tolerance), integrated cases not above RGibbs equilibrium; Python vs Aspen heat duties (aspen_kinetic.json, catalyst_comparison.json). Validation status of the underlying models: results/research/validation/aspen_kinetic.json: 163 pass, 5 fail, 22 informational (failures: cat_nire_ceo2_5ni1ru_lucentini_lhhw_below_equilibrium, cat_nire_ceo2_2p5ni0p5ru_lucentini_lhhw_below_equilibrium, cat_ru_takahashi_microkinetic_below_equilibrium, k1p2_nire_ceo2_5ni1ru_lucentini_lhhw_below_equilibrium_partialpres, k1p2_nire_ceo2_2p5ni0p5ru_lucentini_lhhw_below_equilibrium_partialpres); results/research/validation/catalyst_comparison.json: 66 pass, 5 fail, 4 informational (failures: HCAT-ASPY-Ru/Al2O3-HI-heat, HCAT-ASPY-5Ni1Ru/CeO2-HI-heat, HCAT-ASPY-2.5Ni0.5Ru/CeO2-HI-heat, HCAT-ASPY-Ni/MgO-HI-heat, HCAT-ASPY-Ru/MgO-HI-heat); results/research/validation/catalyst_economics.json: 141 pass, 0 fail, 1 informational.

**Evidence kinds.** numerical verification, python vs aspen.

**Key uncertainty (what would change the verdict).** Outside this envelope the verdict may change: 20 bar, conversion 0.95, PSA 0.85. Resolved for Ru/Al2O3, Ru/MgO (operating temperature 499, 522 degC against 594 degC for Ni/MgO), that is only for temperature differences of 72 K or more; unresolved for 5Ni1Ru/CeO2, 2.5Ni0.5Ru/CeO2. 20 bar, X 0.95 (equal conversion), 499-594 degC, with and without FEHE. With FEHE the saving is about 0.26 kW per K (25 kW from 594 to 499 degC, about 5 % of fired duty); it exceeds the absolute Python-Aspen offset (15 kW) only for a temperature drop of about 60 K or more (Ru/Al2O3, Ru/MgO against Ni; not the NiRu/CeO2 catalysts, 4-5 kW). Without FEHE 31-163 kW. The direction is kinetics-independent; WHICH catalyst reaches which T rests on extrapolated laws.

**Uncertainty range.** Python fired duty is 13.8-15.2 kW below Aspen at the same T and X for all five catalysts (spread 1.4 kW, so the T-dependence is reproduced within 1.4 kW over 95 K); FEHE duty offset +20.8 kW (model form, task X1).

- Singapore scenario: Jurong Island cracker; 100 kmol/h liquid NH3 (0.2 mol% H2O), 20 bar, 95 % NH3 conversion for every catalyst, PSA recovery 0.85; grey NH3 price scenario; amcrax.economics.singapore.evaluate, grey 450 USD/t, catalyst W*price/lifetime (2 yr); Phase 2: catalyst prices are the DERIVED central scenario prices of research/data/catalyst_prices.json (Cho TEA prices only in the Cho reconstruction and the labelled published-TEA sensitivity case); full catalyst economics in results/research/catalyst_economics/.
- Aspen model: Aspen Plus V15 integrated flowsheet with kinetic RPLUG cracker (ci_* cases, with and without heat integration), 100 kg catalyst, each catalyst at its operating temperature as defined in aspen_kinetic/catalyst_comparison.json.
- Python model: amcrax.research.catalyst_comparison fired-duty post-processing (tail-gas firing, furnace efficiency).
- Case ids: ci_kum_T499_P20_W100_hi, ci_kum_T499_P20_W100_nohi, ci_tru_T522_P20_W100_hi, ci_tru_T522_P20_W100_nohi, ci_luc5_T572_P20_W100_hi, ci_luc5_T572_P20_W100_nohi, ci_luc25_T576_P20_W100_hi, ci_luc25_T576_P20_W100_nohi, ci_tni_T594_P20_W100_hi, ci_tni_T594_P20_W100_nohi
- Validation: Aspen RPLUG vs Python PFR (|dX| below tolerance), integrated cases not above RGibbs equilibrium; Python vs Aspen heat duties (aspen_kinetic.json, catalyst_comparison.json). Validation status of the underlying models: results/research/validation/aspen_kinetic.json: 163 pass, 5 fail, 22 informational (failures: cat_nire_ceo2_5ni1ru_lucentini_lhhw_below_equilibrium, cat_nire_ceo2_2p5ni0p5ru_lucentini_lhhw_below_equilibrium, cat_ru_takahashi_microkinetic_below_equilibrium, k1p2_nire_ceo2_5ni1ru_lucentini_lhhw_below_equilibrium_partialpres, k1p2_nire_ceo2_2p5ni0p5ru_lucentini_lhhw_below_equilibrium_partialpres); results/research/validation/catalyst_comparison.json: 66 pass, 5 fail, 4 informational (failures: HCAT-ASPY-Ru/Al2O3-HI-heat, HCAT-ASPY-5Ni1Ru/CeO2-HI-heat, HCAT-ASPY-2.5Ni0.5Ru/CeO2-HI-heat, HCAT-ASPY-Ni/MgO-HI-heat, HCAT-ASPY-Ru/MgO-HI-heat); results/research/validation/catalyst_economics.json: 141 pass, 0 fail, 1 informational.
- Input assumptions: Operating temperatures come from the Python kinetics study (Aspen confirms conversion).; Furnace efficiency 0.85 and thermal-loss allowance 2 % (assumptions) for the fired duty.; Takahashi Ni/MgO and Ru/MgO rows use a fitted LHHW approximation (python fit, valid at 20 bar only; rate error RMS 12 %, max about 50 %) and are extrapolations from 1 atm data.
- Literature: `kum2026heatintegrated` (Kum et al. 2026: Ru/Al2O3 Temkin-Pyzhev law); `takahashi2016kinetic` (Takahashi & Fujitani 2016: Ni/MgO and Ru/MgO microkinetics); `lucentini2021nirukinetic` (Lucentini et al. 2021: Ni-Ru/CeO2 LHHW (Table 3))
- Limitations: The temperature difference between catalysts rests on extrapolated rate laws (see H3-b); the energy effect of temperature itself is thermodynamic and computed by Aspen.; Python FEHE recovered duty is above Aspen beyond the validation tolerance (HCAT-ASPY-*-HI-heat failures).; All rate laws are extrapolated to 20 bar from their fit pressure (1 atm; Kum: 10 bar); the Takahashi laws are evaluated on a mole-fraction basis and the Lucentini laws on concentrations; the Ni/MgO law fails its own validation (EXISTING-KIN-NI-PRED). No catalyst ranking at 20 bar is a property of the catalysts.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| operating T, Ru/Al2O3 (100 kg, 95 %) | 499 | degC | python | `results/research/aspen_kinetic/catalyst_comparison.json` | `rows/[catalyst_id=ru_kum_temkin_pyzhev]/operating_temperature_C` |
| operating T, Ni/MgO (100 kg, 95 %) | 594 | degC | python | `results/research/aspen_kinetic/catalyst_comparison.json` | `rows/[catalyst_id=ni_takahashi_microkinetic]/operating_temperature_C` |
| external heating with HI, Ru/Al2O3 | 2221.4 | kW | aspen | `results/research/aspen_kinetic/catalyst_comparison.json` | `rows/[catalyst_id=ru_kum_temkin_pyzhev]/integrated_hi_total_external_heating_kW` |
| external heating with HI, Ni/MgO | 2258.8 | kW | aspen | `results/research/aspen_kinetic/catalyst_comparison.json` | `rows/[catalyst_id=ni_takahashi_microkinetic]/integrated_hi_total_external_heating_kW` |
| external heating without HI, Ru/Al2O3 | 2690.6 | kW | aspen | `results/research/aspen_kinetic/catalyst_comparison.json` | `rows/[catalyst_id=ru_kum_temkin_pyzhev]/integrated_nohi_total_external_heating_kW` |
| external heating without HI, Ni/MgO | 2862.3 | kW | aspen | `results/research/aspen_kinetic/catalyst_comparison.json` | `rows/[catalyst_id=ni_takahashi_microkinetic]/integrated_nohi_total_external_heating_kW` |
| fired duty reduction Ru/Al2O3 vs Ni/MgO, with HI | 0.17 | fraction | aspen | `results/research/catalyst_comparison/catalyst_comparison.json` | `findings/fixed_inventory_100kg_aspen/Ru_Al2O3_vs_Ni_fired_duty_reduction_HI` |
| fired duty reduction Ru/Al2O3 vs Ni/MgO, without HI | 0.197 | fraction | aspen | `results/research/catalyst_comparison/catalyst_comparison.json` | `findings/fixed_inventory_100kg_aspen/Ru_Al2O3_vs_Ni_fired_duty_reduction_noHI` |
| LHV efficiency with HI, Ru/Al2O3 | 0.8755 | fraction | aspen | `results/research/aspen_kinetic/catalyst_comparison.json` | `rows/[catalyst_id=ru_kum_temkin_pyzhev]/integrated_hi_lhv_efficiency` |
| LHV efficiency with HI, Ni/MgO | 0.8746 | fraction | aspen | `results/research/aspen_kinetic/catalyst_comparison.json` | `rows/[catalyst_id=ni_takahashi_microkinetic]/integrated_hi_lhv_efficiency` |
| catalyst inventory in every ci_* case | 100 | kg | assumption | `results/research/aspen_kinetic/catalyst_comparison.json` | `rows/[catalyst_id=ru_kum_temkin_pyzhev]/W_kg` |
| furnace efficiency | 0.85 | fraction of NH3 LHV | assumption | `results/research/catalyst_comparison/assumptions.json` | `[name=furnace_efficiency]/value` |
| thermal-loss allowance | 0.02 | fraction of reactor + trim heater duty | assumption | `results/research/catalyst_comparison/assumptions.json` | `[name=thermal_loss_fraction]/value` |
| fired-duty saving against Ni/MgO at equal conversion, Ru/Al2O3, heat integration on | 25.119 | kW | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-a/numbers/python_Top_X095_fired_duty_saving_kW_HI/Ru~1Al2O3` |
| fired-duty saving against Ni/MgO at equal conversion, Ru/MgO, heat integration on | 18.627 | kW | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-a/numbers/python_Top_X095_fired_duty_saving_kW_HI/Ru~1MgO` |
| fired-duty saving against Ni/MgO at equal conversion, 5Ni1Ru/CeO2, heat integration on | 5.426 | kW | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-a/numbers/python_Top_X095_fired_duty_saving_kW_HI/5Ni1Ru~1CeO2` |
| fired-duty saving against Ni/MgO at equal conversion, 2.5Ni0.5Ru/CeO2, heat integration on | 4.423 | kW | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-a/numbers/python_Top_X095_fired_duty_saving_kW_HI/2.5Ni0.5Ru~1CeO2` |
| same, heat integration off, Ru/Al2O3 | 162.6 | kW | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-a/numbers/python_Top_X095_fired_duty_saving_kW_noHI/Ru~1Al2O3` |
| same, heat integration off, Ru/MgO | 123.4 | kW | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-a/numbers/python_Top_X095_fired_duty_saving_kW_noHI/Ru~1MgO` |
| same, heat integration off, 5Ni1Ru/CeO2 | 37.832 | kW | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-a/numbers/python_Top_X095_fired_duty_saving_kW_noHI/5Ni1Ru~1CeO2` |
| same, heat integration off, 2.5Ni0.5Ru/CeO2 | 30.962 | kW | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-a/numbers/python_Top_X095_fired_duty_saving_kW_noHI/2.5Ni0.5Ru~1CeO2` |

Figures: `results/figures/research/catalyst_heat_duty.png`, `results/figures/research/catalyst_cost_breakdown.png`, `results/figures/research/aspen_kinetic_operating_point.png`
Aspen screenshots: `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__01_flowsheet.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__02_reactions_kinetic.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__03_reactions_kinetic_tab.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__05_reactor_configuration.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__06_reactor_catalyst.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__08_reactor_results.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__09_reactor_profiles.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__10_run_status.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__11_components.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__12_property_method.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__13_stream_results.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__14_psa_block.png`, `docs/images/aspen_evidence/cs_OP_tni_T594_P20_W100__02_reactions_kinetic.png`, `docs/images/aspen_evidence/cs_OP_tni_T594_P20_W100__03_reactions_kinetic_tab.png`
Data: `results/research/aspen_kinetic/catalyst_comparison.json`, `results/research/aspen_kinetic/catalyst_integrated.csv`, `results/research/aspen_kinetic/ci_kum_T499_P20_W100_hi.json`, `results/research/aspen_kinetic/ci_kum_T499_P20_W100_nohi.json`, `results/research/aspen_kinetic/ci_luc25_T576_P20_W100_hi.json`, `results/research/aspen_kinetic/ci_luc25_T576_P20_W100_nohi.json`, `results/research/aspen_kinetic/ci_luc5_T572_P20_W100_hi.json`, `results/research/aspen_kinetic/ci_luc5_T572_P20_W100_nohi.json`, `results/research/aspen_kinetic/ci_tni_T594_P20_W100_hi.json`, `results/research/aspen_kinetic/ci_tni_T594_P20_W100_nohi.json`, `results/research/aspen_kinetic/ci_tru_T522_P20_W100_hi.json`, `results/research/aspen_kinetic/ci_tru_T522_P20_W100_nohi.json`, `results/research/catalyst_comparison/assumptions.json`, `results/research/catalyst_comparison/catalyst_comparison.json`, `results/research/catalyst_economics/catalyst_economics.json`

### H3-b: INCONCLUSIVE

Role: primary (H3-T). Version 1 verdict: INCONCLUSIVE.

**Sub-claim.** Low-temperature, high-activity catalysts allow the cracker to run at a lower temperature for the same duty.

**Numerical conclusions.**

- Operating temperature at 100 kg: Ru/Al2O3 499, Ru/MgO 522, 5Ni1Ru/CeO2 572, 2.5Ni0.5Ru/CeO2 576, Ni/MgO 594 degC.
- Kinetic validity: 0 laws validated at relevant conditions, 3 validated against literature (their own fitting data), 2 extrapolated, 3 catalysts unmodelled; no rate law is validated at 20 bar.

**Conclusion.** The temperature ordering exists in the models but rests on rate laws extrapolated to 20 bar.

**Rule and outcome.** Validity rule (methodology v2: no model is called validated outside its checked range): the temperature ordering can support or contradict the row only if every rate law used is in the class validated_at_relevant_conditions (kinetics/validity_classification.json); otherwise INCONCLUSIVE.

**Envelope.** 20 bar, X 0.95, 100 kg per 100 kmol/h NH3; equilibrium limits X 0.95 to about 485 degC and above

**Assumptions.**

- isothermal PFR, effectiveness factor 1, no pressure drop
- 1 atm (Takahashi, Lucentini) or 1-10 bar (Kum) laws used at 20 bar
- AmCraX reversibility factor for Takahashi and Lucentini (not in the papers)

**Uncertainty.** no law validated at 20 bar; Ni/MgO and Ru/MgO laws fail their literature comparison at 1 atm (KIN-NI-PRED, KIN-RU-PRED)

**Validation status.** Lucentini Table 1 points reproduced (consistency, not independent); Takahashi predictions carried over as failures; Aspen native laws vs spec points (kinetics.json, aspen_kinetic.json). Validation status of the underlying models: results/research/validation/aspen_kinetic.json: 163 pass, 5 fail, 22 informational (failures: cat_nire_ceo2_5ni1ru_lucentini_lhhw_below_equilibrium, cat_nire_ceo2_2p5ni0p5ru_lucentini_lhhw_below_equilibrium, cat_ru_takahashi_microkinetic_below_equilibrium, k1p2_nire_ceo2_5ni1ru_lucentini_lhhw_below_equilibrium_partialpres, k1p2_nire_ceo2_2p5ni0p5ru_lucentini_lhhw_below_equilibrium_partialpres); results/research/validation/kinetics.json: 10 pass, 2 fail, 7 informational (failures: EXISTING-KIN-NI-PRED, EXISTING-KIN-RU-PRED).

**Evidence kinds.** python vs aspen, literature comparison.

**Key uncertainty (what would change the verdict).** Outside this envelope the verdict may change: 20 bar, X 0.95, 100 kg per 100 kmol/h NH3; equilibrium limits X 0.95 to about 485 degC and above

**Uncertainty range.** no law validated at 20 bar; Ni/MgO and Ru/MgO laws fail their literature comparison at 1 atm (KIN-NI-PRED, KIN-RU-PRED)

- Singapore scenario: Jurong Island cracker; 100 kmol/h liquid NH3 (0.2 mol% H2O), 20 bar, 95 % NH3 conversion for every catalyst, PSA recovery 0.85; grey NH3 price scenario; amcrax.economics.singapore.evaluate, grey 450 USD/t, catalyst W*price/lifetime (2 yr); Phase 2: catalyst prices are the DERIVED central scenario prices of research/data/catalyst_prices.json (Cho TEA prices only in the Cho reconstruction and the labelled published-TEA sensitivity case); full catalyst economics in results/research/catalyst_economics/.
- Aspen model: Aspen standalone RPLUG operating-point checks (cs_OP_* cases) confirm the Python temperatures.
- Python model: amcrax.kinetics laws in the isothermal PFR (study_temperature_for_target_conversion).
- Case ids: cs_OP_kum_T499_P20_W100, cs_OP_tru_T522_P20_W100, cs_OP_luc5_T572_P20_W100, cs_OP_luc25_T576_P20_W100, cs_OP_tni_T594_P20_W100
- Validation: Lucentini Table 1 points reproduced (consistency, not independent); Takahashi predictions carried over as failures; Aspen native laws vs spec points (kinetics.json, aspen_kinetic.json). Validation status of the underlying models: results/research/validation/aspen_kinetic.json: 163 pass, 5 fail, 22 informational (failures: cat_nire_ceo2_5ni1ru_lucentini_lhhw_below_equilibrium, cat_nire_ceo2_2p5ni0p5ru_lucentini_lhhw_below_equilibrium, cat_ru_takahashi_microkinetic_below_equilibrium, k1p2_nire_ceo2_5ni1ru_lucentini_lhhw_below_equilibrium_partialpres, k1p2_nire_ceo2_2p5ni0p5ru_lucentini_lhhw_below_equilibrium_partialpres); results/research/validation/kinetics.json: 10 pass, 2 fail, 7 informational (failures: EXISTING-KIN-NI-PRED, EXISTING-KIN-RU-PRED).
- Input assumptions: Effectiveness factor 1, no pressure drop (assumptions); catalyst masses are lower bounds.; Takahashi Ni/MgO and Ru/MgO rows use a fitted LHHW approximation (python fit, valid at 20 bar only; rate error RMS 12 %, max about 50 %) and are extrapolations from 1 atm data.
- Literature: `kum2026heatintegrated` (Kum et al. 2026: Ru/Al2O3 Temkin-Pyzhev law); `takahashi2016kinetic` (Takahashi & Fujitani 2016: Ni/MgO and Ru/MgO microkinetics); `lucentini2021nirukinetic` (Lucentini et al. 2021: Ni-Ru/CeO2 LHHW (Table 3)); `lucentini2019ceo2` (Lucentini et al. 2019: Ru/CeO2 vs Ni/CeO2 conversion at atmospheric pressure (no rate law)); `sayas2020high` (Sayas et al. 2020: Ru-K/CaO (full text not obtained; values unverified))
- Limitations: All 20 bar operating points are outside the fitted ranges (within_fitted_range false).; Ni/CeO2, Ru/CeO2 and Ru-K/CaO not modelled: no usable rate law.; Takahashi Ni and Ru predictions fail the existing validation (EXISTING-KIN-NI-PRED, EXISTING-KIN-RU-PRED).; All rate laws are extrapolated to 20 bar from their fit pressure (1 atm; Kum: 10 bar); the Takahashi laws are evaluated on a mole-fraction basis and the Lucentini laws on concentrations; the Ni/MgO law fails its own validation (EXISTING-KIN-NI-PRED). No catalyst ranking at 20 bar is a property of the catalysts.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| T for 95 % at 20 bar, 100 kg, Ru/Al2O3 | 498.3 | degC | python | `results/research/kinetics/study_temperature_for_target_conversion.json` | `rows/[catalyst_id=ru_kum_temkin_pyzhev;P_bar=20;W_cat_kg=100;X_target=0.95]/T_required_C` |
| T for 95 % at 20 bar, 100 kg, Ru/MgO | 521.7 | degC | python | `results/research/kinetics/study_temperature_for_target_conversion.json` | `rows/[catalyst_id=ru_takahashi_microkinetic;P_bar=20;W_cat_kg=100;X_target=0.95]/T_required_C` |
| T for 95 % at 20 bar, 100 kg, 5Ni1Ru/CeO2 | 571.6 | degC | python | `results/research/kinetics/study_temperature_for_target_conversion.json` | `rows/[catalyst_id=nire_ceo2_5ni1ru_lucentini_lhhw;P_bar=20;W_cat_kg=100;X_target=0.95]/T_required_C` |
| T for 95 % at 20 bar, 100 kg, 2.5Ni0.5Ru/CeO2 | 575.8 | degC | python | `results/research/kinetics/study_temperature_for_target_conversion.json` | `rows/[catalyst_id=nire_ceo2_2p5ni0p5ru_lucentini_lhhw;P_bar=20;W_cat_kg=100;X_target=0.95]/T_required_C` |
| T for 95 % at 20 bar, 100 kg, Ni/MgO | 593.3 | degC | python | `results/research/kinetics/study_temperature_for_target_conversion.json` | `rows/[catalyst_id=ni_takahashi_microkinetic;P_bar=20;W_cat_kg=100;X_target=0.95]/T_required_C` |
| T for 99 % at 20 bar, any catalyst (equilibrium minimum) | 684.8 | degC | python | `results/research/kinetics/study_temperature_for_target_conversion.json` | `rows/[catalyst_id=ni_takahashi_microkinetic;P_bar=20;W_cat_kg=100;X_target=0.99]/T_equilibrium_min_C` |
| T for 99 % at 1 atm, 100 kg, Ru/MgO (within fitted range) | 525.5 | degC | python | `results/research/kinetics/study_temperature_for_target_conversion.json` | `rows/[catalyst_id=ru_takahashi_microkinetic;P_bar=1.01325;W_cat_kg=100;X_target=0.99]/T_required_C` |
| T for 99 % at 1 atm, 100 kg, Ni/MgO (within fitted range) | 607.4 | degC | python | `results/research/kinetics/study_temperature_for_target_conversion.json` | `rows/[catalyst_id=ni_takahashi_microkinetic;P_bar=1.01325;W_cat_kg=100;X_target=0.99]/T_required_C` |
| Aspen operating temperature for X 0.95 at 100 kg, Ru/Al2O3 | 499 | degC | aspen | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-b/numbers/aspen_T_op_100kg_C/Ru~1Al2O3` |
| Aspen operating temperature for X 0.95 at 100 kg, Ru/MgO | 522 | degC | aspen | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-b/numbers/aspen_T_op_100kg_C/Ru~1MgO` |
| Aspen operating temperature for X 0.95 at 100 kg, 5Ni1Ru/CeO2 | 572 | degC | aspen | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-b/numbers/aspen_T_op_100kg_C/5Ni1Ru~1CeO2` |
| Aspen operating temperature for X 0.95 at 100 kg, 2.5Ni0.5Ru/CeO2 | 576 | degC | aspen | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-b/numbers/aspen_T_op_100kg_C/2.5Ni0.5Ru~1CeO2` |
| Aspen operating temperature for X 0.95 at 100 kg, Ni/MgO | 594 | degC | aspen | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-b/numbers/aspen_T_op_100kg_C/Ni~1MgO` |
| rate laws validated at relevant conditions | 0 | count | literature | `results/research/kinetics/validity_classification.json` | `counts/validated_at_relevant_conditions` |
| rate laws validated against literature (own fitting data) | 3 | count | literature | `results/research/kinetics/validity_classification.json` | `counts/validated_against_literature` |
| rate laws extrapolated | 2 | count | literature | `results/research/kinetics/validity_classification.json` | `counts/extrapolated` |
| catalysts without a rate law | 3 | count | literature | `results/research/kinetics/validity_classification.json` | `counts/unmodelled` |

Figures: `results/figures/research/kinetics_conversion_vs_T.png`, `results/figures/research/aspen_kinetic_conversion_vs_T.png`
Aspen screenshots: `docs/images/aspen_evidence/cs_OP_tni_T594_P20_W100__02_reactions_kinetic.png`, `docs/images/aspen_evidence/cs_OP_tni_T594_P20_W100__03_reactions_kinetic_tab.png`
Data: `results/research/aspen_kinetic/catalyst_standalone_runs.csv`, `results/research/catalyst_economics/catalyst_economics.json`, `results/research/kinetics/study_temperature_for_target_conversion.csv`, `results/research/kinetics/study_temperature_for_target_conversion.json`, `results/research/kinetics/validity_classification.json`

### H3-d: SUPPORTED

Role: primary (H3-H). Version 1 verdict: SUPPORTED.

**Sub-claim.** Effective heat integration reduces energy use (and cost) of the cracker, and matters more than the catalyst's temperature.

**Numerical conclusions.**

- Aspen first-law heat deficit 1385 kW without and 773 kW with heat integration (-44 %).
- That reduction (612 kW) is larger than the largest equal-conversion catalyst-temperature saving (25.1 kW).
- Gross fuel saving 0.214 USD/kg; net 0.067 to 0.095 USD/kg after the exchanger cost.

**Conclusion.** Heat integration reduces energy use, by far more than the catalyst temperature does; the net cost benefit is positive on the reference basis but depends on an unsourced heat-transfer coefficient.

**Rule and outcome.** Energy rule (methodology v2): SUPPORTED if heat integration lowers the Aspen first-law heat deficit by more than the Python against Aspen fired-duty offset (15.2 kW) and by more than the largest equal-conversion catalyst-temperature saving; otherwise INCONCLUSIVE. The cost side depends on the overall heat-transfer coefficient, for which no value at 20 bar is sourced: it is reported in the envelope and threshold and does not vote.

**Envelope.** 20 bar, 499-625 degC reactor, FEHE hot-end approach 20-200 K (python), U >= break-even U Cost: the net saving is negative only below the break-even U, for NH3 near the low end of the price range or a high capital recovery factor.

**Threshold.** overall heat-transfer coefficient at which the exchanger cost equals the fuel saving: 7.677, 11.305. Sourced: none sourced. Comparison: "no sourced U at 20 bar; typical ranges at 1 bar straddle the threshold".

**Assumptions.**

- U typical-range cases (VDI Heat Atlas C3; central derived)
- Turton 2018 module costing, SS/SS, 19.5 barg, CEPCI 797.9
- TCI-equivalent = bare module x 1.4336 (reference indirect factor, conservative)
- fuel saving on the unified reference basis (first-law deficit, supplementary NH3 at 450 USD/t)
- reference CAPEX does not change between HI on and off; exchanger treated as incremental

**Uncertainty.** U 10-500 W/(m2 K), NH3 300-1000 USD/t, CRF 0.094-0.199, CEPCI 720-800, material CS/CS to SS/SS, Towler correlation, F=1 vs multi-shell

**Validation status.** Pinch baseline reproduced (HCAT-PINCH-BASELINE); Python vs Aspen external heating within tolerance, FEHE recovered duty outside tolerance (HCAT-ASPY-*-HI-heat). Validation status of the underlying models: results/research/validation/aspen_kinetic.json: 163 pass, 5 fail, 22 informational (failures: cat_nire_ceo2_5ni1ru_lucentini_lhhw_below_equilibrium, cat_nire_ceo2_2p5ni0p5ru_lucentini_lhhw_below_equilibrium, cat_ru_takahashi_microkinetic_below_equilibrium, k1p2_nire_ceo2_5ni1ru_lucentini_lhhw_below_equilibrium_partialpres, k1p2_nire_ceo2_2p5ni0p5ru_lucentini_lhhw_below_equilibrium_partialpres); results/research/validation/catalyst_comparison.json: 66 pass, 5 fail, 4 informational (failures: HCAT-ASPY-Ru/Al2O3-HI-heat, HCAT-ASPY-5Ni1Ru/CeO2-HI-heat, HCAT-ASPY-2.5Ni0.5Ru/CeO2-HI-heat, HCAT-ASPY-Ni/MgO-HI-heat, HCAT-ASPY-Ru/MgO-HI-heat); results/research/validation/economics.json: 9 pass, 0 fail, 6 informational; results/research/validation/heat_exchanger.json: 24 pass, 0 fail, 13 informational.

**Evidence kinds.** python vs aspen, numerical verification, literature comparison.

**Key uncertainty (what would change the verdict).** Outside this envelope the verdict may change: 20 bar, 499-625 degC reactor, FEHE hot-end approach 20-200 K (python), U >= break-even U Cost: the net saving is negative only below the break-even U, for NH3 near the low end of the price range or a high capital recovery factor.

**Uncertainty range.** U 10-500 W/(m2 K), NH3 300-1000 USD/t, CRF 0.094-0.199, CEPCI 720-800, material CS/CS to SS/SS, Towler correlation, F=1 vs multi-shell

- Singapore scenario: Jurong Island cracker; 100 kmol/h liquid NH3 (0.2 mol% H2O), 20 bar, 95 % NH3 conversion for every catalyst, PSA recovery 0.85; grey NH3 price scenario; amcrax.economics.singapore.evaluate, grey 450 USD/t, catalyst W*price/lifetime (2 yr); Phase 2: catalyst prices are the DERIVED central scenario prices of research/data/catalyst_prices.json (Cho TEA prices only in the Cho reconstruction and the labelled published-TEA sensitivity case); full catalyst economics in results/research/catalyst_economics/.
- Aspen model: Aspen Plus V15 integrated flowsheets with and without FEHE (ci_* cases) and the stored RGibbs baseline (rgibbs_baseline_600C).
- Python model: amcrax.heat_integration pinch analysis (catalyst_pinch_dTmin.csv); amcrax.economics.singapore tornado.
- Case ids: ci_kum_T499_P20_W100_hi, ci_kum_T499_P20_W100_nohi, ci_tru_T522_P20_W100_hi, ci_tru_T522_P20_W100_nohi, ci_luc5_T572_P20_W100_hi, ci_luc5_T572_P20_W100_nohi, ci_luc25_T576_P20_W100_hi, ci_luc25_T576_P20_W100_nohi, ci_tni_T594_P20_W100_hi, ci_tni_T594_P20_W100_nohi, baseline (stored Aspen), baseline_no_hi (stored Aspen)
- Validation: Pinch baseline reproduced (HCAT-PINCH-BASELINE); Python vs Aspen external heating within tolerance, FEHE recovered duty outside tolerance (HCAT-ASPY-*-HI-heat). Validation status of the underlying models: results/research/validation/aspen_kinetic.json: 163 pass, 5 fail, 22 informational (failures: cat_nire_ceo2_5ni1ru_lucentini_lhhw_below_equilibrium, cat_nire_ceo2_2p5ni0p5ru_lucentini_lhhw_below_equilibrium, cat_ru_takahashi_microkinetic_below_equilibrium, k1p2_nire_ceo2_5ni1ru_lucentini_lhhw_below_equilibrium_partialpres, k1p2_nire_ceo2_2p5ni0p5ru_lucentini_lhhw_below_equilibrium_partialpres); results/research/validation/catalyst_comparison.json: 66 pass, 5 fail, 4 informational (failures: HCAT-ASPY-Ru/Al2O3-HI-heat, HCAT-ASPY-5Ni1Ru/CeO2-HI-heat, HCAT-ASPY-2.5Ni0.5Ru/CeO2-HI-heat, HCAT-ASPY-Ni/MgO-HI-heat, HCAT-ASPY-Ru/MgO-HI-heat); results/research/validation/economics.json: 9 pass, 0 fail, 6 informational; results/research/validation/heat_exchanger.json: 24 pass, 0 fail, 13 informational.
- Input assumptions: Heat-exchanger capital does not respond to heat integration (no sourced cost per area): HI acts only through fuel and cooling.
- Literature: `linnhoff1983pinch` (Linnhoff & Hindmarsh 1983: pinch method)
- Limitations: Python FEHE duty above Aspen beyond the validation tolerance (HCAT-ASPY-*-HI-heat failures).; All rate laws are extrapolated to 20 bar from their fit pressure (1 atm; Kum: 10 bar); the Takahashi laws are evaluated on a mole-fraction basis and the Lucentini laws on concentrations; the Ni/MgO law fails its own validation (EXISTING-KIN-NI-PRED). No catalyst ranking at 20 bar is a property of the catalysts.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| recovered heat with HI, Ru/Al2O3 (FEHE) | 469.1 | kW | aspen | `results/research/aspen_kinetic/catalyst_comparison.json` | `rows/[catalyst_id=ru_kum_temkin_pyzhev]/integrated_hi_recovered_heat_kW` |
| recovered heat with HI, Ni/MgO (FEHE) | 603.5 | kW | aspen | `results/research/aspen_kinetic/catalyst_comparison.json` | `rows/[catalyst_id=ni_takahashi_microkinetic]/integrated_hi_recovered_heat_kW` |
| baseline external heating with HI (RGibbs, 600 degC) | 2293.1 | kW | aspen | `results/research/aspen_kinetic/catalyst_comparison.json` | `rgibbs_baseline_600C/heat_integration/total_external_heating_kW` |
| baseline external heating without HI | 2905.3 | kW | aspen | `results/research/aspen_kinetic/catalyst_comparison.json` | `rgibbs_baseline_600C/no_heat_integration/total_external_heating_kW` |
| LCOH reduction from heat integration (tornado) | 0.2138 | USD/kg H2 | python | `results/research/singapore/tornado.json` | `bars/[parameter=heat_integration]/swing` |
| first-law heat deficit, heat integration on (Aspen) | 772.9 | kW | aspen | `results/research/heat_exchanger/heat_exchanger_study.json` | `row_evidence/H3-d/numbers/energy_first_law_deficit_kW_hi_vs_nohi/0` |
| first-law heat deficit, heat integration off (Aspen) | 1385.1 | kW | aspen | `results/research/heat_exchanger/heat_exchanger_study.json` | `row_evidence/H3-d/numbers/energy_first_law_deficit_kW_hi_vs_nohi/1` |
| reduction of the first-law deficit | 0.442 | fraction | aspen | `results/research/heat_exchanger/heat_exchanger_study.json` | `row_evidence/H3-d/numbers/energy_reduction_first_law` |
| gross fuel saving | 0.2138 | USD/kg H2 | python | `results/research/heat_exchanger/heat_exchanger_study.json` | `row_evidence/H3-d/numbers/baseline_fuel_saving_USD_per_kg` |
| net saving after exchanger cost, low U | 0.06684 | USD/kg H2 | python | `results/research/heat_exchanger/heat_exchanger_study.json` | `row_evidence/H3-d/numbers/baseline_net_USD_per_kg/low` |
| net saving after exchanger cost, high U | 0.09537 | USD/kg H2 | python | `results/research/heat_exchanger/heat_exchanger_study.json` | `row_evidence/H3-d/numbers/baseline_net_USD_per_kg/high` |

Figures: `results/figures/research/catalyst_heat_duty.png`, `results/figures/research/singapore_tornado.png`
Aspen screenshots: `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__01_flowsheet.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__02_reactions_kinetic.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__03_reactions_kinetic_tab.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__05_reactor_configuration.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__06_reactor_catalyst.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__08_reactor_results.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__09_reactor_profiles.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__10_run_status.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__11_components.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__12_property_method.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__13_stream_results.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__14_psa_block.png`, `docs/images/aspen_evidence/cs_OP_tni_T594_P20_W100__02_reactions_kinetic.png`, `docs/images/aspen_evidence/cs_OP_tni_T594_P20_W100__03_reactions_kinetic_tab.png`
Data: `results/research/aspen_kinetic/catalyst_comparison.json`, `results/research/aspen_kinetic/catalyst_integrated.csv`, `results/research/catalyst_comparison/catalyst_pinch_dTmin.csv`, `results/research/heat_exchanger/heat_exchanger_study.json`, `results/research/singapore/tornado.json`

### H3-c: INCONCLUSIVE

Role: primary (H3-K). Version 1 verdict: INCONCLUSIVE.

**Sub-claim.** The energy saved by a low-temperature, high-activity catalyst can outweigh its higher catalyst cost.

**Numerical conclusions.**

- At equal conversion and derived prices every low-temperature catalyst is dearer than Ni/MgO: Ru/Al2O3 +0.081, Ru/MgO +0.043, 5Ni1Ru/CeO2 +0.011, 2.5Ni0.5Ru/CeO2 +0.005 USD/kg H2 (resolution 0.006).
- Break-even catalyst prices Ru/Al2O3 1506, Ru/MgO 1297, 5Ni1Ru/CeO2 177, 2.5Ni0.5Ru/CeO2 151 USD/kg against derived central prices 4791, 3006, 628, 330 USD/kg.
- Ni temperature threshold 540 to 676 degC: sourced Ni designs (736, 760 degC) are above it, the AmCraX Ni optimum (537 degC, extrapolated law) is below it.

**Conclusion.** At ruthenium prices derived from metal content, the low-temperature catalysts do not pay at equal conversion (against the essay). Against sourced Ni design temperatures the low-temperature designs win; against the AmCraX Ni optimum they do not.

**Rule and outcome.** Cost and threshold rule (methodology v2): SUPPORTED if at least one low-temperature catalyst is cheaper than Ni/MgO by more than the Python against Aspen resolution at equal conversion and both the sourced Ni design temperatures and the AmCraX Ni optimum lie above the Ni temperature threshold; CONTRADICTED if every low-temperature catalyst is dearer by more than the resolution and both lie below the threshold; otherwise INCONCLUSIVE (sourced values and model straddle). Here: cheaper at equal conversion False, dearer for all beyond resolution False, sourced Ni temperatures above threshold True, AmCraX Ni optimum above threshold False.

**Envelope.** 20 bar, X 0.95, PSA 0.85, grey 450 USD/t base; Python flowsheet (cost-optimal) or Aspen duties (fixed 100 kg)

**Threshold.** Ni design temperature above which a low-temperature catalyst design is cheaper: 669.0, 670.2, 675.5, 675.6, 637.5, 639.8, 540, 539.6. Sourced: sourced Ni design temperature, Cho et al. 2026 735.5, sourced Ni design temperature, Mehr et al. 2026 (outlet) 760. Comparison: "sourced above, AmCraX Ni optimum below".

**Assumptions.**

- catalyst prices DERIVED from metal content + 32.2 USD/kg non-metal part (no quotation exists)
- lifetime 2 yr (Cho, assumed), varied 1-5 yr
- FEHE U central 72.5 W/(m2 K) (derived), varied 35-150
- reactor CAPEX by NH3 feed (frozen basis) or by catalyst mass (sensitivity)
- no Ru recovery credit (no sourced refining charge or recovery fraction)

**Uncertainty.** Ru price (USGS 2025 average to Nov 2026 JM spot), lifetime 1-5 yr, NH3 300-1000 USD/t, fuel price, natural-gas heat, electricity 0.084-0.222 USD/kWh, discount 0.085-0.10, 7000-8000 h, U 35-150, reactor cost driver, rates /5. The FEHE cost is a step function of temperature (4 -> 5 shells in series between 537 and 538 degC at U central, +0.235 MUSD TCI, about +0.023 USD/kg): in the 'exchanger' mode it pins several optima at 537 degC and is of the same size as the catalyst differences; the 'reference' mode (no exchanger response) is reported beside it.

**Validation status.** Analytic catalyst-cost addition matches full evaluate(); T_opt interior to the grid; mass and energy closure (catalyst_comparison.json). Validation status of the underlying models: results/research/validation/catalyst_comparison.json: 66 pass, 5 fail, 4 informational (failures: HCAT-ASPY-Ru/Al2O3-HI-heat, HCAT-ASPY-5Ni1Ru/CeO2-HI-heat, HCAT-ASPY-2.5Ni0.5Ru/CeO2-HI-heat, HCAT-ASPY-Ni/MgO-HI-heat, HCAT-ASPY-Ru/MgO-HI-heat); results/research/validation/catalyst_economics.json: 141 pass, 0 fail, 1 informational; results/research/validation/kinetics.json: 10 pass, 2 fail, 7 informational (failures: EXISTING-KIN-NI-PRED, EXISTING-KIN-RU-PRED).

**Evidence kinds.** numerical verification, python vs aspen, literature comparison.

**Key uncertainty (what would change the verdict).** Outside this envelope the verdict may change: 20 bar, X 0.95, PSA 0.85, grey 450 USD/t base; Python flowsheet (cost-optimal) or Aspen duties (fixed 100 kg)

**Uncertainty range.** Ru price (USGS 2025 average to Nov 2026 JM spot), lifetime 1-5 yr, NH3 300-1000 USD/t, fuel price, natural-gas heat, electricity 0.084-0.222 USD/kWh, discount 0.085-0.10, 7000-8000 h, U 35-150, reactor cost driver, rates /5. The FEHE cost is a step function of temperature (4 -> 5 shells in series between 537 and 538 degC at U central, +0.235 MUSD TCI, about +0.023 USD/kg): in the 'exchanger' mode it pins several optima at 537 degC and is of the same size as the catalyst differences; the 'reference' mode (no exchanger response) is reported beside it.

- Singapore scenario: Jurong Island cracker; 100 kmol/h liquid NH3 (0.2 mol% H2O), 20 bar, 95 % NH3 conversion for every catalyst, PSA recovery 0.85; grey NH3 price scenario; amcrax.economics.singapore.evaluate, grey 450 USD/t, catalyst W*price/lifetime (2 yr); Phase 2: catalyst prices are the DERIVED central scenario prices of research/data/catalyst_prices.json (Cho TEA prices only in the Cho reconstruction and the labelled published-TEA sensitivity case); full catalyst economics in results/research/catalyst_economics/.
- Aspen model: Aspen duties for the fixed-inventory comparison (ci_* cases); no Aspen run at the Python cost-optimal temperatures (those rows are Python only).
- Python model: amcrax.research.catalyst_comparison: W(T) from PFR kinetics, T_opt = argmin LCOH, heat_integration configuration (c), amcrax.economics.singapore.evaluate.
- Case ids: ci_kum_T499_P20_W100_hi, ci_kum_T499_P20_W100_nohi, ci_tru_T522_P20_W100_hi, ci_tru_T522_P20_W100_nohi, ci_luc5_T572_P20_W100_hi, ci_luc5_T572_P20_W100_nohi, ci_luc25_T576_P20_W100_hi, ci_luc25_T576_P20_W100_nohi, ci_tni_T594_P20_W100_hi, ci_tni_T594_P20_W100_nohi
- Validation: Analytic catalyst-cost addition matches full evaluate(); T_opt interior to the grid; mass and energy closure (catalyst_comparison.json). Validation status of the underlying models: results/research/validation/catalyst_comparison.json: 66 pass, 5 fail, 4 informational (failures: HCAT-ASPY-Ru/Al2O3-HI-heat, HCAT-ASPY-5Ni1Ru/CeO2-HI-heat, HCAT-ASPY-2.5Ni0.5Ru/CeO2-HI-heat, HCAT-ASPY-Ni/MgO-HI-heat, HCAT-ASPY-Ru/MgO-HI-heat); results/research/validation/catalyst_economics.json: 141 pass, 0 fail, 1 informational; results/research/validation/kinetics.json: 10 pass, 2 fail, 7 informational (failures: EXISTING-KIN-NI-PRED, EXISTING-KIN-RU-PRED).
- Input assumptions: Catalyst prices: Cho Ni 33.4 and Ru 542 USD/kg used as proxies, 2-year life (assumption); no sourced NiRu/CeO2 price.; CAPEX does not respond to reactor volume, exchanger area or temperature (volume scaling is a sensitivity only).; Furnace efficiency and thermal-loss allowance as in H3-a (assumptions).
- Literature: `kum2026heatintegrated` (Kum et al. 2026: Ru/Al2O3 Temkin-Pyzhev law); `takahashi2016kinetic` (Takahashi & Fujitani 2016: Ni/MgO and Ru/MgO microkinetics); `lucentini2021nirukinetic` (Lucentini et al. 2021: Ni-Ru/CeO2 LHHW (Table 3)); `cho2026nickel` (Cho et al. 2026: Ni and Ru catalyst prices)
- Limitations: Ni/MgO law fails its prediction check (EXISTING-KIN-NI-PRED).; No sourced price for NiRu/CeO2.; N2O not quantified.; All rate laws are extrapolated to 20 bar from their fit pressure (1 atm; Kum: 10 bar); the Takahashi laws are evaluated on a mole-fraction basis and the Lucentini laws on concentrations; the Ni/MgO law fails its own validation (EXISTING-KIN-NI-PRED). No catalyst ranking at 20 bar is a property of the catalysts.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| LCOH at cost-optimal T, Ru/Al2O3, HI | 4.092 | USD/kg H2 | python | `results/research/catalyst_comparison/catalyst_comparison.json` | `findings/cost_optimal_python/Ru~1Al2O3/HI/lcoh_USD_per_kg` |
| LCOH at cost-optimal T, Ni/MgO, HI | 4.080 | USD/kg H2 | python | `results/research/catalyst_comparison/catalyst_comparison.json` | `findings/cost_optimal_python/Ni~1MgO/HI/lcoh_USD_per_kg` |
| LCOH Ru/Al2O3 minus Ni/MgO, fixed 100 kg, HI (Aspen duties) | 0.1191 | USD/kg H2 | python | `results/research/catalyst_comparison/catalyst_comparison.json` | `findings/fixed_inventory_100kg_aspen/Ru_Al2O3_minus_Ni_lcoh_HI` |
| LCOH Ru/Al2O3 minus Ni/MgO, fixed 100 kg, no HI (Aspen duties) | 0.06343 | USD/kg H2 | python | `results/research/catalyst_comparison/catalyst_comparison.json` | `findings/fixed_inventory_100kg_aspen/Ru_Al2O3_minus_Ni_lcoh_noHI` |
| largest \|best low-T catalyst minus Ni\| over 32 sensitivity cases | 0.01899 | USD/kg H2 | python | `results/research/catalyst_comparison/catalyst_comparison.json` | `findings/ranking_robustness/max_abs_best_low_T_minus_Ni_USD_per_kg` |
| cases with unchanged best catalyst | 30 | count | python | `results/research/catalyst_comparison/catalyst_comparison.json` | `findings/ranking_robustness/n_same_best_as_base` |
| sensitivity cases | 32 | count | python | `results/research/catalyst_comparison/catalyst_comparison.json` | `findings/ranking_robustness/n_cases` |
| break-even Ru/Al2O3 price vs Ni/MgO at its cost optimum | 531.4 | USD/kg | python | `results/research/catalyst_comparison/catalyst_comparison.json` | `findings/breakeven_price/[catalyst=Ru~1Al2O3 (Kum);reference=Ni~1MgO (Takahashi) at its cost-optimal T]/breakeven_price_USD_per_kg` |
| break-even Ru/Al2O3 price vs Ni/MgO fixed at 735 degC | 7400.4 | USD/kg | python | `results/research/catalyst_comparison/catalyst_comparison.json` | `findings/breakeven_price/[catalyst=Ru~1Al2O3 (Kum);reference=Ni~1MgO fixed at 735 degC]/breakeven_price_USD_per_kg` |
| Monte Carlo LCOH p95, grey (economic uncertainty band, upper) | 4.882 | USD/kg H2 | python | `results/research/singapore/monte_carlo.json` | `results/grey/lcoh_p95` |
| Monte Carlo LCOH p5, grey (economic uncertainty band, lower) | 3.253 | USD/kg H2 | python | `results/research/singapore/monte_carlo.json` | `results/grey/lcoh_p5` |
| Ni catalyst price (Cho published TEA, historical case) | 33.400 | USD/kg | assumption | `results/research/catalyst_comparison/assumptions.json` | `[name=catalyst_price_Ni_published_TEA]/value` |
| Ru catalyst price (Cho published TEA, historical case, below the Ru metal value) | 542 | USD/kg | assumption | `results/research/catalyst_comparison/assumptions.json` | `[name=catalyst_price_Ru_published_TEA]/value` |
| catalyst lifetime | 2 | yr | assumption | `results/research/catalyst_comparison/assumptions.json` | `[name=catalyst_lifetime]/value` |
| Python against Aspen LCOH resolution | 0.006022 | USD/kg H2 | python | `results/research/catalyst_economics/catalyst_economics.json` | `resolution/max_abs_python_minus_aspen_lcoh_USD_per_kg` |
| net LCOH change choosing Ru/Al2O3 over Ni/MgO, equal conversion, derived central price | 0.08128 | USD/kg H2 | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-c/numbers/fixed_inventory_aspen_HI_exchanger/Ru~1Al2O3/net_lcoh_delta_USD_per_kg` |
| net LCOH change choosing Ru/MgO over Ni/MgO, equal conversion, derived central price | 0.04344 | USD/kg H2 | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-c/numbers/fixed_inventory_aspen_HI_exchanger/Ru~1MgO/net_lcoh_delta_USD_per_kg` |
| net LCOH change choosing 5Ni1Ru/CeO2 over Ni/MgO, equal conversion, derived central price | 0.01143 | USD/kg H2 | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-c/numbers/fixed_inventory_aspen_HI_exchanger/5Ni1Ru~1CeO2/net_lcoh_delta_USD_per_kg` |
| net LCOH change choosing 2.5Ni0.5Ru/CeO2 over Ni/MgO, equal conversion, derived central price | 0.004568 | USD/kg H2 | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-c/numbers/fixed_inventory_aspen_HI_exchanger/2.5Ni0.5Ru~1CeO2/net_lcoh_delta_USD_per_kg` |
| break-even catalyst price, Ru/Al2O3 | 1505.9 | USD/kg | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-c/numbers/fixed_inventory_aspen_HI_exchanger/Ru~1Al2O3/breakeven_price_USD_per_kg` |
| break-even catalyst price, Ru/MgO | 1297.3 | USD/kg | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-c/numbers/fixed_inventory_aspen_HI_exchanger/Ru~1MgO/breakeven_price_USD_per_kg` |
| break-even catalyst price, 5Ni1Ru/CeO2 | 177.3 | USD/kg | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-c/numbers/fixed_inventory_aspen_HI_exchanger/5Ni1Ru~1CeO2/breakeven_price_USD_per_kg` |
| break-even catalyst price, 2.5Ni0.5Ru/CeO2 | 150.9 | USD/kg | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-c/numbers/fixed_inventory_aspen_HI_exchanger/2.5Ni0.5Ru~1CeO2/breakeven_price_USD_per_kg` |
| derived central catalyst price, Ru/Al2O3 | 4790.5 | USD/kg | literature | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-c/numbers/fixed_inventory_aspen_HI_exchanger/Ru~1Al2O3/central_price_USD_per_kg` |
| derived central catalyst price, Ru/MgO | 3006.1 | USD/kg | literature | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-c/numbers/fixed_inventory_aspen_HI_exchanger/Ru~1MgO/central_price_USD_per_kg` |
| derived central catalyst price, 5Ni1Ru/CeO2 | 627.8 | USD/kg | literature | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-c/numbers/fixed_inventory_aspen_HI_exchanger/5Ni1Ru~1CeO2/central_price_USD_per_kg` |
| derived central catalyst price, 2.5Ni0.5Ru/CeO2 | 330.0 | USD/kg | literature | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-c/numbers/fixed_inventory_aspen_HI_exchanger/2.5Ni0.5Ru~1CeO2/central_price_USD_per_kg` |
| AmCraX Ni/MgO cost-optimal temperature (extrapolated law) | 537 | degC | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-c/numbers/ni_temperature_threshold/0/AmCraX_Ni_costopt_T_C_extrapolated` |

Figures: `results/figures/research/catalyst_breakeven_price.png`, `results/figures/research/catalyst_ranking_robustness.png`, `results/figures/research/catalyst_cost_breakdown.png`
Data: `results/research/catalyst_comparison/assumptions.json`, `results/research/catalyst_comparison/catalyst_breakeven_price.json`, `results/research/catalyst_comparison/catalyst_comparison.csv`, `results/research/catalyst_comparison/catalyst_comparison.json`, `results/research/catalyst_comparison/catalyst_design_curves.csv`, `results/research/catalyst_comparison/catalyst_ranking_robustness.json`, `results/research/catalyst_economics/catalyst_economics.json`, `results/research/singapore/monte_carlo.json`

### H3-e: INCONCLUSIVE

Role: secondary (H3-K). Version 1 verdict: INCONCLUSIVE.

**Sub-claim.** Cho et al. (2026): the Ru process at 567 degC needs no supplementary fuel while the Ni process at 736 degC burns supplementary NH3.

**Numerical conclusions.**

- Cho's pattern appears only for PSA recovery 0.7564 to 0.7813.

**Conclusion.** The fuel pattern reported by Cho et al. is reproduced only in a narrow band of PSA recovery.

**Rule and outcome.** Reproduction rule: Cho's pattern (Ru needs no supplementary fuel, Ni does) holds for PSA recoveries between the Ni and Ru thresholds. SUPPORTED if it holds over the whole checked recovery range; CONTRADICTED if the band is empty; otherwise INCONCLUSIVE. Secondary row: does not vote.

**Envelope.** X 0.97; Ni 735.52 degC / 24.34 bar; Ru 566.69 degC / 10 bar

**Threshold.** PSA recovery at which supplementary fuel becomes necessary: 0.7564, 0.7813. Sourced: none sourced. Comparison: "pattern only between the two thresholds".

**Assumptions.**

- Cho operating points rebuilt on AmCraX boundaries (no compression, recycle, TSA, expander)
- supplementary fuel needed when the temperature-feasible process heat import after tail-gas firing is > 0

**Uncertainty.** PSA recovery 0.70-0.95; boundary differences to Cho; Python only at Cho's points

**Validation status.** Cho REC-direction items recorded as informational (catalyst_comparison.json). Validation status of the underlying models: results/research/validation/catalyst_comparison.json: 66 pass, 5 fail, 4 informational (failures: HCAT-ASPY-Ru/Al2O3-HI-heat, HCAT-ASPY-5Ni1Ru/CeO2-HI-heat, HCAT-ASPY-2.5Ni0.5Ru/CeO2-HI-heat, HCAT-ASPY-Ni/MgO-HI-heat, HCAT-ASPY-Ru/MgO-HI-heat); results/research/validation/catalyst_economics.json: 141 pass, 0 fail, 1 informational.

**Evidence kinds.** numerical verification, literature comparison.

**Key uncertainty (what would change the verdict).** Outside this envelope the verdict may change: X 0.97; Ni 735.52 degC / 24.34 bar; Ru 566.69 degC / 10 bar

**Uncertainty range.** PSA recovery 0.70-0.95; boundary differences to Cho; Python only at Cho's points

- Singapore scenario: Cho's operating points rebuilt on AmCraX boundaries (conversion 0.97, Cho economic inputs).
- Aspen model: No Aspen run at Cho's operating points: Python only (heat balance calibrated against the Aspen ci_* cases).
- Python model: amcrax.research.catalyst_comparison Cho rebuild (catalyst_cho_comparison.json).
- Case ids: Ni_735.52C_24.34bar, RuAl2O3_566.69C_10bar
- Validation: Cho REC-direction items recorded as informational (catalyst_comparison.json). Validation status of the underlying models: results/research/validation/catalyst_comparison.json: 66 pass, 5 fail, 4 informational (failures: HCAT-ASPY-Ru/Al2O3-HI-heat, HCAT-ASPY-5Ni1Ru/CeO2-HI-heat, HCAT-ASPY-2.5Ni0.5Ru/CeO2-HI-heat, HCAT-ASPY-Ni/MgO-HI-heat, HCAT-ASPY-Ru/MgO-HI-heat); results/research/validation/catalyst_economics.json: 141 pass, 0 fail, 1 informational.
- Input assumptions: Proxy kinetics: Ni/MgO (Takahashi) and Ru/Al2O3 (Kum) instead of Cho's Collins Ni/Al2O3 and Sayas Ru-K/CaO (in an unavailable SI).; PSA recovery 0.85 (AmCraX) or 0.756 (Cho).
- Literature: `cho2026nickel` (Cho et al. 2026: Table 7 p. 13, pp. 14-15)
- Limitations: AmCraX has no product compression to 180 bar, no H2 recycle, no TSA, no expander, no NOx SCR cost.; Kinetics are proxies: Ni/MgO and Ru/Al2O3, Ru/MgO laws; Cho uses Ni/Al2O3 (Collins 1993) and Ru-K/CaO (Sayas 2020), both in an unavailable SI.; Cho optimises T, P and reactor jointly with the Aspen boiler; here T and P are fixed to Cho's optima.; Economic overrides: discount 8.5 %, electricity 0.084 USD/kWh, 25 yr (cho2026nickel Table 4); CAPEX from amcrax.economics.singapore (does not respond to T or P).; All rate laws are extrapolated to 20 bar from their fit pressure (1 atm; Kum: 10 bar); the Takahashi laws are evaluated on a mole-fraction basis and the Lucentini laws on concentrations; the Ni/MgO law fails its own validation (EXISTING-KIN-NI-PRED). No catalyst ranking at 20 bar is a property of the catalysts.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| Cho Ni design temperature | 735.5 | degC | literature | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `designs/[design=Ni_735.52C_24.34bar;psa_recovery=0.85;inventory_basis=kinetic_minimum]/T_C` |
| Cho Ru design temperature | 566.7 | degC | literature | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `designs/[design=RuAl2O3_566.69C_10bar;psa_recovery=0.85;inventory_basis=kinetic_minimum]/T_C` |
| conversion of the rebuilt designs | 0.97 | fraction | literature | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `designs/[design=RuAl2O3_566.69C_10bar;psa_recovery=0.85;inventory_basis=kinetic_minimum]/X` |
| supplementary NH3, Ni design, AmCraX PSA recovery | 161.1 | kg/h | python | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `summary/[psa_recovery=0.85;inventory_basis=kinetic_minimum]/Ni_supp_nh3_kg_h` |
| supplementary NH3, Ru design, AmCraX PSA recovery | 152.0 | kg/h | python | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `summary/[psa_recovery=0.85;inventory_basis=kinetic_minimum]/Ru_supp_nh3_kg_h` |
| Cho: Ru supplementary fuel | 0 | kmol/h | literature | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `summary/[psa_recovery=0.85;inventory_basis=kinetic_minimum]/cho_values/Ru_fuel_kmol_h` |
| Cho: Ni supplementary fuel | 1.736 | kmol/h | literature | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `summary/[psa_recovery=0.85;inventory_basis=kinetic_minimum]/cho_values/Ni_fuel_kmol_h` |
| PSA recovery above which Ni at Cho's point needs supplementary fuel | 0.7564 | fraction | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-e/numbers/psa_recovery_threshold_for_zero_supplementary_fuel/Ni_735.52C_24.34bar/psa_recovery_threshold` |
| PSA recovery above which Ru at Cho's point needs supplementary fuel | 0.7813 | fraction | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-e/numbers/psa_recovery_threshold_for_zero_supplementary_fuel/RuAl2O3_566.69C_10bar/psa_recovery_threshold` |
| Ni import at the lowest checked recovery | 0 | kW | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-e/numbers/psa_recovery_threshold_for_zero_supplementary_fuel/Ni_735.52C_24.34bar/import_kW_at_0.70` |
| Ru import at the highest checked recovery | 1564.0 | kW | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-e/numbers/psa_recovery_threshold_for_zero_supplementary_fuel/RuAl2O3_566.69C_10bar/import_kW_at_0.95` |

Data: `results/research/catalyst_comparison/catalyst_cho_comparison.csv`, `results/research/catalyst_comparison/catalyst_cho_comparison.json`, `results/research/catalyst_economics/catalyst_economics.json`

### H3-f: INCONCLUSIVE

Role: secondary (H3-K). Version 1 verdict: INCONCLUSIVE.

**Sub-claim.** Cho et al. (2026): the Ru process has a 7.0 % lower relative economic cost (REC) than the Ni process.

**Numerical conclusions.**

- Ru REC difference -16.2 to 1.6 % across 12 cases, against Cho's 7.0 %.

**Conclusion.** Cho's 7 % REC advantage of Ru is not reproduced; the sign depends on the price and inventory basis.

**Rule and outcome.** Reproduction rule (unchanged from version 1): INCONCLUSIVE if the sign of the REC difference changes across inventory, PSA and price cases; otherwise the sign decides. Secondary row: does not vote.

**Envelope.** Cho operating points on AmCraX boundaries

**Assumptions.**

- Cho economic basis (8.5 %, 0.084 USD/kWh, 25 yr)
- Ru/Al2O3 kinetics as a proxy for Cho's Ru-K/CaO
- Ru-K/CaO priced as 3 wt% Ru (derived) or at Cho's 542 USD/kg (published TEA, below the Ru floor)

**Uncertainty.** inventory basis (kinetic minimum or Cho GHSV 9000), PSA recovery, catalyst price case

**Validation status.** Cho's own REC difference (1.995 vs 1.856 USD/kg) reproduced as 7.0 % (economics.json); AmCraX rebuild informational. Validation status of the underlying models: results/research/validation/catalyst_comparison.json: 66 pass, 5 fail, 4 informational (failures: HCAT-ASPY-Ru/Al2O3-HI-heat, HCAT-ASPY-5Ni1Ru/CeO2-HI-heat, HCAT-ASPY-2.5Ni0.5Ru/CeO2-HI-heat, HCAT-ASPY-Ni/MgO-HI-heat, HCAT-ASPY-Ru/MgO-HI-heat); results/research/validation/catalyst_economics.json: 141 pass, 0 fail, 1 informational; results/research/validation/economics.json: 9 pass, 0 fail, 6 informational.

**Evidence kinds.** numerical verification, literature comparison.

**Key uncertainty (what would change the verdict).** Outside this envelope the verdict may change: Cho operating points on AmCraX boundaries

**Uncertainty range.** inventory basis (kinetic minimum or Cho GHSV 9000), PSA recovery, catalyst price case

- Singapore scenario: Cho's operating points rebuilt on AmCraX boundaries.
- Aspen model: No Aspen run at Cho's operating points: Python only.
- Python model: amcrax.research.catalyst_comparison Cho rebuild with amcrax.economics.singapore.
- Case ids: Ni_735.52C_24.34bar, RuAl2O3_566.69C_10bar
- Validation: Cho's own REC difference (1.995 vs 1.856 USD/kg) reproduced as 7.0 % (economics.json); AmCraX rebuild informational. Validation status of the underlying models: results/research/validation/catalyst_comparison.json: 66 pass, 5 fail, 4 informational (failures: HCAT-ASPY-Ru/Al2O3-HI-heat, HCAT-ASPY-5Ni1Ru/CeO2-HI-heat, HCAT-ASPY-2.5Ni0.5Ru/CeO2-HI-heat, HCAT-ASPY-Ni/MgO-HI-heat, HCAT-ASPY-Ru/MgO-HI-heat); results/research/validation/catalyst_economics.json: 141 pass, 0 fail, 1 informational; results/research/validation/economics.json: 9 pass, 0 fail, 6 informational.
- Input assumptions: Catalyst inventory basis (kinetic minimum vs Cho's space-velocity charge) and PSA recovery varied.; CAPEX does not respond to T or P.
- Literature: `cho2026nickel` (Cho et al. 2026: REC of the Ni and Ru processes, Fig. 8d)
- Limitations: AmCraX has no product compression to 180 bar, no H2 recycle, no TSA, no expander, no NOx SCR cost.; Kinetics are proxies: Ni/MgO and Ru/Al2O3, Ru/MgO laws; Cho uses Ni/Al2O3 (Collins 1993) and Ru-K/CaO (Sayas 2020), both in an unavailable SI.; Cho optimises T, P and reactor jointly with the Aspen boiler; here T and P are fixed to Cho's optima.; Economic overrides: discount 8.5 %, electricity 0.084 USD/kWh, 25 yr (cho2026nickel Table 4); CAPEX from amcrax.economics.singapore (does not respond to T or P).; All rate laws are extrapolated to 20 bar from their fit pressure (1 atm; Kum: 10 bar); the Takahashi laws are evaluated on a mole-fraction basis and the Lucentini laws on concentrations; the Ni/MgO law fails its own validation (EXISTING-KIN-NI-PRED). No catalyst ranking at 20 bar is a property of the catalysts.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| REC Ru lower by, kinetic-minimum mass, AmCraX PSA recovery | 1.554 | % | python | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `summary/[psa_recovery=0.85;inventory_basis=kinetic_minimum]/rec_Ru_lower_by_pct` |
| REC Ru lower by, Cho GHSV mass, AmCraX PSA recovery | -1.535 | % | python | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `summary/[psa_recovery=0.85;inventory_basis=cho_ghsv_9000]/rec_Ru_lower_by_pct` |
| REC Ru lower by, kinetic-minimum mass, Cho PSA recovery | -0.1895 | % | python | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `summary/[psa_recovery=0.756;inventory_basis=kinetic_minimum]/rec_Ru_lower_by_pct` |
| REC Ru lower by, Cho GHSV mass, Cho PSA recovery | -4.537 | % | python | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `summary/[psa_recovery=0.756;inventory_basis=cho_ghsv_9000]/rec_Ru_lower_by_pct` |
| Cho: REC Ru lower by | 7 | % | literature | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `summary/[psa_recovery=0.85;inventory_basis=kinetic_minimum]/cho_values/rec_Ru_lower_by_pct` |
| Cho: REC Ni | 1.995 | USD/kg H2 | literature | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `summary/[psa_recovery=0.85;inventory_basis=kinetic_minimum]/cho_values/rec_Ni` |
| Cho: REC Ru | 1.856 | USD/kg H2 | literature | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `summary/[psa_recovery=0.85;inventory_basis=kinetic_minimum]/cho_values/rec_Ru` |
| Ru REC lower than Ni by, published_TEA_Cho\|psa0.85\|cho_ghsv_9000 | -1.535 | % | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-f/numbers/rec_Ru_lower_by_pct/published_TEA_Cho\|psa0.85\|cho_ghsv_9000` |
| Ru REC lower than Ni by, derived_central\|psa0.85\|cho_ghsv_9000 | -9.833 | % | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-f/numbers/rec_Ru_lower_by_pct/derived_central\|psa0.85\|cho_ghsv_9000` |
| Ru REC lower than Ni by, derived_floor\|psa0.85\|cho_ghsv_9000 | -2.554 | % | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-f/numbers/rec_Ru_lower_by_pct/derived_floor\|psa0.85\|cho_ghsv_9000` |
| Ru REC lower than Ni by, published_TEA_Cho\|psa0.85\|kinetic_minimum | 1.554 | % | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-f/numbers/rec_Ru_lower_by_pct/published_TEA_Cho\|psa0.85\|kinetic_minimum` |
| Ru REC lower than Ni by, derived_central\|psa0.85\|kinetic_minimum | 0.9993 | % | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-f/numbers/rec_Ru_lower_by_pct/derived_central\|psa0.85\|kinetic_minimum` |
| Ru REC lower than Ni by, derived_floor\|psa0.85\|kinetic_minimum | 1.492 | % | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-f/numbers/rec_Ru_lower_by_pct/derived_floor\|psa0.85\|kinetic_minimum` |
| Ru REC lower than Ni by, published_TEA_Cho\|psa0.756\|cho_ghsv_9000 | -4.537 | % | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-f/numbers/rec_Ru_lower_by_pct/published_TEA_Cho\|psa0.756\|cho_ghsv_9000` |
| Ru REC lower than Ni by, derived_central\|psa0.756\|cho_ghsv_9000 | -16.232 | % | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-f/numbers/rec_Ru_lower_by_pct/derived_central\|psa0.756\|cho_ghsv_9000` |
| Ru REC lower than Ni by, derived_floor\|psa0.756\|cho_ghsv_9000 | -5.983 | % | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-f/numbers/rec_Ru_lower_by_pct/derived_floor\|psa0.756\|cho_ghsv_9000` |
| Ru REC lower than Ni by, published_TEA_Cho\|psa0.756\|kinetic_minimum | -0.1895 | % | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-f/numbers/rec_Ru_lower_by_pct/published_TEA_Cho\|psa0.756\|kinetic_minimum` |
| Ru REC lower than Ni by, derived_central\|psa0.756\|kinetic_minimum | -0.9718 | % | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-f/numbers/rec_Ru_lower_by_pct/derived_central\|psa0.756\|kinetic_minimum` |
| Ru REC lower than Ni by, derived_floor\|psa0.756\|kinetic_minimum | -0.2776 | % | python | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-f/numbers/rec_Ru_lower_by_pct/derived_floor\|psa0.756\|kinetic_minimum` |
| Cho et al. value | 7 | % | literature | `results/research/catalyst_economics/catalyst_economics.json` | `row_evidence/H3-f/numbers/cho_value_pct` |

Data: `results/research/catalyst_comparison/catalyst_cho_comparison.csv`, `results/research/catalyst_comparison/catalyst_cho_comparison.json`, `results/research/catalyst_economics/catalyst_economics.json`, `results/research/singapore/benchmarks.json`

## H4: PARTIALLY SUPPORTED

**Primary hypothesis.** Purification: must balance purity requirements against recovery losses, energy and equipment cost.

**Verdict.** PARTIALLY SUPPORTED (methodology v2). Version 1 verdict of the 23 November release: INCONCLUSIVE. Version 1 rule applied to the current rows: INCONCLUSIVE.

**Strongest defensible statement.** Recovery losses trade against energy: unrecovered hydrogen covers the furnace up to recovery 0.765 (computed). Stricter purity raises cost, but the purity-only part is small and rests on assumed recoveries. PSA against Pd-Ag membrane is not robust either way (parity near PSA recovery 0.79 for Grade D hydrogen; the industrial-grade value is in row H4-d).

**Findings against the essay.**

- The Phase 1 finding that a raw membrane is cheaper than PSA does not hold robustly on sourced ranges.

**Components.**

| Component | Verdict | Primary rows | Secondary rows | Envelope |
|---|---|---|---|---|
| H4-B Purity must be balanced against recovery, energy and cost | PARTIALLY SUPPORTED | H4-a, H4-b, H4-e | H4-c, H4-d | H4-e: 20 bar baseline; above recovery 0.765 the tail gas does not cover the furnace and NH3 is burned; below it the lost H2 has no use in this flowsheet |

**Verdict conditions.** Hypothesis verdict from its components (methodology v2; the cross-claim H2-X counts as a component): SUPPORTED if every component is SUPPORTED; CONTRADICTED if no component is SUPPORTED or PARTIALLY SUPPORTED and at least half are CONTRADICTED; MIXED if at least one component is SUPPORTED or PARTIALLY SUPPORTED and at least one is CONTRADICTED; PARTIALLY SUPPORTED if at least one component is SUPPORTED or PARTIALLY SUPPORTED, none is CONTRADICTED and not all are SUPPORTED; otherwise INCONCLUSIVE. Components: H4-B PARTIALLY SUPPORTED. Component verdict from its primary rows (methodology v2): SUPPORTED if every primary row is SUPPORTED; CONTRADICTED if no primary row is SUPPORTED and at least half are CONTRADICTED; MIXED if at least one is SUPPORTED and at least one CONTRADICTED; PARTIALLY SUPPORTED if at least one is SUPPORTED, none is CONTRADICTED and at least one is INCONCLUSIVE; otherwise INCONCLUSIVE. Secondary rows are reported but do not vote. Row outcomes: SUPPORTED: H4-e; CONTRADICTED: H4-c; INCONCLUSIVE: H4-a, H4-b, H4-d.

### H4-a: INCONCLUSIVE

Role: primary (H4-B). Version 1 verdict: INCONCLUSIVE.

**Sub-claim.** Higher hydrogen purity from PSA costs hydrogen recovery (purity-recovery trade-off).

**Numerical conclusions.**

- Only sourced slope: Yanez et al. 2020, recovery 0.753 at 99.25 % to 0.555 at 99.97 %, for ammonia-plant purge gas, not cracked ammonia.
- The AmCraX mass-balance relation is flat by construction (0.7516 and 0.7513).

**Conclusion.** No purity-recovery relation is computed for cracked ammonia; the direction rests on one source for a different feed.

**Rule and outcome.** Computation rule (methodology v2): the trade-off can be SUPPORTED or CONTRADICTED only by a computed purity-recovery relation. In AmCraX every PSA recovery is an input (source_type of each entry in phase2_comparison.json inputs/psa_recovery is literature or assumption: computed = False), so the row is INCONCLUSIVE.

**Envelope.** none (not computed)

**Assumptions.**

- AmCraX has no adsorption-cycle model; the PSA recovery at any purity is an input

**Uncertainty.** Grade D recovery 0.555 (Yanez, different feed) to 0.81 (Mehr, low confidence); no cracked-ammonia value

**Validation status.** PSA point reproduction is true by construction (informational); mass closure for all configurations (purification.json). Validation status of the underlying models: results/research/validation/purification.json: 10 pass, 0 fail, 7 informational.

**Evidence kinds.** literature comparison.

**Key uncertainty (what would change the verdict).** Outside this envelope the verdict may change: none (not computed)

**Uncertainty range.** Grade D recovery 0.555 (Yanez, different feed) to 0.81 (Mehr, low confidence); no cracked-ammonia value

- Singapore scenario: Jurong Island cracker, 20 bar Aspen baseline cracked gas; base costs use the existing AmCraX economics defaults (purification assumptions.json), Singapore NH3 and electricity prices in singapore_price_scenario.json; delivery 30 bar (industrial, blend) or 350 bar (Grade D).
- Aspen model: Stored Aspen Plus V15 baseline stream S7 (cracked gas) and H2PROD; PSA in Aspen is a split block with assumed fractions (no adsorption model).
- Python model: amcrax.separation.purification: PSA mass-balance relation, Sieverts membrane with pinch limit, ISO 14687 evaluator.
- Case ids: PSA_CHO, PSA_D_MB, PSA_D_LOW
- Validation: PSA point reproduction is true by construction (informational); mass closure for all configurations (purification.json). Validation status of the underlying models: results/research/validation/purification.json: 10 pass, 0 fail, 7 informational.
- Input assumptions: PSA recovery at 99.975 % purity is not in the library: 0.751 from holding Cho's tail-H2 fraction (optimistic) and 0.71 from the lowest published point applied outside its range.
- Literature: `iso14687_2019` (ISO 14687:2019 Tables 2-4 (grade D, E3, B limits)); `cho2026nickel` (Cho et al. 2026: published PSA recovery and purity point); `hansen2024hysys` (Hansen et al. 2024: lowest published PSA recovery point); `richard2024technoeconomic` (Richard et al. 2024: Pd-Ag permeability, Table 2); `cechetto2023membrane` (Cechetto et al. 2023: membrane review, NH3 in permeate)
- Limitations: Only two usable published PSA points (Cho; Hansen), at different adsorbents and pressures; the Mehr points are mutually inconsistent.; The mass-balance relation is flat by construction and is not evidence of a small penalty.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| PSA recovery, Cho point | 0.756 | fraction | literature | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_CHO]/h2_recovery` |
| PSA purity, Cho point | 0.9911 | mol fraction | literature | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_CHO]/product_purity_h2_mole_frac` |
| PSA recovery at Grade D purity, mass-balance relation | 0.7513 | fraction | assumption | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_D_MB]/h2_recovery` |
| PSA purity for Grade D | 0.9997 | mol fraction | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_D_MB]/product_purity_h2_mole_frac` |
| PSA recovery, lowest published point applied out of range | 0.71 | fraction | literature | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_D_LOW]/h2_recovery` |
| Yanez 2020 recovery at 99.25 % (different feed) | 0.753 | fraction | literature | `results/research/purification/phase2_comparison.json` | `row_evidence/H4-a/numbers/yanez2020_recovery_99.25` |
| Yanez 2020 recovery at 99.97 % (different feed) | 0.555 | fraction | literature | `results/research/purification/phase2_comparison.json` | `row_evidence/H4-a/numbers/yanez2020_recovery_99.97` |
| mass-balance recovery at 99.91 % | 0.7516 | fraction | assumption | `results/research/purification/phase2_comparison.json` | `row_evidence/H4-a/numbers/mass_balance_recovery_99.91` |
| mass-balance recovery at 99.975 % | 0.7513 | fraction | assumption | `results/research/purification/phase2_comparison.json` | `row_evidence/H4-a/numbers/mass_balance_recovery_99.975` |

Figures: `results/figures/research/purification_recovery_purity.png`
Data: `results/research/purification/phase2_comparison.json`, `results/research/purification/psa_recovery_vs_purity.csv`, `results/research/purification/purification_configurations.csv`, `results/research/purification/purification_study.json`

### H4-b: INCONCLUSIVE

Role: primary (H4-B). Version 1 verdict: INCONCLUSIVE.

**Sub-claim.** Purification must be matched to the end use: stricter purity requirements raise the cost per kg of usable hydrogen.

**Numerical conclusions.**

- The order raw < industrial < Grade D holds in all 3 electricity cases.
- Purity-only Grade D increment at equal delivery: psa_yanez_different_feed 0.1657, psa_mass_balance_assumption 0.0020, membrane_central 0.0174 USD/kg (resolution 0.0060).

**Conclusion.** Stricter purity costs more, but the purity-only part is small, partly below the model resolution, and rests on a cost proxy.

**Rule and outcome.** Resolution rule (methodology v2): raw < industrial is structural and most of the Grade D increment is 350 bar delivery, so the purity effect is tested at equal delivery pressure. SUPPORTED if the order raw < industrial < Grade D holds in every case and the purity-only increment exceeds the Python against Aspen LCOH resolution on every recovery basis; CONTRADICTED if the order is reversed everywhere; otherwise INCONCLUSIVE. Here: order holds everywhere True, increment resolved on every basis False.

**Envelope.** 20 bar baseline cracked gas, grey NH3 450 USD/t, electricity 0.084-0.222 USD/kWh, unified basis

**Assumptions.**

- PSA recoveries are inputs; polishing-bed cost is a proxy (adsorber share); delivery 30 / 350 bar

**Uncertainty.** factorial over all sourced inputs (PSA recovery, CAPEX basis, electricity, membrane cost, life, selectivity, flux, recovery)

**Validation status.** Component and mass closure for all configuration/case combinations; ISO limit transcription (purification.json). Validation status of the underlying models: results/research/validation/purification.json: 10 pass, 0 fail, 7 informational.

**Evidence kinds.** numerical verification, literature comparison.

**Key uncertainty (what would change the verdict).** Outside this envelope the verdict may change: 20 bar baseline cracked gas, grey NH3 450 USD/t, electricity 0.084-0.222 USD/kWh, unified basis

**Uncertainty range.** factorial over all sourced inputs (PSA recovery, CAPEX basis, electricity, membrane cost, life, selectivity, flux, recovery)

- Singapore scenario: Jurong Island cracker, 20 bar Aspen baseline cracked gas; base costs use the existing AmCraX economics defaults (purification assumptions.json), Singapore NH3 and electricity prices in singapore_price_scenario.json; delivery 30 bar (industrial, blend) or 350 bar (Grade D).
- Aspen model: Stored Aspen Plus V15 baseline stream S7 (cracked gas) and H2PROD; PSA in Aspen is a split block with assumed fractions (no adsorption model).
- Python model: amcrax.separation.purification: PSA mass-balance relation, Sieverts membrane with pinch limit, ISO 14687 evaluator.
- Case ids: RAW, PSA_AMCRAX, PSA_D_MB, PSA_D_LOW
- Validation: Component and mass closure for all configuration/case combinations; ISO limit transcription (purification.json). Validation status of the underlying models: results/research/validation/purification.json: 10 pass, 0 fail, 7 informational.
- Input assumptions: PSA recoveries are assumed (0.85 AmCraX; 0.751 and 0.71 bounds for Grade D).; TSA regeneration energy, compression CAPEX, membrane housing and skid not modelled: purified-route costs are lower bounds.; Grade D cost includes delivery to 350 bar; industrial and blend to 30 bar.
- Literature: `iso14687_2019` (ISO 14687:2019 Tables 2-4 (grade D, E3, B limits)); `cho2026nickel` (Cho et al. 2026: published PSA recovery and purity point); `hansen2024hysys` (Hansen et al. 2024: lowest published PSA recovery point); `richard2024technoeconomic` (Richard et al. 2024: Pd-Ag permeability, Table 2); `cechetto2023membrane` (Cechetto et al. 2023: membrane review, NH3 in permeate)
- Limitations: Part of the Grade D increment is delivery pressure (1.59 vs 0.22 kWh/kg compression), not purity.; Contaminants other than NH3, N2 and H2O are not evaluated for Grade D.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| cost usable H2, raw cracked gas for turbine blend | 3.784 | USD/kg H2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=RAW]/costs/turbine_blend/usd_per_kg_usable_h2` |
| cost usable H2, industrial 99.9 %, PSA_AMCRAX (industrial delivery) | 4.046 | USD/kg H2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_AMCRAX]/costs/industrial_99.9/usd_per_kg_usable_h2` |
| cost usable H2, Grade D, PSA_D_MB (fuel-cell delivery) | 4.463 | USD/kg H2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_D_MB]/costs/fuel_cell_grade_D/usd_per_kg_usable_h2` |
| cost usable H2, Grade D, PSA_D_LOW (fuel-cell delivery) | 4.710 | USD/kg H2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_D_LOW]/costs/fuel_cell_grade_D/usd_per_kg_usable_h2` |
| purification-only cost, PSA_D_MB at industrial delivery | 0.1873 | USD/kg H2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_D_MB]/costs/industrial_99.9/purification_only_usd_per_kg` |
| purification-only cost, PSA_AMCRAX at industrial delivery | 0.1692 | USD/kg H2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_AMCRAX]/costs/industrial_99.9/purification_only_usd_per_kg` |
| compression energy to industrial delivery, PSA | 0.2194 | kWh/kg H2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_D_MB]/costs/industrial_99.9/compression_kWh_per_kg_h2` |
| compression energy to fuel-cell delivery, PSA | 1.590 | kWh/kg H2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_D_MB]/costs/fuel_cell_grade_D/compression_kWh_per_kg_h2` |
| PSA recovery, PSA_AMCRAX (assumed split) | 0.85 | fraction | assumption | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_AMCRAX]/h2_recovery` |
| Singapore prices (blue): raw gas, turbine blend | 3.997 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_blue;config=RAW;end_use=turbine_blend]/usd_per_kg_usable_h2` |
| Singapore prices (blue): PSA_AMCRAX, industrial | 4.296 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_blue;config=PSA_AMCRAX;end_use=industrial_99.9]/usd_per_kg_usable_h2` |
| Singapore prices (blue): PSA_D_MB, Grade D | 4.746 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_blue;config=PSA_D_MB;end_use=fuel_cell_grade_D]/usd_per_kg_usable_h2` |
| Singapore prices (blue): PSA_D_LOW, Grade D | 5.009 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_blue;config=PSA_D_LOW;end_use=fuel_cell_grade_D]/usd_per_kg_usable_h2` |
| Singapore prices (green_2030): raw gas, turbine blend | 5.272 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_green_2030;config=RAW;end_use=turbine_blend]/usd_per_kg_usable_h2` |
| Singapore prices (green_2030): PSA_AMCRAX, industrial | 5.796 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_green_2030;config=PSA_AMCRAX;end_use=industrial_99.9]/usd_per_kg_usable_h2` |
| Singapore prices (green_2030): PSA_D_MB, Grade D | 6.443 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_green_2030;config=PSA_D_MB;end_use=fuel_cell_grade_D]/usd_per_kg_usable_h2` |
| Singapore prices (green_2030): PSA_D_LOW, Grade D | 6.805 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_green_2030;config=PSA_D_LOW;end_use=fuel_cell_grade_D]/usd_per_kg_usable_h2` |
| Singapore prices (green_current): raw gas, turbine blend | 6.943 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_green_current;config=RAW;end_use=turbine_blend]/usd_per_kg_usable_h2` |
| Singapore prices (green_current): PSA_AMCRAX, industrial | 7.762 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_green_current;config=PSA_AMCRAX;end_use=industrial_99.9]/usd_per_kg_usable_h2` |
| Singapore prices (green_current): PSA_D_MB, Grade D | 8.667 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_green_current;config=PSA_D_MB;end_use=fuel_cell_grade_D]/usd_per_kg_usable_h2` |
| Singapore prices (green_current): PSA_D_LOW, Grade D | 9.158 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_green_current;config=PSA_D_LOW;end_use=fuel_cell_grade_D]/usd_per_kg_usable_h2` |
| Singapore prices (grey): raw gas, turbine blend | 3.784 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_grey;config=RAW;end_use=turbine_blend]/usd_per_kg_usable_h2` |
| Singapore prices (grey): PSA_AMCRAX, industrial | 4.046 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_grey;config=PSA_AMCRAX;end_use=industrial_99.9]/usd_per_kg_usable_h2` |
| Singapore prices (grey): PSA_D_MB, Grade D | 4.463 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_grey;config=PSA_D_MB;end_use=fuel_cell_grade_D]/usd_per_kg_usable_h2` |
| Singapore prices (grey): PSA_D_LOW, Grade D | 4.710 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_grey;config=PSA_D_LOW;end_use=fuel_cell_grade_D]/usd_per_kg_usable_h2` |
| Python against Aspen LCOH resolution | 0.006022 | USD/kg H2 | python | `results/research/catalyst_economics/catalyst_economics.json` | `resolution/max_abs_python_minus_aspen_lcoh_USD_per_kg` |
| purity-only Grade D increment at equal delivery pressure, psa_yanez_different_feed | 0.1657 | USD/kg H2 | python | `results/research/purification/phase2_comparison.json` | `row_evidence/H4-b/numbers/equal_delivery_increment/psa_yanez_different_feed/increment` |
| purity-only Grade D increment at equal delivery pressure, psa_mass_balance_assumption | 0.001955 | USD/kg H2 | python | `results/research/purification/phase2_comparison.json` | `row_evidence/H4-b/numbers/equal_delivery_increment/psa_mass_balance_assumption/increment` |
| purity-only Grade D increment at equal delivery pressure, membrane_central | 0.01742 | USD/kg H2 | python | `results/research/purification/phase2_comparison.json` | `row_evidence/H4-b/numbers/equal_delivery_increment/membrane_central/increment` |

Figures: `results/figures/research/purification_recovery_purity.png`, `results/figures/research/purification_recovery_cost.png`, `results/figures/research/purification_config_comparison.png`
Data: `results/research/catalyst_economics/catalyst_economics.json`, `results/research/purification/phase2_comparison.json`, `results/research/purification/psa_recovery_vs_purity.csv`, `results/research/purification/purification_configurations.csv`, `results/research/purification/purification_study.json`, `results/research/purification/recovery_vs_cost.csv`, `results/research/purification/singapore_price_scenario.csv`, `results/research/purification/singapore_price_scenario.json`

### H4-e: SUPPORTED

Role: primary (H4-B). Version 1 verdict: SUPPORTED.

**Sub-claim.** Recovery losses trade against energy: hydrogen not recovered by purification returns as fuel for the cracker, up to the furnace demand.

**Numerical conclusions.**

- Furnace demand 2293 kW; the tail gas covers it at recovery 0.765; at 0.85 the deficit is 773 kW.

**Conclusion.** Hydrogen not recovered returns as furnace fuel up to the furnace demand (computed energy balance).

**Rule and outcome.** Energy-balance rule: SUPPORTED if the computed recovery at which tail-gas heat equals the furnace demand lies between 0 and 1 and a recovery above it (0.85) leaves a positive deficit, consistent with the trade; otherwise INCONCLUSIVE.

**Envelope.** 20 bar baseline; above recovery 0.765 the tail gas does not cover the furnace and NH3 is burned; below it the lost H2 has no use in this flowsheet

**Threshold.** recovery where tail-gas heat equals furnace demand: 0.7651. Sourced: none sourced. Comparison: "computed".

**Assumptions.**

- tail gas or retentate burned in the cracker furnace with the baseline furnace model; surplus not credited

**Uncertainty.** computed for recoveries 0.50-0.95 (PSA and membrane trade-off grids)

**Validation status.** Mass closure; tail-gas LHV from closed component balances (purification.json). Validation status of the underlying models: results/research/validation/economics.json: 9 pass, 0 fail, 6 informational; results/research/validation/purification.json: 10 pass, 0 fail, 7 informational.

**Evidence kinds.** numerical verification.

**Key uncertainty (what would change the verdict).** Outside this envelope the verdict may change: 20 bar baseline; above recovery 0.765 the tail gas does not cover the furnace and NH3 is burned; below it the lost H2 has no use in this flowsheet

**Uncertainty range.** computed for recoveries 0.50-0.95 (PSA and membrane trade-off grids)

- Singapore scenario: Jurong Island cracker, 20 bar Aspen baseline cracked gas; base costs use the existing AmCraX economics defaults (purification assumptions.json), Singapore NH3 and electricity prices in singapore_price_scenario.json; delivery 30 bar (industrial, blend) or 350 bar (Grade D).
- Aspen model: Stored Aspen Plus V15 baseline stream S7 (cracked gas) and H2PROD; PSA in Aspen is a split block with assumed fractions (no adsorption model). Furnace demand from the stored Aspen baseline.
- Python model: amcrax.separation.purification: PSA mass-balance relation, Sieverts membrane with pinch limit, ISO 14687 evaluator.
- Case ids: PSA_AMCRAX, PSA_D_MB, baseline (stored Aspen)
- Validation: Mass closure; tail-gas LHV from closed component balances (purification.json). Validation status of the underlying models: results/research/validation/economics.json: 9 pass, 0 fail, 6 informational; results/research/validation/purification.json: 10 pass, 0 fail, 7 informational.
- Input assumptions: Tail gas burned in the cracker furnace with the baseline furnace model; surplus heat beyond the demand is not credited.
- Literature: `iso14687_2019` (ISO 14687:2019 Tables 2-4 (grade D, E3, B limits)); `cho2026nickel` (Cho et al. 2026: published PSA recovery and purity point); `hansen2024hysys` (Hansen et al. 2024: lowest published PSA recovery point); `richard2024technoeconomic` (Richard et al. 2024: Pd-Ag permeability, Table 2); `cechetto2023membrane` (Cechetto et al. 2023: membrane review, NH3 in permeate)
- Limitations: Heat-integration effect of placing a membrane on the hot effluent not modelled.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| PSA recovery, PSA_AMCRAX | 0.85 | fraction | assumption | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_AMCRAX]/h2_recovery` |
| PSA recovery, PSA_D_MB | 0.7513 | fraction | assumption | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_D_MB]/h2_recovery` |
| tail-gas heat to furnace, PSA_AMCRAX | 1520.2 | kW | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_AMCRAX]/tail_heat_to_furnace_kW` |
| net heat deficit, PSA_AMCRAX | 772.9 | kW | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_AMCRAX]/net_heat_deficit_kW` |
| tail-gas heat to furnace, PSA_D_MB | 2418.5 | kW | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_D_MB]/tail_heat_to_furnace_kW` |
| net heat deficit, PSA_D_MB | 0 | kW | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_D_MB]/net_heat_deficit_kW` |
| surplus tail-gas heat not credited, PSA_D_MB | 125.4 | kW | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_D_MB]/surplus_heat_kW_not_credited` |
| furnace demand (Aspen baseline external heating) | 2293.1 | kW | aspen | `results/research/purification/purification_study.json` | `cases/20bar_baseline/furnace_demand_kW` |
| furnace demand | 2293.1 | kW | python | `results/research/purification/phase2_comparison.json` | `row_evidence/H4-e/numbers/furnace_demand_kW` |
| recovery at which tail-gas heat equals the furnace demand | 0.7651 | fraction | python | `results/research/purification/phase2_comparison.json` | `row_evidence/H4-e/numbers/recovery_where_tail_heat_equals_demand` |
| net deficit at PSA recovery 0.85 | 772.9 | kW | python | `results/research/purification/phase2_comparison.json` | `row_evidence/H4-e/numbers/psa_0.85_net_deficit_kW` |

Figures: `results/figures/research/purification_recovery_cost.png`
Data: `results/research/purification/phase2_comparison.json`, `results/research/purification/psa_recovery_vs_purity.csv`, `results/research/purification/purification_configurations.csv`, `results/research/purification/purification_study.json`

### H4-c: CONTRADICTED

Role: secondary (H4-B). Version 1 verdict: CONTRADICTED.

**Sub-claim.** A published PSA operating point (Cho: 75.6 % recovery at 99.11 % H2) is sufficient for hydrogen end uses with ISO 14687 grades.

**Numerical conclusions.**

- Cho point: recovery 75.6 %, purity 99.11 %, N2 8900 ppm; fails the 99.9 % index and Grade D.

**Conclusion.** The published PSA point does not meet ISO 14687 grades B or D.

**Rule and outcome.** Specification rule (unchanged from version 1): CONTRADICTED if the published composition fails both grade B and grade D in the ISO 14687 evaluator. Secondary row: does not vote.

**Envelope.** ISO 14687:2019 grades B and D, modelled species NH3, N2, H2O

**Assumptions.**

- NH3 at the TSA design limit

**Uncertainty.** none for the specification check

**Validation status.** ISO 14687 evaluator applied per modelled contaminant (NH3, N2, H2O); P-ISO-2 Aspen H2PROD vs Grade D informational (purification.json). Validation status of the underlying models: results/research/validation/purification.json: 10 pass, 0 fail, 7 informational.

**Evidence kinds.** numerical verification, literature comparison.

**Key uncertainty (what would change the verdict).** Outside this envelope the verdict may change: ISO 14687:2019 grades B and D, modelled species NH3, N2, H2O

**Uncertainty range.** none for the specification check

- Singapore scenario: Jurong Island cracker, 20 bar Aspen baseline cracked gas; base costs use the existing AmCraX economics defaults (purification assumptions.json), Singapore NH3 and electricity prices in singapore_price_scenario.json; delivery 30 bar (industrial, blend) or 350 bar (Grade D).
- Aspen model: Stored Aspen Plus V15 baseline stream S7 (cracked gas) and H2PROD; PSA in Aspen is a split block with assumed fractions (no adsorption model).
- Python model: amcrax.separation.purification: PSA mass-balance relation, Sieverts membrane with pinch limit, ISO 14687 evaluator.
- Case ids: PSA_CHO, PSA_AMCRAX
- Validation: ISO 14687 evaluator applied per modelled contaminant (NH3, N2, H2O); P-ISO-2 Aspen H2PROD vs Grade D informational (purification.json). Validation status of the underlying models: results/research/validation/purification.json: 10 pass, 0 fail, 7 informational.
- Input assumptions: NH3 at the PSA outlet set to the TSA design target rather than computed.; The Aspen baseline PSA split is an assumption; its purity supports no purity claim.
- Literature: `iso14687_2019` (ISO 14687:2019 Tables 2-4 (grade D, E3, B limits)); `cho2026nickel` (Cho et al. 2026: published PSA recovery and purity point); `hansen2024hysys` (Hansen et al. 2024: lowest published PSA recovery point); `richard2024technoeconomic` (Richard et al. 2024: Pd-Ag permeability, Table 2); `cechetto2023membrane` (Cechetto et al. 2023: membrane review, NH3 in permeate)
- Limitations: Only NH3, N2 and H2O are evaluated; meeting a grade within model scope is not a fuel-cell grade claim.; The Aspen baseline product (N2 400 ppm, Grade D within model scope: False) is not Grade D and must not be called fuel-cell grade.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| H2 recovery, Cho PSA point | 0.756 | fraction | literature | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_CHO]/h2_recovery` |
| N2 in product, Cho PSA point | 8900.0 | ppm | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_CHO]/product_ppm/N2` |
| H2 purity, Cho PSA point | 0.9911 | mol fraction | literature | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_CHO]/product_purity_h2_mole_frac` |
| N2 in product, PSA_AMCRAX (Aspen baseline split) | 400.0 | ppm | assumption | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_AMCRAX]/product_ppm/N2` |
| Cho PSA recovery | 0.756 | fraction | literature | `results/research/purification/phase2_comparison.json` | `row_evidence/H4-c/numbers/cho_recovery` |
| Cho PSA purity | 0.9911 | mol fraction | literature | `results/research/purification/phase2_comparison.json` | `row_evidence/H4-c/numbers/cho_purity` |
| N2 in product | 8900 | ppm | python | `results/research/purification/phase2_comparison.json` | `row_evidence/H4-c/numbers/n2_ppm` |

Figures: `results/figures/research/purification_config_comparison.png`
Data: `results/research/purification/phase2_comparison.json`, `results/research/purification/psa_recovery_vs_purity.csv`, `results/research/purification/purification_configurations.csv`, `results/research/purification/purification_study.json`

### H4-d: INCONCLUSIVE

Role: secondary (H4-B). Version 1 verdict: INCONCLUSIVE.

**Sub-claim.** A Pd-Ag membrane balances purity, recovery and cost better than PSA for fuel-cell hydrogen.

**Numerical conclusions.**

- Membrane cheaper in 60 % of sourced input pairs; parity at PSA recovery 0.788 (Grade D) and 0.801 (industrial).
- Pd-Ag ideal H2/N2 selectivity 40541 (printed permeances) to 500000 (stated), single gas, new membrane, against a requirement of 12919; the paper is internally inconsistent.

**Conclusion.** PSA against Pd-Ag membrane is not robust either way; it turns on PSA recovery. Membrane TRL 4 to 5 against PSA 9.

**Rule and outcome.** Robustness rule: SUPPORTED if the membrane is cheaper in every sourced input combination; CONTRADICTED if in none; otherwise INCONCLUSIVE. Secondary row: does not vote.

**Envelope.** membrane cheaper only if PSA Grade D recovery is below about 0.788 (central membrane) or 0.749 (high-cost membrane)

**Threshold.** PSA recovery at cost parity: 0.7884, 0.8008. Sourced: none sourced. Comparison: "sourced PSA recoveries straddle parity".

**Assumptions.**

- membrane housing, skid and heating CAPEX not modelled (favours the membrane); PSA own power and TSA heat not modelled (favours PSA); permeate at 1 bar

**Uncertainty.** factorial over sourced inputs; ranking reverses inside it

**Validation status.** Sieverts hand calculation and pinch limit checks (purification.json). Validation status of the underlying models: results/research/validation/purification.json: 10 pass, 0 fail, 7 informational.

**Evidence kinds.** numerical verification, literature comparison.

**Key uncertainty (what would change the verdict).** Outside this envelope the verdict may change: membrane cheaper only if PSA Grade D recovery is below about 0.788 (central membrane) or 0.749 (high-cost membrane)

**Uncertainty range.** factorial over sourced inputs; ranking reverses inside it

- Singapore scenario: Jurong Island cracker, 20 bar Aspen baseline cracked gas; base costs use the existing AmCraX economics defaults (purification assumptions.json), Singapore NH3 and electricity prices in singapore_price_scenario.json; delivery 30 bar (industrial, blend) or 350 bar (Grade D).
- Aspen model: No Aspen membrane model: Python/literature only.
- Python model: amcrax.separation.purification: PSA mass-balance relation, Sieverts membrane with pinch limit, ISO 14687 evaluator.
- Case ids: MEM_1bar_polish, MEM_1bar_raw, PSA_D_MB
- Validation: Sieverts hand calculation and pinch limit checks (purification.json). Validation status of the underlying models: results/research/validation/purification.json: 10 pass, 0 fail, 7 informational.
- Input assumptions: Infinite H2/N2 selectivity in the base case (no numeric selectivity in the library).; Membrane cost 6000 EUR/m2 applied as USD at parity; housing, skid and compression CAPEX not modelled.; Membrane recovery 0.90 is a design choice.
- Literature: `iso14687_2019` (ISO 14687:2019 Tables 2-4 (grade D, E3, B limits)); `cho2026nickel` (Cho et al. 2026: published PSA recovery and purity point); `hansen2024hysys` (Hansen et al. 2024: lowest published PSA recovery point); `richard2024technoeconomic` (Richard et al. 2024: Pd-Ag permeability, Table 2); `cechetto2023membrane` (Cechetto et al. 2023: membrane review, NH3 in permeate); `cechetto2021fpt` (Pd-Ag membrane permeances)
- Limitations: Without polishing the permeate carries 2.9 ppm NH3 (measured, Cechetto 2021) and fails Grade D.; Membrane results are lower bounds on cost.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| cost usable H2, Grade D, Pd-Ag membrane + polishing (350 bar) | 4.327 | USD/kg H2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=MEM_1bar_polish]/costs/fuel_cell_grade_D/usd_per_kg_usable_h2` |
| membrane H2 recovery (design) | 0.9 | fraction | assumption | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=MEM_1bar_polish]/h2_recovery` |
| membrane area | 31.063 | m2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=MEM_1bar_polish]/area_m2` |
| cost usable H2, Grade D, PSA_D_MB | 4.463 | USD/kg H2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_D_MB]/costs/fuel_cell_grade_D/usd_per_kg_usable_h2` |
| NH3 in membrane permeate without polishing | 2.900 | ppm | literature | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=MEM_1bar_raw]/product_ppm/NH3` |
| membrane cost (applied as USD at parity) | 6000 | EUR/m2 | assumption | `results/research/purification/assumptions.json` | `[name=Membrane cost]/value` |
| share of sourced input pairs in which the membrane is cheaper (Grade D) | 0.5988 | fraction | python | `results/research/purification/phase2_comparison.json` | `row_evidence/H4-d/numbers/share_pairs_membrane_cheaper` |
| PSA recovery at parity, central membrane | 0.7884 | fraction | python | `results/research/purification/phase2_comparison.json` | `row_evidence/H4-d/numbers/psa_recovery_at_parity_central_membrane` |
| PSA recovery at parity, industrial | 0.8008 | fraction | python | `results/research/purification/phase2_comparison.json` | `row_evidence/H4-d/numbers/industrial_psa_recovery_at_parity` |
| required H2/N2 selectivity | 12919.0 | - | python | `results/research/purification/phase2_comparison.json` | `row_evidence/H4-d/numbers/required_selectivity` |
| ideal H2/N2 selectivity from the printed permeances (Cechetto et al. 2021) | 40540.5 | - | literature | `results/research/purification/phase2_comparison.json` | `row_evidence/H4-d/numbers/sourced_selectivity/0` |
| ideal H2/N2 selectivity as stated (Cechetto et al. 2021) | 500000 | - | literature | `results/research/purification/phase2_comparison.json` | `row_evidence/H4-d/numbers/sourced_selectivity/2` |

Figures: `results/figures/research/purification_recovery_cost.png`, `results/figures/research/purification_sensitivity.png`
Data: `results/research/purification/assumptions.json`, `results/research/purification/membrane_recovery_area_cost.csv`, `results/research/purification/membrane_required_selectivity.csv`, `results/research/purification/phase2_comparison.json`, `results/research/purification/purification_study.json`

