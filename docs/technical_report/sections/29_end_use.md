<!-- cites: ahmad2025gtcc, halim2025ammonia, cho2026nickel, chopra2026decentralized, mpa_ema_ammonia_2025, nea_carbon_tax -->

# 29 End-use comparison for Singapore

## 29.1 Scope and boundary

This section compares cracking ammonia with using it directly, by end use, at the Jurong Island setting of Section 27. Two functional units are used: 1 MWh of net electricity from a combined-cycle gas turbine (CCGT), and 1 kg of hydrogen at a stated purity. Sixteen power-pathway variants (13 shown in Table 29.2) and four hydrogen pathways are compared (Tables 29.2 and 29.5).

* **Power:** direct NH~3~; partially cracked NH~3~ at 30, 40, 50 and 60 vol % H~2~ in the fuel; fully cracked H~2~/N~2~; fully cracked and PSA-purified H~2~; and NH~3~ blended with PSA-purified H~2~. Each partial and full cracking case has two heat modes: a cracker **heated by turbine exhaust** (efficiency calibrated to the literature) and a **fired** cracker whose heat comes from extra NH~3~ (stored Aspen reactor and pre-heater duty).
* **Hydrogen:** industrial 99.9 % hydrogen, and hydrogen made to ISO 14687:2019 Grade D purity targets (Section 28), each from the stored Aspen baseline and from the purification study.

The boundary is the plant gate for both units. Ammonia is delivered at a price scenario (Section 27), so every cost is stated either at a common 450 USD/t, which isolates the technology, or at the route's own scenario price. Electricity pathways are reported in USD/MWh and kg CO~2~e/MWh. Hydrogen pathways are in USD/kg and kg CO~2~e/kg. Carbon tax applies only to direct emissions inside Singapore (the turbine N~2~O); upstream emissions and shipping are outside the Singapore tax base (National Environment Agency, n.d.). The work is **independent Python calculation** on stored **Aspen Plus V15** results with **literature** turbine data. No combustion was simulated.

## 29.2 Method

**Efficiency.** The efficiency of the turbine on ammonia, $\eta_\mathrm{d}$, is the electricity per kg NH~3~ of Ahmad et al. (2025, Table 6, Case 2a), restated on the AmCraX lower-heating-value basis (18.6 MJ/kg): 0.4964. The fully cracked, exhaust-heated efficiency is the 0.54 of Ahmad et al. (2025, p. 15) scaled to the same basis, giving 0.546. Intermediate cracked shares are interpolated linearly (an assumption, because the paper gives only the end points):

$$ \eta(s) = \eta_\mathrm{d} + g\,s\,(\eta_\mathrm{c} - \eta_\mathrm{d}) \qquad (29.1) $$

where $s$ (–) is the cracked share of the NH~3~, $\eta_\mathrm{c}$ the fully cracked exhaust-heated efficiency, and $g$ (–) a gain scale (1 for the literature end point, 0.5 and 0 as sensitivities). For the fired and purified variants the direct-NH~3~ turbine efficiency is applied to the H~2~-rich fuel (assumption) and the cracking heat is charged as extra NH~3~.

**Cost.** The cost of electricity is

$$ c_\mathrm{el} = \frac{\mathrm{CRF}\; C_\mathrm{TCI}}{W_\mathrm{net}\,t_\mathrm{op}} + \frac{C_\mathrm{fix}}{W_\mathrm{net}\,t_\mathrm{op}} + \frac{m_{\mathrm{NH_3}}\,p_{\mathrm{NH_3}}}{1000} \qquad (29.2) $$

where $C_\mathrm{TCI}$ (USD) is the total capital investment of the power block and cracker, $W_\mathrm{net}$ (MW) the net output, $t_\mathrm{op}$ (h/yr) the operating hours (8000), $C_\mathrm{fix}$ (USD/yr) the fixed operating cost, $m_{\mathrm{NH_3}}$ (kg/MWh) the ammonia consumed and $p_{\mathrm{NH_3}}$ (USD/t) its price. The non-cracker plant cost is the 181.25 MUSD at 43.1 MW of Ahmad et al. (2025, Sec. 3.1.3) scaled with $(W/43.1)^{0.67}$ (the exponent is an assumption); the fixed operating cost is 0.02843 USD/kWh at 7200 h (Ahmad et al., 2025, Case 2a) scaled with power to the same exponent; in version 2.0 the cracker is priced with the unified reference CAPEX of Section 32, sized on the NH~3~ through the cracker, with the PSA and adsorber items removed for unpurified variants (version 1.0 used the 18.171 $S^{0.7451}$ MUSD correlation of Section 19, which remains a sensitivity basis in Section 33). Hydrogen cost follows the unified reference scenario (Section 32).

**Hydrogen efficiency** is $\eta_{\mathrm{H_2}} = \dot m_{\mathrm{H_2}}\,\mathrm{LHV}_{\mathrm{H_2}} / (\dot m_{\mathrm{NH_3}}\,\mathrm{LHV}_{\mathrm{NH_3}})$ on the total NH~3~ consumed, including supplementary fuel.

**Emissions.** Carbon intensities use the factors and boundary of Section 30; N~2~O (0.15 µmol/mol in the exhaust) and NO (107 µmol/mol) come from the simulated exhaust of Ahmad et al. (2025, p. 9), converted at their flue-gas flow of 3.492 t/MWh. NO is reported on its own and never added to CO~2~e.

## 29.3 Data and assumptions

Table: **Table 29.1.** Principal inputs. *Source: results/research/enduse/assumptions.json; results/research/enduse/enduse_results.json price_set.*

| Input | Value | Origin | Source |
|---|---|---|---|
| Direct-NH~3~ turbine efficiency | 0.4912 (Ahmad basis), 0.4964 (AmCraX LHV basis) | literature, restated | Ahmad et al. (2025), Table 6 |
| Fully cracked exhaust-heated efficiency | 0.54 | literature | Ahmad et al. (2025), p. 15 |
| Interpolation of intermediate cases | linear in cracked share | assumption | no source |
| Non-cracker plant | 181.25 MUSD at 43.1 MW, exponent 0.67 | literature, assumed exponent | Ahmad et al. (2025), Sec. 3.1.3 |
| Cracker CAPEX | unified reference CAPEX (Section 32); 18.171 S^0.7451^ MUSD as a sensitivity basis | literature | Cho et al. (2026), Table 7; Ahmad et al. (2025), Fig. 6 |
| Cracker heat | linear in cracked share, 600 °C, 20 bar | Aspen Plus V15 (stored) | results/simulations/baseline.json |
| NH~3~ price | 450 (reference), 487, 709, 1000, 463 USD/t | scenario | Section 27 |
| Operating hours, discount rate, life | 8000 h/yr, 0.10, 25 yr | literature | Section 27 |
| H~2~ blend range of the turbine | 30 to 60 vol % | brief, unverified | Halim et al. (2025); only the abstract was read |
| Natural-gas combustor limit | 30 vol % H~2~ | literature | Ahmad et al. (2025), p. 2 |

Singapore context: the Maritime and Port Authority of Singapore (2025) announced a consortium for the next phase of a study on ammonia power generation and bunkering, with direct combustion at 55 to 65 MW; this is the setting in which direct use is of practical interest, and AmCraX does not model that plant.

## 29.4 Results

### Power

Table: **Table 29.2.** Electricity pathways at 450 USD/t NH~3~ and 8000 h/yr. Efficiency is NH~3~ LHV to electricity. Carbon intensity (CI) is for green and blue NH~3~ delivered over 5000 km (Section 30). *Source: results/research/enduse/enduse_results.json power_pathways[*] (efficiency_NH3_LHV_to_electricity, cost_USD_per_MWh_at_450, CI_green_kgCO2e_per_MWh, CI_blue_kgCO2e_per_MWh).*

| Pathway | Efficiency | Cost (USD/MWh) | CI green (kg CO~2~e/MWh) | CI blue (kg CO~2~e/MWh) |
|---|---|---|---|---|
| Direct NH~3~ | 0.496 | 258.9 | 128.9 | 473.9 |
| 30 vol % H~2~, exhaust-heated | 0.509 | 259.3 | 125.8 | 462.2 |
| 30 vol % H~2~, fired | 0.492 | 266.1 | 130.0 | 477.9 |
| 40 vol % H~2~, exhaust-heated | 0.515 | 258.9 | 124.4 | 457.0 |
| 40 vol % H~2~, fired | 0.490 | 268.6 | 130.5 | 479.6 |
| 50 vol % H~2~, exhaust-heated | 0.522 | 258.3 | 122.7 | 451.0 |
| 50 vol % H~2~, fired | 0.488 | 271.4 | 131.0 | 481.7 |
| 60 vol % H~2~, exhaust-heated | 0.530 | 257.5 | 120.8 | 443.9 |
| 60 vol % H~2~, fired | 0.486 | 274.6 | 131.7 | 484.0 |
| Full crack H~2~/N~2~, exhaust-heated | 0.546 | 255.6 | 117.3 | 431.0 |
| Full crack H~2~/N~2~, fired | 0.482 | 280.1 | 132.8 | 488.2 |
| Full crack and PSA H~2~ | 0.436 | 310.2 | 146.9 | 540.1 |
| NH~3~ with 40 vol % PSA H~2~ | 0.474 | 278.0 | 135.0 | 496.2 |

<!-- data: results/research/enduse/enduse_results.json power_pathways ids direct, partial_exhaust_30..60, partial_fired_30..60, full_exhaust, full_fired, full_purified, blend_purified_40 -->

At 450 USD/t, direct NH~3~ costs 258.9 USD/MWh, of which capital is 57.9, fixed operating cost 25.6 and ammonia 175.4. The ammonia term is about two thirds of the cost for every pathway (64 to 68 %); the cracker adds capital and, in the fired and purified cases, ammonia as well.
<!-- data: enduse_results.json power_pathways[id=direct].cost_capital 57.9127, cost_fixed_om 25.5875, cost_ammonia 175.428 -->

Table: **Table 29.3.** Cost of direct NH~3~ at each route's own price (USD/MWh). *Source: enduse_results.json power_pathways[id=direct].cost_USD_per_MWh_at_\*.*

| Grey, 450 USD/t | Blue, 487 USD/t | Green 2030, 709 USD/t | Green now, 1000 USD/t |
|---|---|---|---|
| 258.9 | 273.4 | 359.9 | 473.3 |

![**Figure 29.1.** Cost and carbon intensity of the power pathways. *Source: independent Python calculation on Aspen Plus V15 baseline results and literature turbine data (results/research/enduse/pathway_table_power.csv).*](../../results/figures/research/enduse_power_cost_vs_ci.png){width=90%}

![**Figure 29.2.** Power cost against NH~3~ price for the main pathways. The curves cross where the efficiency gain of a pathway pays for its extra capital. *Source: independent Python calculation (results/research/enduse/price_sweep.csv).*](../../results/figures/research/enduse_power_cost_vs_price.png){width=85%}

![**Figure 29.3.** Net efficiency of the power pathways. *Source: literature-calibrated (Ahmad et al., 2025) and independent Python calculation (results/research/enduse/pathway_table_power.csv).*](../../results/figures/research/enduse_power_efficiency.png){width=85%}

### The 40 % claim

The project brief states that direct NH~3~ combustion is about 40 % cheaper than cracking-based power (Halim et al., 2025). The computed gap is far smaller and depends on how the cracker is heated and whether the hydrogen is purified.

Table: **Table 29.4.** Direct NH~3~ against full cracking, by cracker type. Positive "direct cheaper" means direct NH~3~ costs less. *Source: results/research/enduse/enduse_results.json halim_claim_check.computed[*].*

| Basis | Cracking pathway | Direct (USD/MWh) | Cracking (USD/MWh) | Direct cheaper by (% of cracking cost) |
|---|---|---|---|---|
| 450 USD/t, 8000 h | exhaust-heated, unpurified | 258.9 | 255.6 | -1.3 |
| 450 USD/t, 8000 h | fired, unpurified | 258.9 | 280.1 | 7.6 |
| 450 USD/t, 8000 h | PSA-purified | 258.9 | 310.2 | 16.5 |
| 480 USD/t, 7200 h (Ahmad basis) | exhaust-heated, unpurified | 279.9 | 276.9 | -1.1 |
| 480 USD/t, 7200 h (Ahmad basis) | fired, unpurified | 279.9 | 303.2 | 7.7 |
| 480 USD/t, 7200 h (Ahmad basis) | PSA-purified | 279.9 | 335.8 | 16.6 |
| 1000 USD/t | exhaust-heated, unpurified | 473.3 | 450.6 | -5.0 |
| 1000 USD/t | fired, unpurified | 473.3 | 501.0 | 5.5 |
| 1000 USD/t | PSA-purified | 473.3 | 554.6 | 14.7 |

<!-- data: results/research/enduse/enduse_results.json halim_claim_check.computed[*].LCOE_direct, LCOE_cracking, direct_cheaper_by_pct_of_cracking(1-d/c) -->

The 40 % figure is not reproduced. On the unified basis the direct pathway is cheaper than a fired cracker by 5.5 to 7.7 % and than a PSA-purified cracker by 14.7 to 16.6 %, and is dearer than an exhaust-heated unpurified cracker by 1.1 to 5.0 % (version 1.0: 4.1 to 5.2 %, 13.8 to 15.0 % and 4.2 to 6.8 %). Ahmad et al. (2025) report 0.217 and 0.22 USD/kWh for direct and fully cracked power at 320 USD/t (validation item EU-ahmad-320), a gap of about 1.4 % (derived), although the attribution of those values in the paper is inconsistent. Exhaust-heated unpurified full cracking undercuts direct use above 355.1 USD/t NH~3~, and 40 vol % partial cracking above 450.1 USD/t. The inputs of Halim et al. (2025) were not accessible, so the reason for their larger gap could not be checked; candidate reasons (not tested) are a purified-hydrogen turbine fed by a standalone fired cracker, a different cracker cost and a lower capacity factor. The direction of the claim (direct use cheaper than a standalone fired or purified cracker) is supported, and its magnitude is not.

### Partial cracking

On the unified basis an exhaust-heated 40 vol % H~2~ blend costs the same as direct NH~3~ at 450 USD/t (258.9 USD/MWh for both; version 1.0 found it 1.3 % cheaper). It needs the full end-point efficiency gain of Ahmad et al. (2025) (gain scale 1.000) to match direct use at 450 USD/t; the requirement is 1.40 at 300 USD/t (unreachable with the literature gain), 0.68 at 700 USD/t and 0.49 at 1000 USD/t. A fired cracker is dearer than direct use at every H~2~ fraction scanned. The advantage of partial cracking therefore depends wholly on exhaust-heat integration whose efficiency gain is taken from the literature and was not simulated here.
<!-- data: enduse_results.json partial_cracking.breakeven_efficiency_gain[*].gain_scale_where_partial_40vol_equals_direct (1.4028, 1.0003, 0.6764, 0.4871 at 300, 450, 700, 1000 USD/t); partial_cracking.scan[*].LCOE_fired; power_pathways partial_exhaust_40 vs direct -->

![**Figure 29.4.** Power cost against hydrogen fraction for partial cracking, with exhaust-heat gain scales 1, 0.5 and 0 and a fired cracker. *Source: independent Python calculation (results/research/enduse/partial_cracking_scan.csv).*](../../results/figures/research/enduse_partial_cracking_cost.png){width=85%}

### Hydrogen

Table: **Table 29.5.** Hydrogen pathways at the stated NH~3~ prices. Purity notes name what was and was not evaluated. *Source: results/research/enduse/enduse_results.json hydrogen_pathways[*].*

| Pathway | Efficiency, NH~3~ LHV to H~2~ | NH~3~ (kg/kg H~2~) | Cost, grey 450 (USD/kg) | Cost, green now 1000 (USD/kg) | CI green / blue (kg CO~2~e/kg) |
|---|---|---|---|---|---|
| Industrial 99.9 %, Aspen baseline (99.961 mol % H~2~) | 0.877 | 7.350 | 4.015 | 8.058 | 2.43 / 8.93 |
| Industrial 99.9 %, PSA at R 0.85, 30 bar | 0.877 | 7.350 | 4.046 | 8.089 | 2.52 / 9.02 |
| Aspen scenario with 99.98 mol % PSA split (NH~3~ polishing and H~2~O, O~2~ not modelled) | 0.868 | 7.426 | 4.094 | 8.179 | 2.46 / 9.03 |
| ISO 14687 Grade D within modelled scope, PSA and TSA at R 0.751, 350 bar | 0.844 | 7.643 | 4.463 | 8.667 | 3.17 / 9.93 |

<!-- data: results/research/enduse/enduse_results.json hydrogen_pathways ids h2_industrial, h2_industrial_purif_study, h2_fuelcell_candidate, h2_fuelcell_gradeD_purif_study: efficiency_NH3_LHV_to_H2, NH3_kg_per_kg_H2, cost_USD_per_kg_at_grey_450, cost_USD_per_kg_at_green_current_1000, CI_green_kgCO2e_per_kgH2, CI_blue_kgCO2e_per_kgH2 -->

The third row is a candidate, not a Grade D product: NH~3~ polishing to 0.1 µmol/mol and the removal of H~2~O and O~2~ are not modelled, and the Aspen baseline H~2~ stream itself carries 392 µmol/mol N~2~ against the 300 limit (Section 28). The fourth row passes the hydrogen index, NH~3~, N~2~ and H~2~O within the model, relies on the optimistic mass-balance recovery, and does not evaluate O~2~, Ar, He, CO, CO~2~, hydrocarbons, sulfur compounds, formaldehyde, formic acid, halogenated compounds or particulates. All four costs are therefore lower bounds for the purity they name. On the unified basis purification adds 0.079 USD/kg to the stored-scenario cost at 450 USD/t (4.015 to 4.094). Version 1.0 gave 3.919 to 3.967 USD/kg on the legacy basis.

![**Figure 29.5.** Hydrogen cost against carbon intensity by ammonia route. *Source: independent Python calculation (results/research/enduse/pathway_table_hydrogen.csv).*](../../results/figures/research/enduse_hydrogen_cost_ci.png){width=85%}

## 29.5 Validation status and failures

`results/research/validation/enduse.json` had 45 items in version 1.0 and now has 75: 69 pass, 0 fail, 6 informational (Phase 2 added the threshold checks of Section 33 and the reproduction of the unified LCOH, 4.015461 USD/kg). The values quoted below are from version 1.0 where the item was not changed. The passes include the stoichiometric match to the Ahmad et al. (2025) bypass table for cracked shares from 0.75 to 0.1, the N and H atom balances and blend round trip for 30 to 60 vol % H~2~, an energy balance for every power pathway, the Aspen LHV efficiency of 0.877 within 0.005, reproduction of the stored LCOH (3.9188 USD/kg), and reproduction of the Ahmad et al. (2025) Case 2a LCOE (0.2798 USD/kWh) within 1 %. The informational items: AmCraX full-cracking total capital investment is 241.0 MUSD on the unified basis against Ahmad's about 230 MUSD; at 320 USD/t AmCraX gives 0.2175 (direct) and 0.2253 (full cracking) USD/kWh against 0.217 and 0.22 in the paper, whose attribution of these values is inconsistent; the Halim claim (Table 29.4); the Halim plant values (60.1 MW, 15.1 and 10.1 USD/kg), which could not be checked; and the ISO purity check. Passing items test arithmetic and agreement with one paper's economics. They do not test the interpolated efficiencies or the cracking-heat assumptions.

## 29.6 Comparison with literature

The AmCraX direct-versus-cracked gap on the unified basis (direct cheaper by 5.5 to 16.6 % of the cracked cost for fired and purified crackers, dearer by 1.1 to 5.0 % for an exhaust-heated one) is of the same order as the gap of about 1.4 % implied by Ahmad et al. (2025) at 320 USD/t and well below the 40 % attributed to Halim et al. (2025). The two papers differ in plant definition: Ahmad et al. compare gas-turbine systems fed by liquid, vaporised and cracked NH~3~ at one site, and the stated direction (direct use preferable for power) is common to both and to the Halim et al. abstract, which gives high cracking capital and operating cost as the reason.

## 29.7 Limitations

* Efficiencies of intermediate blends are linear interpolations between two end points of one paper; fired and purified variants apply the direct-NH~3~ efficiency to an H~2~-rich fuel.
* Cracker heat is the stored 600 °C, 20 bar Aspen duty scaled linearly with cracked share; temperature scenarios were not propagated.
* The 30 to 60 vol % H~2~ range and the 30 vol % natural-gas limit are labels. No combustion, flame-stability or NO~x~ result exists for blends; NO~x~ is "not quantified" for every blend and cracked fuel.
* No NO~x~ abatement cost. Plant sizes are scaled from one 43.1 MW case with an assumed exponent.
* Hydrogen costs use the unified reference scenario (Section 32) and are lower bounds for the stated purity.
* Boil-off, storage and distribution are excluded; landed cost is not computed.

## 29.8 Implication for hypothesis H1

For power, the computed evidence favours direct use in all cases except an exhaust-heated, unpurified cracker, which is 1.1 to 5.0 % cheaper at 450 to 1000 USD/t on the unified basis (4 to 7 % in version 1.0) and whose advantage rests on a literature efficiency gain and on a hydrogen-capable combustor beyond 60 vol % H~2~. Direct use is cheaper than a fired or purified cracker by 5.5 to 16.6 % of the cracked cost. Section 33 gives the turbine-efficiency thresholds that decide these comparisons. The sign of that result is set by the assumption that the turbine reaches the direct-NH~3~ efficiency on hydrogen-rich fuel: a fired or purified cracker can then only add ammonia burn and capital, so only the size of the gap is a computed result. For hydrogen as the product, no direct-use alternative exists, and the cracker delivers 0.877 of the ammonia heating value as H~2~ at 4.015 USD/kg (450 USD/t, unified basis of Section 32); the purity-specific costs in Table 29.5 are lower bounds. The size of the power gap is much smaller than the 40 % attributed to the literature. The verdict on H1 is given in Section 40.
