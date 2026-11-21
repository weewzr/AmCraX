<!-- cites: linnhoff1983pinch, mehr2026highcapacity, cho2026nickel, richard2024technoeconomic -->

# 16 Energy efficiency

## 16.1 Energy accounting and efficiency definition

In the **Aspen Plus V15 simulation** of the baseline the NH~3~ feed carries 8782.40 kW (LHV), the H~2~ product 8383.52 kW and the PSA tail gas 1647.98 kW. Product plus tail gas exceed the feed by 1249.09 kW: the endothermic reaction stores part of the supplied heat as chemical energy. The process imports 2293.12 kW of heat (VAPORIZR 739.46, HEATER 73.66, CRACKER 1480.00 kW) and 1.85 kW of pump work; FEHE moves 612.21 kW internally, COOLER rejects 304.95 kW and FLUEHX recovers 1520.25 kW from the flue gas. The overall energy balance closes to 3.2 × 10^−9^.

<!-- data: results/simulations/baseline.json kpis, blocks.*.duty_kW, blocks.PUMP.power_kW, balances.energy_closure_rel; LHV via amcrax.kpis.lhv_kW with amcrax.schemas.LHV_KJ_PER_MOL (H2 241.826, NH3 316.8 kJ/mol) -->

The efficiency KPI (`backend/amcrax/kpis.py`) is

$$ \eta_\mathrm{LHV} = \frac{\dot{H}_\mathrm{LHV,H_2}}{\dot{H}_\mathrm{LHV,NH_3} + \max(Q_\mathrm{ext} - Q_\mathrm{flue},\,0) + W_\mathrm{pump}} = \frac{8383.52}{8782.40 + 772.87 + 1.85} = 0.8772 \qquad (16.1) $$

where $\dot{H}_\mathrm{LHV}$ (kW) are LHV flows of product and feed, $Q_\mathrm{ext}$ (kW) the summed VAPORIZR, HEATER and CRACKER duties, $Q_\mathrm{flue}$ (kW) the FLUEHX duty and $W_\mathrm{pump}$ (kW) the pump power. The definition counts the net heat deficit one-to-one as purchased energy. It excludes furnace losses, the temperature level of heat (first law only), PSA and product-compression power (the PSA is a splitter), cooling utilities, and gives no credit for a heat surplus. The 772.87 kW deficit is what remains after tail-gas firing (Section 11.4).

## 16.2 Pinch analysis

The **independent Python calculation** `amcrax.heat_integration.analyse` rebuilds H–T curves for the feed (−32.54 → 600 °C, 1404.80 kW), the isothermal reaction (1480.00 kW at 600 °C), the cracked gas (600 → 40 °C, 918.00 kW) and the flue gas (1368.90 → 150 °C, 1520.24 kW), and targets minimum utilities at ΔT~min~ = 20 K (Linnhoff & Hindmarsh, 1983). Model and Aspen duties agree within 2.7 % (vaporiser) and 0.09 % (cracked gas).

With process streams only the problem is a threshold case: all 918.00 kW of cracked-gas heat can be recovered, no cooling is needed and 1966.81 kW must be imported (Figure 16.1, left). Adding the flue gas creates a pinch at 600 °C (hot) / 580 °C (cold): minimum hot utility 507.81 kW, minimum cold utility 61.24 kW (Figure 16.1, right; Figure 16.2).

<!-- data: results/simulations/heat_integration_baseline.json streams, targets_process, targets_with_flue, consistency -->

![**Figure 16.1.** Hot and cold composite curves of the baseline, process streams only (left) and with the tail-gas flue gas (right), ΔT~min~ = 20 K. The long isothermal reaction segment at 600 °C dominates the cold composite and fixes the pinch. *Source: independent Python calculation on Aspen Plus V15 results.*](../../results/figures/hi_composite_baseline.png){width=95%}

![**Figure 16.2.** Grand composite curves for the same two cases. With flue gas (right) the curve touches zero at a shifted 590 °C; the residual 507.8 kW at the top is the unavoidable import. *Source: independent Python calculation on Aspen Plus V15 results.*](../../results/figures/hi_grand_composite_baseline.png){width=95%}

The temperature level explains the residual import. Reaction heat at 600 °C must come from gas above 620 °C; the flue gas holds only 977.52 kW above 620 °C against 1480.00 kW needed (1480.00 + 5.33 kW of feed preheat near the pinch − 977.52 = 507.81 kW). Its 542.72 kW below 620 °C, with the cracked gas, can serve only the preheat and the vaporiser (494.05 kW latent heat at 50.88 °C). More tail gas at low temperature cannot cover the reaction.

<!-- data: heat_integration_baseline.json streams.FLUE curve_T_C/curve_H_kW (interpolated at 620 degC), targets_with_flue.problem_table (cascade 5.33 kW), feed_latent_heat_kW, feed_saturation_temperature_C -->

Table: **Table 16.1.** Heat-recovery configurations of the baseline (Figure 16.3). (b) and (c) use the Aspen FEHE duty; remaining duties from model H–T curves. Efficiency by Eq. (16.1) with the listed external heating (derived arithmetic). In (d) the 61.24 kW cold utility is unused flue heat, not process cooling. *Source: independent Python calculation on Aspen Plus V15 results, heat_integration_baseline.json.*

| Configuration | External heating (kW) | External cooling (kW) | kWh/kg H~2~ | Reduction vs (a) | η~LHV~ |
|---|---|---|---|---|---|
| (a) No heat recovery | 2884.80 | 918.00 | 11.47 | – | – |
| (b) FEHE only | 2272.59 | 305.78 | 9.03 | 21.2 % | – |
| (c) FEHE + tail-gas firing | 752.63 | 305.78 | 2.99 | 73.9 % | 0.8791 |
| (d) Pinch target incl. flue gas | 507.81 | 0 | 2.02 | 82.4 % | 0.9022 |

<!-- data: heat_integration_baseline.json configurations[a,b,c,d2]; eta = 8383.52/(8782.40 + Q + 1.85) -->

Configuration (c) gives 752.63 kW versus the Aspen deficit of 772.87 kW; the difference reflects the model vaporiser duty. The remaining 244.82 kW gap to the target is recoverable cracked-gas heat that now goes to the COOLER. The no-FEHE case (heat_integration_baseline_no_hi.json) gives the same targets, as expected since targets depend only on stream data.

![**Figure 16.3.** External heating and cooling for configurations (a)–(d). It ranks the value of each integration step against the thermodynamic minimum. *Source: independent Python calculation on Aspen Plus V15 results.*](../../results/figures/hi_configuration_comparison_baseline.png){width=80%}

## 16.3 FEHE size

Aspen reports UA = 6.657 kW/K (Section 11.2); the Python module gives 6.661 kW/K from the LMTD and 7.319 kW/K from a segmented profile that follows the non-linear H–T curves. With an **engineering assumption** of U = 50 W/(m^2^ K) (gas–gas service, range 10–100) the area is 146 m^2^ (73–732 m^2^), an order-of-magnitude estimate only.

<!-- data: heat_integration_baseline.json fehe (ua_lmtd_kW_K, ua_segmented_kW_K, U_assumed_W_m2K, area_m2, area_range_m2); baseline.json blocks.FEHE.details -->

## 16.4 Comparison with published values

**Published literature**, on different plants and definitions: Mehr et al. (2026) give about 88 % thermal efficiency for a heat-recovered cracking unit (p. 8) and about 68 % LHV for the whole plant, which delivers H~2~ at 104 bar (pp. 3, 9). Cho et al. (2026, Table 7) report 79.25 % (Ni, 24.34 bar) and 80.82 % (Ru, 10 bar) with NH~3~ fuel and net power in the denominator. Richard et al. (2024, p. 14) report 68.5 % for a fired tubular reactor, with auxiliary work subtracted. The AmCraX value of 0.8772 lies at the upper end because Eq. (16.1) omits furnace losses and compression power; it is an upper bound, not a like-for-like result.
