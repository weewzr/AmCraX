<!-- cites: lee2022ammonia, ipcc2006v2ch2, ema2025ses, glec2023v3, eu2023_1185, kum2026heatintegrated, cho2026nickel, cechetto2023membrane -->

# 19 Environmental implications

## 19.1 Method and system boundary

`amcrax.environmental.carbon_intensity` (**independent Python calculation**) multiplies the activity data of the **Aspen Plus V15** baseline by emission factors. It is a simplified carbon-intensity account and **not a life-cycle assessment**: there is no inventory analysis, no impact categories other than CO~2~e, no allocation and no critical review. The boundary is cradle-to-gate of H~2~ at the PSA outlet. Inside the boundary are upstream NH~3~ production, sea transport of NH~3~, process electricity and external heat supply. Outside it are plant construction, catalyst and adsorbent manufacture, N~2~O, NO~x~ and NH~3~ emissions from combustion, H~2~ leakage, H~2~ compression and delivery, NH~3~ boil-off and the upstream natural-gas supply chain. Process electricity covers only the feed pump (1.85 kW), because no PSA or compressor power is simulated.

Table: **Table 19.1.** Emission factors. † = confirmed only through a secondary listing or search extract; to be verified against the primary source. *Source: backend/amcrax/data/environmental.yaml.*

| Factor | Value | Unit | Source |
|---|---|---|---|
| Grey NH~3~ (SMR + Haber–Bosch) | 2.60 | kg CO~2~e/kg NH~3~ | Lee et al. (2022), Fig. 8 |
| Blue NH~3~ (process CO~2~ captured) | 1.16 | kg CO~2~e/kg NH~3~ | Lee et al. (2022), Fig. 8 |
| Green NH~3~ (renewable) | 0 | kg CO~2~e/kg NH~3~ | Lee et al. (2022); equipment manufacture excluded |
| Ship transport (liquefied-gas tanker) | 0.011 | kg CO~2~e/(t km) | GLEC v3.0 (Smart Freight Centre, 2023) † |
| Transport distance | 5000 | km | assumption (illustrative) |
| Natural-gas combustion | 56 100 | kg CO~2~/TJ (LHV) | IPCC (2006), Vol. 2, Table 2.2 |
| Singapore grid, 2024 | 0.402 | kg CO~2~/kWh | EMA (2025) † |
| Heater efficiency (fired, electric) | 1.0 | – | assumption (lower bound) |
| EU RFNBO comparator / saving | 94 / 70 % | g CO~2~e/MJ / – | Regulation (EU) 2023/1185 † |

## 19.2 Results

Nine combinations are compared: three NH~3~ routes (green, blue, grey) and three ways of covering the 772.87 kW heat deficit (imported natural gas, extra NH~3~ burnt with the tail gas, and electric heating) (Figure 19.1).

![**Figure 19.1.** Carbon intensity of baseline H~2~ for green, blue and grey NH~3~ under three heating options. Dashed lines are the EU RFNBO and IEA low-emission thresholds, drawn only as cited reference lines. The NH~3~ route matters far more than the heating option. *Source: independent Python calculation on Aspen Plus V15 baseline; factors from Table 19.1.*](../../results/figures/ci_scenarios_baseline.png){width=90%}

Upstream NH~3~ dominates whenever it is non-zero. Each kilogram of H~2~ requires 6.756 kg of NH~3~ feed, which carries 17.56 kg CO~2~e for grey NH~3~ (95 % of the 18.56 kg CO~2~e/kg H~2~ total with natural-gas heating) and 7.84 kg CO~2~e for blue NH~3~ (Figure 19.2). Transport adds 0.37 kg CO~2~e/kg H~2~ in every case. Self-firing emits no CO~2~ at the plant. However, the 0.595 kg of extra NH~3~ per kg H~2~ carries its own upstream emissions. Self-firing is therefore the best option for green NH~3~ (0.41 kg CO~2~e/kg H~2~) and the worst for grey NH~3~ (19.52). Electric heating on the 2024 Singapore grid gives 1.61 kg CO~2~e/kg H~2~ with green NH~3~, more than natural gas (0.99).

![**Figure 19.2.** Contributions of upstream NH~3~, transport, electricity and external heat for the nine cases. Shows that upstream NH~3~ (feed rate × factor) dominates blue and grey routes, while heat supply and transport dominate the green routes. *Source: independent Python calculation on Aspen Plus V15 baseline.*](../../results/figures/ci_breakdown_baseline.png){width=95%}

<!-- data: results/simulations/environmental_baseline.json comparison.rows[*], scenarios.*.kg_nh3_per_kg_h2, nh3_fuel_kg_h, electricity_kW, heat_deficit_kW -->

Without the FEHE the heat deficit rises to 1385.1 kW. The carbon intensity then rises to 1.49 kg CO~2~e/kg H~2~ for green NH~3~ with natural gas, to 2.59 with electric heating and to 20.77 for grey NH~3~ with self-firing. Heat integration therefore matters most where the heat supply, not the NH~3~ route, dominates.

<!-- data: results/simulations/environmental_baseline_no_hi.json comparison.rows[*], notes -->

The thresholds of 3.38 kg CO~2~e/kg H~2~ (derived from Regulation (EU) 2023/1185) and 4.0 kg CO~2~e/kg H~2~ (IEA, as quoted by Kum et al., 2026) use broader well-to-wheel boundaries. They are reference lines only, not compliance checks. Only the green routes fall below them.

## 19.3 Emissions not modelled

The burner model assumes complete combustion to N~2~ and H~2~O (Section 11.4), so NO~x~, N~2~O and NH~3~ slip are not quantified. Cho et al. (2026) report 863–1517 mg/Nm^3^ NO~x~ in NH~3~-fired flue gas. Kum et al. (2026) estimate negligible N~2~O from an equilibrium calculation. N~2~O has a high global-warming potential, so measured burner data would be needed before the self-firing results can be relied on. Upstream factors also span a range: Cechetto et al. (2023) give 2.0–4.6 t CO~2~/t for grey NH~3~. The results above are therefore indicative.
