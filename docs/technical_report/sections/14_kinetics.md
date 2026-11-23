<!-- cites: takahashi2016kinetic, kum2026heatintegrated, dicarlo2014ammonia, maccarrone2025comprehensive, richard2024technoeconomic, smith_grimech30, goodwin2018cantera -->

# 14 Catalyst kinetics

## 14.1 Scope

The Aspen cracker is an equilibrium reactor (Section 9) and says nothing about the catalyst needed to approach equilibrium. AmCraX therefore adds a kinetic plug-flow reactor in Python (`amcrax.kinetics`, `amcrax.reactor`). **Every result in this section is an independent Python calculation** built on **published literature** rate laws, whose parameters, units and page references are kept in `backend/amcrax/data/kinetics.yaml`.

## 14.2 Rate laws

**Temkin-Pyzhev, Ru/Al~2~O~3~.** Kum et al. (2026, p. 4, Eq. 2) fitted a reversible Temkin-Pyzhev law to the commercial Ru/Al~2~O~3~ data of Di Carlo et al. (2014):

$$ r = k_0\exp\!\left(-\frac{E_a}{RT}\right)\left[\left(\frac{p_{\mathrm{NH_3}}^2}{p_{\mathrm{H_2}}^3}\right)^{\beta} - \frac{p_{\mathrm{N_2}}}{K_{eq}^2}\left(\frac{p_{\mathrm{H_2}}^3}{p_{\mathrm{NH_3}}^2}\right)^{1-\beta}\right] \qquad (14.1) $$

with $r$ in mol NH~3~/(g~cat~ s), partial pressures $p_i$ in bar, $T$ in K, $R$ = 8.314 J/(mol K), $k_0$ = 55245.9 mol/(g~cat~ s bar^0.27^), $E_a$ = 114224 J/mol and $\beta$ = 0.27 (Kum et al., 2026, p. 5, Table 1). The fit covers 36 points at 350-450 °C and 1-10 bar with a mean absolute percentage error of 0.81 % (p. 9). The source gives $\Delta G_r = 95117 - 193.67\,T - 0.035293\,T^2 + 9.22\times10^{-6}\,T^3$ without a unit (Eqs. 3-4, p. 4). AmCraX reads it as J per 2 mol NH~3~ and sets $K_{eq}^2 = \exp(-\Delta G_r/RT)$, the only reading for which the bracket vanishes at equilibrium (**engineering assumption**). The law is singular at $p_\mathrm{H_2}$ = 0, so a pure-NH~3~ feed starts at $X$ = 10^-6^.

**Microkinetics, Ni/MgO and Ru/MgO.** Takahashi and Fujitani (2016, pp. 2-5) lump the mechanism into four steps on sites $s$: NH~3~ adsorption (equilibrated), irreversible dehydrogenation NH~3~(a) + 3s → N(a) + 3H(a), irreversible N~2~ desorption and reversible H~2~ desorption. With coverages $\theta$ and mole fractions $p_i/P$:

$$ r_1 = k_1\frac{p_\mathrm{NH_3}}{P}\theta_s - k_{-1}\theta_\mathrm{NH_3},\quad r_2 = k_2\theta_\mathrm{NH_3}\theta_s^3,\quad r_3 = k_3\theta_\mathrm{N}^2,\quad r_4 = k_4\theta_\mathrm{H}^2 - k_{-4}\frac{p_\mathrm{H_2}}{P}\theta_s^2 \qquad (14.2) $$

$$ \theta_s + \theta_\mathrm{NH_3} + \theta_\mathrm{N} + \theta_\mathrm{H} = 1,\qquad r_1 = r_2 = 2r_3 = \tfrac{2}{3}r_4,\qquad r_\mathrm{NH_3} = r_2 \qquad (14.3) $$

$$ k_i = A_i\exp\!\left(-\frac{E_{a,i}}{RT}\right),\quad k_1 = A_1,\quad K_1 = A_5\exp\!\left(-\frac{E_{a,5}}{RT}\right),\quad K_4 = A_6\exp\!\left(-\frac{E_{a,4}}{RT}\right) $$

$$ k_{-1} = \frac{k_1}{K_1},\qquad k_{-4} = \frac{k_4}{K_4} \qquad (14.4) $$

where $r_j$ are step rates (mol/(g~cat~ s)), $k_j$ rate constants (mol/(g~cat~ s)), $K_1$ and $K_4$ dimensionless equilibrium constants, $P$ the total pressure and $A$, $E_a$ the Arrhenius parameters of Table 14.1. For a given vacant fraction $\theta_s$ the quasi-steady-state relations give the other coverages explicitly; the site balance is then solved for $\ln\theta_s$. Because only $p_i/P$ enters, the model has no intrinsic total-pressure dependence. Power-law and Langmuir-Hinshelwood forms (Maccarrone et al., 2025) were not implemented.

Table: **Table 14.1.** Implemented kinetic parameters. *Source: published literature as cited (backend/amcrax/data/kinetics.yaml); not AmCraX results.*

| Parameter | Unit | Ni/MgO (30 wt%) | Ru/MgO (5 wt%) | Reference |
|---|---|---|---|---|
| $A_1$ | mol/(g s) | 75.5 | 83.6 | Takahashi and Fujitani (2016), p. 4, Table 1 |
| $A_2$; $E_{a,2}$ | mol/(g s); kJ/mol | 7.54 × 10^15^; 144.0 | 1.34 × 10^14^; 105.8 | as above |
| $A_3$; $E_{a,3}$ | mol/(g s); kJ/mol | 3.12 × 10^6^; 127.8 | 6.26 × 10^5^; 123.5 | as above |
| $A_4$; $E_{a,4}$ | mol/(g s); kJ/mol | 3.92 × 10^4^; 109.0 | 7.18 × 10^2^; 67.8 | as above |
| $A_5$; $E_{a,5}$ ($K_1$) | -; kJ/mol | 2.26 × 10^-14^; -79.4 | 3.49 × 10^-13^; -64.0 | as above |
| $A_6$ ($K_4$) | - | 4.13 × 10^6^ | 1.51 × 10^4^ | as above |
| Fitted / validated range | | 350-450 / 500-650 °C, 1 atm, X < 20 % in fit | 300-400 / 450-550 °C, 1 atm | p. 5, Figs. 1-5 |
| Ru/Al~2~O~3~ (8 wt%): $k_0$; $E_a$; $\beta$ | mol/(g s bar^0.27^); J/mol; - | 55245.9; 114224; 0.27 | | Kum et al. (2026), p. 5, Table 1; 350-450 °C, 1-10 bar |

**Units.** Source rates in mol/(g~cat~ s) are multiplied by 1000 to give mol/(kg~cat~ s); Takahashi's activation energies are converted from kJ/mol to J/mol. Pressures enter Eqs. (14.2)-(14.3) as ratios, so atm and bar give the same rate, and the unit of $k_0$ makes Eq. (14.1) consistent in bar. Both sources use $R$ = 8.314 J/(mol K); $T$ in kelvin reproduces Takahashi's Table 2.

**Equilibrium-approach factor (AmCraX extension).** Steps 2 and 3 are irreversible in the source, acceptable at 1 atm far from equilibrium; at 20 bar the law would predict conversion above equilibrium. AmCraX therefore multiplies the Takahashi rates by

$$ r_\mathrm{AmCraX} = r_\mathrm{published}\left(1 - \frac{Q}{K_p(T)}\right), \qquad Q = \frac{(p_\mathrm{N_2}/p^\circ)^{1/2}(p_\mathrm{H_2}/p^\circ)^{3/2}}{p_\mathrm{NH_3}/p^\circ} \qquad (14.5) $$

with $K_p$ from Section 13 and $p^\circ$ = 1 bar. This factor is an **engineering assumption**, not part of any source; it is on by default and can be switched off.

<!-- data: backend/amcrax/data/kinetics.yaml catalysts.*.parameters, validity, equilibrium_constant, equilibrium_approach_factor, unit_conversions; backend/amcrax/kinetics/rate_laws.py takahashi_constants, takahashi_coverages, rate_mol_per_kgcat_s, kum_keq -->

## 14.3 Plug-flow reactor model

`amcrax.reactor.simulate_pfr` integrates a one-dimensional pseudo-homogeneous packed bed over the catalyst mass $W$ (kg):

$$ \frac{dX}{dW} = \frac{r}{F_{\mathrm{NH_3},0}},\qquad \frac{dT}{dW} = \frac{-\Delta H_\mathrm{r}(T)\, r + U \frac{4}{D_t}\,(T_w - T)/\rho_\mathrm{bed}}{\sum_i F_i\, c_{p,i}(T)},\qquad \frac{dP}{dW} = \frac{(dP/dz)_\mathrm{Ergun}}{\rho_\mathrm{bed} A} \qquad (14.6) $$

$$ \left(\frac{dP}{dz}\right)_\mathrm{Ergun} = -\frac{G}{\rho_g d_p}\,\frac{1-\varepsilon_b}{\varepsilon_b^3}\left[\frac{150\,(1-\varepsilon_b)\,\mu}{d_p} + 1.75\,G\right] \qquad (14.7) $$

where $X$ is the NH~3~ conversion (-), $r$ the rate (mol NH~3~/(kg~cat~ s)), $F_i$ molar flows (mol/s), $\Delta H_\mathrm{r}$ the reaction enthalpy (J/mol), $c_{p,i}$ ideal-gas heat capacities (J/(mol K)) from Section 13, $U$ the overall heat-transfer coefficient (W/(m^2^ K)), $D_t$ the tube diameter (m), $T_w$ the wall temperature (K), $\rho_\mathrm{bed} = (1-\varepsilon_b)\rho_p$ the bed density (kg/m^3^), $A$ the total tube cross-section (m^2^), $G$ the mass flux (kg/(m^2^ s)), $\rho_g$ the ideal-gas density (kg/m^3^), $d_p$ the particle diameter (m), $\varepsilon_b$ the bed voidage (-) and $\mu$ the gas viscosity (Pa s, Cantera mixture-averaged with GRI-Mech 3.0 transport data; Goodwin et al., 2018; Smith et al., n.d.); $P$ is converted from Pa/m to bar. The energy balance has three modes: isothermal ($dT/dW$ = 0), adiabatic ($U$ = 0) and wall-heated. Flows follow from $X$ by stoichiometry, so the element balances hold by construction. Bed data are $\varepsilon_b$ = 0.36, $\rho_p$ = 980 kg/m^3^, $d_p$ = 0.6 mm and $D_t$ = 0.126 m (Kum et al., 2026, p. 5, Table 1), also used for the Takahashi powders; 40 parallel tubes are an **engineering assumption**. The integration stops when the pressure falls below 5 % of the inlet value (hydraulic limit).

<!-- data: backend/amcrax/reactor/pfr.py (module docstring, DEFAULT_BED, simulate_pfr rhs, low_p event); results/simulations/pfr_baseline.json assumptions (n_tubes 40) -->

## 14.4 Validation against published data

The rate constants from Takahashi's Table 1 reproduce his Table 2 at 500 °C within -6.8 % to +0.1 % (12 values), consistent with rounding in the source. The reactor predictions are weaker (Figure 14.1, Table 14.2). The source reports no catalyst mass, so W/F was inferred from one anchor point per catalyst (Ni 500 °C, Ru 450 °C; 2499.45 and 2417.36 g s/mol), a disclosed assumption. The temperature series is then reproduced within -4.9 to +1.0 percentage points (pp), but conversion is under-predicted by up to 11.0 pp (Ni) and 11.1 pp (Ru) with Ar dilution or H~2~ co-feed. Six of 12 Ni and six of 11 Ru points fall outside the 0.05 tolerance (an engineering assumption): **both items fail**. The Kum law matches the Di Carlo data at 500 °C and 1-10 bar within +0.4 pp (Di Carlo et al., 2014, as cited in Maccarrone et al., 2025), but it was fitted to them, so this check is informational only.

Table: **Table 14.2.** Kinetic validation summary. *Source: independent Python calculation (results/validation/kinetics_validation.csv); literature values from Takahashi and Fujitani (2016, Tables 2 and Figs. 3-5, read from figures) and Maccarrone et al. (2025, Table 2).*

| Data set | Points | Deviation (model - literature) | Outside tolerance | Matrix status |
|---|---|---|---|---|
| Rate constants, Table 2, 500 °C (Ni, Ru) | 12 | -6.8 % to +0.1 % | 0 of 12 (10 %) | KIN-TABLE2 pass |
| Ni/MgO conversion, Figs. 3a, 3b, 5a | 12 | -0.110 to +0.010 | 6 of 12 (0.05) | KIN-NI-PRED fail |
| Ru/MgO conversion, Figs. 4a, 4b, 5b | 11 | -0.111 to +0.007 | 6 of 11 (0.05) | KIN-RU-PRED fail |
| Ru/Al~2~O~3~, Di Carlo, 500 °C, 1/5/10 bar | 3 | +0.0005 / +0.0027 / +0.0039 | 0 of 3 (0.01) | KIN-DICARLO informational |

<!-- data: results/validation/kinetics_validation.csv (Table2 deviations -0.0683 ... +0.0010; fig3a predictions +0.0012, -0.0039, +0.0097; fig4a -0.0493, +0.0006; fig3b 0.25 atm -0.1096; fig5b 0.7 atm -0.1113; dicarlo deviations; W/F_total 2499.447 and 2417.356 g s/mol); results/validation/validation_matrix.json KIN-TABLE2, KIN-NI-PRED, KIN-RU-PRED, KIN-DICARLO -->

![**Figure 14.1.** Takahashi Ni/MgO (top) and Ru/MgO (bottom) microkinetics against published conversions: temperature (left), NH~3~ partial pressure (centre) and H~2~ co-feed (right) at 1 atm, with and without the AmCraX $(1-Q/K)$ factor. The temperature trend is reproduced from one anchor point, but conversion is under-predicted in Ar-diluted and H~2~-co-fed gas. *Source: independent Python calculation; data points from Takahashi and Fujitani (2016), Figs. 3-5, read from figures.*](../../results/figures/kinetics_validation.png){width=100%}

## 14.5 Catalyst demand

At the baseline (600 °C, 20 bar, 99.8 kmol/h NH~3~ and 0.2 kmol/h H~2~O, isothermal, ideal-gas equilibrium conversion 0.9809), 99 % of equilibrium conversion needs 112.7 kg Ni/MgO against 25.2 kg Ru/MgO, a factor of 4.5 (Table 14.3). The pressure drop at these masses is below 0.2 bar. The demand rises steeply as the temperature falls (Figure 14.2). For Ru/MgO the 99 % mass grows from 25.2 kg at 600 °C to 164.8 kg at 500 °C and 566.5 kg at 450 °C. For Ni it reaches 2064 kg at 500 °C and 4968 kg at 475 °C, where the bed already loses 8.85 bar. This 475 °C value was missing in the first edition; fixing the handling of the hydraulic stop produced it and changed no other mass (`results/validation/pfr_fix_note.md`). At 400-450 °C Ni reaches neither 95 % nor 99 % of equilibrium before the hydraulic stop (at 450 °C: 8139 kg, X = 0.844). The cracker temperature is thus a catalyst-cost decision as well as an equilibrium one.

<!-- data: results/simulations/pfr_baseline.json cases.*@600C (X_eq 0.98086, W_95pct_eq_kg, W_99pct_eq_kg, at_W99.pressure_drop_bar), ru_takahashi_microkinetic@500C/@450C; results/sensitivity/pfr_temperature_sweep.csv (Ni 500 degC W99 2063.66, 475 degC W99 4968.12; NaN at 400-450 degC); results/validation/pfr_fix_note.md (8.85 bar, stop 8139.0 kg at X 0.844 at 450 degC; all other masses unchanged) -->

Table: **Table 14.3.** Catalyst mass to reach 95 % and 99 % of equilibrium conversion, isothermal, 20 bar, 100 kmol/h feed, 40 tubes. *Source: independent Python calculation with kinetics extrapolated to 20 bar (results/simulations/pfr_baseline.json, results/sensitivity/pfr_temperature_sweep.csv).*

| Catalyst (rate law) | T (°C) | W~95~ (kg) | W~99~ (kg) | ΔP at W~99~ (bar) | Inside fitted T range |
|---|---|---|---|---|---|
| Ni/MgO (microkinetic) | 600 | 73.5 | 112.7 | 0.199 | yes (1 atm only) |
| Ru/MgO (microkinetic) | 600 | 17.9 | 25.2 | 0.043 | no |
| Ru/Al~2~O~3~ (Temkin-Pyzhev) | 600 | 8.9 | 11.1 | 0.019 | no |
| Ru/MgO (microkinetic) | 500 | 112.4 | 164.8 | 0.237 | yes (1 atm only) |
| Ru/Al~2~O~3~ (Temkin-Pyzhev) | 500 | 63.0 | 80.1 | 0.113 | no |
| Ru/Al~2~O~3~ (Temkin-Pyzhev) | 450 | 199.2 | 257.6 | 0.325 | yes (up to 10 bar) |
| Ni/MgO (microkinetic) | 475 | 3526.9 | 4968.1 | 8.85 | yes (1 atm only) |

<!-- data: results/simulations/pfr_baseline.json cases (W_95pct_eq_kg, W_99pct_eq_kg, at_W99.pressure_drop_bar); results/sensitivity/pfr_temperature_sweep.csv within_fitted_T_range; results/validation/pfr_fix_note.md (475 degC dP 8.85 bar) -->

![**Figure 14.2.** Catalyst mass for 99 % (solid) and 95 % (dotted) of equilibrium conversion versus isothermal bed temperature at 20 bar, 100 kmol/h feed, logarithmic scale. Ru needs several times less catalyst than Ni, and the Ni curve ends at 475 °C because lower temperatures hit the hydraulic limit first. *Source: independent Python calculation with kinetics extrapolated to 20 bar.*](../../results/figures/pfr_catalyst_mass_vs_T.png){width=85%}

Heat transfer, not kinetics, limits a real bed. In **illustrative examples** with 221.9 kg Ru/Al~2~O~3~ (20 times the isothermal W~99~), an adiabatic bed from 600 °C stops reacting at X = 0.276 and 312.8 °C, and a wall-heated bed (650 °C wall, U = 60 W/(m^2^ K), a gas-gas exchanger value from Richard et al. (2024, Table 1), not a furnace-tube value) reaches only X = 0.358.

<!-- data: results/simulations/pfr_baseline.json cases.ru_kum_temkin_pyzhev@600C_adiabatic.outlet (conversion 0.27636, T_C 312.80), @600C_external (conversion 0.35828, T_wall 650, U 60, note); W_kg 221.8818 = 20 x 11.0941 -->

## 14.6 Limits

All 20 bar results extrapolate kinetics fitted at 1 atm (Takahashi) or at most 10 bar and 450 °C (Kum). The approach factor of Eq. (14.5) and the $K_{eq}$ reading of Eq. (14.1) are AmCraX assumptions. The model neglects intraparticle diffusion (effectiveness factor 1, although the Takahashi rates were measured on powders), external transfer, radial gradients, axial dispersion, non-ideal gas behaviour in the energy balance and deactivation, so the catalyst masses are lower bounds. Two of the four kinetic validation items fail, and no kinetic result enters the Aspen flowsheet or the economics.
