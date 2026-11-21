<!-- cites: peng1976new, cho2026nickel, hansen2024hysys, farokhi2025costoptimization, mehr2026highcapacity, ahmad2025gtcc, chopra2026decentralized, bell2014coolprop -->

# 8 Thermodynamic property method

## 8.1 Selection logic

One property method has to cover refrigerated liquid NH~3~ at -33 °C that is pumped to 21 bar and evaporated, an NH~3~/H~2~/N~2~ gas from 40 to 600 °C at about 20 bar (up to 40 bar in the sensitivity studies), and combustion gas near 1 bar up to the 1368.90 °C flame temperature: mostly light, supercritical gases with one polar, condensable component and a trace of water.

Activity-coefficient methods need Henry components for H~2~, N~2~ and O~2~ and a separate vapour model; an ideal gas ignores non-ideality at 20-40 bar. A cubic equation of state covers both phases and all conditions with one parameter set and supplies the fugacity coefficients that RGibbs needs. Peng-Robinson is the usual choice in published cracker flowsheets (Cho et al., 2026; Hansen et al., 2024; Farokhi et al., 2025; Mehr et al., 2026; PR-BM in Ahmad et al., 2025; RKS-BM in Chopra et al., 2026), and Hansen et al. (2024) found no significant difference between Peng-Robinson and Soave-Redlich-Kwong. AmCraX therefore uses `PENG-ROB` for the whole flowsheet (Figure 8.1).
<!-- data: results/simulations/baseline.json streams.FLUE.temperature_C 1368.90; research/notes/cho2026nickel.md, hansen2024hysys.md (p. 6), farokhi2025costoptimization.md, mehr2026highcapacity.md, ahmad2025gtcc.md, chopra2026decentralized.md -->

## 8.2 The Peng-Robinson equation

The Peng-Robinson equation (Peng & Robinson, 1976) is

$$ P = \frac{RT}{v - b} - \frac{a(T)}{v(v + b) + b(v - b)} \qquad (8.1) $$

with the pure-component parameters and alpha function

$$ a_i(T) = 0.45724\,\frac{R^2 T_{c,i}^2}{P_{c,i}}\,\alpha_i(T), \qquad b_i = 0.07780\,\frac{R T_{c,i}}{P_{c,i}} \qquad (8.2) $$

$$ \alpha_i(T) = \left[1 + \kappa_i\left(1 - \sqrt{T/T_{c,i}}\right)\right]^2, \qquad \kappa_i = 0.37464 + 1.54226\,\omega_i - 0.26992\,\omega_i^2 \qquad (8.3) $$

and the van der Waals one-fluid mixing rules

$$ a = \sum_i \sum_j x_i x_j \sqrt{a_i a_j}\,(1 - k_{ij}), \qquad b = \sum_i x_i b_i \qquad (8.4) $$

Here $P$ is the pressure (Pa), $T$ the temperature (K), $v$ the molar volume (m^3^/mol), $R$ = 8.314 J/(mol K), $T_{c,i}$ and $P_{c,i}$ the critical temperature (K) and pressure (Pa) of component $i$, $\omega_i$ its acentric factor, $x_i$ its mole fraction in the phase and $k_{ij}$ the binary interaction parameter (all dimensionless). From Eq. (8.1) Aspen derives the fugacity coefficients and the enthalpy departure, so the latent heat in VAPORIZR also comes from the equation of state. Every baseline run reports that the binary parameters (PRKBV, data set 1) were retrieved from the Aspen literature databank EOS-LIT; uncovered pairs keep $k_{ij}$ = 0, and the values are not exposed in the input forms.
<!-- data: results/simulations/baseline.json status.messages (PRKBV ... EOS-LIT); results/validation/aspen_binary_parameters.json (PRKBV-1 form holds no values); docs/validation/discrepancy_analysis.md section 6(b) -->

![**Figure 8.1.** Global property-method specification in Aspen Plus V15: base method PENG-ROB for the whole flowsheet, equation-of-state model ESPRSTD with data set 1 and the Modify option unticked, so the method is used as supplied. This one setting fixes the feed-section phase behaviour, the fugacity coefficients in the RGibbs equilibrium and all enthalpies. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/03_property_method.png){width=95%}

## 8.3 The feed section: a model-form difference

A cubic equation fitted to vapour pressure through $\omega$ alone is weakest for a polar, hydrogen-bonding fluid such as NH~3~ near saturation. Table 8.1 therefore compares the feed section with the independent Python model, which uses the reference equation of state for ammonia (CoolProp; Bell et al., 2014) and an ideal-liquid (Raoult) dew point, at identical states where possible.

Table: **Table 8.1.** Feed-section properties: Aspen PENG-ROB against alternative models. *Sources: Aspen Plus V15 simulation (results/simulations/baseline.json); independent Python calculation (results/validation/feed_section_analysis.json, independent_physics_checks.csv, results/simulations/python_baseline.json).*

| Quantity | Aspen PENG-ROB | Alternative (independent Python calculation) |
|---|---|---|
| Feed bubble point at 1.013 bar (°C) | -32.96 | -33.28 (reference EOS and Raoult) |
| Pump brake power (kW) | 1.845 | 1.851 (hand calculation with reference-EOS liquid volume; +0.29 %) |
| Vaporiser duty between the Aspen S1 and S2 states (kW) | 739.46 | 721.8 (reference EOS); Aspen 2.4 % higher |
| NH~3~ vapour residual enthalpy at S2, 75.9 °C and 20.8 bar (kJ/mol) | -1.017 (Peng-Robinson, $k_{ij}$ = 0) | -1.436 (reference EOS) |
| Dew point at 20.8 bar (°C) | 65.9 | 60.1 (Raoult); 52.7 (Peng-Robinson, $k_{ij}$ = 0); 65.1 (Peng-Robinson, $k_{ij}$(NH~3~-H~2~O) = -0.25); 50.9 (pure NH~3~, reference EOS) |

<!-- data: results/simulations/baseline.json streams.FEED.temperature_C -32.9617, blocks.PUMP.power_kW 1.84528517; results/simulations/python_baseline.json streams.FEED.temperature_C -33.2807; results/validation/independent_physics_checks.csv baseline pump_W_hand_kW 1.850709 (rel. dev. 0.00294); results/validation/feed_section_analysis.json vaporiser_at_aspen_states (721.82, 739.46, 0.02444), nh3_residual_enthalpy_S2_kJ_mol, dew_point (S2 - 10 K = 65.90; raoult 60.09; PR kij 0 52.68; PR kij -0.25 65.14; pure NH3 50.88) -->

The liquid side agrees closely: bubble point within 0.32 K and pump power within 0.3 %. At identical states the Aspen PENG-ROB vaporiser duty is 2.4 % above the reference equation of state (739.5 against 721.8 kW). This is consistent with the smaller magnitude of the Peng-Robinson residual enthalpy of NH~3~ vapour at the vaporiser outlet; for pure-ammonia enthalpy the reference equation is the more accurate model. The difference is 17.6 kW, 0.8 % of the 2293.12 kW external heating.

The dew point is a different matter. With 0.2 mol% water it lies above the 50.9 °C saturation temperature of pure NH~3~, because the water evaporates last, and it depends on the NH~3~-H~2~O vapour-liquid equilibrium model: 52.7 to 65.9 °C in Table 8.1. No reference mixture model or measurement was available to arbitrate, so neither value can be called right. Through the "dew point + 10 K" rule the dew point sets the vaporiser outlet (75.90 °C in Aspen, 70.09 °C in the Python model) and hence part of the exchanger and cooler duties. The 20 flowsheet cross-check items that fail in the validation matrix trace back to these feed-section differences. They measure a model-form difference in both directions and are not evidence that either model is the weaker one (Section 16).
<!-- data: results/validation/feed_section_analysis.json; (739.4596 - 721.8207) = 17.64 kW; 17.64 / 2293.12 = 0.0077; results/simulations/baseline.json streams.S2.temperature_C 75.9001; results/simulations/python_baseline.json streams.S2.temperature_C 70.0875; docs/validation/discrepancy_analysis.md section 4; results/validation/validation_matrix.json FEEDSEC-ANALYSIS -->

## 8.4 The reaction section

At 600 °C and 20 bar the fugacity coefficients are close to one: Aspen RGibbs runs with PENG-ROB and with an ideal gas differ by only 0.00004 in conversion, against 1.51 percentage points at 250 °C and 40 bar, the largest effect in the 84-point grid. The property method therefore matters for the reactor only in low-temperature, high-pressure designs (Section 13).
<!-- data: results/validation/equilibrium_aspen_grid.csv 600 degC / 20 bar PENG-ROB 0.980792051, IDEAL 0.9808314405; results/validation/equilibrium_discrepancy_summary.json n_points 84, max_abs_eos_effect_aspen_pp -1.508851 -->
