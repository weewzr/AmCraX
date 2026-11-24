<!-- cites: cho2026nickel, takahashi2016kinetic, kum2026heatintegrated, lucentini2021nirukinetic, linnhoff1983pinch, sayas2020high -->

# 26 Catalyst comparison and heat integration

This section tests hypothesis H3: low-temperature, high-activity catalysts combined with effective heat integration reduce energy use and can outweigh higher catalyst cost. It combines the Aspen RPlug results of Section 25 with the pinch analysis of Section 18 and the Singapore cost basis of Section 27.

**Status in version 2.0.** This section reports the Phase 1 study as released on 23 November 2026: its costs are on the Phase 1 equipment basis (about 3.67 USD/kg, superseded for research outputs) with the published TEA catalyst prices of Cho et al. (2026) (Ru 542, Ni 33.4 USD/kg), and its numbers trace to the preserved copies in `results/research_releases/2026-11-23/catalyst_comparison/`. The working files under `results/research/catalyst_comparison/` have since been regenerated on the unified basis with derived catalyst prices, so their values differ. Section 35 supersedes this section on three points. (1) The 17 % fired-duty reduction of Ru/Al~2~O~3~ against Ni/MgO comes from runs at unequal conversion and is withdrawn; at equal conversion the saving is at most 25.1 kW with heat integration (4.9 % of fired duty, 1.1 % of total external heating; Python only) and 163 kW without. (2) The Ru price of 542 USD/kg lies below the ruthenium metal value; at derived prices, with heat integration and the Ni reference at its modelled 594 °C, three of the four low-temperature catalysts are dearer than Ni/MgO beyond the model resolution at equal conversion, which goes against the essay; against sourced Ni design temperatures every low-temperature design is cheaper. (3) The heat-integration saving is now net of a sized and costed exchanger (+0.067 to +0.095 USD/kg on the reference basis, resting on an unsourced heat-transfer coefficient).

## 26.1 Method

A catalyst comparison can become circular if the catalyst only enters through an assumed temperature: a "low-temperature catalyst" then saves energy by definition. To avoid this, the temperature and the catalyst mass of every catalyst are derived from its own rate law, and the energy and cost follow from a flowsheet that is solved at the resulting conversion.

1. **Common duty.** Every catalyst cracks 100 kmol/h of liquid NH~3~ (0.2 mol% H~2~O) at 20 bar to the same 95 % conversion, and the PSA recovers 0.85 of the hydrogen, so every design delivers the same 248.8 kg/h of H~2~. The 95 % target is used because 99 % at 20 bar is equilibrium-limited at 684.8 °C for every catalyst (Section 25.6).
2. **Two comparisons.** *Equal mass:* 100 kg of catalyst per 100 kmol/h, each catalyst at its operating temperature T~op~ (Table 25.6), solved in the integrated **Aspen Plus V15** flowsheet with and without the feed/effluent exchanger (ten ci_* runs). *Cost-optimal:* for each catalyst the **independent Python calculation** finds the catalyst mass $W(T)$ needed for 95 % conversion from the PFR, solves the Python flowsheet at that conversion and minimises the LCOH over 470-760 °C (5 K grid refined to 1 K). The Python flowsheet holds the cracker at the kinetic conversion and refuses any conversion above equilibrium.
3. **Heat import.** The external heat is the temperature-feasible import after the feed/effluent exchanger and tail-gas firing (configuration (c) of Section 18), with a minimum approach of 20 K; without the exchanger it is the problem-table import of feed and reaction heat against the flue gas (Linnhoff & Hindmarsh, 1983). This import is supplied by burning extra NH~3~ in a furnace of efficiency 0.85, with a further 2 % of the reactor and trim-heater duty as thermal loss; both are **engineering assumptions**. The fired duty is the furnace heat release.
4. **Cost and carbon.** The LCOH uses the Singapore evaluation of Section 27 with grey ammonia at 450 USD/t. The catalyst cost is mass × price / lifetime, with the prices of Cho et al. (2026), 542 USD/kg for Ru and 33.4 USD/kg for Ni, and a 2-year lifetime; these are proxy prices, and no sourced price exists for Ni-Ru/CeO~2~, so 542 USD/kg is applied to it as an upper bound and the break-even price is reported instead. The carbon intensity uses the life-cycle factors of Section 30 with 5000 km of shipping.
<!-- data: results/research/catalyst_comparison/catalyst_comparison.json basis (feed, operating_temperature, heat_import dT_min 20 K, furnace 0.85 + 2 %, economics grey 450 USD/t, lifetime 2 yr, lca 5000 km); results/research/catalyst_comparison/assumptions.json; docs/internal/research_reports/heat-integration-catalyst-comparison.md (248.8 kg/h) -->

## 26.2 Equal catalyst mass

Table 26.1 gives the integrated Aspen results at 100 kg. All ten flowsheets converged, and in none of them is the cracker conversion above the stored RGibbs flowsheet at the same temperature.

Table: **Table 26.1.** Integrated flowsheet with each catalyst at its T~op~, 20 bar, 100 kg catalyst. *Source: Aspen Plus V15 simulation, results/research/aspen_kinetic/catalyst_comparison.json rows (integrated_hi_*, integrated_nohi_*); fired duty: independent Python calculation on the Aspen duties, results/research/catalyst_comparison/catalyst_comparison.json findings.fixed_inventory_100kg_aspen.*

| Catalyst (T~op~) | X | H~2~ (kg/h) | External heating with / without exchanger (kW) | Recovered heat (kW) | LHV efficiency with / without | Fired duty with / without (kW) |
|---|---|---|---|---|---|---|
| Ru/Al~2~O~3~ (499 °C) | 0.950 | 243.6 | 2221 / 2691 | 469 | 0.8755 / 0.8333 | 497 / 975 |
| Ru/MgO, approx. (522 °C) | 0.953 | 244.6 | 2233 / 2734 | 501 | 0.8755 / 0.8307 | 535 / 1046 |
| 5Ni1Ru/CeO~2~ (572 °C) | 0.952 | 244.1 | 2243 / 2815 | 572 | 0.8741 / 0.8235 | 533 / 1116 |
| 2.5Ni0.5Ru/CeO~2~ (576 °C) | 0.951 | 243.8 | 2242 / 2820 | 578 | 0.8738 / 0.8227 | 524 / 1113 |
| Ni/MgO, approx. (594 °C) | 0.959 | 246.0 | 2259 / 2862 | 604 | 0.8746 / 0.8217 | 599 / 1214 |
| RGibbs baseline (600 °C) | 0.981 | 251.6 | 2293 / 2905 | 612 | 0.8772 / 0.8244 | - |

<!-- data: results/research/aspen_kinetic/catalyst_comparison.json rows[].integrated_hi_X_cracker, integrated_hi_h2_product_kg_h, integrated_hi_total_external_heating_kW, integrated_nohi_total_external_heating_kW, integrated_hi_recovered_heat_kW, integrated_hi_lhv_efficiency, integrated_nohi_lhv_efficiency; rgibbs_baseline_600C; catalyst_comparison/catalyst_comparison.json findings.fixed_inventory_100kg_aspen.fired_duty_HI_kW, fired_duty_noHI_kW -->

At equal mass the lowest-temperature catalyst, Ru/Al~2~O~3~ at 499 °C, needs 17.0 % less fired duty than Ni/MgO at 594 °C with the exchanger and 19.7 % less without it. The total external heating, which includes the vaporiser and the preheat, differs much less: 2221 against 2259 kW with the exchanger (1.7 %) and 2691 against 2862 kW without it (6.0 %). The LHV efficiency is 0.874-0.876 for every catalyst with the exchanger. The exchanger itself saves 469-604 kW for every catalyst, several times more than the choice of catalyst (Figure 26.1). A lower reactor temperature also leaves less heat in the reactor effluent, so the exchanger recovers less: 469 kW at 499 °C against 604 kW at 594 °C. Heat integration and a low-temperature catalyst therefore partly substitute for each other rather than adding up.
<!-- data: catalyst_comparison.json findings.fixed_inventory_100kg_aspen.Ru_Al2O3_vs_Ni_fired_duty_reduction_HI 0.1700, _noHI 0.1970; aspen_kinetic/catalyst_comparison.json rows (2221.43 vs 2258.8; 2690.56 vs 2862.3; nohi minus hi 469.1 (Kum) to 603.5 (Ni)) -->

![**Figure 26.1.** Fired duty of each catalyst at its operating temperature with 100 kg of catalyst, with and without the feed/effluent exchanger. The exchanger reduces the fired duty of every catalyst by more than the difference between the best and the worst catalyst. *Source: Aspen Plus V15 simulation (duties) and independent Python calculation (fired duty).*](../../results/figures/research/catalyst_heat_duty.png){width=85%}

The cost result at equal mass reverses with heat integration. With the exchanger, the 100 kg Ru charge costs more than the fuel it saves, and Ru/Al~2~O~3~ has a 0.006 USD/kg higher LCOH than Ni/MgO (3.676 against 3.670 USD/kg); without the exchanger the fuel saving dominates and Ru/Al~2~O~3~ is 0.050 USD/kg cheaper (3.878 against 3.928 USD/kg).
<!-- data: catalyst_comparison.json findings.fixed_inventory_100kg_aspen.lcoh_HI_USD_per_kg (3.67571, 3.66954), lcoh_noHI_USD_per_kg (3.87816, 3.92768), Ru_Al2O3_minus_Ni_lcoh_HI 0.00617, _noHI -0.04952 -->

## 26.3 Cost-optimal design of each catalyst

Equal mass favours the fast catalyst, because a slow catalyst could simply be given more mass. When each catalyst's temperature and mass are optimised for LCOH (Table 26.2, Figure 26.2), the cheap Ni/MgO catalyst compensates its low activity with ten times the mass at a lower temperature, and the five designs end within 0.011 USD/kg of each other.

Table: **Table 26.2.** Cost-optimal temperature and catalyst mass at 95 % conversion, 20 bar, with the feed/effluent exchanger. *Source: independent Python calculation, results/research/catalyst_comparison/catalyst_comparison.json findings.cost_optimal_python[*].HI.*

| Catalyst | T~opt~ (°C) | Band within 0.001 USD/kg (°C) | Mass (kg) | Bed volume (m^3^) | Fired duty (kW) | LCOH (USD/kg) | Grey carbon intensity (kg CO~2~e/kg H~2~) |
|---|---|---|---|---|---|---|---|
| Ni/MgO (approx.) | 547 | 530-570 | 378 | 0.60 | 498 | 3.6644 | 19.76 |
| Ru/Al~2~O~3~ | 535 | 515-565 | 36 | 0.058 | 495 | 3.6648 | 19.75 |
| Ru/MgO (approx.) | 562 | 540-595 | 40 | 0.063 | 502 | 3.6684 | 19.77 |
| 5Ni1Ru/CeO~2~ | 621 | 595-655 | 35 | 0.033 | 517 | 3.6738 | 19.80 |
| 2.5Ni0.5Ru/CeO~2~ | 625 | 600-665 | 41 | 0.039 | 518 | 3.6750 | 19.80 |

<!-- data: catalyst_comparison.json findings.cost_optimal_python.<cat>.HI: T_opt_C, T_range_within_0.001USD_kg_C, W_kg, bed_volume_m3, fired_duty_kW, lcoh_USD_per_kg, grey_kgCO2e_per_kgH2 -->

At the optima the fired duty differs by less than 5 % between catalysts (495-518 kW), the carbon intensity by at most 0.3 %, and the LCOH by 0.011 USD/kg, or 0.3 %. The LCOH optimum is flat: it stays within 0.001 USD/kg over a 40-65 K band for every catalyst. Ru/Al~2~O~3~ chooses a temperature above its T~op~, because with the exchanger a higher temperature costs little fuel and saves catalyst. Without the exchanger the optima move down and apart: Ru/Al~2~O~3~ at 498 °C with 101 kg (3.8745 USD/kg) against Ni/MgO at 511 °C with 1633 kg (3.8837 USD/kg), and the carbon intensity rises to 20.9-21.1 kg CO~2~e/kg H~2~ for grey ammonia.
<!-- data: cost_optimal_python.<cat>.HI fired_duty_kW 495.19-517.54; grey 19.749-19.805; noHI: Ru/Al2O3 T_opt_C 498, W_kg 101.37, lcoh 3.87448; Ni/MgO 511, 1632.85, 3.88374; grey noHI 20.92-21.11 -->

![**Figure 26.2.** Breakdown of the LCOH at each catalyst's cost-optimal design. The ammonia feed dominates every design; the catalyst and fuel terms that distinguish the catalysts are a small fraction of the total. *Source: independent Python calculation.*](../../results/figures/research/catalyst_cost_breakdown.png){width=85%}

## 26.4 Break-even catalyst price

The break-even price is the catalyst price at which a low-temperature catalyst gives the same LCOH as the nickel reference. It depends strongly on how the reference is designed (Table 26.3, Figure 26.3).

Table: **Table 26.3.** Break-even catalyst price against Ni/MgO, with the feed/effluent exchanger. *Source: independent Python calculation, results/research/catalyst_comparison/catalyst_breakeven_price.json; catalyst_comparison.json findings.breakeven_price.*

| Catalyst | Against Ni/MgO at its cost-optimal temperature (USD/kg) | Against Ni/MgO fixed at 700 °C (USD/kg) | Against Ni/MgO fixed at 735 °C (USD/kg) |
|---|---|---|---|
| Ru/Al~2~O~3~ | 498 | 4329 | 7390 |
| Ru/MgO (approx.) | 252 | 1933 | 2996 |
| 5Ni1Ru/CeO~2~ | 75 | 857 | 1571 |
| 2.5Ni0.5Ru/CeO~2~ | 77 | 657 | 1115 |

<!-- data: catalyst_comparison.json findings.breakeven_price[] (498.16, 251.57, 74.73, 77.25; 4329.30, 1932.56, 856.88, 657.23; 7390.41, 2996.29, 1571.37, 1114.76) -->

Against a nickel cracker forced to about 735 °C, the temperature of the nickel design of Cho et al. (2026), every low-temperature catalyst pays for itself at prices well above the 542 USD/kg assumed for ruthenium. Against a nickel design whose temperature and mass are optimised on the Takahashi Ni/MgO kinetics, none does: the break-even prices of 75-498 USD/kg are all below 542 USD/kg. The cost advantage of a low-temperature catalyst therefore comes from the comparison with a high-temperature nickel design, not from the catalyst alone.

![**Figure 26.3.** Break-even catalyst price of each low-temperature catalyst against three Ni/MgO reference designs, with the assumed Ru price of 542 USD/kg (Cho et al., 2026) marked. *Source: independent Python calculation.*](../../results/figures/research/catalyst_breakeven_price.png){width=85%}

## 26.5 Pinch analysis and the size of the remaining heat gap

The temperature-feasible heat import with the exchanger is 467-568 kW at the five operating points and does not change when the minimum approach temperature is varied from 10 to 50 K, because the exchanger and the firing, not the approach, set it. A pinch target that lets the flue gas exchange heat freely with every process stream is lower: 192-396 kW over the same range of approach temperatures (493-552 kW for the baseline at 600 °C). A better heat-exchanger network than a single feed/effluent exchanger plus firing therefore has a further 200-300 kW of scope, which is of the same order as the whole difference between catalysts.
<!-- data: results/research/catalyst_comparison/catalyst_pinch_dTmin.csv external_heat_import_kW (HI: 467.17 Kum to 568.21 Ni, constant over dT_min 10-50; baseline 752.63), pinch_min_hot_utility_with_flue_kW (192.35 Kum dT10 to 396.27 Ni dT50; baseline 493.0-551.8) -->

## 26.6 Robustness of the ranking

The cost-optimal comparison was repeated for 32 one-at-a-time variations of prices, lifetimes, pressures, furnace efficiency, heat integration, capital-cost scaling and rate constants (Figure 26.4). The best catalyst is the same as in the base case in 21 of 32 cases. A low-temperature catalyst beats nickel when the Ru price is halved, the Ni price doubled, the lifetime extended to 4 years, the ammonia price raised to 610 or 1000 USD/t, the pressure lowered to 10 bar, the furnace efficiency lowered to 0.65, the exchanger removed, the cracker capital cost scaled with bed volume, all rates multiplied by 5, or the Ni rate divided by 5. The largest difference between the best low-temperature catalyst and nickel in any of these cases is 0.017 USD/kg, under 0.5 % of the LCOH. The Monte Carlo range of the LCOH from economic uncertainty alone is 2.85-4.43 USD/kg (p5-p95, grey scenario; Section 27). The ranking does not change with the approach temperature, the electricity price, the conversion target between 0.90 and 0.99, or a PSA recovery of 0.756.
<!-- data: results/research/catalyst_comparison/catalyst_sensitivity_ranking.csv delta_vs_Ni_USD_per_kg (min -0.00935, max 0.03632); catalyst_comparison.json findings.ranking_robustness (n_cases 32, n_same_best_as_base 21, cases_where_a_low_T_catalyst_beats_Ni [11 cases], max_abs_best_low_T_minus_Ni_USD_per_kg 0.01679); results/research/catalyst_comparison/catalyst_ranking_robustness.json; results/research/singapore/monte_carlo.json grey p5 2.85, p95 4.43 -->

![**Figure 26.4.** LCOH of each low-temperature catalyst minus that of Ni/MgO, each at its own cost-optimal temperature, across the 32 sensitivity cases (negative: cheaper than Ni). All differences lie between -0.010 and +0.037 USD/kg, far inside the economic uncertainty of the LCOH. *Source: independent Python calculation.*](../../results/figures/research/catalyst_ranking_robustness.png){width=85%}

## 26.7 Comparison with Cho et al. (2026)

Cho et al. (2026) report that a Ru process at 566.69 °C and 10 bar needs no supplementary fuel, while a Ni process at 735.52 °C and 24.34 bar burns supplementary NH~3~, and that the Ru process has a 7.0 % lower reconversion cost (REC, the LCOH minus the ammonia feed cost; Cho et al., 2026, Eq. 23). Both designs were rebuilt on AmCraX boundaries at 97 % conversion with Cho's economic inputs, using Ni/MgO and Ru/Al~2~O~3~ as kinetic proxies for their catalysts (Table 26.4).

Table: **Table 26.4.** Cho et al. (2026) designs rebuilt in AmCraX. Negative values mean that Ru is more expensive. *Source: independent Python calculation, results/research/catalyst_comparison/catalyst_cho_comparison.json summary and designs; published literature, Cho et al. (2026, Table 7, pp. 13-15).*

| PSA recovery | Catalyst inventory | REC of Ru lower by (%) | LCOH of Ru lower by (%) | Supplementary NH~3~, Ni / Ru (kg/h) |
|---|---|---|---|---|
| 0.85 | kinetic minimum (Ni 10 kg, Ru 17 kg) | 2.6 | 0.4 | 161.1 / 152.0 |
| 0.85 | GHSV 9000 h^-1^ (249 kg each) | -2.5 | -0.4 | 161.1 / 152.0 |
| 0.756 | kinetic minimum | -0.4 | -0.04 | 7.1 / 6.9 |
| 0.756 | GHSV 9000 h^-1^ | -10.2 | -0.9 | 7.1 / 6.9 |
| Cho et al. (2026) | | 7.0 | 2.7 | Ni burns 1.736 kmol/h NH~3~; Ru none |

<!-- data: catalyst_cho_comparison.json summary[] (rec_Ru_lower_by_pct 2.562, -2.526, -0.43, -10.156; lcoh_Ru_lower_by_pct 0.407, -0.402, -0.04, -0.914; Ni_supp_nh3_kg_h 161.08 / 7.11, Ru 151.98 / 6.94; cho_values rec 1.995/1.856, 7.0 %, 2.7 %, Ni_fuel_kmol_h 1.736); designs[] W_kinetic_min_kg (10.27, 16.58), W_kg 248.55 -->

The direction of Cho's REC result is reproduced only with the kinetic-minimum inventory at a PSA recovery of 0.85, and then at about a third of Cho's size. The fuel result is not reproduced: at a PSA recovery of 0.85 both designs need supplementary NH~3~, and at Cho's 0.756 the tail gas covers the whole process heat for both, leaving only the 7 kg/h thermal-loss allowance. On AmCraX boundaries the PSA recovery, not the catalyst, decides whether supplementary fuel is needed. When the Ni catalyst is moved to the Ru conditions (566.69 °C, 10 bar) it needs 230 kg and gives the lowest LCOH of all four designs, 3.6391 USD/kg, whereas Cho report a 116 % higher LCOH for that swap. The differences have identifiable causes: Cho's Ru advantage lies mainly in capital cost (boiler, heat exchangers, NO~x~ reduction), and their plant includes compression to 180 bar, hydrogen recycle, temperature-swing adsorption and an expander that AmCraX does not have; the AmCraX capital cost does not respond to temperature or pressure; and the kinetic laws are proxies, because Cho's Ni/Al~2~O~3~ law and the Ru-K/CaO law of Sayas et al. (2020) are in supplementary material that could not be obtained.
<!-- data: catalyst_cho_comparison.json designs Ni_swap_566.69C_10bar kinetic_minimum (W_kg 230.4, lcoh 3.6391), boundary_differences; research/notes/cho2026nickel.md (+116 % swap) -->

## 26.8 Validation

The catalyst-comparison validation file holds 75 items: 66 pass, 5 fail and 4 are informational. The passes include the pinch import of the baseline (752.63 kW against the stored 752.6 kW), mass and energy closure of every Python and Aspen configuration, the Python against Aspen external heating and tail-gas heat within 3 % for every catalyst (Python is 1.3 % below Aspen with the exchanger), the analytic catalyst-cost addition against the full evaluation (to 10^-9^), and the interior position of every T~opt~. The five failures are the recovered heat of the feed/effluent exchanger, where the Python flowsheet is 20.8 to 20.9 kW (3.45 to 4.44 %) above Aspen for every catalyst against a 3 % tolerance. The offset is the same for all catalysts and comes from the different property basis of the two models in the exchanger (Section 16.4); it was not tuned. Because it is common to all catalysts, it does not affect the ranking.
<!-- data: results/research/validation/catalyst_comparison.json (75 items: pass 66, fail 5, informational 4; HCAT-PINCH-BASELINE; HCAT-ASPY-*-HI-heat observed 489.95/469.14 ... 624.34/603.50, tolerance 0.03 relative) -->

## 26.9 What the results mean for H3

* **Energy.** At an equal 100 kg catalyst inventory, 20 bar and a nominal 95 % conversion, Ru/Al~2~O~3~ at 499 °C needs 17 % less fired duty than Ni/MgO at 594 °C with the exchanger and 20 % less without it (Aspen duties). Phase 2 showed that these runs reach unequal conversion (Ni 0.9589, Ru 0.9496) and that at equal conversion the saving is at most 25.1 kW, 4.9 % of fired duty, with the exchanger (Section 35.3); the 17 % figure is withdrawn. Total external heating differs much less (1.7 % with the exchanger). Once each catalyst's temperature and mass are optimised, the fired-duty difference falls below 5 %.
* **Heat integration.** The exchanger saves 469-604 kW for every catalyst, more than any catalyst choice, and it shrinks the benefit of a low reactor temperature instead of adding to it.
* **Cost.** At the cost-optimal designs the LCOH differs by at most 0.011 USD/kg between catalysts in the base case and by at most 0.017 USD/kg between the best low-temperature catalyst and nickel across the 32 sensitivity cases, below the resolution of the cost model and far below its uncertainty; the ranking changes under many plausible variations. The largest difference found, 0.050 USD/kg in favour of Ru/Al~2~O~3~, occurs only at equal catalyst mass and without the exchanger.
* **Catalyst price.** A ruthenium catalyst outweighs its price against nickel forced to about 735 °C (break-even 1115-7390 USD/kg), and the break-even against a nickel design optimised on its own kinetics (75-498 USD/kg, against the 542 USD/kg proxy price) lies inside the same model resolution, so the model cannot say whether ruthenium pays against an optimised nickel design. The 542 USD/kg proxy lies below the ruthenium metal value; at derived prices (Section 35) the low-temperature catalysts do not pay at equal conversion.
* **Conditions.** These results hold at 20 bar and 95 % conversion; at 99 % every catalyst is equilibrium-limited to about 685 °C. All laws are extrapolated to 20 bar from their fit pressure (1 atm; Kum et al.: 10 bar), on different pressure bases (Takahashi on mole fractions, Lucentini on concentrations), the Ni/MgO law fails its own validation against published curves (Section 14.4), and the activation-energy uncertainty of the Lucentini laws alone changes their rates several-fold.

The verdict for H3 is {{VERDICT:H3}} and is set in the evidence matrix (Section 40) together with the other sub-claims.

## 26.10 Limitations

The capital-cost model does not respond to reactor volume, exchanger area or temperature, so scaling the cracker cost with bed volume appears only as a sensitivity case; the exchanger area uses an assumed U of 50 W/(m^2^ K). Furnace efficiency, thermal loss and all catalyst prices are assumptions, and the price multipliers of 4 and 8 used in the stress cases are not sourced prices. The effectiveness factor is 1 and the bed has no pressure drop. N~2~O from the furnace is not quantified. The cost-optimal designs of Table 26.2 were not re-run in Aspen; they are Python results.
