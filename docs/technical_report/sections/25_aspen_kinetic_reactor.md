<!-- cites: kum2026heatintegrated, dicarlo2014ammonia, lucentini2021nirukinetic, lucentini2019ceo2, takahashi2016kinetic, sayas2020rukcao, cho2026nickel -->

# 25 Kinetic reactor modelling in Aspen Plus

The baseline flowsheet uses an RGibbs equilibrium cracker (Section 9), which carries no catalyst. Hypothesis H3 is about catalysts, so it needs a reactor in which the catalyst sets the conversion. This section describes how published rate laws were implemented in Aspen Plus V15 RPlug reactors, how the implementation was verified against the independent Python plug-flow reactor (PFR) of Section 14, and what the kinetic studies show. Every Aspen value below comes from a stored run in `results/research/aspen_kinetic/`; all 146 catalyst-study runs and the 16 infrastructure runs converged with status ok. The case lists, drivers and commands that reproduce them are given in Appendix F (research expansion), and every run stores its input file and a sanitised backup file in `aspen/models/research/`.
<!-- data: results/research/aspen_kinetic/run_status.json; docs/internal/research_reports/aspen-catalyst-cases.md (146 runs: 34 validation, 102 study, 10 integrated) -->

**Status in version 2.0.** Phase 2 added 60 standalone RPlug runs with the Lucentini law in an exact partial-pressure form, all converged, and corrected the block label of 12 stored integrated files (the cracker was stored as RGibbs with placeholder outlet conditions; it is now RPlug with outlet temperature and pressure from stream S5; duties unchanged). The validation counts quoted in this section are those of version 1.0. The current file `results/research/validation/aspen_kinetic.json` holds 190 items: 163 pass, 5 fail and 22 informational, and Section 38.2 gives the quantified cause of every failure. Section 35.2 classifies the validity of every rate law at 20 bar: none is validated there.

## 25.1 Which catalysts could be modelled

A catalyst enters the comparison only if a complete rate law (form, pre-exponential factor, activation energy and every adsorption or inhibition constant, with units) was found in a primary source. Table 25.1 lists the outcome.

Table: **Table 25.1.** Catalysts considered and the status of their rate laws. *Source: results/research/kinetics/aspen_kinetics_spec.json (catalysts, not_included); research/notes.*

| Catalyst | Rate law and source | Fitted range | Aspen form |
|---|---|---|---|
| Ru/Al~2~O~3~ | Temkin-Pyzhev, Kum et al. (2026, Eqs. 2-4, Table 1), fitted to the data of Di Carlo et al. (2014) | 350-450 °C, 1-10 bar | native POWERLAW (exact) |
| 5Ni1Ru/CeO~2~ | Langmuir-Hinshelwood-Hougen-Watson (LHHW), Lucentini et al. (2021, Eqs. 17-18, Table 3) | 350-600 °C, 1 atm | native LHHW (exact) |
| 2.5Ni0.5Ru/CeO~2~ | as above, own parameters | 350-600 °C, 1 atm | native LHHW (exact) |
| Ni/MgO | microkinetic, Takahashi and Fujitani (2016, Tables 1-2) | 350-450 °C fit, 1 atm | fitted LHHW approximation (20 bar only) |
| Ru/MgO | microkinetic, Takahashi and Fujitani (2016, Tables 1-2) | 300-400 °C fit, 1 atm | fitted LHHW approximation (20 bar only) |
| Ni/CeO~2~, Ru/CeO~2~ | none: Lucentini et al. (2019) report conversions only, with no rate law, activation energy or orders | - | not modelled |
| Ru-K/CaO | Sayas et al. (2020): main text read in full on 24 November 2026; it gives the form (power law with an approach-to-equilibrium term), the orders and an apparent activation energy, but no rate constant and no equilibrium term of the fit (both in the supplementary information, not obtained) | kinetic fit at 1 atm; conversions measured at 1-40 bar | not modelled |

The essay's conversion comparison of Ru/CeO~2~ (98 %) and Ni/CeO~2~ (63 %) at 450 °C was confirmed in the text of Lucentini et al. (2019), but without a rate law no pre-exponential factor can be derived from it honestly, so these catalysts are not modelled. The Ru-K/CaO values quoted in the essay are now confirmed in the main text of Sayas et al. (2020, Table 4, at 350 °C and 1 atm): the apparent activation energy falls from 96 to 75 kJ/mol with potassium and the H~2~ order from -1.9 to -1.2 (NH~3~ order 0.8 to 0.5). The 111 kJ/mol carried for this catalyst from a review is not in the main text. Without the rate constant the law is still incomplete; nothing was fitted or estimated, and Ru-K/CaO stays unmodelled. The paper's 15 measured conversions at 10 to 40 bar are stored as literature comparison points that no model uses (Section 35.2). Cho et al. (2026) use a Ni/Al~2~O~3~ law and the Ru-K/CaO law of Sayas et al. (2020) from supplementary material that was not available, so their two catalysts are represented in Section 26 by the proxies Ni/MgO and Ru/Al~2~O~3~.
<!-- data: results/research/kinetics/aspen_kinetics_spec.json not_included; docs/internal/research_reports/kinetics.md (literature findings) -->

## 25.2 Rate laws

**Ru/Al~2~O~3~ (Temkin-Pyzhev).** The rate per mole of NH~3~ is

$$ r = k_0 \exp\left(-\frac{E_a}{RT}\right)\left[\left(\frac{p_{\mathrm{NH_3}}^2}{p_{\mathrm{H_2}}^3}\right)^{\beta} - \frac{p_{\mathrm{N_2}}}{K_{eq}^2}\left(\frac{p_{\mathrm{H_2}}^3}{p_{\mathrm{NH_3}}^2}\right)^{1-\beta}\right] \qquad (25.1) $$

with $r$ in mol/(g~cat~ s), partial pressures $p_i$ in bar, $k_0$ = 55245.9 mol/(g~cat~ s), $E_a$ = 114.224 kJ/mol and $\beta$ = 0.27, so that the forward term is $p_{\mathrm{NH_3}}^{0.54} p_{\mathrm{H_2}}^{-0.81}$ (Kum et al., 2026). $K_{eq}$ is the equilibrium constant of NH~3~ ⇌ ½N~2~ + 3/2H~2~ on a 1 bar basis, $R$ the gas constant and $T$ the temperature in K. The rate is infinite at $p_{\mathrm{H_2}} = 0$, so a small hydrogen seed is needed at the reactor inlet (Section 25.3).
<!-- data: results/research/kinetics/aspen_kinetics_spec.json catalysts[ru_kum_temkin_pyzhev].python_law, kinetic_factor (k 55245.9, E_kJ_per_mol 114.224), driving_force.term1.exponents (NH3 0.54, H2 -0.81), validity -->

**Ni-Ru/CeO~2~ (LHHW).** With the first dehydrogenation step rate determining and hydrogen adsorption quasi-equilibrated, Lucentini et al. (2021) obtain

$$ r = \frac{k K_1 C_{\mathrm{NH_3}}}{\left(1 + K_1 C_{\mathrm{NH_3}} + \sqrt{C_{\mathrm{H_2}}/K_4}\right)^2}, \qquad k = k_0 \exp\left(-\frac{E_k}{RT}\right) \qquad (25.2) $$

with $r$ in mol NH~3~/(g~cat~ s), concentrations $C_i$ in mol/m^3^, and the temperature-independent adsorption constants $K_1$ (m^3^/mol) and $K_4$ (mol/m^3^) of Table 25.2. The published law is irreversible. Near equilibrium AmCraX multiplies it by the approach factor

$$ \phi = 1 - \frac{Q}{K_p}, \qquad Q = \frac{(p_{\mathrm{N_2}}/p^\circ)^{1/2}(p_{\mathrm{H_2}}/p^\circ)^{3/2}}{p_{\mathrm{NH_3}}/p^\circ} \qquad (25.3) $$

with $p^\circ$ = 1 bar. The factor is an **engineering assumption** that stops the rate law from converting past equilibrium; it is not part of the published law.

Table: **Table 25.2.** Parameters of the Ni-Ru/CeO~2~ LHHW law. *Source: published literature, Lucentini et al. (2021, Table 3); results/research/kinetics/aspen_kinetics_spec.json.*

| Catalyst | *k*~0~ (mol/(g s)) | *E*~k~ (kJ/mol) | *K*~1~ (m^3^/mol) | *K*~4~ (mol/m^3^) |
|---|---|---|---|---|
| 5Ni1Ru/CeO~2~ | 3.9 × 10^6^ | 124 ± 8 | 1.1 | 0.047 |
| 2.5Ni0.5Ru/CeO~2~ | 3.3 × 10^5^ | 107 ± 11 | 1.2 | 0.045 |

The **independent Python calculation** reproduces the conversions of Table 1 of Lucentini et al. (2021) (0.1 g catalyst, 25 mL/min, Ar:NH~3~ 1.2:1, 1 atm, 400-500 °C) with a root-mean-square error of 0.023 and a largest error of 0.039 for 5Ni1Ru/CeO~2~, and a largest error of 0.025 for 2.5Ni0.5Ru/CeO~2~ (Figure 25.1). These points belong to the data the law was fitted to, so this is a consistency check of the implementation, not an independent validation. The reported confidence interval of $E_k$ alone moves the predicted conversion at 450 °C between 0.42 and 0.995; since $k_0$ and $E_k$ are correlated and no covariance is published, this overstates the joint uncertainty but shows that the rate is uncertain by a large factor.
<!-- data: results/research/kinetics/validation_5Ni1Ru_CeO2.json statistics (rmse 0.02283, max_abs_error 0.03941), sensitivity.X_by_case (Ek_plus 0.41998, Ek_minus 0.99464 at 450 degC); validation_2p5Ni0p5Ru_CeO2.json statistics.max_abs_error; results/research/validation/kinetics.json KINR-LUC-* -->

![**Figure 25.1.** Measured conversions of Lucentini et al. (2021, Table 1) against the Python PFR with the Table 3 rate law for both Ni-Ru/CeO~2~ catalysts at 1 atm. The agreement checks the implementation of Eq. (25.2) and its units; it is not independent validation, because these points were used in the fit. *Source: independent Python calculation; published literature.*](../../results/figures/research/kinetics_validation_lucentini.png){width=80%}

**Ni/MgO and Ru/MgO (microkinetic).** The elementary-step model of Takahashi and Fujitani (2016), with its site balance solved numerically, is described in Section 14.2. Aspen's built-in rate expressions cannot represent a coverage solve, and a user kinetics subroutine needs a Fortran compiler, which is not installed. The kinetics workstream therefore fitted the native LHHW form

$$ r = k_0 \exp\left(-\frac{E}{RT}\right) \frac{y_{\mathrm{NH_3}}^{a} - \dfrac{P/p^\circ}{K_p}\, y_{\mathrm{N_2}}^{0.5}\, y_{\mathrm{H_2}}^{1.5}\, y_{\mathrm{NH_3}}^{a-1}}{\left(1 + K_H y_{\mathrm{H_2}}^{b} + K_N y_{\mathrm{NH_3}}\right)^{m}} \qquad (25.4) $$

by least squares to the published microkinetic rate at 20 bar, with $y_i$ the mole fractions, $P$ the total pressure, $\ln K_H$ and $\ln K_N$ linear in $1/T$, and $r$ in kmol/(kg~cat~ s). The fitted parameters are an **independent Python calculation**, not literature values, and the pressure term makes the fit valid at 20 bar only; the Aspen input layer refuses the approximation at any other pressure.

Table: **Table 25.3.** Fitted LHHW approximation of the Takahashi microkinetic laws (Eq. (25.4)) and its error against the published law. *Source: independent Python calculation, results/research/kinetics/aspen_kinetics_spec.json catalysts[*_takahashi_microkinetic].best_native_approximation.*

| Quantity | Ni/MgO | Ru/MgO |
|---|---|---|
| $k_0$ (kmol/(kg~cat~ s)) | 766.2 | 155.6 |
| $E$ (kJ/mol) | 84.78 | 67.71 |
| Exponents $a$; $b$; $m$ | 0.966; 0.978; 1.778 | 0.760; 1.276; 0.815 |
| Fit range | 350-650 °C, $y_{\mathrm{NH_3}}$ 0.02-1, $y_{\mathrm{H_2}}$ 10^-4^-0.7 | 300-550 °C, same compositions |
| Rate error: RMS; maximum (relative) | 0.118; 0.483 | 0.106; 0.526 |
| Largest conversion error at the 10 reference points | 0.034 | 0.019 |

<!-- data: aspen_kinetics_spec.json best_native_approximation.kinetic_factor (k 766.2220774, 155.6144786; E_J_per_mol 84775.42, 67714.65), fitted_parameters (a_NH3, b_H2, adsorption_exponent_m), fit_range (T_K 623.15-923.15, 573.15-823.15), rate_error_vs_python_law (rms_rel 0.11755/0.10597, max_rel 0.48321/0.52580), conversion_error_vs_python_pfr.max_abs (0.034346, 0.018870) -->

## 25.3 Implementation in Aspen Plus

**Reaction set.** Each case has one reaction set, NH3KIN, of type GENERAL with a single vapour-phase reaction and rate basis per kilogram of catalyst (Cat (wt)). The Ru/Al~2~O~3~ law is entered as POWERLAW with the reverse rate computed by microscopic reversibility from Aspen's own Gibbs-energy equilibrium constant. Because the reaction is written as 2 NH~3~ → N~2~ + 3 H~2~ with partial pressures in bar, the pre-exponential factor becomes 55245.9/2 = 27622.95 kmol/(kg~cat~ s bar^0.27^) and the activation energy is entered as 27281.9 cal/mol (114.224 kJ/mol); Figure 25.3 shows both values in the Aspen form. The Ni-Ru/CeO~2~ laws and the Takahashi approximations use the LHHW class, written for NH~3~ → ½N~2~ + 3/2H~2~, in SI units: rate in kmol/(kg~cat~ s), activation energy in J/kmol, concentrations in kmol/m^3^ (molarity basis, Lucentini) or as mole fractions (Takahashi approximation). Aspen writes each constant of the driving force and adsorption terms as $\ln K = A + B/T + C \ln T + DT$. The equilibrium constant in the reverse term was fitted in this form to the AmCraX NASA-7 $K_p$ between 573 and 1123 K, with a largest error in $\ln K$ of 2.8 × 10^-4^; $K_1$ = 1100 m^3^/kmol and $K_4$ = 4.7 × 10^-5^ kmol/m^3^ (5Ni1Ru) are the published constants converted to kmol.
<!-- data: results/research/kinetics/aspen_kinetics_spec.json equilibrium_constant_fit (T_range_K, max_abs_error_lnK 0.000275), catalysts[].kinetic_factor, driving_force notes (K1 = 1100 m3/kmol, K4 = 4.7e-05 kmol/m3); docs/internal/research_reports/aspen-rplug-infrastructure.md (PRE-EXP 27622.95, E 27281.9 cal/mol confirmed on the kinetic tab) -->

**Check of the native forms.** Before any Aspen run, the native forms were evaluated in Python against the original laws: the Ru/Al~2~O~3~ form differs by at most 5.8 × 10^-4^ (relative, 72 samples, 350-600 °C, 1-40 bar) and the Ni-Ru/CeO~2~ forms by at most 6.2 × 10^-4^ (84 samples, 350-800 °C). The only source of difference is the $\ln K_p$ fit; the algebra is exact.
<!-- data: aspen_kinetics_spec.json catalysts[].native_form_error_vs_python (max_rel_rate_error 0.000581, 0.000622; n_samples 72, 84; range) -->

**RPlug block.** The standalone cases contain an RPLUG reactor (RXR) fed with 100 kmol/h of pure NH~3~, operated isothermally, adiabatically (optionally with an Ergun pressure drop) or against a constant-temperature coolant, with an RGibbs block (REQ) at the same temperature and pressure as the equilibrium reference. The catalyst loading is specified directly; the bed voidage is 0.36 and the particle density 980 kg/m^3^ for Ru/Al~2~O~3~ (Kum et al., 2026, Table 1); for Ni-Ru/CeO~2~ the laboratory powder density of 1651.8 kg/m^3^ is used, an **engineering assumption** for an industrial bed. A hydrogen seed of 10^-3^ of the NH~3~ feed, pre-cracked to N~2~ and H~2~, removes the singularity of Eq. (25.1); seeds of 10^-6^ and 10^-4^ produced mass-imbalance errors in the adiabatic and coolant runs, and the Python result changes by less than 3 × 10^-5^ in conversion across seeds. All Python comparison runs use the same seed.
<!-- data: aspen_kinetics_spec.json catalysts[0].bed_properties (0.36, 980, 0.126 m); results/research/aspen_kinetic/assumptions.json; docs/internal/research_reports/aspen-rplug-infrastructure.md (seed tests); docs/internal/research_reports/aspen-catalyst-cases.md (1651.8 kg/m3) -->

**Integrated flowsheet.** For the integrated cases the CRACKER block of the baseline flowsheet becomes an RPLUG with the same block identifier and streams (Figure 25.2). The hydrogen seed (10^-4^ of the feed, 0.015 kmol/h of H~2~) enters as a separate stream, H2SEED, at the HEATER inlet, because seeding the liquid feed caused enthalpy-initialisation errors. Without the Ergun option the RPLUG outlet stays at the HEATER outlet pressure, 20.2 bar, where RGibbs was set to exactly 20 bar; downstream pressures are unchanged. The input file for existing cases is unchanged, which a regression test checks.
<!-- data: docs/internal/research_reports/aspen-rplug-infrastructure.md (integrated pressure 20.2 bar, H2SEED 1e-4, 0.015 kmol/h; regression test of 4 baseline text variants) -->

![**Figure 25.2.** Aspen Plus V15 main flowsheet of the integrated case with the 5Ni1Ru/CeO~2~ kinetic cracker (case ci_luc5_T572_P20_W100_hi). The CRACKER block is an RPLUG reactor; the small H2SEED stream joins the HEATER inlet. All other blocks and streams are those of the baseline flowsheet (Section 5), so the kinetic and equilibrium flowsheets differ only in the reactor. *Source: Aspen Plus V15 screenshot, cropped to the relevant part of the window.*](../../docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__01_flowsheet.png){width=100% crop=220,300,1640,720}

![**Figure 25.3.** Kinetic tab of reaction set NH3KIN for Ru/Al~2~O~3~ (case kv_ru_kum_T450_P5_W20): POWERLAW class, reversible by microscopic reversibility, k = 27623 kmol/(kg s) and E = 27281.9 cal/mol, partial-pressure basis in bar, rate basis Cat (wt), exponents 0.54 (NH~3~) and -0.81 (H~2~). These entries are Eq. (25.1) for the reaction written with stoichiometric coefficient 2, which is why k is half the published value. *Source: Aspen Plus V15 screenshot, cropped to the relevant part of the window.*](../../docs/images/aspen_evidence/kv_ru_kum_T450_P5_W20__03_reactions_kinetic_tab.png){width=85% crop=0,175,880,830}

![**Figure 25.4.** Kinetic tab of reaction set NH3KIN for 5Ni1Ru/CeO~2~ (case ci_luc5_T572_P20_W100_hi): LHHW class with k = 3.9 × 10^6^ kmol/(kg s) and E = 29616.9 cal/mol (124 kJ/mol), molarity basis in kmol/m^3^, forward exponent 1 for NH~3~. The adsorption term of Eq. (25.2) is entered in the Adsorption dialog, which is a pop-up and was not captured. *Source: Aspen Plus V15 screenshot, cropped to the relevant part of the window.*](../../docs/images/aspen_evidence/ci_luc5_T572_P20_W100_hi__03_reactions_kinetic_tab.png){width=85% crop=0,175,880,830}

![**Figure 25.5.** Kinetic tab for the fitted Ni/MgO approximation (case cs_OP_tni_T594_P20_W100): LHHW class, k = 766.222 kmol/(kg s), E = 20248.3 cal/mol (84.78 kJ/mol), mole-fraction basis, NH~3~ exponent 0.966. The values are those of Table 25.3; they are a Python fit, not literature parameters. *Source: Aspen Plus V15 screenshot, cropped to the relevant part of the window.*](../../docs/images/aspen_evidence/cs_OP_tni_T594_P20_W100__03_reactions_kinetic_tab.png){width=85% crop=0,175,880,830}

![**Figure 25.6.** Catalyst tab of the RPLUG block (case kv_ru_kum_T450_P5_W20): catalyst present, bed voidage 0.36 and particle density 0.98 g/cm^3^ from Kum et al. (2026, Table 1). These two values convert the catalyst mass into bed volume and residence time; the greyed particle diameter is used only when the Ergun pressure drop is switched on. *Source: Aspen Plus V15 screenshot, cropped to the relevant part of the window.*](../../docs/images/aspen_evidence/kv_ru_kum_T450_P5_W20__06_reactor_catalyst.png){width=80% crop=0,175,730,470}

## 25.4 Verification against the Python plug-flow reactor

The **Aspen Plus V15 simulation** and the **independent Python calculation** solve the same rate laws with different thermodynamics (PENG-ROB against ideal gas) and different integrators, so agreement tests the units, forms and bookkeeping of the Aspen input. Table 25.4 lists the infrastructure checks with Ru/Al~2~O~3~ and 5Ni1Ru/CeO~2~.

Table: **Table 25.4.** Aspen RPlug against the Python PFR at identical conditions (100 kmol/h NH~3~, isothermal unless stated). *Source: Aspen Plus V15 simulation and independent Python calculation, results/research/aspen_kinetic/aspen_vs_python.csv.*

| Case | Conditions | X Aspen | X Python | Remark |
|---|---|---|---|---|
| 9 isothermal points, Ru/Al~2~O~3~ | 400/450/500 °C × 2/5/10 bar, 20 kg | 0.1609-0.7592 | 0.1608-0.7590 | largest difference 2.3 × 10^-4^; duty within 0.7 % |
| kv_ru_kum_T450_P10_W500_neareq | 450 °C, 10 bar, 500 kg | 0.95681 | 0.95735 | RGibbs in the same model: 0.95726 |
| kv_ru_kum_T450_P5_W20_adiabatic_ergun | inlet 450 °C, 5 bar, 20 kg, Ergun | 0.10196 | 0.10209 | outlet 339.30 against 339.37 °C |
| kv_ru_kum_T450_P5_W100_coolant | inlet 450 °C, 5 bar, 100 kg, coolant | 0.17317 | 0.17342 | outlet 340.47 against 340.58 °C |
| kl_ru_kum_lhhw_T450_P5_W20 | Ru/Al~2~O~3~ entered as LHHW | 0.37680 | 0.37668 | same as the POWERLAW entry |
| kl_nire_5ni1ru_T450_P1_W100 | 5Ni1Ru/CeO~2~, 450 °C, 1.013 bar, 100 kg | 0.37695 | 0.37671 | LHHW, molarity basis |

<!-- data: results/research/aspen_kinetic/aspen_vs_python.csv all rows (X_aspen, X_python, dX, X_eq_aspen_rgibbs, T_out_aspen_C, T_out_python_C, duty_aspen_kW, heat_python_kW) -->

The catalyst studies extended the check to all five catalysts. At the 24 reference points of the kinetics specification the three native laws agree with the Python value within 7 × 10^-4^ in conversion against a tolerance of 0.005, and the Takahashi approximations agree within 2 × 10^-4^ with the Python evaluation of the same approximation. Against the published microkinetic law itself the approximation differs by up to 0.034 (Ni) and 0.019 (Ru) at the reference points; the study runs at very small catalyst loadings show larger differences, for example 0.5735 in Aspen against 0.5082 for the published Ru/MgO law at 600 °C and 5 kg. The approximation is therefore adequate near the operating points used in Section 26 and not at short contact times. In total the Aspen kinetic validation file holds {{VAL:validation/summary.json#areas/aspen_kinetic/total}} items: {{VAL:validation/summary.json#areas/aspen_kinetic/pass}} pass, {{VAL:validation/summary.json#areas/aspen_kinetic/fail}} fail and {{VAL:validation/summary.json#areas/aspen_kinetic/informational}} are informational (read from the validation summary at build time; the failures are explained in Section 38.2).
<!-- data: results/research/validation/aspen_kinetic.json (190 items: pass 163, fail 5, informational 22; cat_* items); summary.json areas.aspen_kinetic; results/research/aspen_kinetic/catalyst_standalone_runs.csv row cs_W_tru_T600_P20_W5 (X_aspen 0.57349, X_python 0.50820) -->

## 25.5 Three runs above equilibrium

Each standalone model checks that the RPlug conversion does not exceed the RGibbs conversion in the same model with the same feed, with a tolerance of 10^-4^. This check fails for 5Ni1Ru/CeO~2~ and 2.5Ni0.5Ru/CeO~2~ by up to 4.9 × 10^-4^ and for the Ru/MgO approximation by up to 1.6 × 10^-4^, in each case at conditions where the bed reaches equilibrium (for example 0.9809 against 0.9808 at 600 °C and 20 bar), with the largest excess at 40 bar. The cause is a model-form difference, not a numerical error: the reverse term of the LHHW forms uses the ideal-gas $K_p$ of the specification with concentrations or mole fractions, while RGibbs minimises the Gibbs energy with PENG-ROB fugacities. The POWERLAW form for Ru/Al~2~O~3~ computes its reverse rate from Aspen's own equilibrium and does not fail. Nothing was tuned to remove the failures. The excess is two orders of magnitude below the conversion differences between catalysts that Section 26 relies on.
<!-- data: results/research/validation/aspen_kinetic.json items cat_nire_ceo2_5ni1ru_lucentini_lhhw_below_equilibrium (observed 4.874e-4), cat_nire_ceo2_2p5ni0p5ru_lucentini_lhhw_below_equilibrium (4.874e-4), cat_ru_takahashi_microkinetic_below_equilibrium (1.604e-4), tolerance 1e-4; catalyst_standalone_runs.csv cs_T_luc5 600 degC (0.98092 vs 0.98081) -->

## 25.6 Kinetic studies

All studies use 100 kmol/h of pure NH~3~ and an isothermal bed without pressure drop unless stated. Conversions are **Aspen Plus V15 simulation** results; the Takahashi rows use the approximation of Table 25.3.

**Conversion against temperature.** At 20 bar and 100 kg of catalyst (Table 25.5, Figure 25.7), Ru/Al~2~O~3~ is within 0.2 % of equilibrium from 500 °C, while the Ni-Ru/CeO~2~ laws convert only 4-5 % at 450 °C and need about 600 °C to reach equilibrium. Above 650 °C every catalyst is at equilibrium, so activity no longer matters.

Table: **Table 25.5.** NH~3~ conversion against temperature at 20 bar and 100 kg catalyst per 100 kmol/h NH~3~, with the RGibbs equilibrium in the same model. *Source: Aspen Plus V15 simulation, results/research/aspen_kinetic/catalyst_standalone_runs.csv (group cs_T).*

| T (°C) | Equilibrium | Ru/Al~2~O~3~ | Ru/MgO (approx.) | 5Ni1Ru/CeO~2~ | 2.5Ni0.5Ru/CeO~2~ | Ni/MgO (approx.) |
|---|---|---|---|---|---|---|
| 450 | 0.9194 | 0.6833 | 0.5188 | 0.0405 | 0.0534 | 0.1204 |
| 500 | 0.9521 | 0.9508 | 0.8842 | 0.1692 | 0.1881 | 0.3304 |
| 550 | 0.9703 | 0.9700 | 0.9703 | 0.6667 | 0.6348 | 0.7123 |
| 600 | 0.9808 | 0.9806 | 0.9808 | 0.9809 | 0.9808 | 0.9692 |
| 650 | 0.9871 | 0.9869 | 0.9871 | 0.9872 | 0.9872 | 0.9871 |
| 700 | 0.9910 | 0.9909 | 0.9910 | 0.9910 | 0.9910 | 0.9910 |

<!-- data: results/research/aspen_kinetic/catalyst_standalone_runs.csv group cs_T: X_aspen, X_eq_aspen_rgibbs -->

![**Figure 25.7.** NH~3~ conversion against temperature for the five catalysts in Aspen RPlug at 20 bar and 100 kg catalyst, with the RGibbs equilibrium curve. The gap between a catalyst curve and the equilibrium curve is the kinetic limitation; it closes for every catalyst above about 600-650 °C. *Source: Aspen Plus V15 simulation.*](../../results/figures/research/aspen_kinetic_conversion_vs_T.png){width=85%}

**Conversion against pressure.** At 550 °C and 100 kg (Figure 25.8), raising the pressure from 1.013 to 40 bar lowers the equilibrium conversion from 0.9984 to 0.9429. Ru/Al~2~O~3~ follows equilibrium at every pressure, while the Ni-Ru/CeO~2~ laws fall from 0.995-0.996 at 1.013 bar to 0.31-0.33 at 40 bar. Their hydrogen inhibition is written in concentrations, which rise with pressure, so these laws become much slower at high pressure. All of this is extrapolation: the laws were fitted at 1 atm.
<!-- data: catalyst_standalone_runs.csv group cs_P (kum 0.99838/0.94251; luc5 0.99543/0.33138; luc25 0.99607/0.30833; X_eq 0.99840/0.94290) -->

![**Figure 25.8.** NH~3~ conversion against pressure at 550 °C and 100 kg for the three catalysts with native rate laws, with the RGibbs equilibrium. Pressure reduces the equilibrium conversion slightly and the Ni-Ru/CeO~2~ rates strongly. *Source: Aspen Plus V15 simulation.*](../../results/figures/research/aspen_kinetic_conversion_vs_P.png){width=85%}

**Catalyst loading and space velocity.** At 600 °C and 20 bar (Figure 25.9), 20 kg of Ru/Al~2~O~3~ (gas hourly space velocity of NH~3~ at standard conditions, GHSV, about 70 300 h^-1^) already reaches equilibrium, while 5Ni1Ru/CeO~2~ reaches 0.925 with 50 kg and equilibrium only with 200 kg. The catalyst mass needed for 95 % and 99 % of the equilibrium conversion, confirmed in Aspen at the Python-derived masses within 0.002 for the native laws, is listed in Table 25.6.
<!-- data: catalyst_standalone_runs.csv group cs_W (kum W20 0.98059, GHSV 70290; luc5 W50 0.92510, W200 0.98092); results/research/validation/aspen_kinetic.json cat_*mass_target* items -->

Table: **Table 25.6.** Operating point and catalyst demand at 20 bar per 100 kmol/h NH~3~. T~op~ is the lowest isothermal temperature at which 100 kg of catalyst gives 95 % conversion. *Source: Aspen Plus V15 simulation (X, bed volume, GHSV, mass checks) and independent Python calculation (T~op~, masses), results/research/aspen_kinetic/catalyst_comparison.json rows and catalyst_mass_targets.json.*

| Catalyst | T~op~ (°C) | X at T~op~ (Aspen) | Bed volume (m^3^) | GHSV (h^-1^) | Mass for 95 / 99 % of equilibrium at 600 °C (kg) | at 500 °C (kg) |
|---|---|---|---|---|---|---|
| Ru/Al~2~O~3~ | 499 | 0.950 | 0.159 | 14 058 | 8.9 / 11.2 | 63 / 81 |
| Ru/MgO (approx.) | 522 | 0.953 | 0.159 | 14 058 | 15.8 / 20.8 | 113 / 167 |
| 5Ni1Ru/CeO~2~ | 572 | 0.953 | 0.095 | 23 695 | 50.9 / 61.1 | 501 / 599 |
| 2.5Ni0.5Ru/CeO~2~ | 576 | 0.952 | 0.095 | 23 695 | 60.1 / 71.2 | 438 / 519 |
| Ni/MgO (approx.) | 594 | 0.959 | 0.159 | 14 058 | 69.9 / 104.2 | 1355 / 2314 |

<!-- data: results/research/aspen_kinetic/catalyst_comparison.json rows[].operating_temperature_C, X_standalone_at_operating_T, bed_volume_m3, GHSV_NH3_STP_h-1, W_for_95pct_eq_600C_kg, W_for_99pct_eq_600C_kg; catalyst_standalone_runs.csv group cs_M (W_kg 63.18/80.54, 112.77/166.53, 500.88/599.27, 437.86/518.53, 1355.19/2313.51) -->

![**Figure 25.9.** Approach to equilibrium (Aspen conversion divided by the RGibbs conversion) against catalyst loading at 600 °C and 20 bar for the five catalysts. The loading needed to reach equilibrium differs by about an order of magnitude between Ru/Al~2~O~3~ and the slowest catalysts. *Source: Aspen Plus V15 simulation.*](../../results/figures/research/aspen_kinetic_approach_vs_loading.png){width=85%}

**Kinetic against equilibrium temperature.** The temperature needed for 95 % conversion at 20 bar with 100 kg spans 498-593 °C, against an equilibrium minimum of 495.5 °C. For 99 % conversion at 20 bar the equilibrium itself requires 684.8 °C, and every catalyst reaches 99 % at that temperature with 100 kg. At the baseline pressure, therefore, catalyst activity cannot lower the cracker temperature for a 99 % conversion target; it can only do so for lower targets or lower pressures. This is why Section 26 compares catalysts at 95 %.
<!-- data: results/research/kinetics/study_temperature_for_target_conversion.json rows (P_bar 20, W_cat_kg 100): X_target 0.95 T_required_C 498.3-593.3, T_equilibrium_min_C 495.5; X_target 0.99 T_required_C 684.8 for all -->

![**Figure 25.10.** Operating points of the five catalysts at 20 bar and 100 kg: the temperature at which each reaches 95 % conversion, with the corresponding Aspen conversion and equilibrium conversion. *Source: Aspen Plus V15 simulation; independent Python calculation for the temperatures.*](../../results/figures/research/aspen_kinetic_operating_point.png){width=85%}

**Adiabatic bed.** With an inlet temperature of 650 °C, 20 bar and 100 kg, a single adiabatic bed converts only 0.20-0.30 of the NH~3~ before the endothermic reaction cools the gas to 339-442 °C, where the rate stops (Table 25.7, Figure 25.11). Ammonia cracking therefore needs heat supplied along the bed, as in a fired tubular reactor, or several beds with interstage heating; the isothermal results above assume that this heat can be delivered.

Table: **Table 25.7.** Adiabatic RPlug, inlet 650 °C, 20 bar, 100 kg, no pressure drop. *Source: Aspen Plus V15 simulation, results/research/aspen_kinetic/catalyst_standalone_runs.csv (group cs_AD).*

| Catalyst | Conversion | Outlet T (°C) | Python conversion |
|---|---|---|---|
| Ru/Al~2~O~3~ | 0.303 | 338.7 | 0.304 |
| Ru/MgO (approx.) | 0.285 | 358.3 | 0.286 |
| 5Ni1Ru/CeO~2~ | 0.204 | 441.8 | 0.204 |
| 2.5Ni0.5Ru/CeO~2~ | 0.211 | 434.5 | 0.211 |
| Ni/MgO (approx.) | 0.211 | 434.0 | 0.216 |

<!-- data: catalyst_standalone_runs.csv group cs_AD: X_aspen, T_out_C, X_python -->

![**Figure 25.11.** Axial profile of the adiabatic Ru/Al~2~O~3~ bed (case cs_AD_kum_Tin650_P20_W100, RXR Profiles form): the temperature falls from 650 °C to about 459 °C within the first 5 mm and to about 369 °C at 87 mm, at constant pressure. The steep initial drop shows that the reaction is limited by heat supply, not by catalyst activity. *Source: Aspen Plus V15 screenshot, cropped to the relevant part of the window.*](../../docs/images/aspen_evidence/cs_AD_kum_Tin650_P20_W100__09_reactor_profiles.png){width=80% crop=200,195,880,810}

## 25.7 Kinetic cracker in the full flowsheet

With Ru/Al~2~O~3~ at 600 °C, 20 bar and 200 kg, the integrated flowsheet gives an NH~3~ conversion of 0.98041 against 0.98081 for the stored RGibbs baseline, an external heating of 2292.5 kW against 2293.1 kW and an LHV efficiency of 0.8773 against 0.8772; without heat integration the heating is 2904.8 kW and the efficiency 0.8244 (Figure 25.12). The kinetic cracker reproduces the equilibrium flowsheet where it should, which confirms that replacing the reactor changes nothing else. This case lies above the 450 °C fit limit of the law, so it verifies the tooling, not the catalyst. The ten integrated catalyst cases of Section 26 use the same set-up at each catalyst's T~op~.
<!-- data: results/research/aspen_kinetic/ki_ru_kum_T600_P20_W200_hi.json aspen.flowsheet_result.kpis (nh3_conversion 0.980414, total_external_heating_kW 2292.538, lhv_efficiency 0.877251, reactor_duty_kW 1479.420); ki_ru_kum_T600_P20_W200_nohi.json (2904.752, 0.824421); results/simulations/baseline.json kpis (0.980810, 2293.117, 0.877202) -->

![**Figure 25.12.** Results summary of the RPLUG CRACKER in the integrated Ru/Al~2~O~3~ case (ki_ru_kum_T600_P20_W200_hi): heat duty 1479.42 kW at a constant 600 °C and a residence time of 1.62 × 10^-4^ h (0.58 s). The duty is within 0.04 % of the 1480.0 kW of the RGibbs cracker, because the bed reaches equilibrium. *Source: Aspen Plus V15 screenshot, cropped to the relevant part of the window.*](../../docs/images/aspen_evidence/ki_ru_kum_T600_P20_W200_hi__08_reactor_results.png){width=75% crop=0,175,600,440}

## 25.8 Limitations

* **Extrapolation.** Every law is used outside its fitted pressure range at 20 bar, and the Ru/Al~2~O~3~ law also above its 450 °C temperature limit at most operating points. The Takahashi results come from a 20-bar approximation of a 1-atm law.
* **Effectiveness factor 1.** Powder kinetics are applied to an industrial bed without pore diffusion, external transfer or radial gradients, so all catalyst masses are lower bounds.
* **Approach factor.** The equilibrium approach factor applied to the irreversible Lucentini law is an AmCraX assumption.
* **Reverse term.** The LHHW reverse term uses an ideal-gas $K_p$, which causes the three small above-equilibrium failures of Section 25.5.
* **No user kinetics.** The Takahashi microkinetic laws could not be implemented exactly without a Fortran user subroutine.
* **Isothermal operating points.** The catalyst comparison assumes the reaction heat can be supplied at the bed temperature; the adiabatic results show that a real reactor needs a fired or multi-bed design, which is not modelled.
* **Not covered.** No Aspen Sensitivity block can vary the RPlug temperature in the integrated flowsheet, so all sweeps are separate runs. Two LHHW dialogs (driving force, adsorption) are pop-ups and were not captured as screenshots.
