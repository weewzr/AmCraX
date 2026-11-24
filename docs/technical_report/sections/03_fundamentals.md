<!-- cites: cho2026nickel, xu2025review, cechetto2023membrane, maccarrone2025comprehensive, kum2026heatintegrated, nist_janaf, smith_grimech30, goodwin2018cantera, su2023review, ganley2004apriori, takahashi2016kinetic, purcel2024stability, sayas2020rukcao -->

# 3 Ammonia-cracking fundamentals

## 3.1 Stoichiometry and atom balance

AmCraX writes the cracking reaction per mole of ammonia:

$$ \mathrm{NH_3} \rightleftharpoons \tfrac{1}{2}\,\mathrm{N_2} + \tfrac{3}{2}\,\mathrm{H_2} \qquad (3.1) $$

Published values for 2NH~3~ ⇌ N~2~ + 3H~2~ are converted to this basis below. The element balances over the reactor are

$$ n_{\mathrm{N,in}} = n_{\mathrm{NH_3}} + 2\,n_{\mathrm{N_2}}, \qquad n_{\mathrm{H,in}} = 3\,n_{\mathrm{NH_3}} + 2\,n_{\mathrm{H_2}} + 2\,n_{\mathrm{H_2O}} \qquad (3.2) $$

where $n_i$ is the outlet molar flow of species $i$ (kmol/h) and the left-hand sides are the N and H atom flows fed (kmol/h). The number of gas moles rises from 1 to 2 per mole of NH~3~ converted, so pressure works against conversion. At complete conversion the gas is 75 mol% H~2~ and 25 mol% N~2~. The 0.2 mol% water in the AmCraX feed has no oxygen-bearing partner in the cracker and passes through unchanged.

## 3.2 Reaction enthalpy and equilibrium constant

The temperature dependence of the reaction enthalpy follows from Kirchhoff's law, that of the equilibrium constant from the van 't Hoff relation:

$$ \Delta H_r(T) = \Delta H_r^\circ(298.15\,\mathrm{K}) + \int_{298.15}^{T} \Delta c_p\,\mathrm{d}T, \qquad \Delta c_p = \tfrac{1}{2}c_{p,\mathrm{N_2}} + \tfrac{3}{2}c_{p,\mathrm{H_2}} - c_{p,\mathrm{NH_3}} \qquad (3.3) $$

$$ K(T) = \exp\!\left(-\frac{\Delta G_r^\circ(T)}{RT}\right), \qquad \frac{\mathrm{d}\ln K}{\mathrm{d}T} = \frac{\Delta H_r^\circ(T)}{RT^2} \qquad (3.4) $$

Here $\Delta H_r$ is the reaction enthalpy (kJ/mol NH~3~), $c_{p,i}$ the ideal-gas heat capacity of species $i$ (J/(mol K)), $\Delta G_r^\circ$ the standard Gibbs energy of reaction (J/mol NH~3~), $K$ the dimensionless equilibrium constant (standard pressure $p^\circ$ = 1 bar), $R$ = 8.314 J/(mol K) and $T$ the temperature (K). Because $\Delta H_r > 0$, $K$ rises with temperature.

The AmCraX thermodynamics package (**independent Python calculation**; GRI-Mech 3.0 NASA-7 polynomials, Smith et al., n.d., loaded through Cantera, Goodwin et al., 2018) gives $\Delta H_r^\circ$(298.15 K) = +45.899 kJ/mol and $\Delta G_r^\circ$(298.15 K) = +16.381 kJ/mol. NIST-JANAF (National Institute of Standards and Technology, n.d.) gives 45.898 and 16.367 kJ/mol. The package's 29 tests, all passing, check both values within 0.05 kJ/mol and log~10~ *K* within 0.01 from 400 to 1500 K. Published values of $\Delta H_r^\circ$ are 45.6 (Cho et al., 2026, p. 2; Xu et al., 2025, p. 5, quoted as 91.2 kJ per 2 mol), 45.92 (Cechetto et al., 2023, p. 10777), 45.984 (Maccarrone et al., 2025, p. 3) and 46.11 kJ/mol NH~3~ (Kum et al., 2026, p. 5).
<!-- data: amcrax.thermodynamics.reaction_enthalpy_kJ_mol(298.15) = 45.8989, reaction_gibbs_kJ_mol(298.15) = 16.3811 (evaluated 2026-11-21); tests/test_thermodynamics.py, 29 passed (pytest run 2026-11-21); docs/validation/discrepancy_analysis.md section 2 (45.899 Python vs 45.898 JANAF); research/notes cho2026nickel p. 2, xu2025review p. 5, cechetto2023membrane p. 3, maccarrone2025comprehensive p. 3, kum2026heatintegrated Table 1 p. 5 -->

Because $\Delta c_p > 0$, the reaction enthalpy grows with temperature, from 50.27 kJ/mol at 250 °C to 54.22 kJ/mol at 600 °C and 55.70 kJ/mol at 900 °C, while $K$ rises from 5.387 to 658.4 and 4572 (both curves are plotted in Figure 13.1, Section 13.3). Higher temperature favours conversion but raises the heat demand per mole cracked; the cracker duty is the largest heat demand of the plant (Section 5.3).
<!-- data: results/validation/equilibrium_python_grid.csv eos=ideal, P_bar=1, columns K_eq and dH_rxn_kJ_per_mol_NH3 at T_C = 250, 600, 900 -->

## 3.3 Le Chatelier trends

For an ideal gas, the equilibrium condition of Eq. (3.1) is

$$ K(T) = \frac{y_{\mathrm{N_2}}^{1/2}\,y_{\mathrm{H_2}}^{3/2}}{y_{\mathrm{NH_3}}}\,\frac{P}{p^\circ} \qquad (3.5) $$

with $y_i$ the mole fraction and $P$ the total pressure (bar). At fixed $T$ the right-hand side must stay constant, so a higher pressure must be offset by a lower product-to-reactant ratio: conversion falls with pressure because the reaction doubles the number of moles. Conversion rises with temperature because $K$ rises, and inert dilution lowers the product partial pressures and also raises conversion (Maccarrone et al., 2025, pp. 4-5). For a pure NH~3~ feed (**independent Python calculation**, ideal gas), conversion exceeds 99 % from 400 °C at 1 bar, whereas at 20 bar about 600 °C is needed to exceed 98 % (0.9808). The pressure penalty is large at low temperature: at 400 °C conversion falls from 0.9914 at 1 bar to 0.8102 at 30 bar, at 700 °C only from 0.9995 to 0.9866. Section 13 derives the closed-form equilibrium conversion, quantifies the non-ideal (Peng-Robinson) correction and compares the Python model with Aspen Plus V15.
<!-- data: results/validation/equilibrium_python_grid.csv eos=ideal nh3_conversion: 400 degC 1 bar 0.9914, 30 bar 0.8102; 600 degC 20 bar 0.9808 (575 degC 0.9763); 700 degC 1 bar 0.9995, 30 bar 0.9866 -->

## 3.4 Mechanism and rate-determining step

On metal catalysts the accepted surface mechanism is adsorption, stepwise dehydrogenation and recombinative desorption (Su et al., 2023, p. 8114; Maccarrone et al., 2025, pp. 6-7):

$$ \mathrm{NH_3} + * \rightleftharpoons \mathrm{NH_3^*};\;\; \mathrm{NH_{x}^*} + * \rightleftharpoons \mathrm{NH_{x-1}^*} + \mathrm{H^*}\;(x = 3, 2, 1);\;\; 2\mathrm{N^*} \rightleftharpoons \mathrm{N_2} + 2*;\;\; 2\mathrm{H^*} \rightleftharpoons \mathrm{H_2} + 2* \qquad (3.6) $$

where * is a vacant surface site. Which step limits the rate depends on the metal and the conditions. Ganley et al. (2004, as cited in Xu et al., 2025, p. 8) assign N-N recombination to non-noble metals such as Ni and Fe and N-H cleavage to noble metals; Maccarrone et al. (2025, p. 6) list N~2~ desorption as rate-limiting on Ru, Ni, Co, Fe and Cr; and the microkinetic fit of Takahashi and Fujitani (2016, pp. 23, 28) finds NH~3~ dehydrogenation rate-limiting on Ni and N~2~ desorption on Ru. Hydrogen inhibits the rate (negative H~2~ order), more strongly at lower temperature (Xu et al., 2025, p. 8), which matters at 20 bar, where the hydrogen partial pressure is high. Section 14 implements two published rate laws in a plug-flow reactor model.

## 3.5 Catalyst families and operating windows

Ru is the most active metal but costly; Ni is the practical non-noble choice but needs higher temperature and sinters (Xu et al., 2025, pp. 4, 15). Table 3.1 collects the operating windows that bear on the AmCraX baseline of 600 °C and 20 bar.

Table: **Table 3.1.** Published catalyst operating windows and findings relevant to the AmCraX baseline. *Source: published literature as cited; none of these values is an AmCraX result.*

| Topic | Finding | Source |
|---|---|---|
| Temperature | Typical catalysts need about 600 °C for complete conversion; research target 400-500 °C | Xu et al. (2025, p. 4) |
| Kinetic data range | Microkinetic models fitted and tested at 1 atm over 350-650 °C (Ni/MgO) and 300-550 °C (Ru/MgO) | Takahashi and Fujitani (2016) |
| Cost-optimal conditions | Ni/Al~2~O~3~ at 735.52 °C and 24.34 bar; Ru-K/CaO at 566.69 °C and 10 bar | Cho et al. (2026, p. 13) |
| Pressure | Ru-10%K/CaO at 500 °C: conversion 98 % (1 bar), 80 % (10 bar), 65 % (20 bar), 60 % (40 bar) | Sayas et al. (2020, as cited in Maccarrone et al., 2025, p. 13); checked against Sayas et al. (2020, Fig. 4A): about 100, 80.5, 68 and 62 % (figure reading, ±2 points) |
| Ni stability | Industrial Ni at 534 °C and 1 atm: 91.9 % conversion at 250 h, 90.4 % at 800 h; sintering is the main deactivation route | Purcel et al. (2025, pp. 2-3); Su et al. (2023, pp. 8118-8119) |
| Membrane reactors | Pd-based membranes should not exceed 500 °C | Cechetto et al. (2023, p. 10784) |

<!-- data: research/notes/xu2025review.md p. 4, p. 15; takahashi2016kinetic.md (operating ranges); cho2026nickel.md Table 7 p. 13; maccarrone2025comprehensive.md p. 13; purcel2024stability.md pp. 2-4; su2023review.md pp. 20-21 (= 8118-8119); cechetto2023membrane.md p. 10 (= 10784) -->

The Sayas data show why this matters: at 500 °C and 20 bar the measured conversion (65 to 68 %) is far below the equilibrium value for pure NH~3~ (0.9522), so at elevated pressure the catalyst, not thermodynamics, can limit conversion. The equilibrium cracker of the AmCraX flowsheet therefore gives an upper bound; whether a realistic Ni or Ru bed approaches it at 20 bar is addressed in Section 14.
<!-- data: results/validation/equilibrium_python_grid.csv eos=ideal, 500 degC, 20 bar: 0.9522 -->
