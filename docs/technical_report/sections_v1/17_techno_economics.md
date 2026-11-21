<!-- cites: cho2026nickel, kum2026heatintegrated, farokhi2025costoptimization, ahmad2025gtcc, chopra2026decentralized, richard2024technoeconomic -->

# 17 Techno-economic assessment

## 17.1 Method and economic basis

The levelised cost of hydrogen (LCOH) is computed by `amcrax.economics.compute_lcoh` (**independent Python calculation**) from the converged **Aspen Plus V15 simulation** of the baseline (600 °C, 20 bar, H~2~ recovery 0.85; Section 6). The inputs are listed in Table 17.1. Costs are nominal USD in the cost year of each source; no CEPCI escalation is applied because the two 2024 CEPCI values in the library conflict, so the result is labelled "mixed 2024–2025 USD".

Table: **Table 17.1.** Economic basis of the baseline LCOH. *Source: backend/amcrax/data/economics.yaml (values with page/table locators; "assumption" = engineering assumption with rationale in the file).*

| Input | Value | Unit | Cost year | Source |
|---|---|---|---|---|
| NH~3~ price | 450 | USD/t | 2024 | Cho et al. (2026), Table 4; range 300–610, Table 8 |
| Electricity | 0.084 | USD/kWh | 2024 | Cho et al. (2026), Table 4 |
| Cooling water | 2.125 × 10^−7^ | USD/kJ | 2024 | Cho et al. (2026), Table 4 |
| Imported heat | extra NH~3~ burnt, 100 % of LHV delivered | – | – | assumption (optimistic) |
| Catalyst (Ni) price / life | 33.4 / 2 | USD/kg, yr | 2024 | Cho et al. (2026), Table 4 |
| CAPEX correlation | 18.171 S^0.7451^ | MUSD (S in t H~2~/h) | not stated | Ahmad et al. (2025), Fig. 6 |
| Maintenance / insurance | 0.03 / 0.015 | 1/yr of CAPEX | 2025 | Chopra et al. (2026), Table 2 |
| Labour | 109 756 | USD/yr | 2025 | Chopra et al. (2026), Table 2 |
| Overhead / G&A | 0.25 / 0.06 | fraction | 2024 | Cho et al. (2026), Table 4 |
| Discount rate / plant life | 0.10 / 25 | –, yr | – | Kum et al. (2026), Table 5 |
| Operating hours | 8000 | h/yr | – | Cho et al. (2026), Table 4 |
| H~2~ compression | 0 | kW | – | assumption (no compressor in flowsheet) |

$$ \mathrm{LCOH} = \frac{\mathrm{CRF}\cdot C_\mathrm{cap} + C_\mathrm{fix} + C_\mathrm{var}}{\dot m_{\mathrm{H_2}}\, t_\mathrm{op}}, \qquad \mathrm{CRF} = \frac{i(1+i)^n}{(1+i)^n - 1} \qquad (17.1) $$

where $C_\mathrm{cap}$ (USD) is the total CAPEX, $C_\mathrm{fix}$ (USD/yr) the fixed OPEX (maintenance, insurance, labour, overhead, G&A), $C_\mathrm{var}$ (USD/yr) the NH~3~ feed, imported heat, electricity, cooling water and catalyst replacement, $\dot m_{\mathrm{H_2}}$ (kg/h) the H~2~ product, $t_\mathrm{op}$ (h/yr) the operating hours, $i$ the discount rate and $n$ (yr) the plant life. With $i$ = 0.10 and $n$ = 25, CRF = 0.1102.

**CAPEX.** The CAPEX is a **preliminary order-of-magnitude estimate** (AACE class 4–5 type), obtained by scaling a plant-level literature correlation to the simulated capacity of 251.59 kg H~2~/h. It is not a detailed engineering estimate: no equipment was sized or priced. The Ahmad et al. (2025) correlation gives 6.50 MUSD. Two point estimates scaled with the same exponent give 4.62 MUSD (Chopra et al., 2026; 350 bar compressor share and India location factor removed by AmCraX) and 3.39 MUSD (Farokhi et al., 2025). The three references therefore span a factor of 1.9. The highest value is used as the default.

<!-- data: results/simulations/economics_baseline.json capex.total_capex_USD, capex.alternatives[*].scaled_capex_USD, crf, h2_product_kg_h -->

## 17.2 Baseline LCOH

The baseline LCOH is **3.925 USD/kg H~2~** (preliminary, order of magnitude). NH~3~ feed is 3.047 USD/kg (78 %), annualised CAPEX 0.356, fixed OPEX 0.252 and imported heat 0.268 USD/kg. Electricity, cooling water and catalyst together are below 0.004 USD/kg (Figure 17.1). Excluding the feed, the reconversion cost is 0.879 USD/kg.

![**Figure 17.1.** Breakdown of the baseline LCOH (3.925 USD/kg H~2~ at 450 USD/t NH~3~) into annualised CAPEX, fixed OPEX, NH~3~ feed, imported heat (as NH~3~ fuel), electricity, cooling water and catalyst. Shows that the feed cost controls the LCOH and that utilities other than heat are negligible. *Source: independent Python calculation (amcrax.economics) on Aspen Plus V15 baseline results.*](../../results/figures/lcoh_breakdown_baseline.png){width=85%}

The feed dominates because of the mass balance. The stoichiometric minimum is 5.632 kg NH~3~/kg H~2~. The simulation needs 6.770 kg/kg of feed (total stream, including 0.2 mol% H~2~O). Its 0.85 PSA recovery leaves H~2~ in the tail gas, giving an overall H~2~ yield of 0.834. Another 0.595 kg/kg of NH~3~ is burnt to close the 772.87 kW heat deficit (Section 11.4). The total is 7.365 kg NH~3~/kg H~2~, 31 % above the floor.

<!-- data: results/simulations/economics_baseline.json lcoh_USD_per_kg, breakdown_USD_per_kg, reconversion_cost_USD_per_kg, stoichiometric_floor_kg_nh3_per_kg_h2, kg_nh3_feed_per_kg_h2, kg_nh3_fuel_per_kg_h2; results/simulations/baseline.json kpis.h2_yield_overall, kpis.net_fuel_heat_deficit_kW -->

Without the FEHE (Aspen case baseline_no_hi), fuel NH~3~ rises to 1.065 kg/kg, imported heat to 0.479 USD/kg and the LCOH to 4.14 USD/kg. Heat integration thus saves 0.21 USD/kg (5 %), or 0.43 MUSD/yr. The CAPEX correlation does not change with the FEHE. The indicative heat-exchanger share of the CAPEX, 0.58 MUSD, annualises to 0.064 MUSD/yr, so the saving outweighs the likely cost of the exchanger.

<!-- data: results/simulations/economics_baseline_no_hi.json lcoh_USD_per_kg, breakdown_USD_per_kg.imported_heat, kg_nh3_fuel_per_kg_h2; capex.equipment_breakdown_USD.heat_exchangers in economics_baseline.json (0.58 MUSD, indicative) -->

## 17.3 Sensitivity and ammonia-price breakeven

Each input was varied one at a time over its published range (Figure 17.2). The NH~3~ price (300–610 USD/t) moves the LCOH from 2.82 to 5.10 USD/kg. The CAPEX multiplier (0.5–1.5) moves it from 3.66 to 4.19 USD/kg. Every other input changes it by less than 0.11 USD/kg.

![**Figure 17.2.** One-at-a-time LCOH sensitivity for the baseline; bars span the LCOH at the low (blue) and high (orange) end of each published input range. Ranks the uncertainties: NH~3~ price first, CAPEX second, all financial and utility inputs minor. *Source: independent Python calculation on Aspen Plus V15 baseline; ranges from Cho et al. (2026) Table 8 and library minimum–maximum.*](../../results/figures/lcoh_tornado_baseline.png){width=95%}

Because the process data are fixed, the LCOH is linear in the NH~3~ price (Figure 17.3). The slope is 7.36 × 10^−3^ USD/kg per USD/t, which equals the total consumption of 7.36 kg NH~3~/kg H~2~. The intercept of 0.61 USD/kg is the non-feed cost. An illustrative target of 5.0 USD/kg (an engineering assumption, not a policy value) is reached at 595.9 USD/t NH~3~.

<!-- data: results/sensitivity/lcoh_tornado_baseline.csv; results/sensitivity/lcoh_vs_ammonia_price_baseline.csv (rows 0, 450, 600 USD/t); results/simulations/economics_baseline.json breakeven -->

![**Figure 17.3.** AmCraX LCOH versus NH~3~ price (line) with LCOH values published by Cho et al. (2026), Kum et al. (2026) and Farokhi et al. (2025) (points; **published literature**, not AmCraX results). All published points lie above the line. *Source: independent Python calculation on Aspen Plus V15 baseline; literature values from economics.yaml.*](../../results/figures/lcoh_vs_ammonia_price_baseline.png){width=85%}

## 17.4 Comparison with published studies

At 450 USD/t, Cho et al. (2026) report 5.439 USD/kg (Ni, 24.34 bar) and 5.293 USD/kg (Ru, 10 bar). Their reconversion costs of 1.995 and 1.856 USD/kg are more than twice the 0.879 USD/kg of AmCraX. Kum et al. (2026) report 6.27 USD/kg at 475 USD/t, where AmCraX gives 4.11 USD/kg. Farokhi et al. (2025) report 5.5 USD/kg at 520 USD/t, compared with 4.48 USD/kg from AmCraX at 525 USD/t. For Cho's Ni case the feed term is 5.439 − 1.995 = 3.444 USD/kg, against 3.047 USD/kg for AmCraX. Most of the gap is therefore in the reconversion cost, and it is explained by the scope of AmCraX rather than by better performance:

* the CAPEX is a single plant-level correlation, with no installed-cost, contingency or owner's-cost factors built up from sized equipment;
* NO~x~ after-treatment of the tail-gas burner, NH~3~ polishing (TSA) of the product, H~2~ compression and storage, land, taxes and working capital are excluded;
* the imported heat is delivered at 100 % of the NH~3~ LHV, with no fired-heater loss;
* the PSA recovery of 0.85 is above the 0.71–0.81 literature range (Section 12.2), so the feed per kg H~2~ is optimistic.

<!-- data: results/simulations/economics_baseline.json literature_benchmarks, notes; results/sensitivity/lcoh_vs_ammonia_price_baseline.csv rows 475, 525 -->

Read in this light, 3.925 USD/kg is a lower bound for the stated scope. The robust conclusions are that the NH~3~ price controls the LCOH and that heat integration lowers it by about 5 %.
