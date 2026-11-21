<!-- cites: hansen2024hysys, farokhi2025costoptimization, richard2024technoeconomic, cho2026nickel, kum2026heatintegrated, mehr2026highcapacity, xu2025review, purcel2024stability, lee2023carbonfree, takahashi2016kinetic, dicarlo2014ammonia, maccarrone2025comprehensive -->

# 10 Reactor configuration

## 10.1 Why an equilibrium reactor is the first model

Ammonia decomposition, NH~3~ ⇌ 0.5 N~2~ + 1.5 H~2~, is endothermic and increases the number of moles, so equilibrium conversion rises with temperature and falls with pressure (Section 4). At industrial cracking temperatures the reaction approaches equilibrium closely, so an equilibrium reactor gives the thermodynamic ceiling on conversion and the corresponding heat demand without catalyst data. Both drive every downstream result: H~2~ production, residual NH~3~, tail-gas heating value and furnace duty. Gibbs crackers are the usual first-level model in published flowsheets (Farokhi et al., 2025; Hansen et al., 2024). Catalyst mass, residence time, axial profiles, heat-flux distribution and deactivation need a kinetic model, summarised in Section 10.5.

## 10.2 RGibbs principle and specification

RGibbs minimises the total Gibbs free energy of the outlet phase at the specified temperature and pressure, subject to element balances:

$$ \min_{n_i \ge 0} \; G = \sum_{i} n_i \left[ g_i^{\circ}(T) + RT \ln \frac{\hat{\varphi}_i \, y_i \, P}{P^{\circ}} \right] \quad \text{s.t.} \quad \sum_i a_{ki}\, n_i = b_k \;\; (k = \mathrm{N}, \mathrm{H}, \mathrm{O}) \qquad (10.1) $$

where $n_i$ is the outlet molar flow of species $i$ (kmol/h), $g_i^{\circ}(T)$ its standard molar Gibbs energy at temperature $T$ (K), $R$ the gas constant (8.314 J/(mol K)), $y_i$ the mole fraction, $\hat{\varphi}_i$ the Peng-Robinson fugacity coefficient, $P$ the pressure (bar), $P^{\circ}$ = 1 bar, $a_{ki}$ the number of atoms of element $k$ in species $i$ and $b_k$ the element flow fed. No stoichiometry is entered; the products list defines the species over which $G$ is minimised.

CRACKER is isothermal at 600 °C and 20 bar, with NH~3~, H~2~, N~2~ and H~2~O as possible products (Figures 10.1 and 10.2). O~2~ is excluded so that no oxygen-containing species can form from the 0.2 mol% feed water; H~2~O is effectively inert (outlet 0.2 kmol/h, equal to the feed). Calculator TLINK sets the HEATER outlet to the cracker temperature and the FEHE cold outlet to the cracker temperature minus 50 K, so STEMP varies one temperature consistently (Section 7.4).

<!-- data: aspen/models/baseline.inp BLOCK CRACKER, CALCULATOR TLINK; results/simulations/baseline.json streams.S5.component_mole_flow_kmol_h.H2O -->

![**Figure 10.1.** CRACKER (RGibbs) setup: calculation option, temperature and pressure. Temperature and pressure alone set the equilibrium conversion of the isothermal reactor. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/05_reactor_setup.png){width=95%}

![**Figure 10.2.** CRACKER products tab listing NH~3~, H~2~, N~2~ and H~2~O. For RGibbs this list is the reaction specification; excluding O~2~ keeps the trace water inert. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/06_reactor_products.png){width=95%}

Table: **Table 10.1.** Choice of the reactor model for the cracker. *Source: engineering assessment; literature usage as cited.*

| Model | Needs | Gives | Use in AmCraX |
|---|---|---|---|
| RGibbs | T, P, product list | equilibrium composition and duty | **selected** (Aspen Plus V15): thermodynamic limit; also used by Hansen et al. (2024) and Farokhi et al. (2025) |
| REquil | stoichiometry, T, P | equilibrium of the written reaction | equivalent for one reaction; no advantage |
| RStoic | stoichiometry, fixed conversion | balance and duty at a chosen conversion | unsuitable, conversion would be an input (used for the burner, Section 11.4) |
| RPlug | kinetics, tube geometry, heat transfer | profiles, catalyst volume | not built in Aspen; the kinetic plug-flow model exists as an independent Python calculation (Section 10.5). Richard et al. (2024) used RPlug with an imposed heat-flux profile |

## 10.3 Baseline results and duty reconciliation

The **Aspen Plus V15 simulation** gives an NH~3~ conversion of 0.9808 at 600 °C and 20 bar. The cracked gas (S5, 197.88 kmol/h) contains 74.20 mol% H~2~, 24.73 mol% N~2~, 0.968 mol% NH~3~ and 0.101 mol% H~2~O, i.e. 146.83 kmol/h H~2~ and 1.915 kmol/h unconverted NH~3~. The isothermal duty, 1480.0 kW or 53.39 kJ per mol NH~3~ fed (1480.0 × 3.6 / 99.8), is the largest energy demand in the plant (Figure 10.3).

<!-- data: results/simulations/baseline.json kpis.nh3_conversion, kpis.reactor_duty_kW, streams.S5 -->

![**Figure 10.3.** CRACKER results of the converged baseline: outlet temperature, pressure and heat duty. The duty is the endothermic heat that the furnace must supply. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/11_reactor_results.png){width=95%}

Because the reactor is isothermal and its inlet is already at 600 °C, the duty equals the heat of reaction times the extent:

$$ Q_{\mathrm{R}} = \xi \, \Delta H_{\mathrm{r}}(T), \qquad \xi = n_{\mathrm{NH_3,in}} - n_{\mathrm{NH_3,out}} \qquad (10.2) $$

with $Q_\mathrm{R}$ in kW, $\xi$ in kmol/h and $\Delta H_\mathrm{r}$ in kJ/mol (factor 1000/3600 to kW). From the Aspen stream table $\xi$ = 99.8 − 1.91512572 = 97.88487 kmol/h; the **independent Python calculation** `amcrax.thermodynamics.reaction_enthalpy_kJ_mol(873.15)` (NASA-7 ideal gas) gives 54.2155 kJ/mol, hence $Q_\mathrm{R}$ = 1474.13 kW (Table 10.2).

Table: **Table 10.2.** Reconciliation of the cracker duty at 600 °C and 20 bar. *Source: as labelled per row.*

| Quantity | Value | Origin |
|---|---|---|
| Extent of reaction $\xi$ | 97.885 kmol/h | Aspen Plus V15 simulation (S4, S5) |
| $\Delta H_\mathrm{r}$(873.15 K), ideal gas | 54.2155 kJ/mol | independent Python calculation |
| $\xi \, \Delta H_\mathrm{r}$ | 1474.13 kW | independent Python calculation on Aspen extent |
| CRACKER duty | 1480.00 kW | Aspen Plus V15 simulation (PENG-ROB) |
| Difference | 5.87 kW (0.40 %) | arithmetic |
| Equilibrium grid, pure NH~3~, 600 °C, 20 bar: PENG-ROB / IDEAL | 53.383 / 53.170 kJ/mol fed | Aspen Plus V15 simulation |
| Python flowsheet duty, ideal gas / Peng-Robinson residual | 1474.20 / 1479.34 kW | independent Python calculation |

<!-- data: results/simulations/baseline.json streams.S4/S5 NH3; python -c amcrax.thermodynamics.reaction_enthalpy_kJ_mol(873.15); results/validation/equilibrium_aspen_grid.csv T_C=600 P_bar=20 (regenerated grid: 53.38339632 / 53.16960024); results/simulations/python_baseline.json and python_baseline_pr.json kpis.reactor_duty_kW -->

The 0.40 % gap is the real-gas enthalpy at 20 bar omitted by the ideal-gas estimate: Aspen's IDEAL and PENG-ROB equilibrium runs differ by the same 0.40 %, and the Python flowsheet closes the gap with its Peng-Robinson residual option. The full equilibrium comparison is in Section 14.

## 10.4 How the heat is supplied in practice

The model treats the 1480 kW as a duty crossing the reactor boundary; in practice the catalyst sits in furnace-heated tubes. **Published literature** examples: a fired multi-tubular Ru/Al~2~O~3~ cracker burning TSA and PSA tail gas (Kum et al., 2026); a fired Ni cracker with 96 tubes in which PSA tail gas covers the full-load duty and an NH~3~ slipstream is burned at part load (Mehr et al., 2026); tail gas burned in an external boiler with supplementary NH~3~ (Cho et al., 2026); a repurposed top-fired steam reformer (Xu et al., 2025); and induction heating (Lee et al., 2023, as cited in Hansen et al., 2024). Temperature level matters as well as quantity: a laboratory furnace at about 680-690 °C was needed to hold a 534 °C bed (Purcel et al., 2025). Whether tail-gas firing can cover the duty is examined in Sections 11.4 and 16.2.

## 10.5 Kinetic plug-flow extension

Three **published literature** rate laws are implemented in `amcrax.kinetics` (Table 10.3). Takahashi and Fujitani (2016) give a four-step microkinetic model (NH~3~ adsorption, N-H scission, N~2~ recombinative desorption, H~2~ desorption) for Ni/MgO and Ru/MgO, fitted at 1 atm and X < 20 %; steps 2 and 3 are irreversible and the rate depends on mole fractions only. Kum et al. (2026) fitted a reversible Temkin-Pyzhev law to Ru/Al~2~O~3~ data of Di Carlo et al. (2014), with partial pressures in bar. The **independent Python calculation** `amcrax.reactor.simulate_pfr` integrates a one-dimensional pseudo-homogeneous packed bed over catalyst mass $W$:

$$ \frac{dX}{dW} = \frac{r}{F_{\mathrm{NH_3},0}}, \qquad \frac{dT}{dW} = \frac{-\Delta H_\mathrm{r}(T)\, r + U \frac{4}{D_t}\,(T_w - T)/\rho_\mathrm{bed}}{\sum_i F_i\, c_{p,i}(T)}, \qquad \frac{dP}{dW} = \frac{(dP/dz)_\mathrm{Ergun}}{\rho_\mathrm{bed} A} \qquad (10.3) $$

where $X$ is the NH~3~ conversion, $r$ the rate (mol NH~3~ kg~cat~^−1^ s^−1^), $F$ molar flows (mol/s), $\Delta H_\mathrm{r}$ the reaction enthalpy (J/mol), $U$ the overall heat-transfer coefficient (W/(m^2^ K)), $D_t$ the tube diameter (m), $T_w$ the wall temperature (K), $\rho_\mathrm{bed}$ the bed density (kg/m^3^), $c_{p,i}$ ideal-gas heat capacities (J/(mol K)) and $A$ the total tube cross-section (m^2^). Energy modes: isothermal, adiabatic ($U$ = 0) or wall-heated. Bed data follow Kum et al. (2026, Table 1); 40 tubes of 0.126 m are an **engineering assumption**.

**Validation.** Rate constants at 500 °C reproduce Takahashi and Fujitani's Table 2 within −6.8 % to +0.1 %. The source gives no catalyst mass, so W/F was inferred from one anchor point per catalyst (Ni 500 °C, Ru 450 °C; disclosed assumption). The temperature dependence agrees within −4.9 to +1.0 percentage points (pp), but conversion is under-predicted by up to 11.1 pp at low NH~3~ partial pressure and with H~2~ co-feed (Figure 10.4). The Kum law matches the Di Carlo data at 500 °C, 1-10 bar, within +0.4 pp (Di Carlo et al., 2014, as cited in Maccarrone et al., 2025), a consistency check only because it was fitted to them.

**Catalyst demand.** At the baseline (600 °C, 20 bar, 99.8 kmol/h NH~3~, equilibrium conversion 0.9809), 99 % of equilibrium conversion needs 112.7 kg Ni/MgO against 25.2 kg Ru/MgO, a factor of 4.5 (Table 10.3, Figure 10.5). At lower temperature the Ni demand grows to 4968 kg at 475 °C (99 %), where the bed already loses 8.85 bar; at 400-450 °C neither 95 % nor 99 % of equilibrium is reached before the outlet pressure falls below 5 % of the inlet (hydraulic limit), so no mass is reported there.

**Limits.** All 20 bar results extrapolate kinetics fitted at 1 atm (Takahashi) or ≤ 10 bar and ≤ 450 °C (Kum). The factor $(1 - Q/K_p)$ that makes the Takahashi laws vanish at equilibrium is an AmCraX **engineering assumption**. Neglected intraparticle diffusion, radial gradients and deactivation make the masses lower bounds. Heat transfer, not kinetics, limits a real bed: in **illustrative examples** with 221.9 kg Ru/Al~2~O~3~, an adiabatic bed from 600 °C stops at X = 0.276 and 312.8 °C, and a wall-heated bed (650 °C wall, assumed U = 60 W/(m^2^ K)) reaches only X = 0.358.

<!-- data: backend/amcrax/data/kinetics.yaml catalysts.*.validity, source; results/validation/kinetics_validation.csv (Table2 deviations -0.0683..+0.0010; fig3a/4a predictions -0.0493..+0.0097; fig3b/4b/5a/5b down to -0.1113; dicarlo +0.0005/+0.0027/+0.0039; W/F_total Ni 2499.447, Ru 2417.356 g s/mol); results/simulations/pfr_baseline.json cases.*@600C X_eq, W_95pct_eq_kg, W_99pct_eq_kg, at_W99; cases.ru_kum_temkin_pyzhev@600C_adiabatic/_external outlet; assumptions (n_tubes 40); results/sensitivity/pfr_temperature_sweep.csv (Ni W_99pct_eq_kg 4968.12 at 475 degC; NaN with hydraulic-limit reason at 400-450 degC); results/validation/pfr_fix_note.md (all baseline masses and kinetics_validation.csv unchanged) -->

Table: **Table 10.3.** Implemented rate laws and catalyst mass to reach 95 % and 99 % of equilibrium conversion at 600 °C and 20 bar (isothermal). *Source: rate laws and validity from published literature as cited; masses are an independent Python calculation (results/simulations/pfr_baseline.json).*

| Rate law (catalyst) | Form | Source | Fitted / validated range | W~95~ (kg) | W~99~ (kg) | ΔP at W~99~ (bar) |
|---|---|---|---|---|---|---|
| 30 wt% Ni/MgO | microkinetic, irreversible, mole-fraction basis | Takahashi and Fujitani (2016), pp. 2-5, Table 1 p. 4 | 350-450 / 500-650 °C, 1 atm | 73.5 | 112.7 | 0.199 |
| 5 wt% Ru/MgO | as above | Takahashi and Fujitani (2016), Table 1 p. 4 | 300-400 / 450-550 °C, 1 atm | 17.9 | 25.2 | 0.043 |
| 8 wt% Ru/Al~2~O~3~ | Temkin-Pyzhev, reversible, bar | Kum et al. (2026), Eqs. 2-4 p. 4, Table 1 p. 5 | 350-450 °C, 1-10 bar | 8.9 | 11.1 | 0.019 |

![**Figure 10.4.** Takahashi Ni/MgO (top) and Ru/MgO (bottom) microkinetics against the published conversions: temperature (left), NH~3~ partial-pressure (centre) and H~2~ co-feed series (right), with and without the AmCraX $(1-Q/K)$ factor. The temperature trend is reproduced from one anchor point; conversion is under-predicted in Ar-diluted and H~2~ co-fed gas. *Source: independent Python calculation; data points from Takahashi and Fujitani (2016), Figs. 3-5, read from figures.*](../../results/figures/kinetics_validation.png){width=100%}

![**Figure 10.5.** Catalyst mass for 99 % (solid) and 95 % (dotted) of equilibrium conversion versus isothermal bed temperature at 20 bar, 100 kmol/h feed, log scale. Ru needs several times less catalyst than Ni and the demand rises steeply as temperature falls (Ru/MgO, 99 %: 25.2 kg at 600 °C, 164.8 kg at 500 °C), so the cracker temperature is a catalyst-cost decision as well as an equilibrium one. *Source: independent Python calculation with kinetics extrapolated to 20 bar.*](../../results/figures/pfr_catalyst_mass_vs_T.png){width=85%}
