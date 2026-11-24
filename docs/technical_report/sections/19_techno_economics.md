<!-- cites: cho2026nickel, kum2026heatintegrated, farokhi2025costoptimization, ahmad2025gtcc, chopra2026decentralized, abdoos2025psa -->

# 19 Techno-economic assessment

**Status in version 2.0.** This section documents the legacy cost model of the core platform. Its results, including the baseline LCOH of 3.919 USD/kg H~2~ at 0.084 USD/kWh, are legacy core results, superseded for research outputs: every research section and the browser simulator use the unified reference scenario of Section 32 (4.015 USD/kg H~2~, 7.67 MUSD CAPEX, 0.1402 USD/kWh). The stored core files in `results/simulations` are unchanged and still reproduce the numbers below.

## 19.1 Method and economic basis

The levelised cost of hydrogen (LCOH) is computed by `amcrax.economics.compute_lcoh` (**independent Python calculation**) from the converged **Aspen Plus V15 simulation** of the baseline (600 °C, 20 bar, H~2~ recovery 0.85; Section 5). Table 19.1 lists the inputs. Costs are nominal USD in the cost year of each source; no CEPCI escalation is applied because the two 2024 CEPCI values in the library conflict, so the result is labelled "mixed 2024–2025 USD".

Table: **Table 19.1.** Economic basis of the baseline LCOH. *Source: backend/amcrax/data/economics.yaml (values with page or table locators; "assumption" = engineering assumption with rationale in the file).*

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

<!-- data: results/simulations/economics_baseline.json assumptions, provenance; backend/amcrax/data/economics.yaml capex ahmad2025_correlation a_MUSD 18.171, exponent 0.7451 -->

$$ \mathrm{LCOH} = \frac{\mathrm{CRF}\cdot C_\mathrm{cap} + C_\mathrm{fix} + C_\mathrm{var}}{\dot m_{\mathrm{H_2}}\, t_\mathrm{op}}, \qquad \mathrm{CRF} = \frac{i(1+i)^n}{(1+i)^n - 1} \qquad (19.1) $$

where $C_\mathrm{cap}$ (USD) is the total CAPEX, $C_\mathrm{fix}$ (USD/yr) the fixed OPEX (maintenance, insurance, labour, overhead, G&A), $C_\mathrm{var}$ (USD/yr) the NH~3~ feed, imported heat, electricity, cooling water and catalyst replacement, $\dot m_{\mathrm{H_2}}$ (kg/h) the H~2~ product, $t_\mathrm{op}$ (h/yr) the operating hours, $i$ (–) the discount rate and $n$ (yr) the plant life. With $i$ = 0.10 and $n$ = 25, CRF = 0.1102.
<!-- data: results/simulations/economics_baseline.json crf (0.110168) -->

**Feed basis.** The ammonia feed is priced on its contained NH~3~, 1699.64 kg/h of the 1703.25 kg/h feed stream; the 0.2 mol% water is not priced.

**CAPEX.** The CAPEX is a **preliminary order-of-magnitude estimate** (AACE class 4–5 type), obtained by scaling a plant-level correlation to the simulated capacity of 251.59 kg H~2~/h. No equipment was sized or priced. The correlation of Ahmad et al. (2025) gives 6.50 MUSD. Two point estimates scaled with the same exponent give 4.62 MUSD (Chopra et al., 2026, with the 350 bar compressor share and the location factor removed by AmCraX) and 3.39 MUSD (Farokhi et al., 2025), a spread of a factor of 1.9; the highest value is the default. Because the correlation depends only on hydrogen capacity, it does not see exchanger area, PSA size or catalyst volume.
<!-- data: results/simulations/economics_baseline.json notes[0..1], capex.total_capex_USD (6498802), capex.alternatives[*].scaled_capex_USD (4622618, 3386348), h2_product_kg_h -->

## 19.2 Baseline LCOH

The legacy baseline LCOH is **3.919 USD/kg H~2~** (preliminary, order of magnitude; legacy core result, superseded for research outputs by 4.015 USD/kg, Section 32). The NH~3~ feed contributes 3.040 USD/kg (78 %), the annualised CAPEX 0.356, the imported heat 0.268 and the fixed OPEX 0.252 USD/kg; electricity, cooling water and catalyst are each below 0.003 USD/kg (Figure 19.1). Excluding the feed, the reconversion cost is 0.879 USD/kg.
<!-- data: results/simulations/economics_baseline.json lcoh_USD_per_kg (3.918842), breakdown_USD_per_kg, reconversion_cost_USD_per_kg (0.878797) -->

![**Figure 19.1.** Breakdown of the baseline LCOH (3.92 USD/kg H~2~ at 450 USD/t NH~3~). The feed cost controls the LCOH, and utilities other than heat are negligible. *Source: independent Python calculation (amcrax.economics) on Aspen Plus V15 baseline results.*](../../results/figures/lcoh_breakdown_baseline.png){width=85%}

The feed dominates because of the mass balance. The stoichiometric minimum is 5.632 kg NH~3~/kg H~2~. The simulation needs 6.756 kg/kg of contained NH~3~ as feed, because the assumed 0.85 PSA recovery leaves H~2~ in the tail gas (overall H~2~ yield 0.834). Another 0.595 kg/kg is burnt to close the 772.87 kW heat deficit. The total of 7.350 kg NH~3~/kg H~2~ is 31 % above the floor.
<!-- data: results/simulations/economics_baseline.json stoichiometric_floor_kg_nh3_per_kg_h2 (5.6321), kg_nh3_feed_per_kg_h2 (6.7557), kg_nh3_fuel_per_kg_h2 (0.5945); baseline.json kpis.h2_yield_overall, net_fuel_heat_deficit_kW; 7.3502/5.6321 - 1 = 0.305 -->

Without the exchanger (Aspen case baseline_no_hi), the fuel NH~3~ rises to 1.065 kg/kg, the imported heat to 0.479 USD/kg and the LCOH to 4.133 USD/kg. The exchanger thus lowers the LCOH by 0.214 USD/kg, 5.2 % of the case without it, or 0.43 MUSD/yr. This comparison leaves out the exchanger's own cost: the CAPEX correlation is blind to equipment size and gives the same 6.50 MUSD for both cases. An indicative split of the CAPEX assigns 0.58 MUSD to all heat exchangers, which annualises to 0.064 MUSD/yr; this suggests, but does not show, that the saving outweighs the exchanger cost.
<!-- data: results/simulations/economics_baseline_no_hi.json lcoh_USD_per_kg (4.132623), breakdown_USD_per_kg.imported_heat (0.479448), kg_nh3_fuel_per_kg_h2 (1.065441), capex.total_capex_USD; (4.132623 - 3.918842) x annual_h2_kg 2012706 = 430277 USD/yr; economics_baseline.json capex.equipment_breakdown_USD.heat_exchangers (580250) x crf -->

## 19.3 Sensitivity and ammonia-price breakeven

Each input was varied one at a time over its published range (Figure 19.2). The NH~3~ price (300–610 USD/t) moves the LCOH from 2.82 to 5.09 USD/kg and the CAPEX multiplier (0.5–1.5) from 3.65 to 4.19 USD/kg. Every other input changes it by less than 0.11 USD/kg.
<!-- data: results/sensitivity/lcoh_tornado_baseline.csv (lcoh_at_low/high, swing) -->

![**Figure 19.2.** One-at-a-time LCOH sensitivity for the baseline; bars span the LCOH at the low (blue) and high (orange) end of each input range. NH~3~ price ranks first, CAPEX second, all financial and utility inputs are minor. *Source: independent Python calculation on Aspen Plus V15 baseline; ranges from Cho et al. (2026) Table 8 and the library minimum–maximum.*](../../results/figures/lcoh_tornado_baseline.png){width=95%}

Because the process data are fixed, the LCOH is linear in the NH~3~ price (Figure 19.3). The slope is 7.350 × 10^−3^ USD/kg per USD/t, equal to the total consumption of 7.350 kg contained NH~3~ per kg H~2~, and the intercept of 0.611 USD/kg is the non-feed cost. An illustrative target of 5.0 USD/kg (an engineering assumption, not a policy value) is reached at 597.1 USD/t NH~3~.
<!-- data: results/sensitivity/lcoh_vs_ammonia_price_baseline.csv (rows 0 and 450 USD/t: 0.611268, 3.918842); amcrax.economics.breakeven_ammonia_price(baseline, defaults, 5.0) = 597.09 -->

![**Figure 19.3.** AmCraX LCOH against NH~3~ price (line) with LCOH values published by Cho et al. (2026), Kum et al. (2026) and Farokhi et al. (2025) (points; **published literature**, not AmCraX results). All published points lie above the line. *Source: independent Python calculation on Aspen Plus V15 baseline; literature values from economics.yaml.*](../../results/figures/lcoh_vs_ammonia_price_baseline.png){width=85%}

## 19.4 Comparison with published studies

Published values at comparable ammonia prices are 5.1–6.4 USD/kg. At 450 USD/t, Cho et al. (2026) report 5.439 USD/kg (Ni, 24.34 bar) and 5.293 USD/kg (Ru, 10 bar), with reconversion costs of 1.995 and 1.856 USD/kg, more than twice the 0.879 USD/kg of AmCraX. Kum et al. (2026) report 6.27 USD/kg at 475 USD/t, where AmCraX gives 4.10 USD/kg. Farokhi et al. (2025) report 5.5 and 5.1 USD/kg at 520 USD/t, where AmCraX gives 4.43 USD/kg. For Cho's Ni case the feed term is 3.444 USD/kg, against 3.040 USD/kg for AmCraX. Most of the gap therefore lies in the reconversion cost, and the scope of AmCraX explains it:

* the CAPEX is a single plant-level correlation, without installed-cost, contingency or owner's-cost factors built up from sized equipment;
* NO~x~ after-treatment of the tail-gas burner, NH~3~ polishing of the product, H~2~ compression and storage, land, taxes and working capital are excluded;
* the imported heat is delivered at 100 % of the NH~3~ LHV, with no fired-heater loss;
* the PSA recovery of 0.85 is above the 0.71–0.81 literature range (Section 11) and above the only published purity-recovery front for cracked-ammonia composition (a simulation by Abdoos et al., 2025: 0.8192 at 99.95 % and 0.7744 at 99.99 % purity, at 8 to 12 bar), so the feed per kg H~2~ is optimistic; Section 32.4 gives the unified baseline at those recoveries.

<!-- data: results/simulations/economics_baseline.json literature_benchmarks, notes[4]; results/sensitivity/lcoh_vs_ammonia_price_baseline.csv rows 475 (4.102596), 500 and 525 (linear interpolation to 520: 4.4334); 5.439 - 1.995 = 3.444 -->

Read in this light, 3.919 USD/kg is a lower bound for the stated scope. The robust conclusions are that the NH~3~ price controls the LCOH and that heat integration lowers it by about 5 % before the exchanger cost is counted.
