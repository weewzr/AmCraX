<!-- cites: xu2025review, cho2026nickel, mehr2026highcapacity, cechetto2023membrane, linnhoff1983pinch -->

# 11 Heat exchangers and process integration

## 11.1 Thermal blocks of the flowsheet

Five blocks change the temperature of process streams (Table 11.1). Four are single-stream Heater blocks specified by outlet temperature (or superheat) and pressure; they report the duty a utility or furnace must provide. FEHE is a two-stream HeatX exchanger that moves heat inside the process and has no external duty.

Table: **Table 11.1.** Thermal blocks: function, model, specification and baseline result (600 °C, 20 bar, heat-integrated). Duties positive = heat added to the process. *Source: Aspen Plus V15 simulation, results/simulations/baseline.json; specifications from aspen/models/baseline.inp.*

| Block | Function | Aspen model | Specification | Outlet T (°C) | Duty (kW) |
|---|---|---|---|---|---|
| VAPORIZR | vaporise and superheat the pumped liquid NH~3~ | Heater | 20.8 bar, 10 K superheat | 75.90 | +739.46 |
| FEHE (cold side) | preheat NH~3~ vapour with reactor effluent | HeatX, shortcut, counter-current | cold outlet = reactor T − 50 K = 550 °C | 550.00 | 612.21 (internal) |
| HEATER | trim the feed to reactor temperature | Heater | 600 °C, 20.2 bar | 600.00 | +73.66 |
| COOLER | cool cracked gas to PSA feed temperature | Heater | 40 °C, 19.5 bar | 40.00 | −304.95 |
| FLUEHX | recover heat from burner flue gas | Heater | 150 °C stack, 1.1 bar | 150.00 | −1520.25 |

<!-- data: results/simulations/baseline.json blocks.*.duty_kW, blocks.*.outlet_temperature_C, blocks.FEHE.details -->

The vaporiser duty (739.46 kW) is half the reactor duty and arises at a low temperature level (the outlet, 75.90 °C, is 10 K above the dew point of the feed at 20.8 bar), so it can be met by low-grade heat. The HEATER and the reactor need heat at or above 600 °C.

## 11.2 Feed/effluent exchanger

FEHE uses the HeatX shortcut method in design mode, counter-current, with 0.3 bar pressure drop on each side. The hot stream is the reactor effluent S5 (600 °C), the cold stream the NH~3~ vapour S2 (75.90 °C). The specification is the cold-outlet temperature, set by calculator TLINK to the reactor temperature minus 50 K. With the hot inlet at the reactor temperature this fixes a 50 K hot-end approach at every reactor temperature, keeps the exchanger feasible over the whole sensitivity range and leaves a final 50 K step to the HEATER, which can control the reactor inlet independently of fouling or load (Figure 11.1). Because the effluent heats its own feed, the flowsheet is not purely feed-forward: Aspen tears stream S4 and converges it with an automatically generated Wegstein block (`$OLVER01`; converged, tear error 0). There is no material recycle (Section 7.2).

<!-- data: aspen/models/baseline.bkp CONV-SUM TEAR-SUMMARY (tear S4, $OLVER01, WEGSTEIN, OPT_STAT OK, errors 0) as cited in Section 7.2 -->


![**Figure 11.1.** FEHE HeatX setup: shortcut model with the cold-stream outlet temperature specification. The cold-outlet specification fixes the 50 K hot-end approach and thereby the trim-heater duty. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/07_heat_exchanger_setup.png){width=95%}

The **Aspen Plus V15 simulation** gives a duty of 612.21 kW, a hot outlet of 228.38 °C, an LMTD of 91.91 K (correction factor 1.0) and UA = 1590.96 cal/(s K), i.e. 6.657 kW/K (Figure 11.2). The terminal temperature differences are 600 − 550 = 50 K at the hot end and 228.38 − 75.90 = 152.48 K at the cold end; the log-mean of these two values reproduces the reported LMTD, and UA × LMTD = 611.8 kW agrees with the duty to 0.1 %. There is no temperature cross.

<!-- data: results/simulations/baseline.json blocks.FEHE.details (lmtd_K, UA, UA_unit, hot/cold temperatures), blocks.FEHE.duty_kW -->

$$ \Delta T_{\mathrm{lm}} = \frac{\Delta T_{\mathrm{c}} - \Delta T_{\mathrm{h}}}{\ln(\Delta T_{\mathrm{c}} / \Delta T_{\mathrm{h}})} = \frac{152.48 - 50}{\ln(152.48/50)} = 91.91\ \mathrm{K} \qquad (11.1) $$

where $\Delta T_\mathrm{h}$ and $\Delta T_\mathrm{c}$ (K) are the hot-end and cold-end temperature differences.

The average heat-capacity rates are 612.21 / (550 − 75.90) = 1.291 kW/K for the feed and 612.21 / (600 − 228.38) = 1.647 kW/K for the effluent, whose molar flow cracking has doubled (100 to 197.88 kmol/h). The feed therefore limits: the temperature difference narrows towards the hot end, where the minimum approach is the specified 50 K (the shortcut model reports terminal values only). The effluent leaves at 228.38 °C and the remaining 304.95 kW of the 917.17 kW released between 600 and 40 °C goes to the COOLER.

![**Figure 11.2.** FEHE thermal results: inlet and outlet conditions and exchanger duty. Confirms the 612 kW of internally recovered heat on which the heat-integration benefit rests. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/12_heat_exchanger_results.png){width=95%}

## 11.3 Effect of heat integration

The variant without FEHE (S2 to HEATER, S5 to COOLER) has the same reactor and separation results; only the heat duties change (Table 11.2).

Table: **Table 11.2.** Heat-integrated baseline versus the flowsheet without FEHE (600 °C, 20 bar). *Source: Aspen Plus V15 simulation, results/simulations/baseline.json and baseline_no_hi.json (KPI definitions in backend/amcrax/kpis.py).*

| KPI | With FEHE | Without FEHE | Change |
|---|---|---|---|
| Recovered heat, FEHE (kW) | 612.21 | 0 | +612.21 |
| HEATER (trim) duty (kW) | 73.66 | 685.87 | −612.21 |
| Total external heating, VAPORIZR + HEATER + CRACKER (kW) | 2293.12 | 2905.33 | −612.21 |
| COOLER duty (kW) | 304.95 | 917.17 | −612.21 |
| Specific heat demand (kWh/kg H~2~) | 9.11 | 11.55 | −2.43 |
| Net fuel-heat deficit after tail-gas credit (kW) | 772.87 | 1385.08 | −612.21 |
| LHV efficiency | 0.8772 | 0.8244 | +0.0528 |

<!-- data: results/simulations/baseline.json kpis; results/simulations/baseline_no_hi.json kpis -->

The exchanger removes the same 612.21 kW from both the heating and the cooling demand. The direction agrees with **published literature**: Xu et al. (2025) report that feed/effluent integration combined with a pre-cracker raised the overall efficiency of a repurposed reformer from 65.7 % to 75.3 %; those values belong to a different plant and efficiency definition and are not comparable numerically with Table 11.2.

## 11.4 Tail-gas burner and flue-gas recovery

The PSA tail gas (73.03 kmol/h, 30.16 mol% H~2~, 2.62 mol% NH~3~) is burned in BURNER, an RStoic block at 1.2 bar with zero duty and two reactions, H~2~ + 0.5 O~2~ → H~2~O and NH~3~ + 0.75 O~2~ → 0.5 N~2~ + 1.5 H~2~O, each at complete conversion of the fuel (Figure 11.3). NO~x~ formation is not modelled. Calculator AIRCALC sets the air flow to $F_\mathrm{air} = 1.15\,(0.5\,F_\mathrm{H_2} + 0.75\,F_\mathrm{NH_3})/0.21$ (kmol/h), i.e. 15 % excess O~2~ (Figure 11.4); with the baseline tail gas this gives 68.17 kmol/h of air.

<!-- data: aspen/models/baseline.inp BLOCK BURNER, CALCULATOR AIRCALC; results/simulations/baseline.json streams.TAILGAS, streams.AIR -->

![**Figure 11.3.** BURNER (RStoic) reactions: complete combustion of H~2~ and NH~3~ in the tail gas. The stoichiometry fixes the flue-gas composition and the heat released. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/09_burner_setup.png){width=95%}

![**Figure 11.4.** Calculator AIRCALC: air flow computed from the tail-gas H~2~ and NH~3~ flows. Keeps 15 % excess air automatically whenever the PSA recovery or the conversion changes the tail gas. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/16_calculator.png){width=95%}

The adiabatic burner outlet, 1368.90 °C, is the adiabatic flame temperature. The flue gas (130.67 kmol/h) contains 79.36 mol% N~2~, 19.21 mol% H~2~O, 1.43 mol% O~2~ and no CO~2~. Cooling it to the 150 °C stack in FLUEHX releases 1520.25 kW, 92 % of the tail-gas LHV (1647.98 kW), which covers 66 % of the external heating with FEHE (2293.12 kW) and 52 % without it (2905.33 kW). The net deficit of 772.87 kW (Table 11.2) needs additional fuel, e.g. burned NH~3~ (Cho et al., 2026; Mehr et al., 2026), or electricity; Cechetto et al. (2023) also state that the off-gas alone is insufficient. This is a first-law balance only; whether the heat is available at 600 °C or above is assessed by the pinch analysis in Section 16.2 (Linnhoff & Hindmarsh, 1983).

<!-- data: results/simulations/baseline.json blocks.BURNER.outlet_temperature_C, streams.FLUE, kpis.tailgas_combustion_heat_kW, kpis.tailgas_lhv_kW, kpis.total_external_heating_kW, kpis.net_fuel_heat_deficit_kW; baseline_no_hi.json kpis.total_external_heating_kW -->
