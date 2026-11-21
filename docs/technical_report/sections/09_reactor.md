<!-- cites: hansen2024hysys, farokhi2025costoptimization, richard2024technoeconomic, cho2026nickel, kum2026heatintegrated, mehr2026highcapacity, xu2025review, purcel2024stability, lee2023carbonfree -->

# 9 Reactor configuration

## 9.1 Why an equilibrium reactor first

Ammonia decomposition, NH~3~ ⇌ 0.5 N~2~ + 1.5 H~2~, is endothermic and increases the number of moles, so equilibrium conversion rises with temperature and falls with pressure (Section 3). An equilibrium reactor gives the thermodynamic ceiling on conversion and the matching heat demand without any catalyst data. Both quantities drive every downstream result: hydrogen production, residual NH~3~, tail-gas heating value and furnace duty. Gibbs reactors are the usual first-level cracker model in published flowsheets (Farokhi et al., 2025; Hansen et al., 2024). Catalyst mass, residence time, axial profiles and pressure drop need a kinetic model; AmCraX treats them in a separate Python model (Section 14).

## 9.2 Gibbs-energy minimisation

RGibbs minimises the total Gibbs energy of the outlet at the specified temperature and pressure, subject to the element balances:

$$ \min_{n_i \ge 0} \; G = \sum_{i} n_i \left[ g_i^{\circ}(T) + RT \ln \frac{\hat{\varphi}_i \, y_i \, P}{P^{\circ}} \right] \quad \text{s.t.} \quad \sum_i a_{ki}\, n_i = b_k \;\; (k = \mathrm{N}, \mathrm{H}, \mathrm{O}) \qquad (9.1) $$

where $n_i$ is the outlet molar flow of species $i$ (kmol/h), $g_i^{\circ}(T)$ its standard molar Gibbs energy at temperature $T$ (J/mol, $T$ in K), $R$ = 8.314 J/(mol K), $y_i$ the mole fraction (-), $\hat{\varphi}_i$ the fugacity coefficient from the property method (-), $P$ the pressure (bar), $P^{\circ}$ = 1 bar, $a_{ki}$ the number of atoms of element $k$ in species $i$ and $b_k$ the element flow fed (kmol/h). No stoichiometry is entered: the product list defines the species over which $G$ is minimised. With the global PENG-ROB method (Section 8), $\hat{\varphi}_i$ comes from the Peng-Robinson equation of state.

## 9.3 Specification

CRACKER is isothermal at 600 °C and 20 bar, with the calculation option "phase equilibrium and chemical equilibrium" (Figure 9.1). The products are NH~3~, H~2~, N~2~ and H~2~O (Figure 9.2). O~2~ is excluded, so no oxygen-containing species other than water can form and the 0.2 kmol/h of feed water leaves unchanged. Calculator TLINK sets the HEATER outlet to the cracker temperature and the FEHE cold outlet to the cracker temperature minus 50 K, so one temperature input moves all three consistently (Section 6). Table 9.1 compares RGibbs with the other Aspen reactor blocks.

<!-- data: aspen/models/baseline.inp BLOCK CRACKER (TEMP=600, PRES=20, PROD NH3/H2/N2/H2O), CALCULATOR TLINK; results/simulations/baseline.json streams.S4/S5.component_mole_flow_kmol_h.H2O = 0.2 -->

![**Figure 9.1.** CRACKER (RGibbs) specifications: chemical and phase equilibrium at 20 bar and 600 °C, heat duty calculated. Temperature and pressure alone fix the equilibrium conversion of the isothermal reactor, so these two fields are the reactor design variables of the Aspen model. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/05_reactor_setup.png){width=95%}

![**Figure 9.2.** CRACKER products tab: "Identify possible products" with NH~3~, H~2~, N~2~ and H~2~O in the mixed phase. For RGibbs this list replaces a reaction equation; leaving O~2~ out keeps the trace feed water inert. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/06_reactor_products.png){width=95%}

Table: **Table 9.1.** Choice of the Aspen reactor block for the cracker. *Source: engineering assessment; literature usage as cited.*

| Block | Needs | Gives | Use in AmCraX |
|---|---|---|---|
| RGibbs | T, P, product list | equilibrium composition and duty | **selected**: thermodynamic limit without a reaction list; also used by Hansen et al. (2024) and Farokhi et al. (2025) |
| REquil | stoichiometry, T, P | equilibrium of the written reactions | equivalent for a single reaction; no advantage |
| RStoic | stoichiometry and a fixed conversion | balance and duty at the chosen conversion | unsuitable, because conversion would become an input; used for the burner (Section 10) |
| RPlug | kinetics, tube geometry, heat-transfer specification | axial profiles, catalyst volume | **not built in Aspen**; the kinetic plug-flow reactor is an independent Python model (Section 14). Richard et al. (2024) used RPlug with an imposed heat-flux profile |

## 9.4 Baseline results and duty reconciliation

The **Aspen Plus V15 simulation** gives an NH~3~ conversion of 0.9808 at 600 °C and 20 bar. The cracked gas S5 (197.885 kmol/h) contains 74.20 mol% H~2~, 24.73 mol% N~2~, 0.968 mol% NH~3~ and 0.101 mol% H~2~O, that is 146.83 kmol/h H~2~ and 1.915 kmol/h unconverted NH~3~. The duty, 1480.0 kW or 53.39 kJ per mol NH~3~ fed, is the largest energy demand of the plant (Figure 9.3).

<!-- data: results/simulations/baseline.json kpis.nh3_conversion 0.98081, kpis.reactor_duty_kW 1479.99984, streams.S5 (mole_flow_kmol_h 197.884874, mole_frac, component_mole_flow_kmol_h); 1479.99984 x 3.6 / 99.8 = 53.387 kJ/mol -->

![**Figure 9.3.** CRACKER results of the converged baseline: outlet at 600 °C and 20 bar, heat duty 1480 kW, one vapour phase. The duty is the endothermic heat that a real furnace must deliver at reactor temperature. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/11_reactor_results.png){width=95%}

Because the feed S4 already enters at 600 °C, the isothermal duty is the heat of reaction times the extent:

$$ Q_{\mathrm{R}} = \frac{1000}{3600}\,\xi \, \Delta H_{\mathrm{r}}(T), \qquad \xi = n_{\mathrm{NH_3,S4}} - n_{\mathrm{NH_3,S5}} \qquad (9.2) $$

with $Q_\mathrm{R}$ in kW, $\xi$ the extent of reaction (kmol/h) and $\Delta H_\mathrm{r}$ the reaction enthalpy per mol NH~3~ (kJ/mol). From the Aspen stream table $\xi$ = 99.8 - 1.9151 = 97.885 kmol/h. The **independent Python calculation** of $\Delta H_\mathrm{r}$(873.15 K) with NASA-7 ideal-gas data (Section 13) gives 54.216 kJ/mol and hence $Q_\mathrm{R}$ = 1474.13 kW (Table 9.2).

Table: **Table 9.2.** Reconciliation of the cracker duty at 600 °C and 20 bar. *Source: as labelled per row.*

| Quantity | Value | Origin |
|---|---|---|
| Extent of reaction $\xi$ | 97.885 kmol/h | Aspen Plus V15 simulation (S4, S5) |
| $\Delta H_\mathrm{r}$(873.15 K), ideal gas | 54.216 kJ/mol | independent Python calculation |
| $\xi \, \Delta H_\mathrm{r}$, Eq. (9.2) | 1474.13 kW | Python enthalpy on the Aspen extent |
| CRACKER duty | 1480.00 kW | Aspen Plus V15 simulation (PENG-ROB) |
| Difference | 5.87 kW (0.40 %) | arithmetic |
| Pure-NH~3~ RGibbs grid at 600 °C, 20 bar: PENG-ROB / IDEAL | 53.383 / 53.170 kJ/mol fed (ratio 1.0040) | Aspen Plus V15 simulation |
| Python flowsheet duty, ideal gas / Peng-Robinson residual | 1474.20 / 1479.34 kW | independent Python calculation |

<!-- data: results/simulations/baseline.json streams.S4/S5.component_mole_flow_kmol_h.NH3 (99.8, 1.91512572), blocks.CRACKER.duty_kW; amcrax.thermodynamics.reaction_enthalpy_kJ_mol(873.15) = 54.2155 (= results/validation/equilibrium_python_grid.csv T_C=600 dH_rxn_kJ_per_mol_NH3); results/validation/equilibrium_aspen_grid.csv T_C=600 P_bar=20 heat_duty_kJ_per_mol_NH3_fed 53.38339632 (PENG-ROB), 53.16960024 (IDEAL); results/simulations/python_baseline.json and python_baseline_pr.json kpis.reactor_duty_kW 1474.2014, 1479.3404 -->

The 0.40 % difference is consistent with the real-gas enthalpy at 20 bar that the ideal-gas estimate omits: Aspen's own IDEAL and PENG-ROB runs of the same equilibrium differ by the same 0.40 %, and the Python flowsheet comes within 0.05 % of the Aspen duty (1479.34 against 1480.00 kW) once its Peng-Robinson residual enthalpy is switched on. The reactor duty is therefore reproduced by an independent calculation, which is the basis of the passing FS-PRIMARY items (Section 16).

## 9.5 How a real cracker supplies the heat

The model treats the 1480 kW as a duty crossing the reactor boundary at 600 °C. In practice the catalyst sits in tubes heated by a furnace or another source. **Published literature** examples are a fired multi-tubular Ru/Al~2~O~3~ cracker burning TSA and PSA tail gas (Kum et al., 2026); a fired Ni cracker in which the PSA tail gas covers the full-load duty and an NH~3~ slipstream is burned at part load (Mehr et al., 2026); tail gas burned in an external boiler with supplementary NH~3~ (Cho et al., 2026); a repurposed top-fired steam reformer (Xu et al., 2025); and induction heating (Lee et al., 2023, as cited in Hansen et al., 2024). The temperature level matters as well as the quantity: a laboratory furnace at about 680-690 °C was needed to hold a Ni bed at 534 °C (Purcel et al., 2025). Section 10 shows how much of the duty the AmCraX tail gas can cover on a first-law basis, and Section 18 tests whether that heat is available at the required temperature.
