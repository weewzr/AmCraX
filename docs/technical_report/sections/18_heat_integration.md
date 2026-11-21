<!-- cites: linnhoff1983pinch, mehr2026highcapacity, cho2026nickel, richard2024technoeconomic -->

# 18 Heat integration

## 18.1 Energy accounting and efficiency definition

In the **Aspen Plus V15 simulation** of the baseline, the NH~3~ feed carries 8782.40 kW (LHV), the H~2~ product 8383.52 kW and the PSA tail gas 1647.98 kW. Product and tail gas together exceed the feed by 1249.09 kW, because the endothermic reaction stores part of the supplied heat as chemical energy. The process imports 2293.12 kW of heat (VAPORIZR 739.46, HEATER 73.66, CRACKER 1480.00 kW) and 1.85 kW of pump work. The feed/effluent exchanger (FEHE) moves 612.21 kW internally, the COOLER rejects 304.95 kW and FLUEHX recovers 1520.25 kW from the flue gas.
<!-- data: results/simulations/baseline.json kpis, blocks.*.duty_kW, blocks.PUMP.power_kW; LHV = n x amcrax.schemas.LHV_KJ_PER_MOL (NH3 316.8, H2 241.826 kJ/mol): 99.8 x 316.8/3.6, 124.803215 x 241.826/3.6 -->

The efficiency KPI (`backend/amcrax/kpis.py`) is

$$ \eta_\mathrm{LHV} = \frac{\dot{H}_\mathrm{LHV,H_2}}{\dot{H}_\mathrm{LHV,NH_3} + \max(Q_\mathrm{ext} - Q_\mathrm{flue},\,0) + W_\mathrm{pump}} = \frac{8383.52}{8782.40 + 772.87 + 1.85} = 0.8772 \qquad (18.1) $$

where $\dot{H}_\mathrm{LHV}$ (kW) are the LHV flows of product and feed, $Q_\mathrm{ext}$ (kW) the summed VAPORIZR, HEATER and CRACKER duties, $Q_\mathrm{flue}$ (kW) the FLUEHX duty and $W_\mathrm{pump}$ (kW) the pump power. The 772.87 kW net heat deficit remains after tail-gas firing (Section 10).
<!-- data: results/simulations/baseline.json kpis.lhv_efficiency (0.8772019), net_fuel_heat_deficit_kW (772.8673), pump_power_kW -->

Eq. (18.1) is a first-law **upper bound**. It counts external heat one-to-one against the LHV, as from a fired heater of 100 % efficiency, and credits all flue heat recovered down to the 150 °C stack, whatever its temperature. It omits PSA and compression power and cooling utilities, and gives no credit for a heat surplus. Section 18.3 tests the temperature-level part.

## 18.2 Pinch analysis

The **independent Python calculation** `amcrax.heat_integration.analyse` rebuilds enthalpy–temperature curves from the Aspen states and targets minimum utilities at ΔT~min~ = 20 K (Linnhoff & Hindmarsh, 1983). The streams are the feed (−32.54 to 600 °C, 1404.80 kW), the isothermal reaction (1480.00 kW at 600 °C), the cracked gas (600 to 40 °C, 918.00 kW) and the flue gas (1368.90 to 150 °C, 1520.24 kW). Model and Aspen duties agree within 2.7 % for the vaporiser, 1.4 % for the whole feed heating and 0.09 % for the cracked gas.
<!-- data: results/simulations/heat_integration_baseline.json streams[*].duty_kW, supply/target temperatures, consistency[*].rel_deviation (-0.0273, -0.0144, 0.0009) -->

With process streams only, the problem is a threshold case: all 918.00 kW of cracked-gas heat can be recovered, no cooling is needed and 1966.81 kW must be imported (Figure 18.1, left). Adding the flue gas creates a pinch at 600 °C (hot) and 580 °C (cold), with a minimum hot utility of 507.81 kW and a minimum cold utility of 61.24 kW (Figure 18.1, right; Figure 18.2).
<!-- data: results/simulations/heat_integration_baseline.json targets_process (hot_utility_kW 1966.81, threshold_problem), targets_with_flue (507.81, 61.24, pinch_hot_C 600, pinch_cold_C 580) -->

![**Figure 18.1.** Hot and cold composite curves of the baseline, process streams only (left) and with the tail-gas flue gas (right), ΔT~min~ = 20 K. The long isothermal reaction segment at 600 °C dominates the cold composite and fixes the pinch. *Source: independent Python calculation on Aspen Plus V15 results.*](../../results/figures/hi_composite_baseline.png){width=100%}

![**Figure 18.2.** Grand composite curves for the same two cases. With flue gas (right) the curve touches zero at a shifted 590 °C; the 508 kW at the top is the unavoidable import. *Source: independent Python calculation on Aspen Plus V15 results.*](../../results/figures/hi_grand_composite_baseline.png){width=100%}

## 18.3 Why temperature level limits tail-gas firing

Reaction heat at 600 °C can only come from gas above 620 °C. The flue gas holds 977.52 kW above 620 °C against the 1480.00 kW the reaction needs. The interval just below the reaction also matters: the feed needs 29.64 kW between 580 and 600 °C, and the flue gas offers 24.31 kW between 600 and 620 °C. The net 5.33 kW of feed preheat that the flue gas cannot cover in that interval adds to the reaction deficit, so the target is 1480.00 + 29.64 − 24.31 − 977.52 = 507.81 kW. The 542.72 kW of flue heat below 620 °C can serve only the lower-temperature preheat and the vaporiser, whose latent heat is 494.05 kW at 50.88 °C. Low-temperature tail gas cannot cover the reaction.
<!-- data: heat_integration_baseline.json streams FEED and FLUE curve_T_C/curve_H_kW interpolated with numpy: FEED H(600)-H(580) = 29.640 kW, FLUE H(620)-H(600) = 24.313 kW, FLUE duty - H(620) = 977.519 kW, FLUE H(620) = 542.721 kW; feed_latent_heat_kW, feed_saturation_temperature_C -->

Table: **Table 18.1.** Heat-recovery configurations of the baseline (Figure 18.3). Configurations (b) and (c) use the Aspen FEHE duty; the remaining duties come from the model curves. Efficiency by Eq. (18.1) with the listed external heating (derived arithmetic). In (d) the 61.24 kW cold utility is unused flue heat, not process cooling. *Source: independent Python calculation on Aspen Plus V15 results, heat_integration_baseline.json.*

| Configuration | External heating (kW) | External cooling (kW) | kWh/kg H~2~ | Reduction vs (a) | η~LHV~ |
|---|---|---|---|---|---|
| (a) No heat recovery | 2884.80 | 918.00 | 11.47 | – | – |
| (b) FEHE only | 2272.59 | 305.78 | 9.03 | 21.2 % | – |
| (c) FEHE + tail-gas firing | 752.63 | 305.78 | 2.99 | 73.9 % | 0.8791 |
| (d) Pinch target incl. flue gas | 507.81 | 0 | 2.02 | 82.4 % | 0.9022 |

<!-- data: heat_integration_baseline.json configurations[a,b,c,d2]; eta = 8383.52/(8782.40 + Q + 1.85) -->

Configuration (c) respects the temperature levels and gives a heat import of 752.63 kW, against the KPI's 772.87 kW; the 20.24 kW difference matches the lower model vaporiser duty. The first-law credit of flue heat therefore does not overstate the baseline import, and the upper-bound character of Eq. (18.1) comes from the ideal fired heater. The 244.82 kW between (c) and (d) is recoverable cracked-gas heat that now goes to the COOLER. The case without exchanger gives the same targets, because targets depend only on stream data.
<!-- data: heat_integration_baseline.json configurations c (752.628) and d2 (507.808), consistency Vaporiser (719.25 vs 739.46 kW); baseline.json kpis.net_fuel_heat_deficit_kW; heat_integration_baseline_no_hi.json targets_with_flue (507.81, 61.24) -->

![**Figure 18.3.** External heating and cooling for configurations (a)–(d). It ranks the value of each integration step against the thermodynamic minimum. *Source: independent Python calculation on Aspen Plus V15 results.*](../../results/figures/hi_configuration_comparison_baseline.png){width=80%}

## 18.4 Exchanger size

Aspen reports UA = 1590.96 cal/(s K), which is 6.661 kW/K with the International Table calorie (Section 10.2). The Python module uses the same Aspen duty (612.21 kW) and terminal temperatures and gives 6.661 kW/K from the log-mean temperature difference, but 7.319 kW/K when it sums dQ/ΔT over 200 segments of its own enthalpy–temperature curves. The difference is the profile, not the duty: the LMTD assumes straight temperature–duty lines, whereas the model curves (heat capacities varying with temperature) give a smaller temperature difference inside the exchanger, 88.3 K at half duty against 101.2 K for straight lines, so the effective mean difference is 83.6 K instead of 91.9 K. With an **engineering assumption** of U = 50 W/(m^2^ K) (gas–gas service, range 10–100) and the segmented UA, the area is 146 m^2^ (73–732 m^2^), an order-of-magnitude estimate only.
<!-- data: baseline.json blocks.FEHE.details.UA (1590.96358 cal/sec-K x 4.1868 J/cal); heat_integration_baseline.json fehe (duty_kW 612.213 = Aspen FEHE duty, ua_lmtd_kW_K 6.661, ua_segmented_kW_K 7.319, profile_hot_T_C[10] - profile_cold_T_C[10] = 415.848 - 327.565 = 88.28 K at 306.1 kW, straight-line value (50.00 + 152.48)/2 = 101.24 K, 612.213/7.31916 = 83.64 K, U_assumed_W_m2K, area_m2 146.38, area_range_m2); backend/amcrax/heat_integration/analysis.py _fehe (201 points, ua_seg) -->

## 18.5 Comparison with published values

Published efficiencies use other plants and other definitions. Mehr et al. (2026) give about 88 % thermal efficiency for a heat-recovered cracking unit and about 68 % LHV for the whole plant, which delivers H~2~ at 104 bar. Cho et al. (2026) report 79.25 % (Ni, 24.34 bar) and 80.82 % (Ru, 10 bar) with NH~3~ fuel and net power in the denominator. Richard et al. (2024) report 68.5 % for a fired tubular reactor with auxiliary work subtracted. The AmCraX value of 0.8772 lies at the upper end because Eq. (18.1) omits furnace losses and compression power; it is an upper bound, not a like-for-like result.
