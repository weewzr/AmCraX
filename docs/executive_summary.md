---
title: "AmCraX Phase 2: executive summary"
author: "AmCraX project"
date: "23 November 2026"
---

# What was done

AmCraX tests four hypotheses about cracking ammonia to hydrogen in Singapore: end use (H1), feedstock (H2), catalyst and heat integration (H3) and purification (H4). Phase 2 added:

- one frozen techno-economic reference scenario used by every workstream, in USD with SGD at one sourced rate (1.288444 SGD/USD, European Central Bank, 20 November 2026);
- threshold analyses for every conclusion that rests on an assumed quantity;
- catalyst prices derived from metal content, and a kinetic validity class for each rate law;
- the actual Singapore carbon-tax boundary, with a hypothetical life-cycle carbon price kept separate;
- a sized and costed feed/effluent heat exchanger, and a PSA against Pd-Ag membrane comparison;
- variance-based uncertainty quantification;
- an interactive process simulator as the first page of the website, tested against the Python model.

Verdicts follow a rule written down before the analysis (version 2). The version 1 verdicts are shown alongside.

# Unified baseline

Grey ammonia at 450 USD/t, 600 °C, 20 bar, heat integration on, 251.6 kg/h hydrogen:

- **LCOH 4.015 USD/kg (5.174 SGD/kg).** Feed 3.040, capital 0.420, fixed operating cost 0.284, ammonia burned for heat 0.268 USD/kg.
- Capital cost 7.67 MUSD. Net present value at 3.06 USD/kg is -17.46 MUSD. Without heat integration the LCOH is 4.229 USD/kg.
- The reference capital cost is at the conservative end of published estimates, which would give 3.64 to 3.92 USD/kg.
- The earlier figures 3.919 and 3.613 USD/kg are superseded for research outputs.

# Verdicts

| Hypothesis | Version 2 | Version 1 | Strongest defensible statement |
|---|---|---|---|
| H1 end use | INCONCLUSIVE | INCONCLUSIVE | Direct ammonia combustion is about 8 to 17 % cheaper than standalone cracking if the turbine is equally efficient on both fuels. Cracking with PSA would need a turbine 12.6 points more efficient, above the only sourced bound of 7.3, so that half is robust. Fired cracking has no sourced efficiency. |
| H2 feedstock | MIXED | INCONCLUSIVE | Ammonia is 76 % of the cost and its price explains about 90 % of the variance. Competitiveness needs ammonia below about 320 USD/t, and low-carbon ammonia is needed for a lower carbon intensity than fossil hydrogen. Under the actual Singapore carbon tax, low-carbon ammonia earns no cost advantage. |
| H3 catalyst and heat integration | PARTIALLY SUPPORTED | INCONCLUSIVE | Heat integration cuts external heating by 21 % and still pays after the exchanger cost (net +0.067 to +0.095 USD/kg). Lower-temperature operation saves about 5 % of fired duty at equal conversion. At realistic ruthenium prices the low-temperature catalysts do not pay. |
| H4 purification | PARTIALLY SUPPORTED | INCONCLUSIVE | Hydrogen not recovered returns as cracker fuel up to a recovery of about 0.765. PSA against membrane is not robust either way; parity is near a PSA recovery of 0.80. |

Findings against the original essay: exhaust-heated cracking is about 1.3 % cheaper than direct use on the reference basis, though not robustly; at ruthenium prices derived from metal content the low-temperature catalysts do not pay; grey ammonia at 450 USD/t is not cheap enough to compete.

The hypothetical life-cycle carbon price is not Singapore law. Under it, blue ammonia overtakes grey at about 33 SGD/t (range 12 to 605), and green ammonia at current prices needs about 305 SGD/t.

# What changed since the release of 23 November 2026

| Finding | Phase 1 release | Phase 2 |
|---|---|---|
| Baseline LCOH | 3.92 and 3.61 USD/kg (two bases) | 4.015 USD/kg (one basis) |
| Feed share | 84 % | 76 % |
| Break-even ammonia price | 375 USD/t | 320 USD/t (277 to 371) |
| Capital cost | 2.78 MUSD | 7.67 MUSD |
| Direct use against fired cracking / cracking + PSA | 5 % / 15 % cheaper | 7.6 % / 16.5 % cheaper |
| Exhaust-heated cracking against direct use | 4 % cheaper | 1.3 % cheaper |
| Low-temperature energy saving | 17 % (unequal conversion) | about 5 % at equal conversion |
| Heat-integration saving | 0.21 USD/kg gross | +0.067 to +0.095 USD/kg net of exchanger |
| Ruthenium catalyst price | 542 USD/kg (published study) | 3006 to 4791 USD/kg (derived from metal content) |
| PSA against membrane, industrial | membrane cheaper | depends on PSA recovery |
| Verdicts | all INCONCLUSIVE | H1 INCONCLUSIVE, H2 MIXED, H3 and H4 PARTIALLY SUPPORTED |

# What is not established

- No independent experimental validation exists. The checks are numerical verification, Python against Aspen comparison and comparison with published literature, and are reported under those names.
- No rate law is validated at 20 bar. Three are validated against their own fitting data, two are extrapolated and three catalysts have no rate law.
- There is no supplier catalyst quotation, no sourced heat-transfer coefficient at 20 bar, no turbine efficiency for fired-cracker fuel, and no measured PSA recovery on cracked ammonia.
- Only one hydrogen price benchmark (3.06 USD/kg) was used, and no Singapore transaction price exists.
- The browser simulator has no membrane model and uses an ideal-gas equilibrium.

# Next steps

1. Obtain a catalyst price quotation and a measured PSA recovery on cracked ammonia.
2. Find or measure a turbine efficiency on cracked fuel, and a rate law fitted at elevated pressure.
3. Estimate the exchanger heat-transfer coefficient at 20 bar.
4. Add a membrane model and a second hydrogen price benchmark.
5. Submit the evidence matrix to an adversarial review before any external use.

Code, data and documents: <https://github.com/weewzr/AmCraX> (Phase 1 release tag amcrax-research-expansion-2026-11-23).
