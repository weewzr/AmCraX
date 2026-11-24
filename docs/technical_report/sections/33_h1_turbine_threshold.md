<!-- cites: ahmad2025gtcc, netl2023h2cc, netl2024nh3cc, netl2022h2turbinereview, abuzayed2025ccgtblends, halim2025ammonia, argus_h2_markers -->

# 33 End use (H1): turbine-efficiency thresholds

Hypothesis H1 states that cracking is most justified where molecular hydrogen is needed, and that for power generation direct ammonia combustion is the cheaper route. Section 29 compared the end-use pathways on the Phase 1 basis. This section repeats the comparison on the unified basis of Section 32 and asks the question that decides it: how much more efficient would a turbine on hydrogen-rich fuel have to be for a cracking pathway to match direct ammonia power, and do sourced efficiencies reach that threshold?

## 33.1 Levelised cost of electricity on the unified basis

Under the modelled operating conditions, direct ammonia combustion produces electricity at a lower cost than the standalone cracking pathways, with a calculated cost advantage of approximately 8 to 17 % (5 to 15 % on the earlier cost basis). This comparison assumes that the hydrogen-rich turbine operates at the same 49.64 % efficiency as the direct-ammonia turbine. The actual economic advantage depends on fuel-specific turbine performance.

Table: **Table 33.1.** Levelised cost of electricity (LCOE) by pathway, grey NH~3~ at 450 USD/t, 8000 h/yr, 10 %, 25 years. *Source: independent Python calculation, results/research/enduse/turbine_threshold.json statement_of_result.*

| Pathway | LCOE (USD/MWh) | Direct NH~3~ relative to it |
|---|---|---|
| Direct NH~3~ combined cycle | 258.93 | reference |
| Full cracking, fired cracker heat | 280.09 | 7.6 % cheaper |
| Full cracking + PSA, pure H~2~ to the turbine | 310.18 | 16.5 % cheaper |
| Full cracking, exhaust-heated cracker | 255.59 | 1.3 % dearer |
| Partial cracking 40 vol% H~2~, exhaust-heated | 258.93 | equal (difference 0.002 USD/MWh) |
| Partial cracking 40 vol% H~2~, fired | 268.61 | cheaper |
| NH~3~ + PSA H~2~ blend, 40 vol% | 277.97 | cheaper |

<!-- data: results/research/enduse/turbine_threshold.json statement_of_result (LCOE values; gaps 1 - d/c 7.6 % and 16.5 %; exhaust -1.3 %) -->

The percentages are 1 - direct/cracking; expressed as cracking/direct - 1 they are 8.2 % and 19.8 %. Only the fired and purified rows assume the 49.64 % efficiency. The exhaust-heated rows use the system efficiency of Ahmad et al. (2025) instead: 54 % on a lower heating value of 18.8 MJ/kg, which is 54.58 % on the AmCraX value of 18.60 MJ/kg, a gain of +4.93 percentage points. That gain enters only once; the exhaust-heated cases add no NH~3~ for cracker heat (validation item EU-P2-no-double-count passes). The fired cases burn NH~3~ for the stored Aspen reactor and preheater duty (3.29 MJ/kg NH~3~) with the fuel counted at 100 % of its lower heating value, an optimistic assumption that favours cracking. Its effect is computed in Section 33.2 (Table 33.3).

**Against the essay.** On the reference basis, exhaust-heated full cracking is about 1.3 % cheaper than direct ammonia power. The essay's statement that direct use is the cheaper power route holds only against the fired and purified cracking pathways.

## 33.2 Efficiency thresholds

For each cracking pathway the threshold is the efficiency on hydrogen-rich fuel at which its LCOE equals direct NH~3~ power. It is computed on the reference basis and on 10 further bases (CAPEX: reference, with the PSA items, the Ahmad Fig. 6 correlation, x0.5 and x2; NH~3~ price 300, 709 and 1000 USD/t; 5000 h; and Ahmad's own basis of 480 USD/t and 7200 h).

Table: **Table 33.2.** Turbine-efficiency thresholds for the cracking pathways to match direct NH~3~ power, in percentage points above 49.64 %, reference value and range over 11 bases, against the sourced efficiency gains. *Source: independent Python calculation, results/research/enduse/turbine_threshold.json thresholds; sourced values from the literature named.*

| Pathway | Threshold (pp) | Range over 11 bases (pp) | Sourced gain (pp) | Outcome |
|---|---|---|---|---|
| Full cracking, fired | +5.16 (54.81 %) | 3.29 to 8.79 | none sourced for H~2~/N~2~ fuel; indirect bracket -1.86 to +7.3 | straddles: undecided |
| Full cracking + PSA | +12.55 (62.19 %) | 9.68 to 18.10 | +7.3, a single upper bound (H-class cycle simulation with steam-diluted H~2~ against NH~3~, not like for like with the 49.64 % AmCraX turbine; National Energy Technology Laboratory, 2023, 2024) | direct NH~3~ cheaper on every basis against that single source |
| NH~3~ + PSA H~2~ blend, 40 vol% | +4.66 | 3.47 to 6.96 | none | undecided |
| Full cracking, exhaust-heated (system gain) | +4.04 | 1.97 to 8.04 | 4.9 to 5.5 (Ahmad et al., 2025, on the AmCraX LHV basis) | cracking cheaper on the reference basis; flips with CAPEX, price and hours |

<!-- data: results/research/enduse/turbine_threshold.json thresholds (fired 54.81 %, +5.16 [3.29, 8.79]; purified 62.19 %, +12.55 [9.68, 18.10], capex x0.25 +8.36; blend +4.66 [3.47, 6.96]; exhaust +4.04 [1.97, 8.04]; Ahmad 4.45-5.46, supported 4.9-5.5; capex multiple at parity 1.22) -->

The cracking + PSA threshold stays above the sourced upper bound even at CAPEX x0.25 (+8.36 pp), so the purified pathway does not beat direct ammonia on any basis tested. That conclusion rests on one source: the NETL value is an H-class cycle simulation with steam-diluted hydrogen, not like for like with the AmCraX turbine, and is used as an upper bound. The fired pathway has no sourced efficiency at all: its threshold lies inside an indirect bracket and cannot be decided. For the exhaust-heated pathway the outcome flips across the bases: the Ahmad correlation gives a threshold of 4.45 pp (at the edge), keeping the PSA items gives 5.27 (straddles), and CAPEX x2 (8.04), NH~3~ at 300 USD/t (5.66) and 5000 h (5.95) all favour direct use. A cracker CAPEX of 1.22 times the reference removes the advantage of exhaust-heated cracking. For partial fired cracking the thresholds rise from +1.17 pp at 20 vol% H~2~ to +4.74 pp at 70 vol%.

**Fuel efficiency of the cracker heat.** The thresholds of Table 33.2 count the NH~3~ burnt for cracker heat at 100 % of its lower heating value (optimistic, favourable to cracking). Table 33.3 repeats the reference-basis thresholds with the cracker heat delivered at the flowsheet's own tail-gas ratio and at the 0.85 furnace efficiency of Section 35. Direct NH~3~ power is unaffected, because it has no cracker. The thresholds rise, so the assumption works in favour of cracking and no conclusion of this section changes.

Table: **Table 33.3.** Reference-basis turbine-efficiency thresholds (percentage points above 49.64 %) with the cracker heat at three fuel efficiencies. *Source: independent Python calculation, results/research/enduse/turbine_threshold.json cracker_heat_fuel_efficiency_sensitivity.*

| Cracker fuel heat delivered | Full cracking, fired (pp) | Full cracking + PSA (pp) |
|---|---|---|
| 1.0 (reference, fuel counted at 100 % of its lower heating value, optimistic) | +{{VAL:enduse/turbine_threshold.json#cracker_heat_fuel_efficiency_sensitivity/cases/0/full_fired/threshold_delta_fuel_pp_vs_direct_turbine|.3f}} | +{{VAL:enduse/turbine_threshold.json#cracker_heat_fuel_efficiency_sensitivity/cases/0/full_purified/threshold_delta_fuel_pp_vs_direct_turbine|.3f}} |
| 0.9225 (the flowsheet's own tail-gas ratio) | +{{VAL:enduse/turbine_threshold.json#cracker_heat_fuel_efficiency_sensitivity/cases/1/full_fired/threshold_delta_fuel_pp_vs_direct_turbine|.3f}} | +{{VAL:enduse/turbine_threshold.json#cracker_heat_fuel_efficiency_sensitivity/cases/1/full_purified/threshold_delta_fuel_pp_vs_direct_turbine|.3f}} |
| 0.85 | +{{VAL:enduse/turbine_threshold.json#cracker_heat_fuel_efficiency_sensitivity/cases/2/full_fired/threshold_delta_fuel_pp_vs_direct_turbine|.3f}} | +{{VAL:enduse/turbine_threshold.json#cracker_heat_fuel_efficiency_sensitivity/cases/2/full_purified/threshold_delta_fuel_pp_vs_direct_turbine|.3f}} |

![**Figure 33.1.** Turbine-efficiency threshold for each cracking pathway against the sourced efficiency values. A pathway beats direct NH~3~ power only where the sourced efficiency gain exceeds its threshold. *Source: independent Python calculation, results/figures/research/enduse_turbine_threshold.png.*](../../results/figures/research/enduse_turbine_threshold.png){width=90%}

![**Figure 33.2.** Two-way map of the H~2~-fuel efficiency gain against the cracker CAPEX multiple. Fired cracking is cheapest only above the threshold line, which runs from +2.4 pp at CAPEX x0.25 to +16 pp at x4; cracking + PSA is never the cheapest option on the grid. *Source: independent Python calculation, results/figures/research/enduse_twoway_map.png.*](../../results/figures/research/enduse_twoway_map.png){width=85%}

## 33.3 Sensitivities

Capacity factor matters: at 6000 h/yr or less, direct use beats exhaust-heated cracking. No capacity factor is sourced; 8000 h is a reference-scenario choice. Sourced capital uplifts (an H~2~/NH~3~ turbine cost ratio of 0.9698 from Abuzayed et al., 2025; +12 to 16 % for an ammonia-fired combined cycle against natural gas from the National Energy Technology Laboratory, 2024) and SCR costs change the differences by no more than about 7 USD/MWh. The stored fired-cracker cases give LCOE (fired / PSA) of 292.6 / 325.1 USD/MWh without heat integration, 279.5 / 311.1 at low temperature and 280.5 / 310.1 at high temperature.

![**Figure 33.3.** LCOE of each pathway against the efficiency gain on hydrogen-rich fuel. *Source: independent Python calculation, results/figures/research/enduse_sensitivity_efficiency.png.*](../../results/figures/research/enduse_sensitivity_efficiency.png){width=85%}

**The 40 % figure.** The essay quotes direct ammonia as about 40 % cheaper than cracking-based power, attributed to Halim et al. (2025), whose full text could not be accessed. The largest computed gap across the three stored bases is 16.6 % (Ahmad basis, purified), and 27.3 % anywhere in the sensitivities (cracking + PSA at CAPEX x3). Reaching 40 % would need a cracker CAPEX of 6.3 times (cracking + PSA) or 11.1 times (fired cracking) the reference. Row H1-b is therefore CONTRADICTED.

## 33.4 Hydrogen as the product (H1-d)

Cracked hydrogen from grey NH~3~ costs 4.015 USD/kg (5.174 SGD/kg; fuel counted at 100 % of its lower heating value, optimistic; 4.038 to 4.063 USD/kg at fuel efficiencies of 0.9225 and 0.85), above the NE Asia SMR marker of 3.06 USD/kg (Argus Media, 2026) and a Singapore willingness to pay of 3.0 USD/kg (search-summary grade), and below the 6.0 USD/kg delivered low-carbon benchmark. The break-even NH~3~ prices against the first two are 320 and 312 USD/t. The energy half of the row depends on the turbine assumption: per kg NH~3~, direct combustion gives 2.565 kWh, cracking + PSA 2.251 kWh with the efficiency copied, 2.582 kWh with the NETL +7.3 pp applied absolutely, and 2.526 kWh with it applied as a ratio. No Singapore hydrogen transaction price, no comparison with liquid hydrogen, LOHC or local electrolysis and no end-user value of purity exists in the library.
<!-- data: results/research/enduse/turbine_threshold.json row_evidence.H1-d, forty_percent_figure (16.6 %, 27.3 %, x6.3, x11.1) -->

## 33.5 Emissions

Direct NH~3~ combustion emits 0.000801 kg N~2~O/MWh in the Ahmad et al. (2025) simulation: 0.2185 kg CO~2~e/MWh at the AR6 GWP of 273 (used for the life-cycle intensity) and 0.2121 at the GWP of 265 used by the Singapore Carbon Pricing Act (used for the tax). At 45 SGD/t the tax is 0.0095 SGD/MWh. NO is 0.389 kg/MWh in a simulation that underestimates NO and is never added to CO~2~e. No N~2~O or NO~x~ value for blends or cracked gas is sourced. The 30 to 60 vol% H~2~ blending range is for H~2~ in natural gas (National Energy Technology Laboratory, 2022), not for NH~3~-H~2~ blends.

## 33.6 What H1 can and cannot claim

The PSA half of row H1-a passes on every basis and is stated as a finding: direct ammonia combustion is cheaper than cracking with purification for power, unless a turbine on pure hydrogen gains at least 9.68 pp of efficiency (the lowest threshold over the 11 bases; 8.36 pp at CAPEX x0.25), more than the only sourced value of 7.3 pp. That value is a single upper-bound source (NETL, an H-class cycle simulation with steam-diluted hydrogen, not like for like), so the finding is as strong as that one source. The fired half cannot be decided without a sourced efficiency for H~2~/N~2~ fuel, so the row, which claims both, is INCONCLUSIVE. Row H1-c (exhaust-heated cracking) is INCONCLUSIVE because its sign changes inside the sourced ranges. Row H1-d is INCONCLUSIVE because the electricity per kg NH~3~ of cracking + PSA at the sourced turbine gains (2.526 to 2.582 kWh) straddles direct combustion (2.565 kWh); cracked hydrogen at 4.015 USD/kg lies above the 3.06 USD/kg marker and below the 6.0 USD/kg delivered benchmark. The hypothesis verdict is in Section 40: {{VERDICT:H1}}.
