# xu2025review - Xu et al. (2025) Review: ammonia catalytic cracking and waste-heat reforming

## Bibliographic data
- Authors: Qi-Yu Xu, Yi-Feng Chen (corresp.), Ning-Ning Yao, Jia-Kai Zhang, Yimin Huang, Dong Han, Wei-Guo Pan (corresp.)
- Title: Recent advancements in ammonia catalytic cracking and waste heat reforming technologies: A review
- Journal: Energy Conversion and Management, vol. 326 (2025), article 119530
- Received 6 Nov 2024; revised 10 Jan 2025; accepted 15 Jan 2025; online 23 Jan 2025 (p. 1)
- DOI: 10.1016/j.enconman.2025.119530 (verified via doi.org handle API, responseCode 1, resolves to PII S0196890425000536)
- APA 7: Xu, Q.-Y., Chen, Y.-F., Yao, N.-N., Zhang, J.-K., Huang, Y., Han, D., & Pan, W.-G. (2025). Recent advancements in ammonia catalytic cracking and waste heat reforming technologies: A review. *Energy Conversion and Management, 326*, 119530. https://doi.org/10.1016/j.enconman.2025.119530
- Type: review (41 PDF pages; references start on p. 34)

## Scope
Review of (i) thermodynamics and mechanisms of NH3 decomposition, (ii) kinetic model families, (iii) Ru / other noble, Ni, Co, Fe, Mo and multi-metallic catalysts (Tables 3-5), (iv) waste-heat NH3 reforming for internal-combustion engines and gas turbines (Sec. 4, Table 6), (v) a short techno-economic section (Sec. 5) and perspectives incl. deactivation (Table 7). It is a secondary source: almost every number is quoted from cited work. **Nothing here is an original measurement of the review authors.** Cite the original source (given below) wherever possible.

## Thermodynamics (Sec. 2.1, p. 5-6)
- Eq. (1), p. 5: `2NH3 <-> N2 + 3H2,  ΔH298 = 91.2 kJ mol-1`. Text: "enthalpy change of 91.2 kJ/mol". The basis is per 2 mol NH3 as written, i.e. 45.6 kJ per mol NH3. **Ambiguity:** "kJ mol-1" with no stated basis. Also note 45.6 kJ/mol NH3 is slightly below the NIST-JANAF value 45.9 kJ/mol (ΔfH NH3(g) = -45.90 kJ/mol). The review gives no source for 91.2.
- Eq. (8), p. 7: `NH3 -> 1/2 N2 + 3/2 H2` (per-mole-NH3 form, no ΔH given).
- Oxidative decomposition, p. 6: Eq. (2) `NH3 + 0.25 O2 -> H2 + 0.5 N2 + 0.5 H2O, ΔH = -75 kJ mol-1`. Eq. (3) `NH3 + 0.75 O2 -> 0.5 N2 + 1.5 H2O, ΔH = -317 kJ mol-1` (refs [67],[80]).
- Equilibrium conversion, Fig. 4(a), p. 6 ("Data from [37]" = Sun S. et al., Renew. Sustain. Energy Rev. 2022, 169:112918, doi 10.1016/j.rser.2022.112918). Curves for 0.1, 0.8, 1.0, 2.0, 3.0 MPa, 0-700 °C.
  - Text (p. 5): at atmospheric pressure the equilibrium conversion "reaches 99 % at 400 °C", and it is strongly sensitive to T and P between 0 and 400 °C.
  - Read from figure, approximate (±2-3 percentage points): 0.1 MPa: about 20 % at 100 °C, 48 % at 150 °C, 74 % at 200 °C, 89 % at 250 °C, 95 % at 300 °C, 98 % at 350 °C. 3.0 MPa: about 20 % at 200 °C, 35 % at 250 °C, 52 % at 300 °C, 69 % at 350 °C, about 80 % at 400 °C, about 92 % at 500 °C, about 97 % at 600 °C, about 98 % at 700 °C. 0.8 to 2.0 MPa lie between those curves.
- Fig. 22(a,b), p. 31 (reprinted from Pashchenko 2024 [70]), text p. 30: H2 share in the product gas is about 73 % at 300 °C and 1 bar, and about 59 % at 300 °C and 20 bar. It is below 50 % at 200 °C and about 75 % at 400 °C (pressure not stated for these two). Note that 75 % H2 is the complete-conversion limit (3/(1+3)).
- Pashchenko et al. [318,319] (p. 29): there is a heat deficit at low pressure (1-10 bar) in TCR systems. They recommend NH3 at ≥20 bar for industrial practice.

## Mechanism (p. 5-10)
- Elementary steps, Fig. 4(c), p. 6:
  - R1 `NH3 + * <-> NH3*`
  - R2 `NH3* + * -> NH2* + H*`
  - R3 `NH2* + * -> NH* + H*`
  - R4 `NH* + * -> N* + H*`
  - R5 `2N* -> N2 + 2*`
  - R6 `2H* -> H2 + 2*`
- Activity order (p. 4, from Ganley et al. 2004 [65], Catal. Lett. 96:117-122, doi 10.1023/b:catl.0000030108.50691.d4): Ru > Ni > Rh > Co > Ir > Fe > Pt > Pd > Cu > Te, Se, Pb.
- Rate-determining step (p. 8, Fig. 4(b) from [65]): N-H scission limits the rate on noble metals. N2 desorption (N-N recombination) limits it on non-noble metals. The RDS shifts with T, P and catalyst. H2 inhibition (negative H2 order) is stronger at lower temperature (p. 8, citing Takahashi & Fujitani 2016 [99], J. Chem. Eng. Jpn. 49:22-28, doi 10.1252/jcej.14we431).
- DFT values quoted (p. 8-9). These are for reference only and are not used by AmCraX. Co-doped graphene initial dehydrogenation barrier 0.98 eV [101]. CeO2/Ni inverse structure: NH3 adsorption -1.021 eV on Ni(111) vs -0.152 eV at the CeO2/Ni interface; N recombination -0.315 eV; N2 desorption -0.524 eV [103].

## Kinetic models (Sec. 2.2.1, Fig. 6, p. 8; equations read from the figure image, PDF p. 8)
In Fig. 6, P is the partial pressure of a component. **The review gives no fitted parameter values except the Tamaru constants.**
1. First order (ref [94] Maleki et al. 2021, Chem. Eng. J. 411:128595): `r = k * P_NH3`. k = rate constant.
2. Zero/first-order combination (ref [95] McCabe 1983, J. Catal. 79:445-450, doi 10.1016/0021-9517(83)90337-8, kinetics on Ni):
   `r = [k1 k2 P_NH3/(k_-1 + k2)] / [1 + k1 k2 P_NH3/(n0 k5 (k_-1 + k2))]`
   - Low-temperature limit: `r = n0 k5`. High-temperature limit: `r = k1 P_NH3`.
   - k1 = NH3 adsorption rate constant; k_-1 = NH3 desorption rate constant; k2 = NH3 decomposition rate constant; k5 = N2 desorption rate constant; n0 = surface atom density of the metal catalyst.
3. Langmuir-Hinshelwood (LHHW) (refs [96] Itoh et al. 2014, Catal. Today 236:70-76, doi 10.1016/j.cattod.2014.02.054; [97] Zhang et al. 2019, ACS Sustain. Chem. Eng. 7:5975-5985, doi 10.1021/acssuschemeng.8b06065):
   `r = k_F (P_NH3^2 - P_H2^3 P_N2 / K_p) / (P_H2^1.5 + sqrt(K_N P_NH3^2))^2`
   - k_F [mmol s/(kg-cat MPa)] = kinetic constant. **The unit is printed this way and looks dimensionally odd. Check against the original source.**
   - K_N [MPa] = adsorption equilibrium constant. K_p [MPa^2] = equilibrium constant in pressure terms. K_p is for 2NH3 = N2 + 3H2, since MPa^2 matches that stoichiometry.
4. Temkin-Pyzhev: `r = k p^alpha(NH3) p^beta(H2) p^gamma(N2)`, with alpha > 0 and beta, gamma < 0 as printed. The text says N2 has no effect.
5. Tamaru (ref [98] Tamaru 1988, Acc. Chem. Res. 21:88-94, doi 10.1021/ar00146a007): `r = k_R K P_NH3 / (1 + K P_NH3)`
   - `k_R = 1.57e28 exp(-49600/RT)` molecule cm^-2 s^-1
   - `K = 6.7e-9 exp(39600/RT)` Torr^-1
   - **Unit of R not stated.** 49600 and 39600 are almost certainly cal/mol (R = 1.987 cal/mol/K), because Tamaru-era work used cal. This is an inference and needs checking against Tamaru 1988. P_NH3 is in Torr.

## Catalysts and operating windows
- General statements (p. 4): most cracking catalysts need about 600 °C for complete conversion. The low-temperature target is 400-500 °C. Ru is the most active but costly. Ni is "considered the best" non-noble material, with "energy efficiency comparable to that of Ru" (p. 15). Ni problems: sintering/agglomeration at high T and low activity at low T (p. 15).
- Ru particle size (p. 10): optimum about 3-5 nm (<8 nm) [38]. Elongated particles peak in B5 sites near 7 nm. Hemispherical particles peak at 1.8-3 nm [118,119]. Ru/MgO(111) TOF 2.90 s^-1 at about 2 nm [100] (p. 11).
- Table 3 (p. 11), Ru examples. Columns: wt% metal; T (°C); SV mL/(h gcat); X_NH3 (%); H2 formation rate mmol/(min gcat).
  - Ru/κ-Al2O3: 1.0; 400; 60,000; 41.0; 230.0 [118]
  - Ru/θ-Al2O3: 1.0; 400; 60,000; 40.1; 150.0 [118]
  - Ru/SiC: 2.5; 400; 60,000; 99.3; 83.4 [119]
  - Ru/MgO(111): 3.1; 450; 60,000; 82.2; 1777.4 [100]
  - Ru(NN)/Al/M: 3.0; 600; "100*" (asterisk unit not checked); 100.0 [136]
  - **Caution:** some rows look internally inconsistent. The Ru/κ-Al2O3 H2 rate of 230 is not compatible with 41 % conversion at 60,000 mL/(h g) of pure NH3 (that would give about 27 mmol/(min g)). Do not use Table 3 for kinetics.
- Table 4 (p. 16), Ni examples (same columns):
  - Ni3Mg7Ce0.3: -; 550; 66,000; 78.3; 57.6 [105]
  - Ni/CeO2-BN: 9.5; 600; 30,000; 89.0; 29.8 [189]
  - Ni-CeO2 (CSCS-3.0): 10; 550; 30,000; 80.4; 26.9 [190]
  - CeO2/Ni: 60; 500; 30,000; 72.4; 24.3 [103]
  - Ni/SBA-15-80: 40; 550; 30,000; 92.2; 30.9 [191]
  - Ni/SrY: 9.36; 600; 9000; 98.0; 9.8 [196]
  - Ni/Al0.5Ce0.5Ox: 10; 600; 30,000; <40.0; 21.79 [203]
  - Ni/CaNH-HS: 10; 500; 30,000; 58.6; 19.6 [92]
  - Cross-check: 30,000 mL/(h g) pure NH3 = 22.3 mmol NH3/(min g), so 100 % conversion gives 33.5 mmol H2/(min g). The Ni rows are roughly consistent.
- Deactivation (Table 7, p. 33-34): high-T sintering of Ni/Co/Fe (lower melting points than noble metals). Mitigations: strong metal-support interaction (CeO2), embedded/core-shell structures.

## Reactor types, demonstrations and commercial-scale items (Sec. 4-5)
- Reformer hydrogen production efficiency (unnumbered equation, p. 26, from Cha et al. 2021 [287], Renew. Sustain. Energy Rev. 152:111562, doi 10.1016/j.rser.2021.111562):
  `eta_T(%) = V_H2,product * LHV_H2 / (V_NH3,reactant * LHV_NH3 + V_fuel * LHV_fuel) * 100`
  - V = flow rate (L/min) of product H2, reactant NH3 and heat-source fuel. LHV in kJ/L.
- Cha et al. [287] (p. 31):
  - Catalyst and reactor: Ru/La-Al2O3 pellets in a 12-sided scalable reformer. The text says "chalcogenide structure"; this is probably a mistranslation of perovskite. Ambiguous.
  - Activity at 450 °C and 2827 h^-1. Stability >6700 h at 550 °C with activity >99.7 %.
  - Output: 66 L/min H2 continuously for 2 h, with NH3 conversion >99 %.
  - Reforming efficiency 83.6 % ("highest value among all current reports").
  - Conversion drops when NH3 flow exceeds 21 L/min. To keep conversion >99.9 % at a system energy input of 124.6 kJ/min, NH3 flow should stay below 21 L/min at 80 % reformer efficiency.
  - Minimum H2 selling price 7.03 USD/kg (10 kW) to 3.98 USD/kg (10 MW).
- Realpe et al. 2024 [323] (Appl. Energy 376:124244, doi 10.1016/j.apenergy.2024.124244) (p. 30). This is a simulation/design study (the review says "demonstrated").
  - Plant: an industrial top-fired multi-tube methane steam reformer repurposed as an NH3 cracker with a Co-Ba-Ce catalyst. 98 % NH3 conversion and 7000 Nm3/h H2.
  - Heat integration (adiabatic pre-cracker plus cracker, with the outlet stream preheating the feed) raises overall process energy efficiency from 65.7 % to 75.3 %.
  - The pre-cracker cuts the total heat load by about 15 % but slightly raises the main-cracker maximum temperature.
  - Hollow-cylinder pellets: average heat demand per tube 5 % lower than spheres, and maximum wall/solids temperature about 25 °C lower.
- Sitar et al. 2024 [324] (Renew. Sustain. Energy Rev. 199:114469, doi 10.1016/j.rser.2024.114469) (p. 31). Aspen Plus TEA of a packed-bed reactor vs a catalytic membrane reformer (CMR).
  - Scaling from 0.1 to 10 MW cuts NH3 treatment cost by 30 %. With heat recovery the CMR cost falls by a factor of 2.7-7.2, to <0.5 USD/kg H2.
  - At 0.1 MW (H2 10-50 vol %, 1-50 bar), the fuel blend costs 2.9 USD/thm.
- Gas turbines (p. 29-30):
  - Pashchenko et al. [319]: Ru-catalyst TCR with a gas turbine. Waste-heat recovery rate up to 43 %, especially above 800 °C.
  - Su et al. 2023 [320] (Appl. Energy 343:121184): Capstone C200 microturbine with a chemically recuperated dual-fuel cycle. Thermal efficiency rises from 29.16-31.79 % to 35.48-36.09 %. Cracking heat is 34.5 kW at 84.51 % conversion, plus 14.9 kW for liquid NH3 evaporation. 309.4 kW of waste heat goes unused.
  - Malenkov et al. 2022 [321]: Ni/Al2O3 catalyst, Aspen Plus, large-scale unit with a heat-recovery steam turbine cycle. About 70 % cracking with a 1100 °C heating-gas inlet temperature.
  - Pashchenko 2024 [70]: TCR raises average NH3 gas turbine efficiency by 5-7 % and lowers the optimal pressure ratio.
  - Required cracking extents: 30-40 % for stable gas-turbine combustion [58,71]. For ICEs, 5-10 % H2 is enough, which corresponds to 3-7 % NH3 cracking [72,73] (p. 5).
- ICE waste heat (Table 6, p. 27):
  - SI exhaust is 400-600 °C (p. 26).
  - Comotti & Frigo 2015 [293]: Ru/Al2O3 at 600 °C and 0.4-2.5 bar; 98.0 % maximum conversion; 1.4 Nm3/h H2; BTE +1.5 % at 3500 rpm. The text says "NH3 flow rate of 1.4 Nm3/h", but Table 6 says the H2 production flow is 1.4 Nm3/h. **Inconsistent within the review.**
  - Li et al. 2024 [314]: Ru/Al2O3 at 299-599 °C, 1 and 3 bar, GHSV 2000-4000 h^-1. Maximum conversion 92.0 %; peak "reforming efficiency" 112.5 %, with efficiency definitions differing between papers. Efficiency falls as pressure and GHSV rise.
  - Sittichompoo et al. 2021 [303]: Rh-Pt at 450-650 °C and 1 bar; fuel economy +30 %.
  - Kim et al. [294,295] micro-reformer with a thermally cycled micro-combustor: >95 % conversion; 20.1 mL/min reformed gas = 5.4 W (LHV); overall efficiency 13.7 % / 10.4 %; NOx 158 ppm.
  - Korea Institute of Machinery & Materials reactor: about 15 L/min H2 for a 10 kW NH3-H2 engine [68] (p. 26).
  - Wang et al. [304]: autothermal reforming (ATR) on Ru with diesel exhaust; about 40 % / 56 % conversion at 500 / 600 °C.
  - Jiang et al. 2024 [307]: Fe-Co-Ni on porous ceramic; cracking rises from 23.6 % to 58.0 % as T goes from 450 to 500 °C.
- Pressure (p. 27): most reported cracking runs at atmospheric or <10 bar.
  - Sayas et al. [299]: K-Ru-CaO at 1-40 bar. Hydrogen yield and TOF at high pressure are "40 times higher" than at atmospheric pressure. **This contradicts equilibrium intuition; probably per-volume or differential-rate, so check the original.** (Checked on 24 November 2026 against the original, `research/notes/sayas2020_full_text.md`: the plotted rates are conversion x feed per gram x pressure; at the same molar feed the NH3 converted per gram falls with pressure. The "40 times" is an artefact of that multiplication, not a larger measured output.)

## Other property data quoted (Table 1, p. 4, data from [6,53,54])
- NH3 / H2 / CH3OH / CH4:
  - LHV (MJ/kg): 18.6 / 120 / 19.8 / 50
  - Adiabatic flame temperature (°C): 1800 / 2100 / 1637 / 1950
  - Auto-ignition temperature (°C): 585 / 500-576 / 438 / 650
  - Flammability limits (vol %): 16-27 / 4.0-75 / 6.7-39 / 5-15
  - Minimum ignition energy (mJ): 8 / 0.01 / 0.14 / 0.28
- Text (p. 3): NH3 17.8 wt% H2; liquefies at 0.7-0.8 MPa (ambient T); boiling point -33.4 °C.
- Pipeline transport over 1610 km (Bartels 2008 [41]): 0.51-3.22 USD/kg H2 for H2 vs about 0.194 USD/kg H2 (0.0344 USD/kg NH3) for NH3.

## Limitations
- Secondary review. Numbers are quoted (sometimes with transcription inconsistencies, see Cautions) and should be cited from the original sources.
- Fig. 4(a) equilibrium data are only available graphically.
- Kinetic model forms are given without fitted parameters (except Tamaru), and the units for Tamaru E are not stated.
- Efficiency definitions (eta_T, "reforming efficiency" >100 %) differ between cited works.
- No pressure-specific kinetic data for Ni at the 20 bar AmCraX baseline.

## Relevance to AmCraX
- Thermodynamics check: Eq. (1) ΔH and Fig. 4(a) give qualitative or approximate cross-checks for `amcrax.thermodynamics.solve_equilibrium` (0.1 and 3.0 MPa curves). Use NIST/JANAF for primary values.
- Kinetics: Fig. 6 lists the model families. Fitted Ni/Ru parameters should come from the originals (McCabe 1983 for Ni; Takahashi & Fujitani 2016 [99]; Tamaru 1988).
- Heat integration: Realpe et al. 2024 (65.7 % -> 75.3 % with feed/effluent heat integration and pre-cracker) is a literature benchmark for the FEHE on/off comparison. Cha et al. 2021 (83.6 % reformer efficiency) gives a reformer-efficiency definition for small scale.
- Economics: Sitar 2024 and Cha 2021 MSP ranges (3.98-7.03 USD/kg H2) are literature context for LCOH. They must not be presented as AmCraX results.
- Operating windows: Ru 400-550 °C, Ni 500-600+ °C at about 1 bar in lab tests. Pashchenko's ≥20 bar recommendation supports the 20 bar baseline.
