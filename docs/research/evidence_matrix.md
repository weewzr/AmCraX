# Research evidence matrix (H1-H4)

Generated from `results/research/evidence_matrix.json` by `scripts/research/build_evidence_matrix.py` (2026-11-23T07:54:09Z). Do not edit by hand; re-run the script.

Verdicts: SUPPORTED, CONTRADICTED, INCONCLUSIVE. Hypothesis verdict from its rows: SUPPORTED if every row is SUPPORTED; CONTRADICTED if no row is SUPPORTED and at least half of the rows are CONTRADICTED; otherwise INCONCLUSIVE, with the mixed row outcomes stated in verdict_conditions.

Each row's conclusion_conditions states the rule that produced its verdict. SUPPORTED only within the stated conditions and when the evidence is computed rather than an assumption built into the model; model-form limited, extrapolated or within-band evidence gives INCONCLUSIVE.

## Verdict table

| Hypothesis | Row | Verdict | Sub-claim |
|---|---|---|---|
| **H1** | | **INCONCLUSIVE** | End-use suitability: cracking is most justified when the end use needs molecular hydrogen, not where ammonia can be used directly. |
| | H1-a | INCONCLUSIVE | Where ammonia can be burned directly (power), direct NH3 combustion is cheaper than power from a standalone (fired) cracker or from cracked and purified hydrogen. |
| | H1-b | CONTRADICTED | Direct NH3 combustion is about 40 % cheaper than cracking-based power (essay, citing Halim et al. 2025). |
| | H1-c | INCONCLUSIVE | Cracking is not justified where ammonia can be used directly: partial or full cracking in front of a turbine does not pay. |
| | H1-d | INCONCLUSIVE | Cracking is most justified when the end use needs molecular hydrogen: the conversion loss is small when H2 is the product and larger when H2 is only an intermediate fuel. |
| **H2** | | **INCONCLUSIVE** | Feedstock: affordable, low-carbon ammonia is essential to economic and environmental competitiveness. |
| | H2-a | SUPPORTED | Ammonia feed cost dominates the cost of cracked hydrogen, so affordable ammonia is essential to economic competitiveness. |
| | H2-b | SUPPORTED | Only affordable ammonia keeps cracked hydrogen competitive with the hydrogen benchmarks relevant to Singapore. |
| | H2-c | SUPPORTED | Low-carbon ammonia is essential for environmental competitiveness of ammonia-based power in Singapore. |
| | H2-d | SUPPORTED | Low-carbon ammonia is essential for cracked hydrogen to have lower carbon intensity than fossil hydrogen. |
| | H2-e | CONTRADICTED | Low-carbon ammonia is essential to economic competitiveness (that is, low carbon intensity is rewarded in the Singapore cost of hydrogen). |
| **H3** | | **INCONCLUSIVE** | Catalyst and heat integration: low-temperature, high-activity catalysts with effective heat integration reduce energy use and can outweigh higher catalyst cost. |
| | H3-a | SUPPORTED | Energy half of the catalyst claim: at equal conversion, running the cracker at the lower temperature that a more active catalyst allows reduces energy use. |
| | H3-b | INCONCLUSIVE | Low-temperature, high-activity catalysts allow the cracker to run at a lower temperature for the same duty. |
| | H3-c | INCONCLUSIVE | The energy saved by a low-temperature, high-activity catalyst can outweigh its higher catalyst cost. |
| | H3-d | SUPPORTED | Effective heat integration reduces energy use (and cost) of the cracker, and matters more than the catalyst's temperature. |
| | H3-e | INCONCLUSIVE | Cho et al. (2026): the Ru process at 567 degC needs no supplementary fuel while the Ni process at 736 degC burns supplementary NH3. |
| | H3-f | INCONCLUSIVE | Cho et al. (2026): the Ru process has a 7.0 % lower relative economic cost (REC) than the Ni process. |
| **H4** | | **INCONCLUSIVE** | Purification: must balance purity requirements against recovery losses, energy and equipment cost. |
| | H4-a | INCONCLUSIVE | Higher hydrogen purity from PSA costs hydrogen recovery (purity-recovery trade-off). |
| | H4-b | INCONCLUSIVE | Purification must be matched to the end use: stricter purity requirements raise the cost per kg of usable hydrogen. |
| | H4-c | CONTRADICTED | A published PSA operating point (Cho: 75.6 % recovery at 99.11 % H2) is sufficient for hydrogen end uses with ISO 14687 grades. |
| | H4-d | INCONCLUSIVE | A Pd-Ag membrane balances purity, recovery and cost better than PSA for fuel-cell hydrogen. |
| | H4-e | SUPPORTED | Recovery losses trade against energy: hydrogen not recovered by purification returns as fuel for the cracker, up to the furnace demand. |

## H1: INCONCLUSIVE

**Statement.** End-use suitability: cracking is most justified when the end use needs molecular hydrogen, not where ammonia can be used directly.

**Summary.** Direct use is cheaper than standalone and purified cracking for power, but that ranking follows from the assumption that the turbine reaches the same efficiency on H2-rich fuel as on NH3, so it is not independent support; the essay's cost margin for direct use is not reproduced, and exhaust-heated cracking in front of a turbine is marginally cheaper than direct use on a single literature efficiency gain.

**Verdict conditions.** Hypothesis verdict from its rows: SUPPORTED if every row is SUPPORTED; CONTRADICTED if no row is SUPPORTED and at least half of the rows are CONTRADICTED; otherwise INCONCLUSIVE, with the mixed row outcomes stated in verdict_conditions. Row outcomes: CONTRADICTED: H1-b; INCONCLUSIVE: H1-a, H1-c, H1-d. Qualified verdict: the hypothesis holds only in the parts marked SUPPORTED, under each row's conclusion_conditions; rows marked CONTRADICTED are findings against the essay statement; INCONCLUSIVE rows are unresolved by the models.

### H1-a: INCONCLUSIVE

**Sub-claim.** Where ammonia can be burned directly (power), direct NH3 combustion is cheaper than power from a standalone (fired) cracker or from cracked and purified hydrogen.

**Conclusion.** Direct NH3 power costs 259 USD/MWh against 273 (fired cracker) and 304 (cracked + PSA H2); efficiency 49.6 % against 43.6 % for the purified route. Direct use is cheaper at every swept NH3 price, but the sign of this result is set by the assumption that the turbine reaches the direct-NH3 efficiency (49.6 %) on H2-rich fuel: a fired or purified cracker can then only add NH3 burn and capital. The computed content is the size of the gap, not its sign.

**Conditions and rule.** Rule: SUPPORTED only if direct is cheaper than both pathways at every NH3 price in the sweep, no crossover exists and the H2-rich-fuel turbine efficiency is not an assumed copy of the direct-NH3 efficiency; otherwise INCONCLUSIVE (here: efficiency copied, so the ranking reproduces an assumption). Conditions: AmCraX plant boundary, 8000 h/yr, no NOx abatement cost.

**Key uncertainty (what would change the verdict).** The fired-cracker efficiency (direct turbine efficiency applied to H2-rich fuel) and the cracker capital; a real H2-fired turbine efficiency gain large enough to exceed the cracker heat penalty would remove the fired-route gap.

**Uncertainty range.** Direct is cheaper by 5.1 % (fired) and 15.0 % (purified) at the common price; 15.0 % (purified, Ahmad basis) and 13.8 % (purified, renewable NH3 today). The ranking holds at every NH3 price of the sweep (250-1100 USD/t); no crossover price exists for these two pathways.

- Singapore scenario: Jurong Island representative power plant burning imported NH3; common reference NH3 price from the Singapore price set (grey), operating hours, Singapore electricity and carbon tax inputs as in price_set of enduse_results.json
- Aspen model: Stored Aspen Plus V15 baseline (results/simulations/baseline.json): cracker reactor and pre-heater duty, PSA heat deficit used as cracker heat; no Aspen combustion model.
- Python model: amcrax.enduse.pathways power pathways (energy balance, Ahmad-scaled plant capital, amcrax.economics).
- Case ids: baseline (stored Aspen), direct, full_fired, full_purified
- Validation: Energy balance closure of every power pathway; Ahmad Case 2a LCOE reproduced; Aspen LHV efficiency reproduced (results/research/validation/enduse.json). Validation status of the underlying models: results/research/validation/enduse.json: 40 pass, 0 fail, 5 informational.
- Input assumptions: Fired variants apply the direct-NH3 turbine efficiency to H2-rich fuel (assumption).; PSA recovery of the stored baseline (assumption) for the purified route.; Plant capital outside the cracker: Ahmad Case 2a scaled with plant power.; No NOx abatement cost; no combustion simulated.
- Literature: `ahmad2025gtcc` (Ahmad et al. 2025: NH3 and cracked-NH3 GTCC efficiencies and Case 2a cost basis); `halim2025ammoniapower` (Halim et al. 2025 (abstract only): direct use preferred to cracking for power)
- Limitations: Efficiencies of intermediate blends are a linear interpolation of Ahmad's two end points (assumption).; Fired variants apply the direct-NH3 turbine efficiency to H2-rich fuel (assumption).; Plant capital outside the cracker is Ahmad's Case 2a scaled with power^0.67; no NOx abatement cost.; Fuel-cell candidate cost excludes NH3 polishing and other ISO 14687 contaminant control.; Halim et al. (2025) full text was not accessible; only the abstract and bibliographic data were checked.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| LCOE direct NH3 CCGT | 258.9 | USD/MWh | python | `results/research/enduse/enduse_results.json` | `power_pathways/[id=direct]/cost_USD_per_MWh_at_450` |
| LCOE full cracking, fired cracker | 272.9 | USD/MWh | python | `results/research/enduse/enduse_results.json` | `power_pathways/[id=full_fired]/cost_USD_per_MWh_at_450` |
| LCOE full cracking + PSA H2 | 304.5 | USD/MWh | python | `results/research/enduse/enduse_results.json` | `power_pathways/[id=full_purified]/cost_USD_per_MWh_at_450` |
| NH3 LHV to electricity, direct | 0.4964 | fraction | literature | `results/research/enduse/enduse_results.json` | `power_pathways/[id=direct]/efficiency_NH3_LHV_to_electricity` |
| NH3 LHV to electricity, cracked + PSA H2 | 0.4356 | fraction | python | `results/research/enduse/enduse_results.json` | `power_pathways/[id=full_purified]/efficiency_NH3_LHV_to_electricity` |
| direct cheaper than fired cracking, 1 - direct/cracking | 5.104 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=AmCraX price set (450 USD~1t, 8000 h);cracking_pathway=full_fired]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| direct cheaper than cracking + PSA, 1 - direct/cracking | 14.954 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=AmCraX price set (450 USD~1t, 8000 h);cracking_pathway=full_purified]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| same, Ahmad basis | 15.025 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=Ahmad basis (480 USD~1t, 7200 h);cracking_pathway=full_purified]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| same, renewable NH3 at today's price | 13.756 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=renewable NH3 today (1000 USD~1t);cracking_pathway=full_purified]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| turbine efficiency on H2-rich fuel (copy of direct case) | 0.4964 | fraction | assumption | `results/research/enduse/assumptions.json` | `[name=eta_gt_gas]/value` |

Figures: `results/figures/research/enduse_power_cost_vs_ci.png`, `results/figures/research/enduse_power_cost_vs_price.png`, `results/figures/research/enduse_power_efficiency.png`
Data: `results/research/enduse/assumptions.json`, `results/research/enduse/enduse_results.json`, `results/research/enduse/pathway_table_power.csv`, `results/research/enduse/price_sweep.csv`

### H1-b: CONTRADICTED

**Sub-claim.** Direct NH3 combustion is about 40 % cheaper than cracking-based power (essay, citing Halim et al. 2025).

**Conclusion.** Not reproduced: the computed cost advantage of direct use is at most 15.0 % against the essay's 40 %; against an exhaust-heated cracker direct use is dearer.

**Conditions and rule.** Rule: CONTRADICTED if the largest computed gap on any basis is below half the claimed value; otherwise INCONCLUSIVE. Holds on AmCraX boundaries; does not show that Halim's own calculation is wrong.

**Key uncertainty (what would change the verdict).** Halim's own inputs (full text not accessed): a purified-H2 turbine with a standalone fired cracker, a much higher cracker capital or a lower capacity factor could produce a larger gap.

**Uncertainty range.** Largest computed gap 15.0 % across 9 basis/pathway combinations; smallest -6.8 % (negative: cracking cheaper).

- Singapore scenario: Jurong Island representative power plant burning imported NH3; common reference NH3 price from the Singapore price set (grey), operating hours, Singapore electricity and carbon tax inputs as in price_set of enduse_results.json
- Aspen model: No Aspen combustion model; cracker duties from the stored Aspen baseline.
- Python model: amcrax.enduse.pathways (halim_claim_check).
- Case ids: direct, full_exhaust, full_fired, full_purified
- Validation: Claim check against computed 1 - direct/cracking on three bases (validation item EU-halim-claim, informational because Halim's inputs were not accessed). Validation status of the underlying models: results/research/validation/enduse.json: 40 pass, 0 fail, 5 informational.
- Input assumptions: Same as H1-a; three price and operating-hour bases (AmCraX, Ahmad, renewable NH3 today).
- Literature: `ahmad2025gtcc` (Ahmad et al. 2025: NH3 and cracked-NH3 GTCC efficiencies and Case 2a cost basis); `halim2025ammoniapower` (Halim et al. 2025 (abstract only): direct use preferred to cracking for power)
- Limitations: Halim et al. (2025) full text not accessible; the claimed figure is from the essay and the abstract-level record.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| essay/Halim claim: direct cheaper than cracking-based power | 40 | % | literature | `results/research/validation/enduse.json` | `[id=EU-halim-claim]/expected` |
| computed gap, AmCraX price set, full_exhaust | -4.303 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=AmCraX price set (450 USD~1t, 8000 h);cracking_pathway=full_exhaust]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| computed gap, AmCraX price set, full_fired | 5.104 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=AmCraX price set (450 USD~1t, 8000 h);cracking_pathway=full_fired]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| computed gap, AmCraX price set, full_purified | 14.954 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=AmCraX price set (450 USD~1t, 8000 h);cracking_pathway=full_purified]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| computed gap, Ahmad basis, full_exhaust | -4.157 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=Ahmad basis (480 USD~1t, 7200 h);cracking_pathway=full_exhaust]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| computed gap, Ahmad basis, full_fired | 5.161 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=Ahmad basis (480 USD~1t, 7200 h);cracking_pathway=full_fired]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| computed gap, Ahmad basis, full_purified | 15.025 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=Ahmad basis (480 USD~1t, 7200 h);cracking_pathway=full_purified]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| computed gap, renewable NH3 today, full_exhaust | -6.781 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=renewable NH3 today (1000 USD~1t);cracking_pathway=full_exhaust]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| computed gap, renewable NH3 today, full_fired | 4.139 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=renewable NH3 today (1000 USD~1t);cracking_pathway=full_fired]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |
| computed gap, renewable NH3 today, full_purified | 13.756 | % | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/computed/[basis=renewable NH3 today (1000 USD~1t);cracking_pathway=full_purified]/direct_cheaper_by_pct_of_cracking(1-d~1c)` |

Figures: `results/figures/research/enduse_power_cost_vs_price.png`
Data: `results/research/enduse/claim_check_direct_vs_cracking.csv`, `results/research/enduse/enduse_results.json`, `results/research/validation/enduse.json`

### H1-c: INCONCLUSIVE

**Sub-claim.** Cracking is not justified where ammonia can be used directly: partial or full cracking in front of a turbine does not pay.

**Conclusion.** Fired partial cracking (265 USD/MWh) is dearer than direct (259), but exhaust-heated cracking is slightly cheaper (256 partial, 248 full; efficiency 54.6 %). The sign of the difference rests on a literature efficiency gain that this project did not simulate.

**Conditions and rule.** Rule: INCONCLUSIVE because the ranking reverses on an input efficiency gain (literature, single source) rather than on a computed result, and the difference is a few per cent of LCOE.

**Key uncertainty (what would change the verdict).** The exhaust-heat efficiency gain (one literature source, not simulated here): with less than the break-even share of Ahmad's gain, direct use wins at every scanned H2 fraction.

**Uncertainty range.** Exhaust-heated partial cracking (40 % H2 by volume) is 3.3 USD/MWh cheaper than direct; it needs 54 % of Ahmad's efficiency gain to break even. Exhaust-heated full cracking beats direct above 147 USD/t NH3.

- Singapore scenario: Jurong Island representative power plant burning imported NH3; common reference NH3 price from the Singapore price set (grey), operating hours, Singapore electricity and carbon tax inputs as in price_set of enduse_results.json
- Aspen model: Partial-cracking heat is the stored Aspen baseline reactor + pre-heater duty scaled with the cracked share; no Aspen combustion or exhaust-heated reactor model.
- Python model: amcrax.enduse.pathways partial-cracking scan and break-even efficiency gain.
- Case ids: direct, partial_exhaust_40, partial_fired_40, full_exhaust
- Validation: Ahmad bypass table reproduced by stoichiometry; N and H atom balance and blend round trip (enduse.json). Validation status of the underlying models: results/research/validation/enduse.json: 40 pass, 0 fail, 5 informational.
- Input assumptions: Exhaust-heated cracker efficiency taken from Ahmad's two end points (literature).; Efficiency of intermediate blends linearly interpolated between Ahmad's end points (assumption).; Fired variants: direct-NH3 turbine efficiency (assumption).
- Literature: `ahmad2025gtcc` (Ahmad et al. 2025: NH3 and cracked-NH3 GTCC efficiencies and Case 2a cost basis); `halim2025ammoniapower` (Halim et al. 2025 (abstract only): direct use preferred to cracking for power)
- Limitations: No combustion simulation; NOx not quantified for blends and cracked fuels.; Turbine H2 tolerance ranges are flags only (Ahmad p. 2; brief value unverified).

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| LCOE full cracking, exhaust-heated, unpurified | 248.2 | USD/MWh | python | `results/research/enduse/enduse_results.json` | `power_pathways/[id=full_exhaust]/cost_USD_per_MWh_at_450` |
| LCOE partial cracking 40 vol% H2, exhaust-heated | 255.6 | USD/MWh | python | `results/research/enduse/enduse_results.json` | `power_pathways/[id=partial_exhaust_40]/cost_USD_per_MWh_at_450` |
| LCOE partial cracking 40 vol% H2, fired | 265.3 | USD/MWh | python | `results/research/enduse/enduse_results.json` | `power_pathways/[id=partial_fired_40]/cost_USD_per_MWh_at_450` |
| LCOE direct NH3 | 258.9 | USD/MWh | python | `results/research/enduse/enduse_results.json` | `power_pathways/[id=direct]/cost_USD_per_MWh_at_450` |
| exhaust-heated efficiency (literature end point) | 0.5458 | fraction | literature | `results/research/enduse/enduse_results.json` | `power_pathways/[id=full_exhaust]/efficiency_NH3_LHV_to_electricity` |
| share of Ahmad's efficiency gain needed for 40 vol% partial cracking to match direct, 450 USD/t | 0.542 | fraction | python | `results/research/enduse/enduse_results.json` | `partial_cracking/breakeven_efficiency_gain/[NH3_price_USD_t=450]/gain_scale_where_partial_40vol_equals_direct` |
| NH3 price above which exhaust-heated full cracking beats direct | 146.8 | USD/t | python | `results/research/enduse/enduse_results.json` | `halim_claim_check/crossover_prices/full_exhaust_vs_direct_NH3_price_USD_t` |
| H2 fraction of the partial-cracking case | 0.4 | vol fraction | assumption | `results/research/enduse/enduse_results.json` | `power_pathways/[id=partial_exhaust_40]/H2_vol_fraction_in_fuel` |

Figures: `results/figures/research/enduse_partial_cracking_cost.png`
Data: `results/research/enduse/enduse_results.json`, `results/research/enduse/partial_cracking_scan.csv`

### H1-d: INCONCLUSIVE

**Sub-claim.** Cracking is most justified when the end use needs molecular hydrogen: the conversion loss is small when H2 is the product and larger when H2 is only an intermediate fuel.

**Conclusion.** When H2 is the product the cracker + PSA keeps 87.7 % of the NH3 LHV (Aspen). For power, routing NH3 through cracking and PSA gives 2.25 kWh/kg NH3 against 2.57 kWh/kg NH3 for direct combustion. The electricity comparison is fixed by construction: the H2 turbine is assumed to reach the direct-NH3 efficiency, so any cracker loss lowers the output. The H2-product efficiency is chemical energy and is not like-for-like with an electrical efficiency. The numbers quantify the cracking loss; they do not test whether cracking is most justified for H2 end uses.

**Conditions and rule.** Rule: SUPPORTED if the H2-product efficiency exceeds the direct power efficiency, cracking for power yields less electricity than direct combustion, and the H2 turbine efficiency is not an assumed copy of the direct-NH3 efficiency; otherwise INCONCLUSIVE (here the efficiency is copied, assumption eta_gt_gas). Conditions: stored Aspen baseline operating point, PSA recovery assumed. The comparison is between end uses; whether cracked H2 is competitive with other H2 sources is tested in H2.

**Key uncertainty (what would change the verdict).** Purification recovery at fuel-cell purity (not in the library) and NH3 price; neither changes the efficiency ranking.

**Uncertainty range.** H2 cost 3.92 USD/kg (industrial) to 4.26 USD/kg (Grade D candidate, lower bound) at the grey price.

- Singapore scenario: Jurong Island cracker supplying industrial or fuel-cell hydrogen from imported grey NH3 (Singapore price set).
- Aspen model: Stored Aspen Plus V15 baseline flowsheet (RGibbs cracker, FEHE, PSA split block) for the LHV efficiency.
- Python model: amcrax.enduse hydrogen pathways with amcrax.economics; purification workstream PSA_D_MB for Grade D.
- Case ids: baseline (stored Aspen), scn_fuel_cell_grade (stored Aspen), PSA_D_MB
- Validation: Aspen LHV efficiency matched within tolerance; stored LCOH reproduced; purification mass closure (enduse.json, purification.json). Validation status of the underlying models: results/research/validation/enduse.json: 40 pass, 0 fail, 5 informational; results/research/validation/purification.json: 4 pass, 0 fail, 4 informational.
- Input assumptions: PSA purity and recovery of the stored Aspen baseline are set by an assumed split (they support no purity claim).; Grade D cost is a lower bound: NH3 polishing and contaminants other than NH3, N2 and H2O not evaluated.
- Literature: `iso14687_2019` (ISO 14687:2019 grade limits); `ahmad2025gtcc` (turbine efficiencies)
- Limitations: No route other than cracking is evaluated for producing H2 from NH3; the comparison is between end uses, not between H2 sources (see H2 for SMR comparators).

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| NH3 LHV to H2 LHV, cracker + PSA | 0.8774 | fraction | aspen | `results/research/enduse/enduse_results.json` | `hydrogen_pathways/[id=h2_industrial]/efficiency_NH3_LHV_to_H2` |
| cost industrial H2 (99.9 %), stored Aspen baseline | 3.919 | USD/kg H2 | python | `results/research/enduse/enduse_results.json` | `hydrogen_pathways/[id=h2_industrial]/cost_USD_per_kg_at_grey_450` |
| cost Grade D candidate, PSA_D_MB at 350 bar (lower bound) | 4.264 | USD/kg H2 | python | `results/research/enduse/enduse_results.json` | `hydrogen_pathways/[id=h2_fuelcell_gradeD_purif_study]/cost_USD_per_kg_at_grey_450` |
| electricity per kg NH3, direct combustion | 2.565 | kWh/kg NH3 | python | `results/research/enduse/enduse_results.json` | `detour/kWh_electricity_per_kg_NH3_direct` |
| electricity per kg NH3, cracked + purified H2 | 2.251 | kWh/kg NH3 | python | `results/research/enduse/enduse_results.json` | `detour/kWh_electricity_per_kg_NH3_cracked_purified` |
| turbine efficiency on H2-rich fuel (copy of direct case) | 0.4964 | fraction | assumption | `results/research/enduse/assumptions.json` | `[name=eta_gt_gas]/value` |

Figures: `results/figures/research/enduse_hydrogen_cost_ci.png`, `results/figures/research/enduse_power_efficiency.png`
Data: `results/research/enduse/assumptions.json`, `results/research/enduse/enduse_results.json`, `results/research/enduse/pathway_table_hydrogen.csv`

## H2: INCONCLUSIVE

**Statement.** Feedstock: affordable, low-carbon ammonia is essential to economic and environmental competitiveness.

**Summary.** Ammonia price dominates hydrogen cost and only green (or very well-captured blue) ammonia cuts emissions against Singapore alternatives; but under current Singapore carbon pricing low carbon intensity earns no cost advantage, so affordable and low-carbon pull apart.

**Verdict conditions.** Hypothesis verdict from its rows: SUPPORTED if every row is SUPPORTED; CONTRADICTED if no row is SUPPORTED and at least half of the rows are CONTRADICTED; otherwise INCONCLUSIVE, with the mixed row outcomes stated in verdict_conditions. Row outcomes: SUPPORTED: H2-a, H2-b, H2-c, H2-d; CONTRADICTED: H2-e. Qualified verdict: the hypothesis holds only in the parts marked SUPPORTED, under each row's conclusion_conditions; rows marked CONTRADICTED are findings against the essay statement; INCONCLUSIVE rows are unresolved by the models.

### H2-a: SUPPORTED

**Sub-claim.** Ammonia feed cost dominates the cost of cracked hydrogen, so affordable ammonia is essential to economic competitiveness.

**Conclusion.** Feed NH3 is 3.04 of 3.61 USD/kg (84 %) and the NH3 price is the largest tornado bar (2.28 USD/kg). This is a computed share of an input price: it follows from the 6.76 kg NH3 needed per kg H2, and its size depends on the assumed price scenarios.

**Conditions and rule.** Rule: SUPPORTED if the NH3 price bar is the largest tornado swing and the feed share exceeds one half even at the low price bound. Conditions: price range 300-610 USD/t, AmCraX screening CAPEX, heat integration on.

**Key uncertainty (what would change the verdict).** CAPEX: Cho reports a lower feed share with a fuller plant boundary; a CAPEX several times higher would lower the share but the NH3 price would still be the largest single driver unless CAPEX uncertainty exceeds the price range.

**Uncertainty range.** Feed share 84 % at 450 USD/t and 81 % at the low end of the tornado range (300 USD/t); NH3 price swing 2.28 USD/kg against 0.40 USD/kg for the next parameter.

- Singapore scenario: Jurong Island cracker (stored Aspen baseline capacity), imported NH3 at the Singapore price scenarios (grey, blue, green 2050, green 2030, green current), heat integration on.
- Aspen model: Stored Aspen Plus V15 baseline (results/simulations/baseline.json): NH3 feed and fuel per kg H2.
- Python model: amcrax.economics.singapore.evaluate (equipment-level CAPEX screening estimate), tornado sensitivity.
- Case ids: baseline (stored Aspen), grey|heat_integration_on
- Validation: Stored LCOH reproduced exactly; cost-share closure; NH3 feed per kg H2 above the stoichiometric floor (economics.json). Validation status of the underlying models: results/research/validation/economics.json: 9 pass, 0 fail, 6 informational.
- Input assumptions: NH3 price scenarios and the 300-610 USD/t tornado range are inputs (Cho Table 8 and secondary web prices); the feed share is computed but scales with these assumed prices.; Equipment-level CAPEX is a feed-scaled screening estimate and probably optimistic, which raises the feed share.
- Literature: `cho2026nickel` (Cho et al. 2026: NH3 price range for sensitivity (Table 8) and feed share of LCOH); `sp_blue_ammonia_2025` (S&P Global 2025: blue ammonia prices (search-result text)); `argus_h2_markers` (Argus 2026: NE Asia SMR hydrogen cost marker (sample report issue 26-01, p. 2, incl. capex)); `sp_singapore_h2_2025` (S&P Global 2025: Singapore willingness to pay (search-result text))
- Limitations: Benchmark and price inputs partly from search-result text (secondary_web).; No product compression, NOx treatment or storage in the plant boundary.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| LCOH grey, HI on | 3.613 | USD/kg H2 | python | `results/research/singapore/scenario_results.json` | `results/grey\|heat_integration_on/lcoh_USD_per_kg` |
| feed NH3 cost component, grey | 3.040 | USD/kg H2 | python | `results/research/singapore/scenario_results.json` | `results/grey\|heat_integration_on/breakdown_USD_per_kg/ammonia_feed` |
| NH3 feed per kg H2 (Aspen activity) | 6.756 | kg/kg | aspen | `results/research/singapore/scenario_results.json` | `results/grey\|heat_integration_on/kg_nh3_feed_per_kg_h2` |
| tornado swing, NH3 price 300-610 USD/t | 2.279 | USD/kg H2 | python | `results/research/singapore/tornado.json` | `bars/[parameter=nh3_price_USD_per_t]/swing` |
| next-largest tornado swing (capacity x0.25-x4) | 0.3996 | USD/kg H2 | python | `results/research/singapore/tornado.json` | `bars/[parameter=capacity_scale]/swing` |

Figures: `results/figures/research/singapore_tornado.png`, `results/figures/research/singapore_cost_breakdown.png`, `results/figures/research/singapore_monte_carlo.png`
Data: `results/research/singapore/scenario_breakdown.csv`, `results/research/singapore/scenario_results.json`, `results/research/singapore/tornado.csv`, `results/research/singapore/tornado.json`

### H2-b: SUPPORTED

**Sub-claim.** Only affordable ammonia keeps cracked hydrogen competitive with the hydrogen benchmarks relevant to Singapore.

**Conclusion.** Cracked H2 matches the NE Asia SMR benchmark (3.06 USD/kg) at 375 USD/t NH3 and Singapore willingness to pay at 367 USD/t. Grey NH3 (450 USD/t) is above the SMR break-even; green 2030 (709) and green current (1000 USD/t, LCOH 7.66) are well above it, and green current is above even the blue-delivered break-even (775 USD/t). Competitiveness with the SMR benchmark requires NH3 at or below 375 USD/t.

**Conditions and rule.** Rule: SUPPORTED if the SMR break-even NH3 price is below both green price scenarios and the Monte Carlo p5 of green 2030 (vs SMR) and green current (vs blue delivered) stay above the benchmark. Conditional on the benchmark values.

**Key uncertainty (what would change the verdict).** The benchmark values (different bases, none a Singapore transaction price): a hydrogen value above the green-2030 LCOH, for example a low-carbon premium, would make green NH3 competitive.

**Uncertainty range.** Monte Carlo LCOH p5-p95: grey 2.85-4.43 USD/kg (straddling the 3.06 USD/kg SMR benchmark); green 2030 p5 4.30 USD/kg (above the SMR benchmark); green current p5 7.05 USD/kg (above the 6.00 USD/kg blue-delivered benchmark).

- Singapore scenario: Jurong Island cracker (stored Aspen baseline capacity), imported NH3 at the Singapore price scenarios (grey, blue, green 2050, green 2030, green current), heat integration on.
- Aspen model: Stored Aspen Plus V15 baseline activities.
- Python model: amcrax.economics.singapore.breakeven_nh3_price and Monte Carlo (n and seed in monte_carlo.json).
- Case ids: grey|heat_integration_on, green_2030|heat_integration_on, green_current|heat_integration_on
- Validation: Break-even consistency check (LCOH at the break-even price equals the benchmark) in economics.json. Validation status of the underlying models: results/research/validation/economics.json: 9 pass, 0 fail, 6 informational.
- Input assumptions: Hydrogen benchmarks in breakeven_ammonia_price.json have different bases and source qualities (listed per benchmark there); none is a Singapore transaction price.; NH3 price scenarios are inputs (data/singapore.yaml).
- Literature: `cho2026nickel` (Cho et al. 2026: NH3 price range for sensitivity (Table 8) and feed share of LCOH); `sp_blue_ammonia_2025` (S&P Global 2025: blue ammonia prices (search-result text)); `argus_h2_markers` (Argus 2026: NE Asia SMR hydrogen cost marker (sample report issue 26-01, p. 2, incl. capex)); `sp_singapore_h2_2025` (S&P Global 2025: Singapore willingness to pay (search-result text)); `ace_h2_delivered` (ASEAN Centre for Energy: delivered blue/green H2 cost to East Asia (search-result text))
- Limitations: Break-even is for the cracker gate; landed cost and product compression excluded.; Constant prices, pre-tax NPV.; Benchmarks are read from breakeven_ammonia_price.json as stored at build time; their sources are listed there.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| break-even NH3 price vs NE Asia SMR benchmark | 374.8 | USD/t | python | `results/research/singapore/breakeven_ammonia_price.json` | `results/heat_integration_on/ne_asia_smr_production_cost/breakeven_nh3_USD_per_t` |
| NE Asia SMR benchmark | 3.060 | USD/kg H2 | literature | `results/research/singapore/breakeven_ammonia_price.json` | `results/heat_integration_on/ne_asia_smr_production_cost/h2_price_USD_per_kg` |
| break-even NH3 price vs Singapore willingness to pay | 366.6 | USD/t | python | `results/research/singapore/breakeven_ammonia_price.json` | `results/heat_integration_on/sg_low_carbon_willingness_to_pay/breakeven_nh3_USD_per_t` |
| break-even NH3 price vs blue H2 delivered East Asia | 774.8 | USD/t | python | `results/research/singapore/breakeven_ammonia_price.json` | `results/heat_integration_on/blue_delivered_east_asia/breakeven_nh3_USD_per_t` |
| grey NH3 price | 450 | USD/t | assumption | `results/research/singapore/scenario_results.json` | `results/grey\|heat_integration_on/nh3_price_USD_per_t` |
| green 2030 NH3 price | 709 | USD/t | assumption | `results/research/singapore/scenario_results.json` | `results/green_2030\|heat_integration_on/nh3_price_USD_per_t` |
| green current NH3 price | 1000 | USD/t | assumption | `results/research/singapore/scenario_results.json` | `results/green_current\|heat_integration_on/nh3_price_USD_per_t` |
| LCOH green current | 7.656 | USD/kg H2 | python | `results/research/singapore/scenario_results.json` | `results/green_current\|heat_integration_on/lcoh_USD_per_kg` |
| Monte Carlo LCOH p95, grey | 4.432 | USD/kg H2 | python | `results/research/singapore/monte_carlo.json` | `results/grey/lcoh_p95` |
| Monte Carlo LCOH p5, green current | 7.045 | USD/kg H2 | python | `results/research/singapore/monte_carlo.json` | `results/green_current/lcoh_p5` |
| Monte Carlo LCOH p5, grey | 2.849 | USD/kg H2 | python | `results/research/singapore/monte_carlo.json` | `results/grey/lcoh_p5` |
| Monte Carlo LCOH p5, green 2030 | 4.300 | USD/kg H2 | python | `results/research/singapore/monte_carlo.json` | `results/green_2030/lcoh_p5` |

Figures: `results/figures/research/singapore_breakeven.png`, `results/figures/research/singapore_monte_carlo.png`
Data: `results/research/singapore/breakeven_ammonia_price.json`, `results/research/singapore/monte_carlo.json`, `results/research/singapore/scenario_results.json`

### H2-c: SUPPORTED

**Sub-claim.** Low-carbon ammonia is essential for environmental competitiveness of ammonia-based power in Singapore.

**Conclusion.** Direct NH3 power emits 129 kg CO2e/MWh with green NH3 and 474 with blue (Lee v1), against 367 for NG CCGT and 402 for the grid. Only NH3 below 0.89 kg CO2e/kg NH3 at the gate cuts emissions: green (0.28) does, blue v1 (1.16) and grey (2.60) do not.

**Conditions and rule.** Rule: SUPPORTED if green is below and blue v1 and grey are above the break-even and the Monte Carlo probability for blue is below 0.05 (method threshold). Conditions: GWP100, 5000 km, CCGT efficiency assumption.

**Key uncertainty (what would change the verdict).** Blue NH3 capture and leakage: Lee v2 blue (0.77) is below the break-even, so blue with near-full process and flue-gas capture and low leakage would also qualify.

**Uncertainty range.** Break-even gate EF 0.89 (vs NG CCGT) and 0.98 (vs grid) kg CO2e/kg NH3; Monte Carlo probability that blue direct power beats NG CCGT 0.0022.

- Singapore scenario: Imported NH3 shipped 5000 km (scenario distance) and burned in a Jurong Island CCGT; comparators NG CCGT and the EMA grid average.
- Aspen model: No Aspen model for combustion: Python/literature only (NH3 per MWh from Ahmad-calibrated efficiency).
- Python model: amcrax.environmental.lca (GWP100 AR6) and its Monte Carlo (uniform over stated ranges).
- Case ids: routes: green, blue, blue_v2, grey, direct_NH3_CCGT
- Validation: Lee v1 and v2 factors reproduced exactly; existing environmental baseline reproduced; breakdown sums (lca.json). Validation status of the underlying models: results/research/validation/lca.json: 7 pass, 0 fail, 4 informational.
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

Figures: `results/figures/research/lca_power_by_route.png`, `results/figures/research/lca_breakeven_power.png`, `results/figures/research/lca_sensitivity_blue_power.png`
Data: `results/research/lca/lca_breakeven.csv`, `results/research/lca/lca_results.json`, `results/research/lca/lca_routes.csv`

### H2-d: SUPPORTED

**Sub-claim.** Low-carbon ammonia is essential for cracked hydrogen to have lower carbon intensity than fossil hydrogen.

**Conclusion.** Grey-NH3 hydrogen (19.5 kg CO2e/kg) is worse than unabated SMR (11.0); blue (8.9) beats it only narrowly and never beats SMR + CCS (3.5); green (2.4) beats both. Break-even gate EF 1.44 (SMR) and 0.42 (SMR + CCS) kg CO2e/kg NH3.

**Conditions and rule.** Rule: SUPPORTED if grey is above unabated SMR, green is below SMR + CCS and blue never beats SMR + CCS in the Monte Carlo. Conditions: GWP100, 5000 km, comparator values as stated.

**Key uncertainty (what would change the verdict).** The SMR + CCS comparator (low confidence) and blue capture rate; a higher SMR + CCS value would let blue NH3 compete.

**Uncertainty range.** Blue H2 is below unabated SMR in 25 % of Monte Carlo draws and below SMR + CCS in 0 %.

- Singapore scenario: Industrial H2 from a Jurong Island cracker fed with imported NH3 (5000 km), compared with SMR hydrogen.
- Aspen model: Stored Aspen Plus V15 baseline: NH3 per kg H2 and process electricity.
- Python model: amcrax.environmental.lca and Monte Carlo.
- Case ids: baseline (stored Aspen), routes: green, blue, grey
- Validation: As H2-c (lca.json). Validation status of the underlying models: results/research/validation/lca.json: 7 pass, 0 fail, 4 informational.
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

Figures: `results/figures/research/lca_h2_by_route.png`
Data: `results/research/lca/lca_breakeven.csv`, `results/research/lca/lca_results.json`

### H2-e: CONTRADICTED

**Sub-claim.** Low-carbon ammonia is essential to economic competitiveness (that is, low carbon intensity is rewarded in the Singapore cost of hydrogen).

**Conclusion.** Under Singapore's carbon tax (45 SGD/t, Scope 1) the cracker pays 0.00 USD/kg H2 of tax and direct NH3 power, below the facility threshold, pays none, so the tax does not reward low-carbon NH3. Green-2030 NH3 raises LCOH from 3.61 to 5.52 USD/kg. Affordability and low carbon intensity therefore pull in opposite directions at current prices and policy.

**Conditions and rule.** Rule: CONTRADICTED if the carbon tax contributes zero to LCOH, its tornado swing is zero and the low-carbon price scenario raises LCOH. Holds only under current Singapore policy; the environmental part of H2 is assessed in H2-c and H2-d.

**Key uncertainty (what would change the verdict).** Policy: a carbon price on imported embedded emissions, a low-carbon hydrogen mandate or a buyer premium (for example willingness to pay) would reward low-carbon NH3.

**Uncertainty range.** Carbon-tax swing in LCOH 0.00 USD/kg. Direct NH3 power: its only in-scope emission is simulated N2O (one Chemkin source, assumed exhaust basis), far below the NEA facility threshold, so its carbon-tax liability is zero.

- Singapore scenario: Jurong Island cracker (stored Aspen baseline capacity), imported NH3 at the Singapore price scenarios (grey, blue, green 2050, green 2030, green current), heat integration on. Singapore carbon tax at the current legislated rate, Scope 1 only, with the NEA facility threshold.
- Aspen model: Stored Aspen Plus V15 baseline: direct emissions of the NH3-fired cracker (no CO2).
- Python model: amcrax.economics.singapore carbon-tax treatment; amcrax.environmental.lca carbon_tax_sg.
- Case ids: grey|heat_integration_on, green_2030|heat_integration_on
- Validation: Zero tax on NH3-fired heat and gas-fired heat below the threshold (economics.json). Validation status of the underlying models: results/research/validation/economics.json: 9 pass, 0 fail, 6 informational; results/research/validation/lca.json: 7 pass, 0 fail, 4 informational.
- Input assumptions: Upstream and shipping emissions are outside Singapore's carbon-tax base (NEA rules).; N2O factor from one simulated source (Ahmad).
- Literature: `nea_carbon_tax` (NEA carbon tax rates, threshold and covered gases)
- Limitations: Only current, legislated Singapore carbon-tax rules; no low-carbon premium or contract-for-difference modelled.; The 'hypothetical' gas-heat carbon-tax heatmap ignores the threshold and is not used here.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| Singapore carbon tax rate used | 45 | SGD/t CO2e | literature | `results/research/lca/lca_results.json` | `carbon_tax_sg/rate_SGD_per_t` |
| carbon tax in LCOH, grey, NH3-fired heat | 0 | USD/kg H2 | python | `results/research/singapore/scenario_results.json` | `results/grey\|heat_integration_on/breakdown_USD_per_kg/carbon_tax` |
| tornado swing, carbon tax | 0 | USD/kg H2 | python | `results/research/singapore/tornado.json` | `bars/[parameter=carbon_tax_SGD_per_t]/swing` |
| LCOH grey | 3.613 | USD/kg H2 | python | `results/research/singapore/scenario_results.json` | `results/grey\|heat_integration_on/lcoh_USD_per_kg` |
| LCOH green 2030 | 5.517 | USD/kg H2 | python | `results/research/singapore/scenario_results.json` | `results/green_2030\|heat_integration_on/lcoh_USD_per_kg` |

Figures: `results/figures/research/singapore_heatmap_nh3_price_carbon_tax.png`
Data: `results/research/lca/lca_results.json`, `results/research/singapore/heatmap_nh3_price_x_carbon_tax_nh3_heat.csv`, `results/research/singapore/scenario_results.json`, `results/research/singapore/tornado.json`

## H3: INCONCLUSIVE

**Statement.** Catalyst and heat integration: low-temperature, high-activity catalysts with effective heat integration reduce energy use and can outweigh higher catalyst cost.

**Summary.** Lower temperature and heat integration both cut energy, heat integration by far the more; the catalyst cost question is unresolved because the differences are inside the uncertainty band, and Cho's fuel and REC findings are not reproduced on AmCraX boundaries.

**Verdict conditions.** Hypothesis verdict from its rows: SUPPORTED if every row is SUPPORTED; CONTRADICTED if no row is SUPPORTED and at least half of the rows are CONTRADICTED; otherwise INCONCLUSIVE, with the mixed row outcomes stated in verdict_conditions. Row outcomes: SUPPORTED: H3-a, H3-d; INCONCLUSIVE: H3-b, H3-c, H3-e, H3-f. Qualified verdict: the hypothesis holds only in the parts marked SUPPORTED, under each row's conclusion_conditions; rows marked CONTRADICTED are findings against the essay statement; INCONCLUSIVE rows are unresolved by the models.

### H3-a: SUPPORTED

**Sub-claim.** Energy half of the catalyst claim: at equal conversion, running the cracker at the lower temperature that a more active catalyst allows reduces energy use.

**Conclusion.** At equal conversion the lower-temperature case needs less external heating (2221 vs 2259 kW with HI; 2691 vs 2862 kW without), but the LHV efficiency barely moves (0.8755 vs 0.8746). The energy saving is real but small once heat is integrated.

**Conditions and rule.** Rule: SUPPORTED if the lower-temperature Aspen case has lower external heating with and without HI and a lower fired duty. Conditions: 100 kmol/h liquid NH3 (0.2 mol% H2O), 20 bar, 95 % NH3 conversion for every catalyst, PSA recovery 0.85; 100 kg catalyst; the AmCraX FEHE flowsheet.

**Key uncertainty (what would change the verdict).** Which metric is meant by 'energy use': total external heating changes by 1.7 % with HI, the fired supplementary duty by 17 %; LHV efficiency is practically unchanged.

**Uncertainty range.** External heating 1.7 % lower with HI and 6.0 % lower without HI for 499 vs 594 degC; fired duty (after tail-gas firing) 17 % lower with HI and 20 % lower without.

- Singapore scenario: Jurong Island cracker; 100 kmol/h liquid NH3 (0.2 mol% H2O), 20 bar, 95 % NH3 conversion for every catalyst, PSA recovery 0.85; grey NH3 price scenario; amcrax.economics.singapore.evaluate, grey 450 USD/t, catalyst W*price/lifetime (2 yr).
- Aspen model: Aspen Plus V15 integrated flowsheet with kinetic RPLUG cracker (ci_* cases, with and without heat integration), 100 kg catalyst, each catalyst at its operating temperature as defined in aspen_kinetic/catalyst_comparison.json.
- Python model: amcrax.research.catalyst_comparison fired-duty post-processing (tail-gas firing, furnace efficiency).
- Case ids: ci_kum_T499_P20_W100_hi, ci_kum_T499_P20_W100_nohi, ci_tru_T522_P20_W100_hi, ci_tru_T522_P20_W100_nohi, ci_luc5_T572_P20_W100_hi, ci_luc5_T572_P20_W100_nohi, ci_luc25_T576_P20_W100_hi, ci_luc25_T576_P20_W100_nohi, ci_tni_T594_P20_W100_hi, ci_tni_T594_P20_W100_nohi
- Validation: Aspen RPLUG vs Python PFR (|dX| below tolerance), integrated cases not above RGibbs equilibrium; Python vs Aspen heat duties (aspen_kinetic.json, catalyst_comparison.json). Validation status of the underlying models: results/research/validation/aspen_kinetic.json: 161 pass, 3 fail, 19 informational (failures: cat_nire_ceo2_5ni1ru_lucentini_lhhw_below_equilibrium, cat_nire_ceo2_2p5ni0p5ru_lucentini_lhhw_below_equilibrium, cat_ru_takahashi_microkinetic_below_equilibrium); results/research/validation/catalyst_comparison.json: 66 pass, 5 fail, 4 informational (failures: HCAT-ASPY-Ru/Al2O3-HI-heat, HCAT-ASPY-5Ni1Ru/CeO2-HI-heat, HCAT-ASPY-2.5Ni0.5Ru/CeO2-HI-heat, HCAT-ASPY-Ni/MgO-HI-heat, HCAT-ASPY-Ru/MgO-HI-heat).
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

Figures: `results/figures/research/catalyst_heat_duty.png`, `results/figures/research/catalyst_cost_breakdown.png`, `results/figures/research/aspen_kinetic_operating_point.png`
Aspen screenshots: `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__01_flowsheet.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__02_reactions_kinetic.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__03_reactions_kinetic_tab.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__05_reactor_configuration.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__06_reactor_catalyst.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__08_reactor_results.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__09_reactor_profiles.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__10_run_status.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__11_components.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__12_property_method.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__13_stream_results.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__14_psa_block.png`, `docs/images/aspen_evidence/cs_OP_tni_T594_P20_W100__02_reactions_kinetic.png`, `docs/images/aspen_evidence/cs_OP_tni_T594_P20_W100__03_reactions_kinetic_tab.png`
Data: `results/research/aspen_kinetic/catalyst_comparison.json`, `results/research/aspen_kinetic/catalyst_integrated.csv`, `results/research/aspen_kinetic/ci_kum_T499_P20_W100_hi.json`, `results/research/aspen_kinetic/ci_kum_T499_P20_W100_nohi.json`, `results/research/aspen_kinetic/ci_luc25_T576_P20_W100_hi.json`, `results/research/aspen_kinetic/ci_luc25_T576_P20_W100_nohi.json`, `results/research/aspen_kinetic/ci_luc5_T572_P20_W100_hi.json`, `results/research/aspen_kinetic/ci_luc5_T572_P20_W100_nohi.json`, `results/research/aspen_kinetic/ci_tni_T594_P20_W100_hi.json`, `results/research/aspen_kinetic/ci_tni_T594_P20_W100_nohi.json`, `results/research/aspen_kinetic/ci_tru_T522_P20_W100_hi.json`, `results/research/aspen_kinetic/ci_tru_T522_P20_W100_nohi.json`, `results/research/catalyst_comparison/assumptions.json`, `results/research/catalyst_comparison/catalyst_comparison.json`

### H3-b: INCONCLUSIVE

**Sub-claim.** Low-temperature, high-activity catalysts allow the cracker to run at a lower temperature for the same duty.

**Conclusion.** Within the fitted range (1 atm) a more active catalyst lowers the temperature for 99 % conversion (525 vs 607 degC, Ru/MgO vs Ni/MgO). At the 20 bar design point the gap (498 to 593 degC for 95 %) comes from extrapolated laws, and for 99 % conversion activity cannot lower the temperature at all (equilibrium-limited for every catalyst).

**Conditions and rule.** Rule: INCONCLUSIVE if no 20 bar operating point lies within its law's fitted range. The 1 atm result is within range but is not the Singapore design condition, and the Takahashi law fails its own prediction check.

**Key uncertainty (what would change the verdict).** Rate laws at 20 bar: every law is extrapolated beyond its fitted pressure (and for Kum temperature) range; a pressure-valid law, or kinetics measured on industrial pellets, could change the temperature gaps either way.

**Uncertainty range.** At 20 bar and 95 %: Ru/Al2O3 498, Ru/MgO 522, 5Ni1Ru/CeO2 572, 2.5Ni0.5Ru/CeO2 576, Ni/MgO 593 degC. At 99 % every catalyst needs at least 684.8 degC (equilibrium). The Lucentini Ek confidence interval alone moves the predicted conversion over most of its range (kinetics validation JSON).

- Singapore scenario: Jurong Island cracker; 100 kmol/h liquid NH3 (0.2 mol% H2O), 20 bar, 95 % NH3 conversion for every catalyst, PSA recovery 0.85; grey NH3 price scenario; amcrax.economics.singapore.evaluate, grey 450 USD/t, catalyst W*price/lifetime (2 yr).
- Aspen model: Aspen standalone RPLUG operating-point checks (cs_OP_* cases) confirm the Python temperatures.
- Python model: amcrax.kinetics laws in the isothermal PFR (study_temperature_for_target_conversion).
- Case ids: cs_OP_kum_T499_P20_W100, cs_OP_tru_T522_P20_W100, cs_OP_luc5_T572_P20_W100, cs_OP_luc25_T576_P20_W100, cs_OP_tni_T594_P20_W100
- Validation: Lucentini Table 1 points reproduced (consistency, not independent); Takahashi predictions carried over as failures; Aspen native laws vs spec points (kinetics.json, aspen_kinetic.json). Validation status of the underlying models: results/research/validation/kinetics.json: 8 pass, 2 fail, 3 informational (failures: EXISTING-KIN-NI-PRED, EXISTING-KIN-RU-PRED); results/research/validation/aspen_kinetic.json: 161 pass, 3 fail, 19 informational (failures: cat_nire_ceo2_5ni1ru_lucentini_lhhw_below_equilibrium, cat_nire_ceo2_2p5ni0p5ru_lucentini_lhhw_below_equilibrium, cat_ru_takahashi_microkinetic_below_equilibrium).
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

Figures: `results/figures/research/kinetics_conversion_vs_T.png`, `results/figures/research/aspen_kinetic_conversion_vs_T.png`
Aspen screenshots: `docs/images/aspen_evidence/cs_OP_tni_T594_P20_W100__02_reactions_kinetic.png`, `docs/images/aspen_evidence/cs_OP_tni_T594_P20_W100__03_reactions_kinetic_tab.png`
Data: `results/research/aspen_kinetic/catalyst_standalone_runs.csv`, `results/research/kinetics/study_temperature_for_target_conversion.csv`, `results/research/kinetics/study_temperature_for_target_conversion.json`

### H3-c: INCONCLUSIVE

**Sub-claim.** The energy saved by a low-temperature, high-activity catalyst can outweigh its higher catalyst cost.

**Conclusion.** At cost-optimal temperatures Ni/MgO (3.6644) and Ru/Al2O3 (3.6648 USD/kg) are practically equal; at equal 100 kg inventory Ru is dearer by 0.006 USD/kg with HI and cheaper by 0.050 without. The differences are far inside the economic uncertainty, so the model cannot rank the catalysts on cost and the claim is neither shown nor refuted. The Ru break-even price against an optimised Ni design (498 USD/kg, against the 542 USD/kg proxy) lies inside the same model resolution; against Ni fixed at Cho's temperature it is 7390 USD/kg.

**Conditions and rule.** Rule: INCONCLUSIVE when the largest catalyst LCOH difference is smaller than the Monte Carlo p5-p95 LCOH band; otherwise the sign of the cost-optimal difference decides. Conditions: 100 kmol/h liquid NH3 (0.2 mol% H2O), 20 bar, 95 % NH3 conversion for every catalyst, PSA recovery 0.85; grey NH3; proxy catalyst prices.

**Key uncertainty (what would change the verdict).** The Ni reference design: against Ni forced to 735 degC (Cho's temperature) Ru pays at up to 7390 USD/kg; against a Ni design optimised on the Takahashi law the break-even is 498 USD/kg. A pressure-valid Ni law and a sourced Ru price would settle it.

**Uncertainty range.** Catalyst LCOH differences at most 0.017 USD/kg against a Monte Carlo p5-p95 band of 1.58 USD/kg; best catalyst unchanged in 21 of 32 cases.

- Singapore scenario: Jurong Island cracker; 100 kmol/h liquid NH3 (0.2 mol% H2O), 20 bar, 95 % NH3 conversion for every catalyst, PSA recovery 0.85; grey NH3 price scenario; amcrax.economics.singapore.evaluate, grey 450 USD/t, catalyst W*price/lifetime (2 yr).
- Aspen model: Aspen duties for the fixed-inventory comparison (ci_* cases); no Aspen run at the Python cost-optimal temperatures (those rows are Python only).
- Python model: amcrax.research.catalyst_comparison: W(T) from PFR kinetics, T_opt = argmin LCOH, heat_integration configuration (c), amcrax.economics.singapore.evaluate.
- Case ids: ci_kum_T499_P20_W100_hi, ci_kum_T499_P20_W100_nohi, ci_tru_T522_P20_W100_hi, ci_tru_T522_P20_W100_nohi, ci_luc5_T572_P20_W100_hi, ci_luc5_T572_P20_W100_nohi, ci_luc25_T576_P20_W100_hi, ci_luc25_T576_P20_W100_nohi, ci_tni_T594_P20_W100_hi, ci_tni_T594_P20_W100_nohi
- Validation: Analytic catalyst-cost addition matches full evaluate(); T_opt interior to the grid; mass and energy closure (catalyst_comparison.json). Validation status of the underlying models: results/research/validation/catalyst_comparison.json: 66 pass, 5 fail, 4 informational (failures: HCAT-ASPY-Ru/Al2O3-HI-heat, HCAT-ASPY-5Ni1Ru/CeO2-HI-heat, HCAT-ASPY-2.5Ni0.5Ru/CeO2-HI-heat, HCAT-ASPY-Ni/MgO-HI-heat, HCAT-ASPY-Ru/MgO-HI-heat); results/research/validation/kinetics.json: 8 pass, 2 fail, 3 informational (failures: EXISTING-KIN-NI-PRED, EXISTING-KIN-RU-PRED).
- Input assumptions: Catalyst prices: Cho Ni 33.4 and Ru 542 USD/kg used as proxies, 2-year life (assumption); no sourced NiRu/CeO2 price.; CAPEX does not respond to reactor volume, exchanger area or temperature (volume scaling is a sensitivity only).; Furnace efficiency and thermal-loss allowance as in H3-a (assumptions).
- Literature: `kum2026heatintegrated` (Kum et al. 2026: Ru/Al2O3 Temkin-Pyzhev law); `takahashi2016kinetic` (Takahashi & Fujitani 2016: Ni/MgO and Ru/MgO microkinetics); `lucentini2021nirukinetic` (Lucentini et al. 2021: Ni-Ru/CeO2 LHHW (Table 3)); `cho2026nickel` (Cho et al. 2026: Ni and Ru catalyst prices)
- Limitations: Ni/MgO law fails its prediction check (EXISTING-KIN-NI-PRED).; No sourced price for NiRu/CeO2.; N2O not quantified.; All rate laws are extrapolated to 20 bar from their fit pressure (1 atm; Kum: 10 bar); the Takahashi laws are evaluated on a mole-fraction basis and the Lucentini laws on concentrations; the Ni/MgO law fails its own validation (EXISTING-KIN-NI-PRED). No catalyst ranking at 20 bar is a property of the catalysts.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| LCOH at cost-optimal T, Ru/Al2O3, HI | 3.665 | USD/kg H2 | python | `results/research/catalyst_comparison/catalyst_comparison.json` | `findings/cost_optimal_python/Ru~1Al2O3/HI/lcoh_USD_per_kg` |
| LCOH at cost-optimal T, Ni/MgO, HI | 3.664 | USD/kg H2 | python | `results/research/catalyst_comparison/catalyst_comparison.json` | `findings/cost_optimal_python/Ni~1MgO/HI/lcoh_USD_per_kg` |
| LCOH Ru/Al2O3 minus Ni/MgO, fixed 100 kg, HI (Aspen duties) | 0.006167 | USD/kg H2 | python | `results/research/catalyst_comparison/catalyst_comparison.json` | `findings/fixed_inventory_100kg_aspen/Ru_Al2O3_minus_Ni_lcoh_HI` |
| LCOH Ru/Al2O3 minus Ni/MgO, fixed 100 kg, no HI (Aspen duties) | -0.04952 | USD/kg H2 | python | `results/research/catalyst_comparison/catalyst_comparison.json` | `findings/fixed_inventory_100kg_aspen/Ru_Al2O3_minus_Ni_lcoh_noHI` |
| largest \|best low-T catalyst minus Ni\| over 32 sensitivity cases | 0.01679 | USD/kg H2 | python | `results/research/catalyst_comparison/catalyst_comparison.json` | `findings/ranking_robustness/max_abs_best_low_T_minus_Ni_USD_per_kg` |
| cases with unchanged best catalyst | 21 | count | python | `results/research/catalyst_comparison/catalyst_comparison.json` | `findings/ranking_robustness/n_same_best_as_base` |
| sensitivity cases | 32 | count | python | `results/research/catalyst_comparison/catalyst_comparison.json` | `findings/ranking_robustness/n_cases` |
| break-even Ru/Al2O3 price vs Ni/MgO at its cost optimum | 498.2 | USD/kg | python | `results/research/catalyst_comparison/catalyst_comparison.json` | `findings/breakeven_price/[catalyst=Ru~1Al2O3 (Kum);reference=Ni~1MgO (Takahashi) at its cost-optimal T]/breakeven_price_USD_per_kg` |
| break-even Ru/Al2O3 price vs Ni/MgO fixed at 735 degC | 7390.4 | USD/kg | python | `results/research/catalyst_comparison/catalyst_comparison.json` | `findings/breakeven_price/[catalyst=Ru~1Al2O3 (Kum);reference=Ni~1MgO fixed at 735 degC]/breakeven_price_USD_per_kg` |
| Monte Carlo LCOH p95, grey (economic uncertainty band, upper) | 4.432 | USD/kg H2 | python | `results/research/singapore/monte_carlo.json` | `results/grey/lcoh_p95` |
| Monte Carlo LCOH p5, grey (economic uncertainty band, lower) | 2.849 | USD/kg H2 | python | `results/research/singapore/monte_carlo.json` | `results/grey/lcoh_p5` |
| Ni catalyst price (Cho, proxy) | 33.400 | USD/kg | assumption | `results/research/catalyst_comparison/assumptions.json` | `[name=catalyst_price_Ni]/value` |
| Ru catalyst price (Cho, proxy; also used for NiRu/CeO2) | 542 | USD/kg | assumption | `results/research/catalyst_comparison/assumptions.json` | `[name=catalyst_price_Ru]/value` |
| catalyst lifetime | 2 | yr | assumption | `results/research/catalyst_comparison/assumptions.json` | `[name=catalyst_lifetime]/value` |

Figures: `results/figures/research/catalyst_breakeven_price.png`, `results/figures/research/catalyst_ranking_robustness.png`, `results/figures/research/catalyst_cost_breakdown.png`
Data: `results/research/catalyst_comparison/assumptions.json`, `results/research/catalyst_comparison/catalyst_breakeven_price.json`, `results/research/catalyst_comparison/catalyst_comparison.csv`, `results/research/catalyst_comparison/catalyst_comparison.json`, `results/research/catalyst_comparison/catalyst_design_curves.csv`, `results/research/catalyst_comparison/catalyst_ranking_robustness.json`, `results/research/singapore/monte_carlo.json`

### H3-d: SUPPORTED

**Sub-claim.** Effective heat integration reduces energy use (and cost) of the cracker, and matters more than the catalyst's temperature.

**Conclusion.** Heat integration lowers external heating for every catalyst (Ru/Al2O3 469 kW, Ru/MgO 501 kW, 5Ni1Ru/CeO2 572 kW, 2.5Ni0.5Ru/CeO2 578 kW, Ni/MgO 604 kW; baseline 2293 vs 2905 kW) and LCOH by 0.21 USD/kg (an upper bound, because exchanger capital is not costed), an order of magnitude more than the catalyst choice. This holds on AmCraX boundaries only; it does not show that low-temperature catalysts are unnecessary in general. It also shrinks the energy advantage of low-temperature operation (see H3-a).

**Conditions and rule.** Rule: SUPPORTED if HI lowers external heating for every catalyst and its LCOH effect exceeds the largest between-catalyst LCOH difference. Conditions: AmCraX FEHE flowsheet, exchanger capital not costed.

**Key uncertainty (what would change the verdict).** Exchanger capital (not costed): a large FEHE cost could cut the net saving; the pinch target (catalyst_pinch_dTmin.csv) shows further scope with a better exchanger network.

**Uncertainty range.** Heat integration saves 469-604 kW of external heating across the five catalysts; LCOH saving 0.21 USD/kg against at most 0.017 USD/kg between catalysts.

- Singapore scenario: Jurong Island cracker; 100 kmol/h liquid NH3 (0.2 mol% H2O), 20 bar, 95 % NH3 conversion for every catalyst, PSA recovery 0.85; grey NH3 price scenario; amcrax.economics.singapore.evaluate, grey 450 USD/t, catalyst W*price/lifetime (2 yr).
- Aspen model: Aspen Plus V15 integrated flowsheets with and without FEHE (ci_* cases) and the stored RGibbs baseline (rgibbs_baseline_600C).
- Python model: amcrax.heat_integration pinch analysis (catalyst_pinch_dTmin.csv); amcrax.economics.singapore tornado.
- Case ids: ci_kum_T499_P20_W100_hi, ci_kum_T499_P20_W100_nohi, ci_tru_T522_P20_W100_hi, ci_tru_T522_P20_W100_nohi, ci_luc5_T572_P20_W100_hi, ci_luc5_T572_P20_W100_nohi, ci_luc25_T576_P20_W100_hi, ci_luc25_T576_P20_W100_nohi, ci_tni_T594_P20_W100_hi, ci_tni_T594_P20_W100_nohi, baseline (stored Aspen), baseline_no_hi (stored Aspen)
- Validation: Pinch baseline reproduced (HCAT-PINCH-BASELINE); Python vs Aspen external heating within tolerance, FEHE recovered duty outside tolerance (HCAT-ASPY-*-HI-heat). Validation status of the underlying models: results/research/validation/aspen_kinetic.json: 161 pass, 3 fail, 19 informational (failures: cat_nire_ceo2_5ni1ru_lucentini_lhhw_below_equilibrium, cat_nire_ceo2_2p5ni0p5ru_lucentini_lhhw_below_equilibrium, cat_ru_takahashi_microkinetic_below_equilibrium); results/research/validation/catalyst_comparison.json: 66 pass, 5 fail, 4 informational (failures: HCAT-ASPY-Ru/Al2O3-HI-heat, HCAT-ASPY-5Ni1Ru/CeO2-HI-heat, HCAT-ASPY-2.5Ni0.5Ru/CeO2-HI-heat, HCAT-ASPY-Ni/MgO-HI-heat, HCAT-ASPY-Ru/MgO-HI-heat); results/research/validation/economics.json: 9 pass, 0 fail, 6 informational.
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

Figures: `results/figures/research/catalyst_heat_duty.png`, `results/figures/research/singapore_tornado.png`
Aspen screenshots: `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__01_flowsheet.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__02_reactions_kinetic.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__03_reactions_kinetic_tab.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__05_reactor_configuration.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__06_reactor_catalyst.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__08_reactor_results.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__09_reactor_profiles.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__10_run_status.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__11_components.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__12_property_method.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__13_stream_results.png`, `docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__14_psa_block.png`, `docs/images/aspen_evidence/cs_OP_tni_T594_P20_W100__02_reactions_kinetic.png`, `docs/images/aspen_evidence/cs_OP_tni_T594_P20_W100__03_reactions_kinetic_tab.png`
Data: `results/research/aspen_kinetic/catalyst_comparison.json`, `results/research/aspen_kinetic/catalyst_integrated.csv`, `results/research/catalyst_comparison/catalyst_pinch_dTmin.csv`, `results/research/singapore/tornado.json`

### H3-e: INCONCLUSIVE

**Sub-claim.** Cho et al. (2026): the Ru process at 567 degC needs no supplementary fuel while the Ni process at 736 degC burns supplementary NH3.

**Conclusion.** Not reproduced on AmCraX boundaries: Cho reports 0.0 kmol/h fuel for Ru and 1.736 kmol/h for Ni, whereas here both designs need supplementary fuel at PSA 0.85 and neither does at PSA 0.756. PSA recovery, not the catalyst, decides whether supplementary fuel is needed.

**Conditions and rule.** Rule: CONTRADICTED only if the Ru design needs supplementary fuel on a boundary like-for-like with Cho's; the AmCraX rebuild lacks Cho's compression, recycle, TSA, expander and SCR units and uses proxy kinetics, so a mismatch is INCONCLUSIVE (not reproduced on AmCraX boundaries). It does not show that Cho's flowsheet is wrong.

**Key uncertainty (what would change the verdict).** Cho's boiler, compression, H2 recycle and expander units, which AmCraX does not have; with them the heat balance and the role of the catalyst could differ.

**Uncertainty range.** At PSA 0.85 both designs need supplementary NH3 (Ni 161, Ru 152 kg/h); at Cho's PSA 0.756 the tail gas covers the process heat for both (pinch import zero; only the thermal-loss allowance remains).

- Singapore scenario: Cho's operating points rebuilt on AmCraX boundaries (conversion 0.97, Cho economic inputs).
- Aspen model: No Aspen run at Cho's operating points: Python only (heat balance calibrated against the Aspen ci_* cases).
- Python model: amcrax.research.catalyst_comparison Cho rebuild (catalyst_cho_comparison.json).
- Case ids: Ni_735.52C_24.34bar, RuAl2O3_566.69C_10bar
- Validation: Cho REC-direction items recorded as informational (catalyst_comparison.json). Validation status of the underlying models: results/research/validation/catalyst_comparison.json: 66 pass, 5 fail, 4 informational (failures: HCAT-ASPY-Ru/Al2O3-HI-heat, HCAT-ASPY-5Ni1Ru/CeO2-HI-heat, HCAT-ASPY-2.5Ni0.5Ru/CeO2-HI-heat, HCAT-ASPY-Ni/MgO-HI-heat, HCAT-ASPY-Ru/MgO-HI-heat).
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

Data: `results/research/catalyst_comparison/catalyst_cho_comparison.csv`, `results/research/catalyst_comparison/catalyst_cho_comparison.json`

### H3-f: INCONCLUSIVE

**Sub-claim.** Cho et al. (2026): the Ru process has a 7.0 % lower relative economic cost (REC) than the Ni process.

**Conclusion.** The sign of the Ru-Ni REC difference changes with the catalyst inventory basis and PSA recovery (-10.2 to 2.6 %, negative meaning Ru dearer), and no case reaches Cho's value. Cho's 7.0 % is not reproduced, but the comparison is boundary-limited.

**Conditions and rule.** Rule: INCONCLUSIVE if the sign of the REC difference changes across the inventory and PSA cases; otherwise the sign decides.

**Key uncertainty (what would change the verdict).** Inventory basis and CAPEX response to temperature (absent in AmCraX); Cho's Ru advantage sits in boiler, exchanger and NOx SCR capital.

**Uncertainty range.** Ru REC lower by 2.6 % / -2.5 % (kinetic / GHSV mass, PSA 0.85) and -0.4 % / -10.2 % (PSA 0.756), against Cho's 7.0 %.

- Singapore scenario: Cho's operating points rebuilt on AmCraX boundaries.
- Aspen model: No Aspen run at Cho's operating points: Python only.
- Python model: amcrax.research.catalyst_comparison Cho rebuild with amcrax.economics.singapore.
- Case ids: Ni_735.52C_24.34bar, RuAl2O3_566.69C_10bar
- Validation: Cho's own REC difference (1.995 vs 1.856 USD/kg) reproduced as 7.0 % (economics.json); AmCraX rebuild informational. Validation status of the underlying models: results/research/validation/catalyst_comparison.json: 66 pass, 5 fail, 4 informational (failures: HCAT-ASPY-Ru/Al2O3-HI-heat, HCAT-ASPY-5Ni1Ru/CeO2-HI-heat, HCAT-ASPY-2.5Ni0.5Ru/CeO2-HI-heat, HCAT-ASPY-Ni/MgO-HI-heat, HCAT-ASPY-Ru/MgO-HI-heat); results/research/validation/economics.json: 9 pass, 0 fail, 6 informational.
- Input assumptions: Catalyst inventory basis (kinetic minimum vs Cho's space-velocity charge) and PSA recovery varied.; CAPEX does not respond to T or P.
- Literature: `cho2026nickel` (Cho et al. 2026: REC of the Ni and Ru processes, Fig. 8d)
- Limitations: AmCraX has no product compression to 180 bar, no H2 recycle, no TSA, no expander, no NOx SCR cost.; Kinetics are proxies: Ni/MgO and Ru/Al2O3, Ru/MgO laws; Cho uses Ni/Al2O3 (Collins 1993) and Ru-K/CaO (Sayas 2020), both in an unavailable SI.; Cho optimises T, P and reactor jointly with the Aspen boiler; here T and P are fixed to Cho's optima.; Economic overrides: discount 8.5 %, electricity 0.084 USD/kWh, 25 yr (cho2026nickel Table 4); CAPEX from amcrax.economics.singapore (does not respond to T or P).; All rate laws are extrapolated to 20 bar from their fit pressure (1 atm; Kum: 10 bar); the Takahashi laws are evaluated on a mole-fraction basis and the Lucentini laws on concentrations; the Ni/MgO law fails its own validation (EXISTING-KIN-NI-PRED). No catalyst ranking at 20 bar is a property of the catalysts.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| REC Ru lower by, kinetic-minimum mass, AmCraX PSA recovery | 2.562 | % | python | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `summary/[psa_recovery=0.85;inventory_basis=kinetic_minimum]/rec_Ru_lower_by_pct` |
| REC Ru lower by, Cho GHSV mass, AmCraX PSA recovery | -2.526 | % | python | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `summary/[psa_recovery=0.85;inventory_basis=cho_ghsv_9000]/rec_Ru_lower_by_pct` |
| REC Ru lower by, kinetic-minimum mass, Cho PSA recovery | -0.4258 | % | python | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `summary/[psa_recovery=0.756;inventory_basis=kinetic_minimum]/rec_Ru_lower_by_pct` |
| REC Ru lower by, Cho GHSV mass, Cho PSA recovery | -10.156 | % | python | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `summary/[psa_recovery=0.756;inventory_basis=cho_ghsv_9000]/rec_Ru_lower_by_pct` |
| Cho: REC Ru lower by | 7 | % | literature | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `summary/[psa_recovery=0.85;inventory_basis=kinetic_minimum]/cho_values/rec_Ru_lower_by_pct` |
| Cho: REC Ni | 1.995 | USD/kg H2 | literature | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `summary/[psa_recovery=0.85;inventory_basis=kinetic_minimum]/cho_values/rec_Ni` |
| Cho: REC Ru | 1.856 | USD/kg H2 | literature | `results/research/catalyst_comparison/catalyst_cho_comparison.json` | `summary/[psa_recovery=0.85;inventory_basis=kinetic_minimum]/cho_values/rec_Ru` |

Data: `results/research/catalyst_comparison/catalyst_cho_comparison.csv`, `results/research/catalyst_comparison/catalyst_cho_comparison.json`, `results/research/singapore/benchmarks.json`

## H4: INCONCLUSIVE

**Statement.** Purification: must balance purity requirements against recovery losses, energy and equipment cost.

**Summary.** Recovery losses partly return as furnace fuel (computed energy balance), and the published Cho PSA point fails ISO 14687 grades B and D; the cost increase with purity, the PSA purity-recovery slope and the membrane advantage rest on assumed recoveries and an unsourced selectivity.

**Verdict conditions.** Hypothesis verdict from its rows: SUPPORTED if every row is SUPPORTED; CONTRADICTED if no row is SUPPORTED and at least half of the rows are CONTRADICTED; otherwise INCONCLUSIVE, with the mixed row outcomes stated in verdict_conditions. Row outcomes: SUPPORTED: H4-e; CONTRADICTED: H4-c; INCONCLUSIVE: H4-a, H4-b, H4-d. Qualified verdict: the hypothesis holds only in the parts marked SUPPORTED, under each row's conclusion_conditions; rows marked CONTRADICTED are findings against the essay statement; INCONCLUSIVE rows are unresolved by the models.

### H4-a: INCONCLUSIVE

**Sub-claim.** Higher hydrogen purity from PSA costs hydrogen recovery (purity-recovery trade-off).

**Conclusion.** The model cannot test the PSA trade-off: the recovery at Grade D purity (0.751) is set by an assumed relation, not computed, and the alternative bound (0.71) is extrapolated.

**Conditions and rule.** Rule: INCONCLUSIVE because the recovery at the purity of interest is an assumption built into the model.

**Key uncertainty (what would change the verdict).** A sourced PSA recovery at Grade D purity (adsorption-cycle simulation or plant data) would settle the slope.

**Uncertainty range.** Recovery at Grade D purity bounded 0.710-0.751 against 0.756 at 99.11 %.

- Singapore scenario: Jurong Island cracker, 20 bar Aspen baseline cracked gas; base costs use the existing AmCraX economics defaults (purification assumptions.json), Singapore NH3 and electricity prices in singapore_price_scenario.json; delivery 30 bar (industrial, blend) or 350 bar (Grade D).
- Aspen model: Stored Aspen Plus V15 baseline stream S7 (cracked gas) and H2PROD; PSA in Aspen is a split block with assumed fractions (no adsorption model).
- Python model: amcrax.separation.purification: PSA mass-balance relation, Sieverts membrane with pinch limit, ISO 14687 evaluator.
- Case ids: PSA_CHO, PSA_D_MB, PSA_D_LOW
- Validation: PSA point reproduction is true by construction (informational); mass closure for all configurations (purification.json). Validation status of the underlying models: results/research/validation/purification.json: 4 pass, 0 fail, 4 informational.
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

Figures: `results/figures/research/purification_recovery_purity.png`
Data: `results/research/purification/psa_recovery_vs_purity.csv`, `results/research/purification/purification_configurations.csv`, `results/research/purification/purification_study.json`

### H4-b: INCONCLUSIVE

**Sub-claim.** Purification must be matched to the end use: stricter purity requirements raise the cost per kg of usable hydrogen.

**Conclusion.** Cost per kg usable H2 rises with the purity requirement: 3.57 (raw gas for a turbine blend), 3.94 (99.9 % industrial), 4.26-4.50 USD/kg (Grade D candidate at 350 bar). At equal 30 bar delivery the purification step costs 0.287 (PSA_AMCRAX) against 0.322 USD/kg (PSA at Grade D purity). The ordering is set by the model's inputs: raw gas skips purification, and the Grade D increment comes from assumed PSA recoveries (see H4-a) and the higher delivery pressure. The magnitudes are lower bounds, not a test of the hypothesis.

**Conditions and rule.** Rule: SUPPORTED if raw < industrial < both Grade D bounds in the base case and in every Singapore price case and the recoveries that set the Grade D increment are computed, not assumed; otherwise INCONCLUSIVE (here the recoveries are assumed, so the ordering, which holds, reproduces an assumption). Conditions: 20 bar baseline gas, grey NH3, assumed recoveries; costs are lower bounds for purified routes.

**Key uncertainty (what would change the verdict).** If membrane routes meet Grade D (conditional on H2/N2 selectivity, see H4-d) the Grade D penalty shrinks, but stays above the raw-gas cost.

**Uncertainty range.** Grade D cost 4.26-4.50 USD/kg across the two recovery bounds (base economics); the ordering raw < industrial < Grade D holds at both bounds and at every Singapore NH3 price case (4 cases, Singapore electricity price). Unmodelled costs only add to the purified routes.

- Singapore scenario: Jurong Island cracker, 20 bar Aspen baseline cracked gas; base costs use the existing AmCraX economics defaults (purification assumptions.json), Singapore NH3 and electricity prices in singapore_price_scenario.json; delivery 30 bar (industrial, blend) or 350 bar (Grade D).
- Aspen model: Stored Aspen Plus V15 baseline stream S7 (cracked gas) and H2PROD; PSA in Aspen is a split block with assumed fractions (no adsorption model).
- Python model: amcrax.separation.purification: PSA mass-balance relation, Sieverts membrane with pinch limit, ISO 14687 evaluator.
- Case ids: RAW, PSA_AMCRAX, PSA_D_MB, PSA_D_LOW
- Validation: Component and mass closure for all configuration/case combinations; ISO limit transcription (purification.json). Validation status of the underlying models: results/research/validation/purification.json: 4 pass, 0 fail, 4 informational.
- Input assumptions: PSA recoveries are assumed (0.85 AmCraX; 0.751 and 0.71 bounds for Grade D).; TSA regeneration energy, compression CAPEX, membrane housing and skid not modelled: purified-route costs are lower bounds.; Grade D cost includes delivery to 350 bar; industrial and blend to 30 bar.
- Literature: `iso14687_2019` (ISO 14687:2019 Tables 2-4 (grade D, E3, B limits)); `cho2026nickel` (Cho et al. 2026: published PSA recovery and purity point); `hansen2024hysys` (Hansen et al. 2024: lowest published PSA recovery point); `richard2024technoeconomic` (Richard et al. 2024: Pd-Ag permeability, Table 2); `cechetto2023membrane` (Cechetto et al. 2023: membrane review, NH3 in permeate)
- Limitations: Part of the Grade D increment is delivery pressure (1.59 vs 0.22 kWh/kg compression), not purity.; Contaminants other than NH3, N2 and H2O are not evaluated for Grade D.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| cost usable H2, raw cracked gas for turbine blend | 3.574 | USD/kg H2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=RAW]/costs/turbine_blend/usd_per_kg_usable_h2` |
| cost usable H2, industrial 99.9 %, PSA_AMCRAX (industrial delivery) | 3.937 | USD/kg H2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_AMCRAX]/costs/industrial_99.9/usd_per_kg_usable_h2` |
| cost usable H2, Grade D, PSA_D_MB (fuel-cell delivery) | 4.264 | USD/kg H2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_D_MB]/costs/fuel_cell_grade_D/usd_per_kg_usable_h2` |
| cost usable H2, Grade D, PSA_D_LOW (fuel-cell delivery) | 4.504 | USD/kg H2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_D_LOW]/costs/fuel_cell_grade_D/usd_per_kg_usable_h2` |
| purification-only cost, PSA_D_MB at industrial delivery | 0.3221 | USD/kg H2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_D_MB]/costs/industrial_99.9/purification_only_usd_per_kg` |
| purification-only cost, PSA_AMCRAX at industrial delivery | 0.2868 | USD/kg H2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_AMCRAX]/costs/industrial_99.9/purification_only_usd_per_kg` |
| compression energy to industrial delivery, PSA | 0.2194 | kWh/kg H2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_D_MB]/costs/industrial_99.9/compression_kWh_per_kg_h2` |
| compression energy to fuel-cell delivery, PSA | 1.590 | kWh/kg H2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_D_MB]/costs/fuel_cell_grade_D/compression_kWh_per_kg_h2` |
| PSA recovery, PSA_AMCRAX (assumed split) | 0.85 | fraction | assumption | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_AMCRAX]/h2_recovery` |
| Singapore prices (blue): raw gas, turbine blend | 3.804 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_blue;config=RAW;end_use=turbine_blend]/usd_per_kg_usable_h2` |
| Singapore prices (blue): PSA_AMCRAX, industrial | 4.199 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_blue;config=PSA_AMCRAX;end_use=industrial_99.9]/usd_per_kg_usable_h2` |
| Singapore prices (blue): PSA_D_MB, Grade D | 4.636 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_blue;config=PSA_D_MB;end_use=fuel_cell_grade_D]/usd_per_kg_usable_h2` |
| Singapore prices (blue): PSA_D_LOW, Grade D | 4.893 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_blue;config=PSA_D_LOW;end_use=fuel_cell_grade_D]/usd_per_kg_usable_h2` |
| Singapore prices (green_2030): raw gas, turbine blend | 5.078 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_green_2030;config=RAW;end_use=turbine_blend]/usd_per_kg_usable_h2` |
| Singapore prices (green_2030): PSA_AMCRAX, industrial | 5.699 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_green_2030;config=PSA_AMCRAX;end_use=industrial_99.9]/usd_per_kg_usable_h2` |
| Singapore prices (green_2030): PSA_D_MB, Grade D | 6.333 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_green_2030;config=PSA_D_MB;end_use=fuel_cell_grade_D]/usd_per_kg_usable_h2` |
| Singapore prices (green_2030): PSA_D_LOW, Grade D | 6.688 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_green_2030;config=PSA_D_LOW;end_use=fuel_cell_grade_D]/usd_per_kg_usable_h2` |
| Singapore prices (green_current): raw gas, turbine blend | 6.749 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_green_current;config=RAW;end_use=turbine_blend]/usd_per_kg_usable_h2` |
| Singapore prices (green_current): PSA_AMCRAX, industrial | 7.665 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_green_current;config=PSA_AMCRAX;end_use=industrial_99.9]/usd_per_kg_usable_h2` |
| Singapore prices (green_current): PSA_D_MB, Grade D | 8.557 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_green_current;config=PSA_D_MB;end_use=fuel_cell_grade_D]/usd_per_kg_usable_h2` |
| Singapore prices (green_current): PSA_D_LOW, Grade D | 9.042 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_green_current;config=PSA_D_LOW;end_use=fuel_cell_grade_D]/usd_per_kg_usable_h2` |
| Singapore prices (grey): raw gas, turbine blend | 3.591 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_grey;config=RAW;end_use=turbine_blend]/usd_per_kg_usable_h2` |
| Singapore prices (grey): PSA_AMCRAX, industrial | 3.949 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_grey;config=PSA_AMCRAX;end_use=industrial_99.9]/usd_per_kg_usable_h2` |
| Singapore prices (grey): PSA_D_MB, Grade D | 4.353 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_grey;config=PSA_D_MB;end_use=fuel_cell_grade_D]/usd_per_kg_usable_h2` |
| Singapore prices (grey): PSA_D_LOW, Grade D | 4.593 | USD/kg H2 | python | `results/research/purification/singapore_price_scenario.json` | `rows/[nh3_price_case=nh3_price_grey;config=PSA_D_LOW;end_use=fuel_cell_grade_D]/usd_per_kg_usable_h2` |

Figures: `results/figures/research/purification_recovery_purity.png`, `results/figures/research/purification_recovery_cost.png`, `results/figures/research/purification_config_comparison.png`
Data: `results/research/purification/psa_recovery_vs_purity.csv`, `results/research/purification/purification_configurations.csv`, `results/research/purification/purification_study.json`, `results/research/purification/recovery_vs_cost.csv`, `results/research/purification/singapore_price_scenario.csv`, `results/research/purification/singapore_price_scenario.json`

### H4-c: CONTRADICTED

**Sub-claim.** A published PSA operating point (Cho: 75.6 % recovery at 99.11 % H2) is sufficient for hydrogen end uses with ISO 14687 grades.

**Conclusion.** The Cho PSA point does not meet the 99.9 % industrial grade or Grade D (N2 8900 ppm). Fuel-cell use needs a higher-purity PSA plus NH3 removal, at lower recovery (see H4-a).

**Conditions and rule.** Rule: CONTRADICTED if the published composition fails both grade B and grade D in the ISO evaluator.

**Key uncertainty (what would change the verdict).** None for the spec check itself (it follows from the published composition); the industrial usefulness depends on the end user's specification.

**Uncertainty range.** Cho point: N2 8900 ppm at 99.11 % H2; fails grade B (99.9 %) and grade D on the index alone.

- Singapore scenario: Jurong Island cracker, 20 bar Aspen baseline cracked gas; base costs use the existing AmCraX economics defaults (purification assumptions.json), Singapore NH3 and electricity prices in singapore_price_scenario.json; delivery 30 bar (industrial, blend) or 350 bar (Grade D).
- Aspen model: Stored Aspen Plus V15 baseline stream S7 (cracked gas) and H2PROD; PSA in Aspen is a split block with assumed fractions (no adsorption model).
- Python model: amcrax.separation.purification: PSA mass-balance relation, Sieverts membrane with pinch limit, ISO 14687 evaluator.
- Case ids: PSA_CHO, PSA_AMCRAX
- Validation: ISO 14687 evaluator applied per modelled contaminant (NH3, N2, H2O); P-ISO-2 Aspen H2PROD vs Grade D informational (purification.json). Validation status of the underlying models: results/research/validation/purification.json: 4 pass, 0 fail, 4 informational.
- Input assumptions: NH3 at the PSA outlet set to the TSA design target rather than computed.; The Aspen baseline PSA split is an assumption; its purity supports no purity claim.
- Literature: `iso14687_2019` (ISO 14687:2019 Tables 2-4 (grade D, E3, B limits)); `cho2026nickel` (Cho et al. 2026: published PSA recovery and purity point); `hansen2024hysys` (Hansen et al. 2024: lowest published PSA recovery point); `richard2024technoeconomic` (Richard et al. 2024: Pd-Ag permeability, Table 2); `cechetto2023membrane` (Cechetto et al. 2023: membrane review, NH3 in permeate)
- Limitations: Only NH3, N2 and H2O are evaluated; meeting a grade within model scope is not a fuel-cell grade claim.; The Aspen baseline product (N2 400 ppm, Grade D within model scope: False) is not Grade D and must not be called fuel-cell grade.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| H2 recovery, Cho PSA point | 0.756 | fraction | literature | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_CHO]/h2_recovery` |
| N2 in product, Cho PSA point | 8900.0 | ppm | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_CHO]/product_ppm/N2` |
| H2 purity, Cho PSA point | 0.9911 | mol fraction | literature | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_CHO]/product_purity_h2_mole_frac` |
| N2 in product, PSA_AMCRAX (Aspen baseline split) | 400.0 | ppm | assumption | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_AMCRAX]/product_ppm/N2` |

Figures: `results/figures/research/purification_config_comparison.png`
Data: `results/research/purification/psa_recovery_vs_purity.csv`, `results/research/purification/purification_configurations.csv`, `results/research/purification/purification_study.json`

### H4-d: INCONCLUSIVE

**Sub-claim.** A Pd-Ag membrane balances purity, recovery and cost better than PSA for fuel-cell hydrogen.

**Conclusion.** The membrane route is cheaper on paper (3.94 vs 4.26 USD/kg, area 31 m2) but meets Grade D only conditionally on a selectivity that no source in the library supports.

**Conditions and rule.** Rule: INCONCLUSIVE when the membrane Grade D result is conditional on an unsourced selectivity; otherwise cost decides.

**Key uncertainty (what would change the verdict).** CONDITIONAL on ideal H2/N2 selectivity >= 12919 (N2 300 ppm); the base model assumes infinite selectivity and no numeric selectivity is available in the library

**Uncertainty range.** Membrane 3.94 vs PSA 4.26 USD/kg; the gap is driven by recovery (0.90 vs PSA bounds) rather than by membrane cost.

- Singapore scenario: Jurong Island cracker, 20 bar Aspen baseline cracked gas; base costs use the existing AmCraX economics defaults (purification assumptions.json), Singapore NH3 and electricity prices in singapore_price_scenario.json; delivery 30 bar (industrial, blend) or 350 bar (Grade D).
- Aspen model: No Aspen membrane model: Python/literature only.
- Python model: amcrax.separation.purification: PSA mass-balance relation, Sieverts membrane with pinch limit, ISO 14687 evaluator.
- Case ids: MEM_1bar_polish, MEM_1bar_raw, PSA_D_MB
- Validation: Sieverts hand calculation and pinch limit checks (purification.json). Validation status of the underlying models: results/research/validation/purification.json: 4 pass, 0 fail, 4 informational.
- Input assumptions: Infinite H2/N2 selectivity in the base case (no numeric selectivity in the library).; Membrane cost 6000 EUR/m2 applied as USD at parity; housing, skid and compression CAPEX not modelled.; Membrane recovery 0.90 is a design choice.
- Literature: `iso14687_2019` (ISO 14687:2019 Tables 2-4 (grade D, E3, B limits)); `cho2026nickel` (Cho et al. 2026: published PSA recovery and purity point); `hansen2024hysys` (Hansen et al. 2024: lowest published PSA recovery point); `richard2024technoeconomic` (Richard et al. 2024: Pd-Ag permeability, Table 2); `cechetto2023membrane` (Cechetto et al. 2023: membrane review, NH3 in permeate)
- Limitations: Without polishing the permeate carries 2.9 ppm NH3 (measured, Cechetto 2021) and fails Grade D.; Membrane results are lower bounds on cost.

| Quantity | Value | Unit | Source type | File | Key |
|---|---|---|---|---|---|
| cost usable H2, Grade D, Pd-Ag membrane + polishing (350 bar) | 3.938 | USD/kg H2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=MEM_1bar_polish]/costs/fuel_cell_grade_D/usd_per_kg_usable_h2` |
| membrane H2 recovery (design) | 0.9 | fraction | assumption | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=MEM_1bar_polish]/h2_recovery` |
| membrane area | 31.063 | m2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=MEM_1bar_polish]/area_m2` |
| cost usable H2, Grade D, PSA_D_MB | 4.264 | USD/kg H2 | python | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=PSA_D_MB]/costs/fuel_cell_grade_D/usd_per_kg_usable_h2` |
| NH3 in membrane permeate without polishing | 2.900 | ppm | literature | `results/research/purification/purification_study.json` | `cases/20bar_baseline/configs/[id=MEM_1bar_raw]/product_ppm/NH3` |
| membrane cost (applied as USD at parity) | 6000 | EUR/m2 | assumption | `results/research/purification/assumptions.json` | `[name=Membrane cost]/value` |

Figures: `results/figures/research/purification_recovery_cost.png`, `results/figures/research/purification_sensitivity.png`
Data: `results/research/purification/assumptions.json`, `results/research/purification/membrane_recovery_area_cost.csv`, `results/research/purification/membrane_required_selectivity.csv`, `results/research/purification/purification_study.json`

### H4-e: SUPPORTED

**Sub-claim.** Recovery losses trade against energy: hydrogen not recovered by purification returns as fuel for the cracker, up to the furnace demand.

**Conclusion.** Lower recovery is partly self-compensating: at the Grade D candidate PSA (assumed recovery) the tail gas covers the whole furnace demand (2293 kW) so no NH3 is burned for heat, while at recovery 0.85 a 773 kW deficit remains. Beyond the demand (125 kW surplus) the lost hydrogen has no use in this flowsheet.

**Conditions and rule.** Rule: SUPPORTED if lower recovery raises tail-gas heat and lowers the furnace deficit (computed mass and energy balance). Conditions: 20 bar baseline, furnace model as stated.

**Key uncertainty (what would change the verdict).** Whether surplus tail-gas heat has a use on site (credit) and the furnace efficiency; beyond the furnace demand lost H2 is a pure loss.

**Uncertainty range.** Tail-gas heat 1520 kW at recovery 0.85 (deficit 773 kW) and 2418 kW at the Grade D PSA, recovery 0.751 (deficit 0 kW, surplus 125 kW not credited) against a demand of 2293 kW.

- Singapore scenario: Jurong Island cracker, 20 bar Aspen baseline cracked gas; base costs use the existing AmCraX economics defaults (purification assumptions.json), Singapore NH3 and electricity prices in singapore_price_scenario.json; delivery 30 bar (industrial, blend) or 350 bar (Grade D).
- Aspen model: Stored Aspen Plus V15 baseline stream S7 (cracked gas) and H2PROD; PSA in Aspen is a split block with assumed fractions (no adsorption model). Furnace demand from the stored Aspen baseline.
- Python model: amcrax.separation.purification: PSA mass-balance relation, Sieverts membrane with pinch limit, ISO 14687 evaluator.
- Case ids: PSA_AMCRAX, PSA_D_MB, baseline (stored Aspen)
- Validation: Mass closure; tail-gas LHV from closed component balances (purification.json). Validation status of the underlying models: results/research/validation/purification.json: 4 pass, 0 fail, 4 informational; results/research/validation/economics.json: 9 pass, 0 fail, 6 informational.
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

Figures: `results/figures/research/purification_recovery_cost.png`
Data: `results/research/purification/psa_recovery_vs_purity.csv`, `results/research/purification/purification_configurations.csv`, `results/research/purification/purification_study.json`

