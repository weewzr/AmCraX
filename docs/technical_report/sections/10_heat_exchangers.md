<!-- cites: xu2025review, cho2026nickel, mehr2026highcapacity, cechetto2023membrane, goodwin2018cantera, smith_grimech30 -->

# 10 Heat exchanger modelling

## 10.1 Thermal blocks of the flowsheet

Five blocks change stream temperatures and the burner releases the tail-gas heat (Table 10.1). Four are Heater blocks specified by outlet temperature (or superheat) and pressure, each reporting the duty a utility or furnace must supply or remove; FEHE is a two-stream HeatX exchanger with no external duty.

Table: **Table 10.1.** Thermal blocks: function, Aspen model, specification and baseline result (600 °C, 20 bar, with FEHE). Duty positive = heat added to the process. *Source: Aspen Plus V15 simulation, results/simulations/baseline.json; specifications from aspen/models/baseline.inp.*

| Block | Function | Aspen model | Specification | Outlet T (°C) | Duty (kW) |
|---|---|---|---|---|---|
| VAPORIZR | vaporise and superheat the pumped liquid NH~3~ | Heater | 20.8 bar, 10 K above the dew point | 75.90 | +739.46 |
| FEHE | preheat NH~3~ vapour with the reactor effluent | HeatX, shortcut, counter-current, design mode | cold outlet = reactor T - 50 K; 0.3 bar drop per side | 550.00 (cold) / 228.38 (hot) | 612.21 (internal) |
| HEATER | trim the feed to reactor temperature | Heater | 600 °C, 20.2 bar | 600.00 | +73.66 |
| COOLER | cool the cracked gas to the PSA feed temperature | Heater | 40 °C, 19.5 bar | 40.00 | -304.95 |
| BURNER | burn the PSA tail gas | RStoic, adiabatic | complete combustion, 15 % excess O~2~, 1.2 bar | 1368.90 | 0 |
| FLUEHX | recover heat from the flue gas | Heater | 150 °C stack, 1.1 bar | 150.00 | -1520.25 |

<!-- data: results/simulations/baseline.json blocks.*.duty_kW, blocks.*.outlet_temperature_C, blocks.FEHE.details; aspen/models/baseline.inp BLOCK VAPORIZR (DEGSUP=10), FEHE (T-COLD, PRES-HOT/PRES-COLD -0.3), HEATER, COOLER, BURNER, FLUEHX -->

**VAPORIZR** takes the largest duty after the reactor, 739.46 kW, at a low temperature level. Its outlet, 75.90 °C, is the dew point of the feed at 20.8 bar plus the assumed 10 K. The dew point depends on the NH~3~-H~2~O vapour-liquid model (65.9 °C with Aspen PENG-ROB, 60.1 °C with an ideal liquid, 50.9 °C for pure NH~3~), so outlet temperature and duty follow from the "dew point + 10 K" rule and the mixture model. At identical states the reference equation of state for ammonia gives 721.8 kW, 2.4 % below Aspen (Section 16).

<!-- data: results/simulations/baseline.json blocks.VAPORIZR; results/validation/feed_section_analysis.json dew_point (65.90, 60.09, 50.88 degC), vaporiser_at_aspen_states (721.82 vs 739.46 kW, +2.44 %) -->

**HEATER** closes the last 50 K to 600 °C with 73.66 kW and controls the reactor inlet independently of exchanger fouling. **COOLER** removes 304.95 kW between 228.38 and 40 °C; the gas stays above its dew point.

## 10.2 Feed/effluent exchanger

FEHE uses the HeatX shortcut method in design mode, counter-current, with the cold-outlet temperature as specification (Figure 10.1). The hot side is the reactor effluent S5 (600 °C), the cold side the NH~3~ vapour S2 (75.90 °C). Calculator TLINK keeps the cold outlet 50 K below the reactor temperature, which fixes a 50 K hot-end approach at every reactor temperature; the 1 K "minimum temperature approach" in the form is only Aspen's feasibility limit. Because the effluent heats its own feed, Aspen tears stream S4 and converges it with the Wegstein block `$OLVER01` (tear error 0); there is no material recycle (Section 6.5).

<!-- data: aspen/models/baseline.inp BLOCK FEHE (CALC-TYPE=DESIGN, CALC-METHOD=SHORTCUT, T-COLD), CALCULATOR TLINK; aspen/models/baseline.bkp convergence summary (tear S4, $OLVER01, Wegstein) as reported in Section 6 -->

![**Figure 10.1.** FEHE (HeatX) specifications: shortcut model, counter-current flow, design mode, cold-stream outlet temperature 550 °C. The cold-outlet specification fixes the 50 K hot-end approach and therefore the duty left to the trim heater. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/07_heat_exchanger_setup.png){width=95%}

The **Aspen Plus V15 simulation** gives a duty of 612.21 kW, a hot outlet of 228.38 °C, a log-mean temperature difference of 91.91 K with correction factor 1.0, and UA = 1590.96 cal/(s K) (Figure 10.2). The terminal differences are 600 - 550 = 50.00 K at the hot end and 228.38 - 75.90 = 152.48 K at the cold end:

$$ \Delta T_{\mathrm{lm}} = \frac{\Delta T_{\mathrm{c}} - \Delta T_{\mathrm{h}}}{\ln(\Delta T_{\mathrm{c}} / \Delta T_{\mathrm{h}})} = \frac{152.48 - 50.00}{\ln(152.48/50.00)} = 91.91\ \mathrm{K} \qquad (10.1) $$

$$ UA = \frac{Q}{F\,\Delta T_{\mathrm{lm}}} = \frac{612.21\ \mathrm{kW}}{1.0 \times 91.91\ \mathrm{K}} = 6.661\ \mathrm{kW/K}, \qquad 1590.96\ \tfrac{\mathrm{cal}}{\mathrm{s\,K}} \times 4.1868\ \tfrac{\mathrm{J}}{\mathrm{cal}} = 6.661\ \mathrm{kW/K} \qquad (10.2) $$

where $\Delta T_\mathrm{h}$ and $\Delta T_\mathrm{c}$ are the hot-end and cold-end temperature differences (K), $Q$ the duty (kW), $F$ the LMTD correction factor (-) and $UA$ the product of overall heat-transfer coefficient and area (kW/K). Aspen's calorie is the International Table calorie: with 4.1868 J the reported UA equals $Q/\Delta T_\mathrm{lm}$ to 5.5 × 10^-10^, with 4.184 J it would deviate by -6.7 × 10^-4^ (PHYS-FEHE-UA). This checks output consistency and unit conversion, not heat transfer.

<!-- data: results/simulations/baseline.json blocks.FEHE.details (lmtd_K 91.909486, UA 1590.96358 cal/sec-K, lmtd_correction_factor 1.0, temperatures), duty_kW 612.213344; results/validation/independent_physics_checks.csv baseline fehe_UA_aspen_kW_K 6.661046317, fehe_UA_Q_over_LMTD_kW_K 6.661046313, rel_dev 5.5e-10; results/validation/validation_matrix.json PHYS-FEHE-UA -->

**Where the pinch lies.** The average heat-capacity rates are 612.21 / (550 - 75.90) = 1.291 kW/K for the feed and 612.21 / (600 - 228.38) = 1.647 kW/K for the effluent, whose molar flow cracking has nearly doubled (100 to 197.885 kmol/h). The cold stream has the smaller rate, so its temperature changes more per kW; in counter-current flow the temperature difference narrows towards the hot end, where the minimum approach is the specified 50 K. Both terminal differences are positive and, with these average rates, the difference varies monotonically between them, so there is no temperature cross. The shortcut block reports terminal values only; the internal profile, with heat capacities varying along the exchanger, was not extracted.

<!-- data: results/simulations/baseline.json blocks.FEHE.details, streams.S4/S5.mole_flow_kmol_h; 612.213/(550-75.900) = 1.2913 kW/K, 612.213/(600-228.380) = 1.6474 kW/K -->

The effluent releases 917.17 kW between 600 and 40 °C; the exchanger takes 612.21 kW of it and the cooler the remaining 304.95 kW. On the feed side, FEHE and HEATER together supply 685.87 kW between S2 and S4, exactly the HEATER duty of the flowsheet without the exchanger.

<!-- data: results/simulations/baseline.json blocks.FEHE.duty_kW + |blocks.COOLER.duty_kW| = 917.167; blocks.FEHE.duty_kW + blocks.HEATER.duty_kW = 685.871; results/simulations/baseline_no_hi.json blocks.HEATER.duty_kW 685.870669, blocks.COOLER.duty_kW -917.167363 -->

![**Figure 10.2.** FEHE thermal results: hot stream S5 to S6 (600 to 228.38 °C, 20 to 19.7 bar), cold stream S2 to S3 (75.90 to 550 °C, 20.8 to 20.5 bar), heat duty 612.213 kW. These terminal temperatures are the input of Eqs. (10.1) and (10.2) and the basis of the heat-integration benefit. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/12_heat_exchanger_results.png){width=95%}

## 10.3 Effect of the exchanger

The variant without FEHE (S2 to HEATER, S5 to COOLER) has the same reactor and separation results; only the duties change (Table 10.2).

Table: **Table 10.2.** Baseline with and without the feed/effluent exchanger (600 °C, 20 bar). *Source: Aspen Plus V15 simulation, results/simulations/baseline.json and baseline_no_hi.json (KPI definitions in backend/amcrax/kpis.py).*

| KPI | With FEHE | Without FEHE | Change |
|---|---|---|---|
| Recovered heat, FEHE (kW) | 612.21 | 0 | +612.21 |
| HEATER duty (kW) | 73.66 | 685.87 | -612.21 |
| External heating, VAPORIZR + HEATER + CRACKER (kW) | 2293.12 | 2905.33 | -612.21 |
| COOLER duty (kW) | 304.95 | 917.17 | -612.21 |
| Specific heat demand (kWh/kg H~2~) | 9.11 | 11.55 | -2.43 |
| Net fuel-heat deficit after flue-gas credit (kW) | 772.87 | 1385.08 | -612.21 |
| LHV efficiency (first-law, upper bound) | 0.877 | 0.824 | +0.053 |

<!-- data: results/simulations/baseline.json kpis; results/simulations/baseline_no_hi.json kpis (recovered_heat_kW, preheat_duty_kW, total_external_heating_kW, cooling_duty_kW, specific_heat_demand_kWh_per_kgH2 9.1146/11.5480, net_fuel_heat_deficit_kW, lhv_efficiency 0.8772/0.8244) -->

The exchanger removes the same 612.21 kW from the heating and the cooling demand. The direction agrees with **published literature**: feed/effluent integration with a pre-cracker raised the efficiency of a repurposed reformer from 65.7 % to 75.3 % (Xu et al., 2025), for a different plant and efficiency definition.

## 10.4 Burner and flue-gas recovery

The PSA tail gas (73.03 kmol/h; 30.16 mol% H~2~, 2.62 mol% NH~3~, the rest mainly N~2~) burns in BURNER, an RStoic block at 1.2 bar with zero duty and two reactions at complete conversion of the fuel: H~2~ + 0.5 O~2~ → H~2~O and NH~3~ + 0.75 O~2~ → 0.5 N~2~ + 1.5 H~2~O (Figure 10.3). NO~x~ formation is not modelled. The calculator block AIRCALC sets the air flow from the tail-gas fuel content by Eq. (6.1); its definition and the Aspen screenshot of its Define tab are in Section 6.4 (Figure 6.2). The baseline needs 68.17 kmol/h of air, 15 % above the stoichiometric 59.28 kmol/h.

<!-- data: aspen/models/baseline.inp BLOCK BURNER, CALCULATOR AIRCALC; results/simulations/baseline.json streams.TAILGAS (73.0327 kmol/h, y_H2 0.30156, y_NH3 0.02622), streams.AIR.mole_flow_kmol_h 68.1698 -->

![**Figure 10.3.** BURNER (RStoic) reactions: fractional conversion 1 of H~2~ and of NH~3~ with the stoichiometry shown. Complete conversion fixes the flue-gas composition and the heat released; it excludes dissociation and NO formation. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/09_burner_setup.png){width=95%}

The burner outlet, 1368.90 °C, is the **complete-combustion** adiabatic flame temperature. An independent Cantera calculation with GRI-Mech 3.0 data and the same complete-combustion products gives 1368.80 °C; an equilibrium calculation with dissociation (OH, H, O, NO) gives 1366.55 °C, 2.25 K lower (Goodwin et al., 2018; Smith et al., n.d.). The flue gas (130.67 kmol/h) contains 79.36 mol% N~2~, 19.21 mol% H~2~O, 1.43 mol% O~2~ and no CO~2~.

<!-- data: results/simulations/baseline.json streams.FLUE (1368.90092 degC, 130.669 kmol/h, mole_frac); results/validation/independent_physics_checks.csv baseline flame_T_cantera_complete_C 1368.802704, flame_T_cantera_HP_equilibrium_C 1366.551215, dT -2.2515 K; validation_matrix.json PHYS-FLAME, PHYS-FLAME-DISSOC -->

Cooling the flue gas to the 150 °C stack in FLUEHX releases 1520.25 kW, 92.2 % of the tail-gas LHV of 1647.98 kW (Cantera recalculation within 6 × 10^-6^). This equals 66.3 % of the external heating with the exchanger and 52.3 % without it. The remaining 772.87 kW needs extra fuel, such as burned NH~3~ (Cho et al., 2026; Mehr et al., 2026), or electricity; Cechetto et al. (2023) also find the off-gas alone insufficient. This first-law figure is an upper bound: it counts external heat 1:1 against the LHV and credits flue heat below reactor temperature. With temperature levels respected, the pinch analysis gives a heat import of 752.6 kW against 772.9 kW (Section 18).

<!-- data: results/simulations/baseline.json kpis.tailgas_combustion_heat_kW 1520.249, tailgas_lhv_kW 1647.975 (ratio 0.9225), total_external_heating_kW 2293.117 (ratio 0.6630), net_fuel_heat_deficit_kW 772.867; baseline_no_hi.json kpis.total_external_heating_kW 2905.330 (ratio 0.5233); results/validation/independent_physics_checks.csv baseline fluehx_rel_dev 6.36e-6; fact sheet F7 (results/simulations/heat_integration_baseline.json, 752.6 kW) -->
