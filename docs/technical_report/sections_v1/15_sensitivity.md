<!-- cites: -->

# 15 Sensitivity analysis

## 15.1 Method

Every point in this section is a full-flowsheet **Aspen Plus V15 simulation** driven through COM (Section 13). Reactor temperature, feed rate, feed water, PSA recovery and FEHE approach were written in place into a loaded model; reactor pressure and the heat-integration switch change the model structure, so each pressure level and the no-FEHE variant were regenerated from `CaseInputs` (Section 13.3). One parameter is varied at a time around the baseline (600 °C, 20 bar, recovery 0.85, 50 K approach), plus a 7 × 5 temperature-pressure map. All 91 runs converged without warnings; the largest relative closures are 3.39 × 10^−9^ (mass) and 4.47 × 10^−9^ (energy). Table 15.1 summarises the response of the three headline KPIs.

<!-- data: results/sensitivity/aspen_{temperature(17),pressure(8),tp_map(35),feed_rate(5),feed_water(5),psa_recovery(6),fehe_approach(6),no_hi_temperature(9)}.csv: converged, has_warnings, mass_closure_rel, energy_closure_rel -->

Table: **Table 15.1.** One-at-a-time sensitivity: KPI values at the two ends of each range (first value at the lower parameter value). Efficiency as defined in Eq. (16.1). *Source: Aspen Plus V15 simulation, results/sensitivity/aspen_*.csv.*

| Parameter (range) | Runs | NH~3~ conversion | Specific heat demand (kWh/kg H~2~) | LHV efficiency |
|---|---|---|---|---|
| Reactor T (400–800 °C) | 17 | 0.8604 → 0.9952 | 9.345 → 9.209 (min 9.102 at 550 °C) | 0.8372 → 0.8758 (max 0.8772 at 600 °C) |
| Reactor P (5–40 bar) | 8 | 0.9951 → 0.9626 | 9.007 → 9.177 | 0.8806 → 0.8746 |
| Feed rate (25–200 kmol/h) | 5 | 0.9808 (constant) | 9.115 (constant) | 0.8772 (constant) |
| Feed H~2~O (0–2 mol%) | 5 | 0.9808 → 0.9810 | 9.031 → 9.389 | 0.8792 → 0.8707 |
| PSA H~2~ recovery (0.70–0.95) | 6 | 0.9808 (constant) | 11.068 → 8.155 | 0.7860 → 0.8928 |
| FEHE hot-end approach (20–150 K) | 6 | 0.9808 (constant) | 8.940 → 9.678 | 0.8813 → 0.8644 |
| Reactor T, no FEHE (400–800 °C) | 9 | 0.8604 → 0.9952 | 10.868 → 12.802 | 0.8320 → 0.8002 |

<!-- data: results/sensitivity/aspen_*.csv columns nh3_conversion, specific_heat_demand_kWh_per_kgH2, lhv_efficiency (pandas min/max/endpoints) -->

## 15.2 Reactor temperature

Conversion rises from 0.8604 at 400 °C to 0.9808 at 600 °C and 0.9952 at 800 °C (Figure 15.1). At the nine common temperatures the COM-driven sweep and the native Sensitivity block STEMP (Section 7.5) agree to a maximum conversion difference of 4.7 × 10^−10^; H~2~ product, CRACKER and HEATER duties are identical to every stored digit. The automation layer therefore adds no error.

![**Figure 15.1.** NH~3~ conversion against cracker temperature at 20 bar: 17 automated runs and the nine STEMP points. The coincidence of both data sets verifies the COM layer against Aspen's own case-study machinery. *Source: Aspen Plus V15 simulation.*](../../results/figures/aspen_conversion_vs_temperature.png){width=80%}

Above 600 °C the CRACKER duty grows by only 50.79 kW to 800 °C while FEHE recovery grows from 612.21 to 917.23 kW, so total external heating rises just 2293.12 → 2350.81 kW (Figure 15.2). Specific heat demand is flat (9.10–9.21 kWh/kg H~2~ between 475 and 800 °C). Efficiency peaks at 600 °C; below 425 °C the tail gas supplies more heat than the process needs (deficit −282.02 kW at 400 °C, zero at 424.4 °C by linear interpolation), and the surplus earns no credit in Eq. (16.1).

<!-- data: results/sensitivity/aspen_temperature.csv; results/sensitivity/aspen_native_STEMP_baseline.csv (merge on reactor_temperature_C, 9 rows); 400 + 25 x 282.02/(282.02 + 6.35) = 424.4 -->

![**Figure 15.2.** Block duties against cracker temperature (20 bar, 100 kmol/h). FEHE recovery, not the reaction duty, carries most of the temperature effect, which keeps the external heating nearly flat above 550 °C. *Source: Aspen Plus V15 simulation.*](../../results/figures/aspen_duties_vs_temperature.png){width=80%}

## 15.3 Pressure and the temperature-pressure map

Raising pressure from 5 to 40 bar lowers conversion at 600 °C from 0.9951 to 0.9626 (Le Chatelier, two moles of gas per mole of NH~3~). The efficiency loss is small (0.8806 → 0.8746) because unconverted NH~3~ is burned in the tail gas. The benefit of high pressure, a pressurised H~2~ product that needs less downstream compression, is not credited because the model contains no product compressor.

Conversion ≥ 0.98 is reached from 500 °C at 5 bar, 550 °C at 10 bar, 600 °C at 20 bar, 650 °C at 30 bar and 700 °C at 40 bar; conversion ≥ 0.99 from 550, 600, 700 and 750 °C at 5, 10, 20 and 30 bar, and not at 40 bar within the map (maximum 0.9871 at 750 °C) (Figure 15.3).

<!-- data: results/sensitivity/aspen_pressure.csv; results/sensitivity/aspen_tp_map.csv (min reactor_temperature_C with nh3_conversion >= 0.98 / 0.99 per pressure) -->

![**Figure 15.3.** NH~3~ conversion (%) over the 450–750 °C × 5–40 bar map, 35 runs. It locates the operating window for a target conversion, which moves to higher temperature as pressure rises. *Source: Aspen Plus V15 simulation.*](../../results/figures/aspen_tp_map_conversion.png){width=80%}

## 15.4 Feed rate and feed water

Every extensive result scales with the feed: per kmol/h of feed, H~2~ product, duties and tail-gas heat vary by less than 4.4 × 10^−9^ (relative) between 25 and 200 kmol/h, and all intensive KPIs are constant. This linearity is expected of a steady-state equilibrium model without equipment sizing, hydraulics, kinetics or heat losses: it contains no scale effects, so capacity matters only through costs (Section 17) and reactor sizing (Section 10).

At fixed total feed, water displaces NH~3~ and must be evaporated: from 0 to 2 mol% H~2~O, H~2~ product falls 125.05 → 122.57 kmol/h, vaporiser duty rises 719.91 → 792.89 kW and specific heat demand rises 4.0 %.

<!-- data: results/sensitivity/aspen_feed_rate.csv (column / feed_total_kmol_h); results/sensitivity/aspen_feed_water.csv -->

## 15.5 PSA recovery, FEHE approach and heat integration

Recovery shifts H~2~ between product and tail gas (Figure 15.4): from 0.70 to 0.95 the product rises 102.78 → 139.49 kmol/h while the tail-gas combustion heat falls 2926.47 → 582.77 kW against a constant demand of 2293.12 kW. The deficit is −164.61 kW at 0.75 and +304.13 kW at 0.80, so tail-gas heat equals demand at

$$ R_0 = 0.75 + 0.05\,\frac{164.61}{164.61 + 304.13} = 0.7676 \qquad (15.1) $$

Below $R_0$ the plant is self-sufficient on a first-law basis but burns product H~2~; above it, fuel must be imported. Efficiency rises monotonically with recovery.

<!-- data: results/sensitivity/aspen_psa_recovery.csv (net_fuel_heat_deficit_kW, tailgas_combustion_heat_kW, total_external_heating_kW) -->

![**Figure 15.4.** Left: H~2~ product against PSA recovery. Right: tail-gas combustion heat, external heat demand and net deficit; the dashed line marks Eq. (15.1). It shows that the recovery choice sets the plant's fuel balance. *Source: Aspen Plus V15 simulation.*](../../results/figures/aspen_psa_recovery_tradeoff.png){width=95%}

Widening the FEHE hot-end approach from 20 to 150 K lowers recovery 656.15 → 470.52 kW; external heating rises by the same 185.64 kW and efficiency falls 0.8813 → 0.8644. A smaller approach needs more exchanger area; that cost trade-off is not part of this energy sensitivity.

Removing the FEHE raises external heating by exactly the FEHE duty, from 336.15 kW at 400 °C to 917.23 kW at 800 °C (Figure 15.5). Without it efficiency falls with temperature above 450 °C (0.8352 → 0.8002); with it efficiency stays between 0.8725 and 0.8772 from 450 °C upward. Heat integration is what makes high cracking temperatures affordable.

<!-- data: results/sensitivity/aspen_fehe_approach.csv; results/sensitivity/aspen_temperature.csv vs aspen_no_hi_temperature.csv (merge on reactor_temperature_C) -->

![**Figure 15.5.** External heating (left) and LHV efficiency (right) with and without the FEHE, 400–800 °C, 20 bar. The gap widens with temperature because the recoverable effluent heat grows. *Source: Aspen Plus V15 simulation.*](../../results/figures/aspen_heat_integration_vs_none.png){width=95%}
