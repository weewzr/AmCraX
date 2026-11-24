<!-- cites: cho2026nickel, chopra2026decentralized, farokhi2025costoptimization, argus_h2_markers -->

# 32 Unified techno-economic baseline and CAPEX audit

Version 1.0 reported two baseline costs: 3.919 USD/kg H~2~ from the legacy plant-level correlation used in Section 19, and 3.613 USD/kg from the Phase 1 equipment method used in Sections 27 to 29. Two baselines for one plant make every comparison ambiguous. Phase 2 therefore fixed one reference scenario, `backend/amcrax/data/reference_scenario.yaml` (version 1.0.0, identifier `amcrax_reference_2026_11_23`), which every research workstream, the evidence matrix and the browser simulator now read. Each entry of the file carries a value, a unit, a source type, a source and a note. The two earlier numbers are history: 3.919 is the legacy core result and 3.613 the Phase 1 equipment result, both superseded for research outputs.

## 32.1 Basis

The plant is the stored Aspen Plus V15 baseline (600 °C, 20 bar, 100 kmol/h feed of 99.8 mol% NH~3~, assumed PSA H~2~ recovery 0.85, heat integration on), producing 251.588 kg/h H~2~ at the plant gate at 19.5 bar with no product compression. The economic basis is 8000 h/yr, a 10 % discount rate and a 25-year life (capital recovery factor 0.1102), grey ammonia at 450 USD/t and electricity at 0.1402 USD/kWh. Calculations are in USD; every Phase 2 economic output also reports SGD at one exchange rate, 1.288444 SGD/USD, the cross-rate of the European Central Bank reference rates of 20 November 2026 (USD 1.0990 and SGD 1.4160 per EUR). No other rate is used as a conversion in this report. The cost basis is mixed nominal: CAPEX in 2024 USD (the analysis year of Cho et al., 2026), Singapore prices of 2026, no escalation index.
<!-- data: results/research/reference_scenario/baseline.json h2_product_kg_h 251.588, crf 0.110168, fx_SGD_per_USD 1.288444, fx_date 2026-11-20, price_year -->

## 32.2 CAPEX method and audit

The CAPEX method `cho2026_itemised_v1` starts from the itemised unit CAPEX of the Ni catalyst case at 24.34 bar of Cho et al. (2026, Table 7, 2024 USD, 82.3 kg/h H~2~). It converts that unit cost to installed cost with Cho's own 8000 h, 8.5 % and 25 years, removes the 180 bar product compressor, splits the T/PSA item 26:4 into PSA and adsorber following Chopra et al. (2026, Fig. 5a), scales each item by its size ratio to the power 0.8 (the size driver is the NH~3~ feed, ratio 2.698), and multiplies by 1.12 x 1.28 for Cho's outside-battery-limits, engineering and contingency factors. The selection criteria were written before the outcomes were compared: traceability, scope completeness, response to design variables and agreement with published costs. It is the only candidate that is itemised, cites one primary source with a stated cost year and includes OSBL, engineering and contingency. The legacy correlation (6.50 MUSD, cost year unknown, built from steam-reforming analogies) and the Phase 1 feed-scaled method based on Farokhi et al. (2025) (2.78 MUSD, unit and cost year inferred) remain selectable for reproduction only.

Table: **Table 32.1.** Unified baseline cost breakdown (grey NH~3~ at 450 USD/t, heat integration on). *Source: independent Python calculation on the Aspen Plus V15 baseline, results/research/reference_scenario/baseline.json.*

| Item | USD/kg H~2~ | SGD/kg H~2~ |
|---|---|---|
| NH~3~ feed | 3.040 | 3.917 |
| Capital charge | 0.420 | 0.541 |
| Fixed operating cost | 0.284 | 0.366 |
| Supplementary NH~3~ for heat | 0.268 | 0.345 |
| Catalyst | 0.002 | 0.003 |
| Electricity | 0.001 | 0.001 |
| Cooling water | 0.001 | 0.001 |
| Carbon tax (actual Singapore boundary) | 0 | 0 |
| **LCOH** | **4.015** | **5.174** |
| Reconversion cost (REC, all items except feed) | 0.975 | 1.257 |

<!-- data: results/research/reference_scenario/baseline.json breakdown_USD_per_kg, breakdown_SGD_per_kg, lcoh 4.015461 / 5.173697, rec 0.975416 / 1.256769 -->

The total capital investment is 7.667 MUSD (9.878 MSGD). By item (TCI, MUSD): boiler 2.69, heat exchangers 2.09, PSA 1.56, adsorber 0.24, reactor 0.77, other ISBL 0.32; the indirect block of 2.32 MUSD is already allocated inside these items. The NPV at a selling price of 3.06 USD/kg (Argus NE Asia SMR marker; Argus Media, 2026) is -17.46 MUSD, and no IRR or payback exists at that price. Without heat integration the LCOH is 4.229 USD/kg. For the other ammonia price scenarios the LCOH is 4.287 (blue, 487 USD/t), 8.058 (green, current, 1000 USD/t), 5.919 (green 2030, 709 USD/t) and 4.111 USD/kg (green 2050, 463 USD/t).
<!-- data: baseline.json capex_tci_by_item_USD, capex_indirects_USD 2318792, npv_USD -17455720, irr null, heat_integration_off.lcoh 4.229242, nh3_scenarios -->

![**Figure 32.1.** Cost breakdown of the unified baseline. The ammonia feed is about three quarters of the LCOH; capital, fixed operating cost and supplementary heat make up most of the rest. *Source: independent Python calculation on Aspen Plus V15 results, results/figures/research/singapore_cost_breakdown.png.*](../../results/figures/research/singapore_cost_breakdown.png){width=85%}

**Audit against published costs.** The audit in `capex_audit.json` normalises the published plant costs in the library to the AmCraX capacity with exponents of 0.6 to 0.8. The independent range is 3.1 to 6.5 MUSD (Chopra 3.1 to 5.4, Farokhi 3.1 to 4.2, legacy Ahmad correlation 6.5), which would give an LCOH of 3.64 to 3.92 USD/kg. The reference CAPEX of 7.67 MUSD lies at or above the top of this range. The choice is therefore conservative: it does not favour cracking. The audit is a comparison with published literature (evidence kind 3), not validation. Three sources could not be compared (Kum: no total investment in the notes; Deka, Makhloufi and Kezibri: primary sources not obtained).
<!-- data: results/research/reference_scenario/capex_audit.json published_normalised, independent_range_USD, not_compared -->

## 32.3 Limits of the basis

The reference CAPEX comes from one paper's itemised table. Cho et al. (2026) do not say clearly whether their ISBL items are purchase or installed costs; if they are purchase costs, installation is missing and the CAPEX is low. For the power-plant cracker of Section 33 the same table is extrapolated more than 30-fold. By default no workstream passes exchanger area or catalyst mass to the method; Section 35 does so explicitly where it matters. The electricity term covers pump power only (about 0.001 USD/kg); PSA and compression power lie outside this boundary, which is why electricity has almost no sensitivity index in Section 37.
