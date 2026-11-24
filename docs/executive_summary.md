---
title: "AmCraX Phase 2: executive summary"
author: "AmCraX project"
date: "24 November 2026"
---

# What was done

AmCraX tests four hypotheses about cracking ammonia to hydrogen in Singapore: end use (H1), feedstock (H2), catalyst and heat integration (H3) and purification (H4). Phase 2 put every workstream on one frozen cost scenario (USD; 1.288444 SGD/USD, European Central Bank, 20 November 2026), tested each assumption-driven conclusion with a threshold against sourced values, and added uncertainty quantification and an interactive simulator. An independent adversarial review moved three rows to INCONCLUSIVE.

**Baseline.** Grey ammonia at 450 USD/t, 600 °C, 20 bar, heat integration on: LCOH **4.015 USD/kg (5.174 SGD/kg)** with the supplementary ammonia fuel counted at 100 % of its lower heating value (optimistic; 4.038 and 4.063 USD/kg at 92.25 % and 85 %), on a capital cost of 7.67 MUSD, the highest comparable estimate; feed is 76 % of the cost.

# Answers and verdicts

The plain answers are a reading aid derived in code from the formal rows of the evidence matrix and change no verdict: Yes only where the test is SUPPORTED, No only where it is CONTRADICTED, otherwise not established; an answer on half of a row is a finding and that row stays INCONCLUSIVE.

| Hypothesis | Plain answers | Formal verdict (components) | Main limitation |
|--------|----------------------------|--------------|-------------|
| H1 end use | Direct ammonia cheaper than cracking + PSA for power: **Yes** (half of row H1-a). Cheaper than fired cracking; cracking in front of a turbine does not pay; cracking justified where hydrogen is the product: not established. | INCONCLUSIVE (H1-P, H1-Q INCONCLUSIVE) | Equal turbine efficiency assumed; one upper-bound source for the PSA half, none for fired cracking. |
| H2 feedstock | Ammonia price dominates the cost: **Yes**. Cheap ammonia makes it competitive: not established (threshold 320 USD/t). Low-carbon ammonia needed for lower emissions in power and hydrogen: **Yes**. Low carbon intensity rewarded in Singapore: **No**. | MIXED (H2-E PARTIALLY SUPPORTED, H2-C SUPPORTED, H2-X CONTRADICTED) | Sourced prices (300 to 1052 USD/t) straddle the break-even (277 to 379 USD/t). |
| H3 catalyst and heat integration | Lower temperature saves energy: **Yes, modestly** (25 kW, 1.1 % of heating). Heat integration saves energy: **Yes** (half of row H3-d). Active catalysts at 20 bar; heat integration saves cost: not established. Savings outweigh catalyst cost: not established, leaning no. | PARTIALLY SUPPORTED, resting only on H3-T (H3-T PARTIALLY SUPPORTED; H3-H, H3-K INCONCLUSIVE) | Python only; rate laws extrapolated to 20 bar; no heat-transfer coefficient at 20 bar. |
| H4 purification | Purity costs recovery; stricter purity raises cost; tail gas offsets furnace fuel (threshold recovery 0.765); membrane beats PSA (parity 0.783): all not established. | INCONCLUSIVE (H4-B INCONCLUSIVE) | PSA recovery is an input, not measured on cracked ammonia. |

**H1.** Under the modelled operating conditions, direct ammonia combustion produces electricity at a lower cost than the standalone cracking pathways, with a calculated cost advantage of approximately 8 to 17 % (5 to 15 % on the earlier cost basis). This comparison assumes that the hydrogen-rich turbine operates at the same 49.64 % efficiency as the direct-ammonia turbine. The actual economic advantage depends on fuel-specific turbine performance. Cracking with PSA would need +12.55 points of turbine efficiency, above the only sourced bound of +7.3; fired cracking would need +5.16 and has no sourced value. Against the essay, exhaust-heated cracking is 1.3 % cheaper than direct use on the reference basis, a margin that reverses with plausible changes of capital cost, ammonia price or operating hours.

**Carbon price.** Under a life-cycle carbon price, which is hypothetical, not Singapore law, blue ammonia overtakes grey at about 33 SGD/t (range 12 to 605); the legislated rate is 45 SGD/t. Published figures not reproduced: the 40 % cost advantage of direct ammonia power (at most 16.6 %) and the published PSA point as industrial or fuel-cell grade hydrogen.

# What is not established

- No independent experimental validation exists. The 696 research checks are numerical verification (464), Python against Aspen comparison (183) and comparison with published literature (48).
- No rate law is validated at 20 bar; there is no supplier catalyst quotation, no heat-transfer coefficient at 20 bar, no turbine efficiency for fired-cracker fuel and no measured PSA recovery on cracked ammonia.

**Next steps:** a catalyst quotation, a measured PSA recovery, a turbine efficiency on cracked fuel, a rate law fitted at pressure and an exchanger coefficient at 20 bar. Code, data and documents: <https://github.com/weewzr/AmCraX>.
