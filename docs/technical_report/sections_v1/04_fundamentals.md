<!-- cites: takahashi2016kinetic, su2023review, maccarrone2025comprehensive, xu2025review, cechetto2023membrane, kum2026heatintegrated, cho2026nickel, purcel2024stability, richard2024technoeconomic, nist_janaf, smith_grimech30, goodwin2018cantera, dicarlo2014ammonia, ganley2004apriori, sayas2020high -->

# 4 Ammonia-cracking fundamentals

## 4.1 Stoichiometry and atom balance

AmCraX writes the cracking reaction per mole of ammonia:

$$ \mathrm{NH_3} \rightleftharpoons \tfrac{1}{2}\,\mathrm{N_2} + \tfrac{3}{2}\,\mathrm{H_2} \qquad (4.1) $$

Papers that use 2NH~3~ ⇌ N~2~ + 3H~2~ quote enthalpies and equilibrium constants per 2 mol NH~3~. The element balances are

$$ n_{\mathrm{N,in}} = n_{\mathrm{NH_3}} + 2n_{\mathrm{N_2}}, \qquad n_{\mathrm{H,in}} = 3n_{\mathrm{NH_3}} + 2n_{\mathrm{H_2}} \qquad (4.2) $$

where $n_i$ is the outlet molar flow of species $i$ (kmol/h). The number of gas moles rises from 1 to 2 per mole converted (Δν = +1), so pressure works against conversion. Feed water (0.2 mol%) is inert in the cracker.

## 4.2 Reaction enthalpy and equilibrium constant

The AmCraX thermodynamics package (**independent Python calculation**; GRI-Mech 3.0 NASA-7 polynomials, Smith et al., n.d., loaded through Cantera, Goodwin et al., 2018) gives Δ*H*°~298~ = +45.898 kJ/mol NH~3~ and Δ*G*°~298~ = +16.367 kJ/mol NH~3~. Its tests check these against NIST-JANAF (National Institute of Standards and Technology, n.d.) within 0.05 kJ/mol, and log~10~ *K* within 0.01 from 400 to 1500 K; all 22 tests in `tests/test_thermodynamics.py` passed. Published values are 45.6 (Cho et al., 2026, p. 2; Xu et al., 2025, p. 5, as 91.2 kJ per 2 mol), 45.92 (Cechetto et al., 2023, p. 10777), 45.984 (Maccarrone et al., 2025, p. 3) and 46.11 kJ/mol NH~3~ (Kum et al., 2026, p. 5).
<!-- data: tests/test_thermodynamics.py (test_formation_and_reaction_enthalpy_298, test_species_vs_janaf, test_equilibrium_constant_vs_janaf_logKf); pytest run 22 passed -->

$$ \Delta H_r(T) = \Delta H_r^\circ(298.15\,\mathrm{K}) + \int_{298.15}^{T} \Delta c_p\,\mathrm{d}T, \qquad \Delta c_p = \tfrac{1}{2}c_{p,\mathrm{N_2}} + \tfrac{3}{2}c_{p,\mathrm{H_2}} - c_{p,\mathrm{NH_3}} \qquad (4.3) $$

$$ K(T) = \exp\!\left(-\frac{\Delta G_r^\circ(T)}{RT}\right), \qquad \frac{\mathrm{d}\ln K}{\mathrm{d}T} = \frac{\Delta H_r^\circ(T)}{RT^2} \qquad (4.4) $$

Δ*H*~r~ is the reaction enthalpy (kJ/mol NH~3~), *c*~p,i~ the ideal-gas heat capacity (J/(mol K)), Δ*G*°~r~ the standard Gibbs energy of reaction (J/mol NH~3~), *K* the dimensionless equilibrium constant (*p*° = 1 bar), *R* = 8.314 J/(mol K) and *T* the temperature (K). Because Δ*c*~p~ > 0, Δ*H*~r~ rises from 50.27 kJ/mol at 250 degC to 54.22 kJ/mol at 600 degC and 55.70 kJ/mol at 900 degC, while *K* rises from 5.387 to 658.4 and 4572 (Figure 4.1).
<!-- data: results/validation/equilibrium_python_grid.csv columns K_eq, dH_rxn_kJ_per_mol_NH3 at T_C = 250, 600, 900 -->

![**Figure 4.1.** Equilibrium constant *K* (left, logarithmic, standard state 1 bar) and reaction enthalpy Δ*H*~r~ (right, kJ/mol NH~3~) from 250 to 900 degC. Higher temperature favours conversion but raises the heat demand per mole cracked. *Source: independent Python calculation (NASA-7 / GRI-Mech 3.0 data).*](../../results/figures/equilibrium_K_and_dH_vs_T.png){width=80%}

## 4.3 Equilibrium conversion of a pure ammonia feed

For a feed of $n_0$ mol NH~3~ and conversion $X = \xi/n_0$ ($\xi$ = extent of reaction), Eq. (4.1) gives

$$ n_{\mathrm{NH_3}} = n_0(1-X), \quad n_{\mathrm{N_2}} = \tfrac{1}{2}n_0X, \quad n_{\mathrm{H_2}} = \tfrac{3}{2}n_0X, \quad n_{\mathrm{tot}} = n_0(1+X) \qquad (4.5) $$

$$ y_{\mathrm{NH_3}} = \frac{1-X}{1+X}, \quad y_{\mathrm{N_2}} = \frac{X}{2(1+X)}, \quad y_{\mathrm{H_2}} = \frac{3X}{2(1+X)} \qquad (4.6) $$

where $y_i$ is the mole fraction. For ideal gases at total pressure *P* (bar):

$$ K = \frac{(y_{\mathrm{N_2}}P/p^\circ)^{1/2}\,(y_{\mathrm{H_2}}P/p^\circ)^{3/2}}{y_{\mathrm{NH_3}}P/p^\circ} = \frac{y_{\mathrm{N_2}}^{1/2}\,y_{\mathrm{H_2}}^{3/2}}{y_{\mathrm{NH_3}}}\,\frac{P}{p^\circ} \qquad (4.7) $$

Substituting Eq. (4.6), with $(1/2)^{1/2}(3/2)^{3/2} = 3\sqrt{3}/4 \approx 1.299$ and $(1-X)(1+X) = 1-X^2$:

$$ K = \frac{3\sqrt{3}}{4}\,\frac{X^2}{1-X^2}\,\frac{P}{p^\circ} \qquad (4.8) $$

$$ X_{\mathrm{eq}} = \left(1 + \frac{3\sqrt{3}}{4}\,\frac{P/p^\circ}{K(T)}\right)^{-1/2} \qquad (4.9) $$

At the baseline (600 degC, 20 bar, *K* = 658.4): 1.299 × 20 / 658.4 = 0.0395 and $X_{\mathrm{eq}} = 1.0395^{-1/2} = 0.9808$, equal to the solver result (0.98084). For a non-ideal gas the partial pressures in Eq. (4.7) become fugacities $y_i\varphi_i P$; the package solves this with Peng-Robinson (Section 9).
<!-- data: results/validation/equilibrium_python_grid.csv T_C=600, P_bar=20, eos=ideal: K_eq 658.446, nh3_conversion 0.980836 -->

## 4.4 Temperature and pressure effects

Eq. (4.9) expresses both Le Chatelier trends: conversion rises with *T* (endothermic, *K* increases) and falls with *P* (mole increase); inert dilution also raises it (Maccarrone et al., 2025, pp. 4-5). At 1 bar conversion exceeds 99 % from 400 degC; at 20 bar 600 degC is needed to exceed 98 % (Table 4.1). The pressure penalty is large below about 500 degC: at 400 degC conversion falls from 99.14 % (1 bar) to 81.02 % (30 bar).

Table: **Table 4.1.** Equilibrium NH~3~ conversion (%) for a pure NH~3~ feed, ideal gas. *Source: independent Python calculation, results/validation/equilibrium_python_grid.csv.*

| T (degC) | 1 bar | 10 bar | 20 bar | 30 bar |
|---|---|---|---|---|
| 300 | 95.90 | 73.06 | 60.34 | 52.56 |
| 400 | 99.14 | 92.28 | 86.10 | 81.02 |
| 500 | 99.74 | 97.52 | 95.22 | 93.08 |
| 600 | 99.90 | 99.03 | 98.08 | 97.17 |
| 700 | 99.95 | 99.55 | 99.10 | 98.66 |

<!-- data: results/validation/equilibrium_python_grid.csv eos=ideal, nh3_conversion -->

Non-ideality is small: at 600 degC and 20 bar Peng-Robinson gives 98.07 % against 98.08 % (ideal); the largest gap in the grid is 29.36 % against 30.65 % at 250 degC and 40 bar. At 5 bar, Cechetto et al. (2023, p. 10783) report 91.9, 95.9, 97.8 and 98.7 % at 350, 400, 450 and 500 degC; AmCraX gives 91.91, 95.91, 97.80 and 98.74 %. Section 9.4 compares the Python and Aspen Plus RGibbs grids.
<!-- data: results/validation/equilibrium_python_grid.csv (600/20 pr 0.980720, ideal 0.980836; 250/40 pr 0.293576, ideal 0.306481; P_bar=5 ideal 0.919075, 0.959052, 0.977979, 0.987383); research/notes/cechetto2023membrane.md Table 3 -->

![**Figure 4.2.** Equilibrium NH~3~ conversion versus temperature at 1-40 bar, pure NH~3~ feed (solid: ideal gas; dashed: Peng-Robinson). The pressure penalty shrinks to about 1.3 percentage points between 1 and 30 bar at 700 degC, which sets the temperature-pressure trade-off for the cracker. *Source: independent Python calculation.*](../../results/figures/equilibrium_conversion_vs_T.png){width=85%}

![**Figure 4.3.** Equilibrium mole fractions of NH~3~, H~2~ and N~2~ at 1 bar (left) and 20 bar (right). The gas tends to 75 % H~2~ / 25 % N~2~; at 20 bar appreciable NH~3~ remains below about 500 degC, raising the downstream NH~3~-removal load. *Source: independent Python calculation (solid = ideal, dashed = Peng-Robinson).*](../../results/figures/equilibrium_composition_vs_T.png){width=95%}

## 4.5 Mechanism and rate-determining step

The accepted surface mechanism is adsorption, stepwise dehydrogenation and recombinative desorption (Su et al., 2023, p. 8114; Maccarrone et al., 2025, pp. 6-7):

$$ \mathrm{NH_3} + * \rightleftharpoons \mathrm{NH_3^*};\;\; \mathrm{NH_3^*} + * \rightleftharpoons \mathrm{NH_2^*} + \mathrm{H^*};\;\; \mathrm{NH_2^*} + * \rightleftharpoons \mathrm{NH^*} + \mathrm{H^*};\;\; \mathrm{NH^*} + * \rightleftharpoons \mathrm{N^*} + \mathrm{H^*};\;\; 2\mathrm{N^*} \rightleftharpoons \mathrm{N_2} + 2*;\;\; 2\mathrm{H^*} \rightleftharpoons \mathrm{H_2} + 2* \qquad (4.10) $$

where * is a vacant site. The rate-determining step (RDS) depends on metal and conditions: N-N recombination on Ni and Fe and N-H cleavage on noble metals (Ganley et al., 2004, as cited in Xu et al., 2025, p. 8); N~2~ desorption on Ru, Ni, Co, Fe and Cr (Maccarrone et al., 2025, p. 6); dehydrogenation on Ni and N~2~ desorption on Ru in the microkinetic fit of Takahashi and Fujitani (2016, pp. 23, 28). H~2~ inhibition (negative H~2~ order) is reported, stronger at lower temperature (Xu et al., 2025, p. 8).

## 4.6 Kinetic rate-law forms

Section 10.5 implements two rate-law families; the theory is given here.

**Temkin-Pyzhev (reversible).** Kum et al. (2026, p. 4, Eq. 2), also Maccarrone et al. (2025, p. 20, Eq. 12):

$$ r = k_0\exp\!\left(-\frac{E_a}{RT}\right)\left[\left(\frac{p_{\mathrm{NH_3}}^2}{p_{\mathrm{H_2}}^3}\right)^{\beta} - \frac{p_{\mathrm{N_2}}}{K_{eq}^2}\left(\frac{p_{\mathrm{H_2}}^3}{p_{\mathrm{NH_3}}^2}\right)^{1-\beta}\right] \qquad (4.11) $$

with *r* in mol/(g~cat~ s) and *p*~i~ in bar. Kum et al. (2026, p. 5, Table 1) fitted *k*~0~ = 55245.9 mol/(g~cat~ s bar^0.27^), *E*~a~ = 114224 J/mol and β = 0.27 to the Ru/Al~2~O~3~ data of Di Carlo et al. (2014), valid 623.15-773.15 K (p. 7). The second term makes the rate vanish at equilibrium; its *K*~eq~^2^ implies the per-mole-NH~3~ basis of Eq. (4.1), which Kum et al. do not state explicitly. Takahashi and Fujitani (2016, p. 27) and Richard et al. (2024, p. 577) use the irreversible form $r = k(p_{\mathrm{NH_3}}^2/p_{\mathrm{H_2}}^3)^{\beta}$.

**Microkinetic model.** Takahashi and Fujitani (2016, pp. 23-25) solve steady-state site balances for four lumped steps; the net rate equals the dehydrogenation rate $r_2 = k_2\theta_{\mathrm{NH_3}}\theta_s^3$ (θ = surface coverage). Fitted activation energies (p. 25, Table 1) are 144.0 (Ni) and 105.8 kJ/mol (Ru) for dehydrogenation, 127.8 and 123.5 kJ/mol for N~2~ desorption, and 109.0 and 67.8 kJ/mol for H~2~ desorption. The model is irreversible, uses *p*~i~/*P* only and was fitted at 1 atm (Ni 350-650 degC, Ru 300-550 degC), so its use at 20 bar is an extrapolation that needs an equilibrium cap (Section 10.5).

Power-law and Langmuir-Hinshelwood forms are also compiled by Maccarrone et al. (2025, p. 20) but are not implemented, because their pre-exponential factors have inconsistent units.

## 4.7 Catalyst data relevant to AmCraX

Table: **Table 4.2.** Published catalyst data used to qualify the equilibrium baseline. *Source: published literature as cited; not AmCraX results.*

| Topic | Finding | Source |
|---|---|---|
| Temperature | Typical catalysts need about 600 degC for complete conversion; research target 400-500 degC | Xu et al. (2025, p. 4) |
| Cost optimum | Ni/Al~2~O~3~ at 735.52 degC, 24.34 bar; Ru-K/CaO at 566.69 degC, 10 bar; catalyst 33.4 (Ni) and 542 USD/kg (Ru) | Cho et al. (2026, pp. 7, 13) |
| Ni stability | 800 h at 534 degC, 1 atm: industrial Ni 91.9 % (250 h) to 90.4 % (800 h); sintering is the main deactivation route | Purcel et al. (2025, pp. 2-3); Su et al. (2023, pp. 8118-8119) |
| Pressure | Ru-10%K/CaO at 500 degC: 98 % (1 bar), 80 % (10 bar), 65 % (20 bar), 60 % (40 bar) | Sayas et al. (2020, as cited in Maccarrone et al., 2025, p. 13) |

The equilibrium model gives the upper bound on conversion. Whether a Ni or Ru bed approaches it at 20 bar is a kinetic question, addressed in Section 10.5.
