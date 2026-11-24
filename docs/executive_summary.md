---
title: "AmCraX Phase 2: executive summary"
author: "AmCraX project"
date: "24 November 2026"
---

# What was done

AmCraX tests four hypotheses about cracking ammonia to hydrogen in Singapore: end use (H1), feedstock (H2), catalyst and heat integration (H3) and purification (H4). Phase 2 put every workstream on one frozen cost scenario (USD; 1.288444 SGD/USD, European Central Bank, 20 November 2026), tested each assumption-driven conclusion with a threshold against sourced values, and added uncertainty quantification and an interactive simulator. An independent adversarial review moved three rows to INCONCLUSIVE.

**Baseline.** Grey ammonia at 450 USD/t, 600 °C, 20 bar, heat integration on: LCOH **4.015 USD/kg (5.174 SGD/kg)** with the supplementary ammonia fuel counted at 100 % of its lower heating value (optimistic; 4.038 and 4.063 USD/kg at 92.25 % and 85 %), on a capital cost of 7.67 MUSD, the highest comparable estimate; feed is 76 % of the cost. The assumed PSA recovery of 0.85 lies above the only published front for this gas composition (simulated); at its 0.82 and 0.77 the LCOH is 4.066 and 4.146 USD/kg.

# Answers

Plain answers state what the model computes and under which assumptions; the formal classification applies a stricter rule fixed before the analysis, under which a result that rests on an untested assumption is not counted as supported; both are published. Yes (assumption) is a conditional statement of the computed result, never a verdict.

| Plain answer | Hypothesis and claims | Main limitation | Formal classification (rule fixed before the analysis) |
|--------|----------------------------|-------------|--------------|
| **Yes, under the modelled conditions** | H1 end use. Direct ammonia cheaper than cracking + PSA for power: **Yes**; than fired cracking: **Yes (assumption)**. Cracking in front of a turbine does not pay; cracking justified where hydrogen is the product: not established. | Gas turbine not modelled: both fuels at 49.64 % efficiency; fired cracking breaks even at +5.16 points (3.29 to 8.79), no published value. | INCONCLUSIVE (H1-P, H1-Q INCONCLUSIVE) |
| **Yes** | H2 feedstock. Ammonia price dominates the cost: **Yes**. Low-carbon ammonia needed for lower emissions: **Yes**. Cheap ammonia makes it competitive: not established (320 USD/t). Low carbon intensity rewarded in Singapore: **No**. | Sourced prices (300 to 1052 USD/t) straddle the break-even (277 to 379 USD/t). | MIXED (H2-E PARTIALLY SUPPORTED, H2-C SUPPORTED, H2-X CONTRADICTED) |
| **Yes for energy** | H3 catalyst and heat integration. Lower temperature saves energy: **Yes, modestly** (25 kW). Heat integration saves energy: **Yes**. Active catalysts at 20 bar; heat integration saves cost: not established. Savings outweigh catalyst cost: not established, leaning no. | Python only; rate laws extrapolated to 20 bar; no heat-transfer coefficient at 20 bar. | PARTIALLY SUPPORTED, resting only on H3-T |
| **Not established** | H4 purification. Purity costs recovery; stricter purity raises cost; tail gas offsets furnace fuel (0.765); membrane beats PSA (parity 0.783): all not established. | Published PSA relations agree on direction, but AmCraX computes none; the purity-only cost increment changes sign within the published model's scatter. | INCONCLUSIVE (H4-B INCONCLUSIVE) |

**H1.** Yes, under the modelled conditions: direct ammonia combustion gives cheaper electricity than the standalone cracking pathways (about 8 to 17 %). The gas turbine is not modelled: both fuels are assumed to run at the same 49.64 % efficiency, and the actual advantage depends on fuel-specific turbine performance. Cracking with PSA would need +12.55 points of turbine efficiency, above the only sourced bound of +7.3; fired cracking would need +5.16 and has no sourced value. Against the essay, exhaust-heated cracking is 1.3 % cheaper than direct use on the reference basis, a margin that reverses with plausible changes of capital cost, ammonia price or operating hours.

**Carbon price.** Under a life-cycle carbon price, which is hypothetical, not Singapore law, blue ammonia overtakes grey at about 33 SGD/t (range 12 to 605); the legislated rate is 45 SGD/t. Published figures not reproduced: the essay's 40 % cost advantage of direct ammonia power (at most 16.6 % in the cost of electricity; the cited paper's 39 to 44 % is a fuel-cost comparison, on which AmCraX gives 20 to 33 %) and the published PSA point as industrial or fuel-cell grade hydrogen. Three papers were read in full on 24 November 2026; no classification moved.

# What is not established

- No independent experimental validation exists. The 705 research checks are numerical verification (466), Python against Aspen comparison (183) and comparison with published literature (55).
- No rate law is validated at 20 bar; there is no supplier catalyst quotation, no heat-transfer coefficient at 20 bar, no turbine efficiency for fired-cracker fuel and no measured PSA recovery on cracked ammonia.

**Next steps:** a catalyst quotation, a measured PSA recovery, a turbine efficiency on cracked fuel, a rate law fitted at pressure and an exchanger coefficient at 20 bar. Code, data and documents: <https://github.com/weewzr/AmCraX>.
