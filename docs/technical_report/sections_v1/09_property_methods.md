<!-- cites: peng1976new, cho2026nickel, hansen2024hysys, farokhi2025costoptimization, ahmad2025gtcc, chopra2026decentralized, bell2014coolprop, smith_grimech30, goodwin2018cantera -->

# 9 Thermodynamic property methods

## 9.1 Selection logic

The property method has to cover three different regions. (i) The feed section: refrigerated liquid NH~3~ at -33 degC and 1 bar, pumped to 21 bar and evaporated. (ii) The reaction and recovery train: an NH~3~/H~2~/N~2~ gas from 40 to 600 degC at about 20 bar, up to 40 bar in the sensitivity studies. (iii) The combustion side: N~2~/H~2~O/O~2~ near 1 bar up to the 1368.90 degC flame temperature. The mixture is mostly light, non-polar, supercritical gases (H~2~, N~2~, O~2~) with one polar, condensable component (NH~3~) and a trace of water.

Activity-coefficient methods (NRTL, UNIQUAC) need a separate vapour model and Henry components for H~2~, N~2~ and O~2~ and have no liquid to describe at high temperature. IDEAL is accurate for the hot gas but ignores non-ideality at 20-40 bar. A cubic equation of state covers both phases and all conditions with one parameter set, supplies the fugacity coefficients for RGibbs and needs only critical constants, acentric factors and optional binary parameters. Peng-Robinson is the usual choice in published cracker flowsheets (Cho et al., 2026; Hansen et al., 2024; Farokhi et al., 2025; PR-BM in Ahmad et al., 2025; RKS-BM in Chopra et al., 2026), and Hansen et al. (2024) found no significant PR-SRK difference. AmCraX therefore uses `PENG-ROB` globally.

<!-- data: results/simulations/baseline.json streams.FLUE.temperature_C; research/notes/cho2026nickel.md, hansen2024hysys.md, farokhi2025costoptimization.md, ahmad2025gtcc.md, chopra2026decentralized.md -->

## 9.2 The Peng-Robinson equation as applied in Aspen Plus

The Peng-Robinson equation (Peng & Robinson, 1976) is

$$ P = \frac{RT}{v - b} - \frac{a(T)}{v(v + b) + b(v - b)} \qquad (9.1) $$

with the pure-component parameters

$$ a_i(T) = 0.45724\,\frac{R^2 T_{c,i}^2}{P_{c,i}}\,\alpha_i(T), \qquad b_i = 0.07780\,\frac{R T_{c,i}}{P_{c,i}} \qquad (9.2) $$

and the alpha function

$$ \alpha_i(T) = \left[1 + \kappa_i\left(1 - \sqrt{T/T_{c,i}}\right)\right]^2, \qquad \kappa_i = 0.37464 + 1.54226\,\omega_i - 0.26992\,\omega_i^2 \qquad (9.3) $$

The mixture parameters follow the van der Waals one-fluid mixing rules

$$ a = \sum_i \sum_j x_i x_j \sqrt{a_i a_j}\,(1 - k_{ij}), \qquad b = \sum_i x_i b_i \qquad (9.4) $$

Here $P$ is pressure (Pa), $T$ temperature (K), $v$ molar volume (m^3^/mol), $R$ = 8.314 J/(mol K), $T_{c,i}$ and $P_{c,i}$ the critical temperature (K) and pressure (Pa) of component $i$, $\omega_i$ its acentric factor (-), $x_i$ the mole fraction in the phase (-) and $k_{ij}$ the binary interaction parameter (-). From Eq. (9.1) Aspen obtains the fugacity coefficients used in the phase and RGibbs equilibria, and the enthalpy departure. Each stream enthalpy is the ideal-gas enthalpy (from the databank formation enthalpy and ideal-gas heat capacity) plus this departure. The liquid enthalpy, and so the latent heat in VAPORIZR, also comes from the EOS. The critical constants and acentric factors are those of the APV150 databanks (Section 8).

The $k_{ij}$ values are not left at zero. The run status of every baseline run records:

> BINARY PARAMETERS PRKBV (DATA SET 1) FOR MODELS ESPR/ESPRSTD ARE RETRIEVED FROM EOS DATABANK. DATABANK NAME = EOS-LIT.

PRKBV is the PR binary-parameter set and EOS-LIT the Aspen literature databank; pairs it does not cover keep $k_{ij} = 0$. Figure 9.1 shows the global setting.

<!-- data: results/simulations/baseline.json status.messages -->

![**Figure 9.1.** Global property-method specification in Aspen Plus V15 (method PENG-ROB for the whole flowsheet). This one setting fixes the VLE of the feed section, the fugacity coefficients in the RGibbs equilibrium and all enthalpies. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/03_property_method.png){width=95%}

## 9.3 Weakness 1: refrigerated liquid ammonia

A two-parameter cubic EOS with the alpha function of Eq. (9.3) is fitted to vapour pressure through $\omega$ only. It is weakest for the saturated-liquid density and enthalpy of a strongly polar, hydrogen-bonding fluid such as NH~3~. Table 9.1 compares the Aspen feed-section results with the independent reference-EOS route of the Python model. That model uses CoolProp (Bell et al., 2014) for the NH~3~ liquid and vaporisation, and Raoult's law for the NH~3~/H~2~O VLE, which is itself an assumption.

Table: **Table 9.1.** Feed-section properties: Aspen PENG-ROB against the CoolProp reference equation of state. *Sources: Aspen Plus V15 simulation (results/simulations/baseline.json); independent Python calculation (results/simulations/python_baseline.json; pure-NH~3~ values computed with CoolProp 8.0.0 for this section).*

| Quantity | Aspen Plus V15, PENG-ROB | Independent Python calculation | Difference |
|---|---|---|---|
| Feed bubble point at 1.013 bar, 99.8/0.2 NH~3~/H~2~O (degC) | -32.96 | -33.28 (CoolProp + Raoult) | +0.32 K |
| Saturation temperature of pure NH~3~ at 1.013 bar (degC) | - | -33.32 (CoolProp) | - |
| Liquid feed density (kg/m^3^) | 683.3 (implied by the Aspen pump head) | 681.6 (CoolProp, pure saturated NH~3~) | +0.2% |
| Vaporiser outlet = dew point + 10 K at 20.8 bar (degC) | 75.90 | 70.09 | +5.81 K |
| Saturation temperature of pure NH~3~ at 20.8 bar (degC) | - | 50.88 (CoolProp) | - |
| Vaporiser duty (kW) | 739.46 | 713.64 | +25.82 kW (+3.5%) |
| Pump brake power (kW) | 1.845 | 1.850 | -0.2% |

<!-- data: results/simulations/baseline.json streams.FEED.temperature_C, streams.S2.temperature_C, blocks.VAPORIZR.duty_kW, blocks.PUMP (power_kW, head_developed 298.282264 m, pressure_change_bar 19.987 -> rho = dP/(g H) = 683.28 kg/m3); results/simulations/python_baseline.json streams.FEED/S2 temperature_C, kpis.vaporiser_duty_kW, kpis.pump_power_kW; CoolProp 8.0.0 PropsSI('T','P',101300,'Q',0,'Ammonia') = 239.829 K, PropsSI('D',...) = 681.64 kg/m3, PropsSI('T','P',20.8e5,'Q',1,'Ammonia') = 324.03 K (computed 2026-11-21, not stored in results/) -->

Liquid density (0.2 %), pump power and bubble point (0.32 K) agree closely. The Aspen dew point at 20.8 bar is 5.81 K higher; both values lie well above the pure-NH~3~ saturation temperature because the 0.2 mol% water evaporates last, so the gap reflects the NH~3~/H~2~O VLE model (PR with EOS-LIT $k_{ij}$ against Raoult's law) as much as pure-NH~3~ properties, and neither is validated for this dew point. The 3.5 % vaporiser-duty difference is 1.1 % of the 2293.12 kW total external heating: a real but second-order weakness for the plant KPIs.

<!-- data: results/simulations/baseline.json kpis.total_external_heating_kW; 25.82/2293.12 = 0.011 -->

## 9.4 Weakness 2: non-ideality in the reaction equilibrium

At 600 degC and 20 bar the gas is far above the critical temperatures of H~2~ and N~2~ and its fugacity coefficients are close to one. The EOS effect was tested with Aspen RGibbs runs at fixed T and P (PENG-ROB and IDEAL, 168 points) and compared with the independent Python solver (NASA-7 data from GRI-Mech 3.0, Smith et al., n.d., via Cantera, Goodwin et al., 2018) in ideal and PR form (Table 9.2).

Table: **Table 9.2.** Equilibrium NH~3~ conversion for pure NH~3~ feed: effect of the equation of state. *Sources: Aspen Plus V15 simulation (results/validation/equilibrium_aspen_grid.csv); independent Python calculation (results/validation/equilibrium_python_grid.csv).*

| T (degC) | P (bar) | Aspen PENG-ROB | Aspen IDEAL | Python PR | Python ideal |
|---|---|---|---|---|---|
| 600 | 1 | 0.99901 | 0.99901 | 0.99901 | 0.99902 |
| 600 | 20 | 0.98079 | 0.98083 | 0.98072 | 0.98084 |
| 600 | 40 | 0.96256 | 0.96272 | 0.96229 | 0.96273 |
| 400 | 20 | 0.86025 | 0.86104 | 0.85967 | 0.86102 |
| 400 | 40 | 0.76460 | 0.76749 | 0.76330 | 0.76748 |
| 300 | 40 | 0.46125 | 0.47202 | 0.46139 | 0.47177 |

<!-- data: results/validation/equilibrium_aspen_grid.csv rows (600,1),(600,20),(600,40),(400,20),(400,40),(300,40) PENG-ROB and IDEAL; results/validation/equilibrium_python_grid.csv same rows eos=pr and eos=ideal -->

PR non-ideality lowers the conversion, because the higher fugacity of the compressed mixture favours the side with fewer moles (NH~3~). In Aspen the effect is 0.00004 at the 600 degC/20 bar baseline, 0.00016 at 600 degC/40 bar and 0.0108 at 300 degC/40 bar; the largest is 1.51 percentage points (pp) at 250 degC/40 bar, against 1.29 pp in the Python solver. Over the 84 grid points the ideal-gas conversions of the two codes differ by 0.005 pp on average (at most 0.045 pp) and the PR conversions by 0.023 pp on average (at most 0.19 pp, 250 degC/40 bar). The EOS also changes the reaction heat little: 53.38 kJ/mol NH~3~ fed with PENG-ROB against 53.17 kJ/mol with IDEAL at 600 degC and 20 bar. The property method therefore matters only for low-temperature, high-pressure designs.

<!-- data: results/validation/equilibrium_aspen_grid.csv 600/20 heat_duty_kJ_per_mol_NH3_fed PENG-ROB 53.38339632, IDEAL 53.16960024; differences 0.9808314405-0.980792051, 0.9627245431-0.9625645535, 0.472020461-0.461247946; results/validation/equilibrium_discrepancy_summary.json n_points 84, max_abs_eos_effect_aspen_pp -1.508851, max_abs_eos_effect_python_pp -1.2905, mean_abs_dX_ideal_vs_ideal_pp 0.00504, max_abs_dX_ideal_vs_ideal_pp 0.0455, mean_abs_dX_pr_vs_pr_pp 0.0226, max_abs_dX_pr_vs_pr_pp -0.1853; results/validation/equilibrium_comparison.csv -->

The grid was regenerated with repeatability and stale-value checks after an automation fault (Section 13); the regenerated IDEAL grid shows no heat-duty anomalies.

<!-- data: results/validation/equilibrium_discrepancy_summary.json aspen_ideal_duty_anomalies [] -->

The baseline flowsheet run at 600 degC and 20 bar gives a conversion of 0.98081, slightly above the 0.98079 of the pure-NH~3~ grid point, because the 0.2 mol% water dilutes the reacting gas.

<!-- data: results/simulations/baseline.json kpis.nh3_conversion 0.98081036; results/validation/equilibrium_aspen_grid.csv 600/20 PENG-ROB 0.980792051 -->
