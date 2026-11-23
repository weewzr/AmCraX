<!-- cites: lee2022ammonia, ahmad2025gtcc, ema2025ses, glec2023v3, ipcc2006v2ch2, ipcc2021ar6wg1ch7, iea2024ghr, elgowainy2024h2lca, ramadan2022h2costs, zhang2022ammoniachina, halim2025ammonia, cechetto2023membrane, nea_carbon_tax, eu2023_1185 -->

# 30 Life-cycle greenhouse-gas assessment

## 30.1 Scope and boundary

This section extends the carbon-intensity accounting of Section 21 to a scenario-based life-cycle greenhouse-gas assessment of ammonia imported to Singapore and then either cracked to hydrogen or burnt for power. It is a **screening assessment on a gate-to-use boundary**, not a full life-cycle assessment with a verified inventory. Two functional units are used: 1 kg of hydrogen at the PSA outlet (99.96 mol % H~2~) at the cracker, and 1 MWh of net electricity. The activity data (7.350 kg NH~3~ per kg H~2~, efficiency 0.877; 389.84 kg NH~3~ per MWh, efficiency 0.496) are stored **Aspen Plus V15** results and the **literature**-calibrated turbine of Section 29. Everything else is an **independent Python calculation** with literature emission factors and labelled assumptions.

The boundary includes: ammonia production up to the production-plant gate (well-to-gate), sea shipping over a stated distance, optional boil-off (default zero, unsourced), process electricity at the Singapore grid factor, and direct N~2~O at the turbine. It excludes plant construction, catalyst, hydrogen compression and delivery, and the natural-gas supply chain of the comparators, except through a methane-leakage parameter. Global warming potentials are GWP-100 from IPCC AR6. NO~x~ is reported separately and is never added to CO~2~e. The carbon tax is applied only to direct in-scope Singapore emissions (National Environment Agency, n.d.), which here means the turbine N~2~O only; upstream and shipping emissions arise outside the Singapore tax base.

## 30.2 Method

The delivered ammonia intensity is the production-gate intensity plus shipping:

$$ e_\mathrm{del} = e_\mathrm{gate} + \frac{f_\mathrm{ship}\,d}{1000} \qquad (30.1) $$

where $e_\mathrm{gate}$ (kg CO~2~e/kg NH~3~) is the gate intensity of the route, $f_\mathrm{ship}$ = 0.011 kg CO~2~e/(t km) the well-to-wake factor for a liquefied-gas tanker (Smart Freight Centre, 2023, via a data-provider listing), and $d$ (km) the sea distance. The intensity per functional unit is

$$ \mathrm{CI}_{\mathrm{H_2}} = y_{\mathrm{NH_3}}\,e_\mathrm{del} + E_\mathrm{el}\,\mathrm{GEF}, \qquad \mathrm{CI}_\mathrm{MWh} = m_{\mathrm{NH_3}}\,e_\mathrm{del} + e_{\mathrm{N_2O}} \qquad (30.2) $$

where $y_{\mathrm{NH_3}}$ (kg NH~3~/kg H~2~) and $m_{\mathrm{NH_3}}$ (kg NH~3~/MWh) are the ammonia consumed, $E_\mathrm{el}$ (kWh/kg H~2~) the process electricity, $\mathrm{GEF}$ = 0.402 kg CO~2~/kWh the 2024 average grid factor (Energy Market Authority, 2025), and $e_{\mathrm{N_2O}}$ (kg CO~2~e/MWh) the turbine N~2~O. Electricity-pathway results are in kg CO~2~e/MWh.

The blue-ammonia gate intensity is parameterised from the Lee et al. (2022) inventory, which gives 2.60 (no capture), 1.16 (process CO~2~ captured, version 1) and 0.77 kg CO~2~e/kg NH~3~ (process and flue-gas CO~2~ captured, version 2):

$$ e_\mathrm{blue} = e_\mathrm{grey} - (1-\pi_\mathrm{p})\,c_\mathrm{p}\,E_\mathrm{p} - (1-\pi_\mathrm{f})\,c_\mathrm{f}\,E_\mathrm{f} + \mathrm{GWP}_{\mathrm{CH_4}}\,\ell\,m_\mathrm{NG} \qquad (30.3) $$

where $e_\mathrm{grey}$ = 2.60, $E_\mathrm{p}$ = 1.49 and $E_\mathrm{f}$ = 0.45 kg CO~2~/kg NH~3~ are the process and flue-gas CO~2~ (Lee et al., 2022, p. 13), $c_\mathrm{p}$ and $c_\mathrm{f}$ (–) the capture fractions, $\pi_\mathrm{p}$ = 0.0336 and $\pi_\mathrm{f}$ = 0.1333 kg CO~2~e per kg CO~2~ captured the capture penalties derived from the two Lee versions, $\mathrm{GWP}_{\mathrm{CH_4}}$ = 29.8 the fossil CH~4~ GWP-100, $\ell$ (–) the extra upstream methane leakage as a fraction of gas supplied, and $m_\mathrm{NG}$ = 0.6904 kg NG/kg NH~3~ (32.52 GJ/t at 47.1 MJ/kg, Lee et al., 2022). Equation (30.3) reproduces version 1 ($c_\mathrm{p}$ = 1, $c_\mathrm{f}$ = 0, $\ell$ = 0) and version 2 ($c_\mathrm{p}$ = $c_\mathrm{f}$ = 1) exactly (validation items LCA-blue-v1, LCA-blue-v2). The "blue_param" route uses $c_\mathrm{p}$ = 0.95, $c_\mathrm{f}$ = 0 and $\ell$ = 0.015 (assumptions).

The natural-gas CCGT comparator uses the IPCC 2006 factor of 56.1 kg CO~2~/GJ (Intergovernmental Panel on Climate Change, 2006) and an assumed efficiency of 0.55: $56.1 \times 3.6 / 0.55 = 367.2$ kg CO~2~/MWh. The **break-even gate intensity** at which a pathway equals an alternative with intensity $\mathrm{CI}_\mathrm{alt}$ follows from Eq. (30.2):

$$ e^{*}_\mathrm{gate} = \frac{\mathrm{CI}_\mathrm{alt} - e_{\mathrm{N_2O}}}{m_{\mathrm{NH_3}}} - \frac{f_\mathrm{ship}\,d}{1000} \qquad (30.4) $$

shown here for power; for hydrogen $e_{\mathrm{N_2O}}$ is replaced by the electricity term and $m_{\mathrm{NH_3}}$ by $y_{\mathrm{NH_3}}$. An ammonia route with gate intensity at or below $e^*_\mathrm{gate}$ cuts emissions against that alternative.

## 30.3 Data and assumptions

Table: **Table 30.1.** Principal inputs and their status. All web values accessed 23 November 2026. *Source: results/research/lca/assumptions.json.*

| Input | Value | Unit | Origin | Source and note |
|---|---|---|---|---|
| Grey NH~3~ gate intensity | 2.6 (range 2.0 to 4.6) | kg CO~2~e/kg NH~3~ | literature | Lee et al. (2022); range from Cechetto et al. (2023), p. 19 |
| Blue NH~3~, Lee v1 / v2 | 1.16 / 0.77 | kg CO~2~e/kg NH~3~ | literature | Lee et al. (2022), p. 13 |
| Green NH~3~ | 0.2752 (0.071 to 0.479), including embedded asset emissions | kg CO~2~e/kg NH~3~ | literature | International Energy Agency (2024) embedded-asset range 0.4 to 2.7 kg CO~2~e/kg H~2~, highlights only; Lee boundary gives 0 |
| Coal NH~3~ | 3.03 (2.18 to 3.88) | kg CO~2~e/kg NH~3~ | literature, low confidence | abstract-level extract; see Section 30.5 |
| Sea distance | 5000 (2000 to 12 000) | km | assumption | scenario values; no sea-distance source reached |
| Shipping factor | 0.011 | kg CO~2~e/(t km) | literature | Smart Freight Centre (2023), via a data-provider listing; primary PDF not opened |
| Boil-off | 0 | fraction | assumption | no sourced value |
| Singapore grid factor | 0.402 | kg CO~2~/kWh | literature | Energy Market Authority (2025), 0.412 in 2023; page script-rendered, value from a search extract |
| NG CCGT efficiency | 0.55 (0.50 to 0.60) | – | assumption | no Singapore plant source |
| NG upstream leakage cases | 0.2, 1.5, 3.0 | % of gas | literature (preprint) | Ramadan et al. (2022), search extract only |
| GWP-100 CH~4~ (fossil), N~2~O | 29.8, 273 | – | literature | IPCC AR6 (Forster et al., 2021); 29.8 and 273 confirmed in the GHG Protocol AR6 GWP table (August 2024) during the independent review |
| SMR H~2~, unabated | 11.0 (10 to 12) | kg CO~2~e/kg H~2~ | literature | International Energy Agency (2024), highlights only |
| SMR H~2~ with CCS | 3.5 (3.4 to 3.6; 5.3 upper) | kg CO~2~e/kg H~2~ | literature, low confidence | literature range quoted by Elgowainy et al. (2024) from other studies (secondary); Ramadan et al. (2022); capture rate and boundary not confirmed |
| Turbine N~2~O, NO | 0.15, 107 | µmol/mol in exhaust | literature (simulated) | Ahmad et al. (2025), p. 9; flue-gas flow 3.492 t/MWh |
| Carbon tax | 45 | SGD/t CO~2~e | literature | National Environment Agency (n.d.) |

The green-ammonia value is taken with embedded renewable-asset emissions from the International Energy Agency (2024) range, whereas the Lee et al. boundary excludes equipment manufacture and gives zero; both are shown. The reference carbon intensity of green hydrogen in Section 21 (0.407 kg CO~2~e/kg H~2~) uses the zero-gate boundary and is reproduced here as the "green_lee" row (validation item LCA-baseline-green).

## 30.4 Results

### Hydrogen and power by route

Table: **Table 30.2.** Carbon intensity of the cracked-ammonia routes at 5000 km. Hydrogen is 1 kg at the PSA outlet; power is 1 MWh from direct NH~3~ in a CCGT, and from cracked and PSA-purified H~2~ in a CCGT. Ranges are the low and high gate intensities. *Source: results/research/lca/lca_results.json routes[*] and lca_routes.csv.*

| Route | Gate intensity (kg CO~2~e/kg NH~3~) | H~2~ (kg CO~2~e/kg H~2~) | H~2~ range | Direct NH~3~ power (kg CO~2~e/MWh) | Cracked and purified H~2~ power (kg CO~2~e/MWh) |
|---|---|---|---|---|---|
| Green, with embedded emissions | 0.275 | 2.43 | 0.93 to 3.93 | 128.9 | 146.9 |
| Green, Lee boundary (zero gate) | 0.000 | 0.41 | 0.41 to 3.93 | 21.7 | 24.6 |
| Blue, Lee v1 | 1.160 | 8.93 | 6.07 to 14.53 | 473.9 | 540.1 |
| Blue, Lee v2 | 0.770 | 6.07 | 6.07 to 11.95 | 321.8 | 366.8 |
| Blue, 95 % process capture, 1.5 % extra leakage | 1.541 | 11.73 | 9.24 to 14.53 | 622.3 | 709.2 |
| Grey | 2.600 | 19.52 | 15.11 to 34.22 | 1035.2 | 1179.9 |
| Coal (low confidence) | 3.030 | 22.68 | 16.43 to 28.93 | 1202.9 | 1370.9 |

<!-- data: results/research/lca/lca_results.json routes[*].gate_kgCO2e_per_kgNH3, H2_kgCO2e_per_kg, H2_low_high, direct_NH3_CCGT_kgCO2e_per_MWh, cracked_purified_H2_CCGT_kgCO2e_per_MWh -->

Comparators: unabated SMR hydrogen 11.0 (10 to 12) and SMR with CCS 3.5 (3.4 to 3.6, upper sensitivity 5.3, low confidence) kg CO~2~e/kg H~2~; natural-gas CCGT 367.2 kg CO~2~e/MWh at efficiency 0.55 (336.6 at 0.60, 403.9 at 0.50, 429.3 at 1.5 % and 491.4 at 3.0 % upstream leakage); and the Singapore grid average 402.0 kg CO~2~e/MWh. Of the direct-ammonia power routes, only green (128.9, or 21.7 on the Lee boundary) and blue with both process and flue-gas CO~2~ captured (321.8) fall below the natural-gas CCGT at 367.2; blue Lee v1 (473.9) is above it and above the grid average. For hydrogen, blue Lee v1 (8.93) is below unabated SMR (11.0) and above SMR with CCS (3.5); blue Lee v2 is 6.07.
<!-- data: results/research/lca/lca_results.json alternatives.ccgt_ng_kgCO2e_per_MWh {central 367.2, high_eff_0.60 336.6, low_eff_0.50 403.92, leak_0.015 429.319, leak_0.03 491.439}, alternatives.grid_average_kgCO2e_per_MWh.central 402.0, alternatives.smr_h2_unabated_kgCO2e_per_kgH2, smr_h2_ccs_kgCO2e_per_kgH2 -->

![**Figure 30.1.** Carbon intensity of hydrogen by ammonia route, with SMR comparators. *Source: independent Python calculation on Aspen Plus V15 activity data (results/research/lca/lca_routes.csv).*](../../results/figures/research/lca_h2_by_route.png){width=85%}

![**Figure 30.2.** Carbon intensity of direct-ammonia and cracked-ammonia power by route, with the natural-gas CCGT and grid average. *Source: independent Python calculation (results/research/lca/lca_routes.csv).*](../../results/figures/research/lca_power_by_route.png){width=85%}

### Break-even gate intensity

Table: **Table 30.3.** Largest ammonia gate intensity (kg CO~2~e/kg NH~3~) at which the pathway emits no more than the alternative (Eq. 30.4). *Source: results/research/lca/lca_results.json breakeven[*].breakeven_NH3_gate_EF_kgCO2e_per_kgNH3.*

| Pathway against alternative | 2000 km | 5000 km | 12 000 km |
|---|---|---|---|
| Direct NH~3~ CCGT against NG CCGT | 0.919 | 0.886 | 0.809 |
| Direct NH~3~ CCGT against NG CCGT with 1.5 % upstream leakage | 1.079 | 1.046 | 0.969 |
| Direct NH~3~ CCGT against grid average | 1.009 | 0.976 | 0.899 |
| 40 vol % partially cracked against NG CCGT | 0.954 | 0.921 | 0.844 |
| Cracked and purified H~2~ CCGT against NG CCGT | 0.804 | 0.771 | 0.694 |
| Cracked and purified H~2~ CCGT against grid average | 0.882 | 0.849 | 0.772 |
| Industrial H~2~ against unabated SMR | 1.474 | 1.441 | 1.364 |
| Industrial H~2~ against SMR with CCS | 0.454 | 0.421 | 0.344 |

Blue Lee v1 (1.16) is above every power break-even in the table and below the unabated-SMR hydrogen break-even; blue Lee v2 (0.77) is below the direct-ammonia power break-evens against natural gas and the grid at every distance, and only just below the cracked-and-purified break-even against natural gas at 5000 km (0.771). Green, at 0.0 to 0.28, is below every break-even in the table, including the lowest (0.344, SMR with CCS at 12 000 km).
<!-- data: results/research/lca/lca_results.json breakeven[*] and routes[*].gate_kgCO2e_per_kgNH3 -->

![**Figure 30.3.** Break-even ammonia gate intensity against sea distance for the power pathways. *Source: independent Python calculation (results/research/lca/lca_breakeven.csv).*](../../results/figures/research/lca_breakeven_power.png){width=85%}

### Distance, sensitivity and uncertainty

Shipping is minor. Over 0 to 12 000 km the green hydrogen intensity rises from 2.026 to 2.996 kg CO~2~e/kg H~2~ and blue (v1) from 8.529 to 9.499; direct-ammonia power rises from 107.5 to 159.0 (green) and from 452.4 to 503.9 kg CO~2~e/MWh (blue). At 5000 km shipping is 0.055 kg CO~2~e/kg NH~3~.
<!-- data: results/research/lca/lca_distance.csv rows distance_km 0 and 12000, routes green and blue -->

Table: **Table 30.4.** One-at-a-time sensitivity of the margin (NG CCGT minus blue Lee v1 direct-ammonia power, kg CO~2~e/MWh; base -255.1, negative means the ammonia route emits more). *Source: results/research/lca/lca_sensitivity_oat.csv.*

| Parameter | Margin at low value | Margin at high value |
|---|---|---|
| Process CO~2~ capture 0.90 to 1.00 | -283.1 | -227.0 |
| Extra upstream CH~4~ leakage 0.2 to 3.0 % | -150.8 | -375.4 |
| Sea distance 2000 to 12 000 km | -242.2 | -285.1 |
| Turbine electricity per kg NH~3~ ±6 % | -294.8 | -219.8 |
| CCGT efficiency 0.50 to 0.60 | -218.3 | -285.7 |
| CCGT upstream CH~4~ leakage 0 to 3 % | -255.1 | -130.8 |

No single parameter in these ranges reverses the sign of the margin. In a Monte Carlo draw (20 000 samples, seed 20261123, uniform over the stated capture, leakage and distance ranges, which are sourced or scenario bounds), blue direct-ammonia power has a carbon intensity of 526.0 (p5), 640.6 (p50) and 759.5 (p95) kg CO~2~e/MWh and beats the natural-gas CCGT in 0.2 % of draws. Blue industrial hydrogen has 10.03, 12.06 and 14.08 kg CO~2~e/kg H~2~ and beats unabated SMR in 25.1 % of draws and SMR with CCS in none. The medians sit above the version 1 point values, which is consistent with the uniform ranges including extra leakage that version 1 excludes.
<!-- data: results/research/lca/lca_results.json monte_carlo.blue_direct_NH3_power.CI_kgCO2e_per_MWh_p5_p50_p95, P_cuts_emissions_vs_NG_CCGT 0.00215; monte_carlo.blue_industrial_H2.CI_kgCO2e_per_kgH2_p5_p50_p95, P_below_SMR_unabated 0.25105, P_below_SMR_CCS 0.0 -->

![**Figure 30.4.** Sensitivity of the blue-ammonia power margin to the main parameters. *Source: independent Python calculation (results/research/lca/lca_sensitivity_oat.csv).*](../../results/figures/research/lca_sensitivity_blue_power.png){width=85%}

### N~2~O, NO~x~ and carbon tax

The turbine N~2~O is 0.0008 kg/MWh, or 0.2186 kg CO~2~e/MWh, and is the only direct in-scope emission. It is a simulated value, not a measurement, and it does not show that N~2~O is negligible in practice. A plant of the size considered here would emit far less than the 25 000 t CO~2~e/yr facility threshold of the Singapore carbon tax, so its carbon-tax liability is zero. (Without the threshold, 45 SGD/t would correspond to 0.0098 SGD/MWh; this hypothetical figure is not a cost the plant would pay.) NO is 0.389 kg/MWh and is reported separately. Both come from the simulated exhaust of Ahmad et al. (2025) with an assumed air-like exhaust molar mass of 28.8 g/mol; NO~x~ is not quantified for blends or cracked fuels, and no NO~x~ abatement cost is included.
<!-- data: results/research/lca/lca_results.json n2o_nox.N2O_kg_per_MWh 0.00080057, N2O_kgCO2e_per_MWh 0.21855, NO_kg_per_MWh 0.38933; carbon_tax_sg.SGD_per_MWh 0.0098349; results/research/enduse/enduse_results.json power_pathways[id=direct].carbon_tax_USD_per_MWh_direct_in_scope 0.0076240 -->

## 30.5 Validation status and failures

`results/research/validation/lca.json` has 11 items: 7 pass, 0 fail, 4 informational. Passes: reproduction of Lee et al. version 1 (1.16) and version 2 (0.77) by Eq. (30.3); reproduction of the Section 21 baseline carbon intensity for grey (19.518), blue (8.933) and green (0.407) with the old settings; closure of the breakdown; and the NH~3~ per kg H~2~ consistent with the stored Aspen feed. Informational items: the computed natural-gas CCGT intensity (367.2) lies below the EMA grid average (402.0); blue Lee v1 hydrogen (8.93) is above the EU RFNBO yardstick implied by Delegated Regulation 2023/1185 (3.38 kg CO~2~e/kg H~2~; European Commission, 2023) and above the International Energy Agency low-emission yardstick as quoted by Kum et al. (4.0); and the comparison with SMR. None of these validates the route factors against independent inventories; they check arithmetic and reproduction of one source.

**Source problems found.** The coal-ammonia range (2.18 to 3.88 kg CO~2~e/kg NH~3~) was recorded from a search extract of a paper whose DOI (10.1007/s11367-021-02010-z) resolves, in Crossref on 23 November 2026, to Zhang et al. (2022), "Life cycle assessment of ammonia synthesis in China", and not to the coal-gasification title originally recorded. The figures are not verified against that paper and the coal route is marked low confidence. The SMR-with-CCS values come from search extracts of Elgowainy et al. (2024), whose title and authors were corrected, and of a preprint (Ramadan et al., 2022); the capture rate and boundary behind 3.4 to 3.6 and 5.3 are not confirmed. The International Energy Agency (2024) values come from the highlights page only. The 29.8 GWP for fossil methane was not re-opened in the IPCC table.

## 30.6 Comparison with literature

On a like-for-like boundary, the ammonia gate intensities reproduce Lee et al. (2022) exactly, by construction. The SMR comparators (International Energy Agency, 2024; Elgowainy et al., 2024) are production-to-gate values that include their own upstream emissions, whereas the AmCraX hydrogen routes add shipping and cracking electricity and exclude compression and plant construction; the comparison with 11.0 and 3.5 kg CO~2~e/kg H~2~ is therefore indicative. The qualitative conclusions of the abstract of Halim et al. (2025) are consistent with the results: green ammonia has near-zero emissions in use, blue ammonia is an interim option (here 8.93 and 6.07 for hydrogen against 11.0 for unabated SMR), and cracked ammonia from coal would exceed the Singapore grid emission factor (1203 against 402 kg CO~2~e/MWh for direct power, 1371 for cracked and purified hydrogen power). Halim et al. (2025) numerical results were not accessible.

## 30.7 Limitations

* Gate intensities for blue and coal ammonia are scenario parameters. Capture fractions, leakage cases and the coal range are not measured values for any Singapore supply.
* Distances are scenario bounds; no route length, boil-off or terminal loss is sourced.
* Green ammonia is shown with and without embedded asset emissions; the choice moves hydrogen from 0.41 to 2.43 kg CO~2~e/kg.
* The natural-gas comparator excludes its own supply chain beyond the leakage parameter, and its efficiency (0.55) is assumed.
* N~2~O and NO come from one simulation in one paper, converted with an assumed exhaust molar mass; N~2~O from furnaces or cracker heating is not quantified.
* This is not an ISO 14040 life-cycle assessment: no construction, catalyst, end-of-life or compression and delivery stages are included.

## 30.8 Implication for hypothesis H2

For the carbon half of H2, the results show that low carbon intensity depends on how the ammonia is made, not only on its price. Green ammonia gives 2.43 kg CO~2~e/kg H~2~ (0.41 on the Lee boundary) and 129 kg CO~2~e/MWh for direct power. Blue ammonia on the Lee version 1 inventory gives 8.93 and 474, which is below unabated SMR but above natural-gas CCGT power and the grid average, and it cuts emissions against natural-gas power only when both process and flue-gas CO~2~ are captured and leakage is low (321.8 kg CO~2~e/MWh for version 2). Grey ammonia, the cheapest scenario in Section 27, gives 19.52 kg CO~2~e/kg H~2~. The verdict on H2 is given in Section 31.
