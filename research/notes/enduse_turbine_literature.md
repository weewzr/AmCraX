# End-use turbine evidence: ammonia, hydrogen and cracked gas

Access date for every item: 23 November 2026. Data: `research/data/turbine_efficiency_literature.json` (efficiency, NOx, programmes) and `research/data/enduse_cost_literature.json` (capital cost, SCR, capacity factor, Halim status). Evidence grades: measured on engine, vendor claim, cycle simulation, review statement. No measured combined-cycle efficiency on ammonia or cracked gas was found; every efficiency below is a simulation or a vendor statement.

## 1. The key number: cracked gas minus direct ammonia, combined cycle

| Source | Cracked gas (H2/N2) | Direct NH3 | Difference | Basis | Grade |
|---|---|---|---|---|---|
| Ahmad et al. 2025 (IJHE 173, 151337), p. 9 and p. 15 | about 54 % (full cracking, exhaust-heated cracker, PR 8) | 49.12 % (vaporised NH3, case 2a); 47.7 % liquid; 48.44 % case 2b | **+4.9 pp** (4.4 to 5.4 allowing for "about 54") | LHV of NH3 feed, same 43 MW-class machine, Aspen Plus | cycle simulation |
| Karpilov, Papkov, Pashchenko 2025 (ICAE2024) | chemically recuperated cycle | same cycle without recuperation | **up to +5.5 (abstract), up to +5 (conclusion)**, unit printed as per cent | HYSYS, TIT 800 to 1200 degC, idealised | cycle simulation |
| NETL 2023 H2 report against NETL 2024 NH3 report | 66.9 % (100 % H2, steam-diluted; no cracker, no N2) | 59.6 % | +7.3 pp (not a cracked-gas value) | LHV net, same method and B32A baseline | cycle simulation |
| MHI patent US 11702988 against NETL 2024 | about 97.4 % of natural-gas gross efficiency (63 % or more) | 59.6 against 61.0 (-1.4 pp versus gas) | about -0.2 pp (cross-source, gross against net, not valid) | vendor claim against agency model | vendor claim |

**Recommended range for the modellers: central +4.9 pp, supported range +4.9 to +5.5 pp, sensitivity range 0 to +5.5 pp. Do not use +7.3 pp for cracked gas.** Positive means cracked gas gives the higher combined-cycle efficiency, with the cracker heated by turbine exhaust and the efficiency counted on the ammonia energy supplied.

**How strong is the evidence: weak to moderate.**
- For: two independent groups give the same sign and a similar size (+4.9 and up to +5 to 5.5 pp). Thermodynamics explains it: the cracking step is endothermic, uses exhaust heat that would otherwise raise low-pressure steam, and returns it as fuel heating value (about 46 kJ per mol NH3 cracked; the MHI patent gives 46 kJ without stating the basis; the MHI patent states "there is no decrease in principle efficiency due to the ammonia pyrolysis reaction").
- Against: all values are cycle simulations. The only two like-for-like comparisons use a 43 MW-class machine at PR 8 and an idealised HYSYS cycle at 800 to 1200 degC. No F- or H-class result exists. In the NETL large-machine model, direct ammonia loses only 1.4 pp against natural gas (59.6 against 61.0 percent, redesigned turbine with the same firing temperature), which leaves little room for a +5 pp gain at that scale. The Ahmad direct-ammonia baseline (49 %) is low compared with a modern large combined cycle, so the gap may shrink on a better machine. Ahmad's cracker heat duty is in a Supplementary Material that was not available. The Karpilov unit (per cent or percentage points) is not stated. The vendor patent gives no direct-ammonia comparison.
- The literature does support a sign and a bounded range for small and mid-size machines. It does not support a number for large frame machines, and no measurement exists for either fuel.

## 2. Efficiency change against natural gas on the same machine (not found as a clean number)

- NETL 2024 (ammonia, redesigned H-class-like turbine, same 1,538 degC firing temperature, LHV net): 100 % NH3 59.6 % against 61.0 % natural gas = -1.4 pp; the mixtures give 59.2 to 59.7 %. "Ammonia combined cycle has similar combined cycle efficiency values." The steam cycle is less efficient because exhaust enthalpy is lower relative to the fuel input.
- NETL 2023 (hydrogen, steam-diluted, 100 % H2 by mass): 66.9 % against 61.0 % = +5.9 pp. Steam taken from the plant's own steam cycle as a NOx diluent raises the figure; this is not dry firing.
- Retrofits of an unmodified natural-gas machine were not found in a primary source with numbers.
- Search summaries mentioned (a) 36.64 % for NH3 and 37.22 % for H2 in one simple-cycle turbine, source unidentified (do not use), and (b) "102.4 / 101.7 % of natural gas GTCC" for a cracked-gas mono-firing plant, source unidentified (do not use). The Energies 19(15):3606 abstract (255.6 MW turbine) only says efficiency falls slightly with ammonia fraction.

## 3. Programmes, status and year

| Programme | Status found | Year | Grade |
|---|---|---|---|
| Mitsubishi Power / MHI H-25 series, 40 MW class, 100 % NH3 | development announced with SCR and a new combustor, commercialisation targeted "in or around 2025"; MHI Technical Review 62(3) 2025 says an ammonia single-fired system and a high-efficiency SCR system are being developed and verified; no published efficiency or NOx; no evidence found that a commercial unit was delivered | 2021, 2025 | vendor claim |
| MHI H-25 on hydrogen | 100 % H2 dry-firing verification ongoing (2025); M501JAC (above 450 MW) verified on actual equipment at 30 vol% H2 | 2025 | vendor claim |
| IHI with GE Vernova, F-class | 18 March 2026: full-scale combustor components fired on 100 % NH3 at full-load pressure, temperature and flow; no numeric emissions; commercial target 2030 | 2026 | vendor claim |
| IHI 2 MW gas turbine and AIST 50 kW micro turbine | ammonia-methane runs; NETL reports "large-scale SCR systems were needed" | earlier (NETL 2024 p. 16-17) | review statement |
| Siemens Energy | nothing found for ammonia | n/a | not found |

The essay's "H-25 takes 30 to 60 vol% H2 in NH3-H2 blends" was not found for the H-25. A "30 to 60 % hydrogen" figure does appear in NETL's 2022 literature review as the capability of Baker Hughes turbines (mostly aeroderivatives) on hydrogen in natural gas, and Ahmad et al. cite about 30 vol% H2 for unmodified natural-gas combustors. The most likely reading is a mis-attribution (unverified).

## 4. Combustion constraints, NOx and N2O

- Ammonia: low flame speed and flame stability, high fuel-bound NOx. NETL 2024 quotes about 200 ppm (16 % O2) for a micro turbine with a conventional combustor and about 500 ppm for a small turbine with a stock combustor, both needing large SCR. Its two-stage rich-lean design calculation gives under 20 ppm (15 % O2) at the combustor outlet (design calculation, not a measurement). Ahmad et al. (Chemkin network): NO 83.8 to 116 ppmv, N2O 0.18 ppmv (liquid NH3) and 0.15 ppmv (vaporised); the paper notes Chemkin underestimates NO and cites AIST experiments at 282 and 337 ppmv. Primary N2O data for turbine-scale ammonia combustion were not found beyond this simulation, and none for cracked gas.
- Hydrogen: higher flame temperature and flashback risk. GE Vernova: NOx up to +35 % at 50 vol% H2, potentially double near 100 %; diffusion flames 200 to 600 ppm, lean premixed single digit; mitigation by a larger SCR or derating. NETL 2023: design target under 45 ppm (40 ppmvd) at 15 % O2, reducible to 2 to 3 ppm with current SCR; nitrogen-diluted fuel has higher NOx potential than steam-diluted, which bears on H2/N2 cracked gas.
- Cracked gas (H2/N2, 75/25 plus residual NH3): no turbine NOx measurement found. The MHI patent states the fuel is about 75 % H2 and 25 % N2 after removal of about 4 mol% residual ammonia from the decomposer outlet. Ahmad et al. report NOx only for direct-ammonia cases in the numbers read.
- SCR cost: the Cambridge working paper quotes 15 to 36 EUR/kW for standard SCR and up to 60 EUR/kW more for 90 % removal (secondary quote of their ref. 109). NETL 2024 lists SCR catalyst use and disposal in variable operating cost and an SCR auxiliary load of 3 to 5 kWe. SCR reagent is ammonia injected at about the NOx molar rate; for an ammonia-fuelled plant this reagent is the fuel chemical. The reagent mass and cost per unit of NOx for an ammonia plant were not found in any source read.

## 5. Heat integration of the cracker with turbine exhaust

- Ahmad et al. 2025: exhaust-heated cracker raises efficiency from 49.12 % to about 54 % at full cracking, with total capital cost 180 to 230 MUSD (+28 %), cracker about 45 MUSD; LCOE is non-monotonic in cracking fraction and the two routes are within about 1.5 % at NH3 price 320 USD/t (0.217 against 0.22 USD/kWh).
- Ahmad et al. 2024 (Energy 304, 132098; abstract only): the cracker takes a large share of the exhaust, which limits steam-turbine output.
- Karpilov et al. 2025: gain up to 5 to 5.5 %, largest below 1000 degC turbine inlet temperature.
- MHI patent: decomposer heated by steam from the exhaust-heat boilers; claims about 60 % gross against 63 % or more for gas.
- Su et al. 2023 (via the Xu 2025 review): microturbine 29.16 to 31.79 % rising to 35.48 to 36.09 % with chemical recuperation; Pashchenko 2024 (via review): 5 to 7 % gain; Shen et al. 2023 (search summary of an abstract, not opened): 56.7 % peak net electrical efficiency, 20.6 pp above an ammonia Brayton cycle. These are not combined-cycle like-for-like and are not used for the range.
- Richard et al. 2024: no heat integration with the combined cycle was modelled.

## 6. Capital cost and capacity factor

- NETL 2024: ammonia combined-cycle total plant cost 12 to 16 % above natural-gas combined cycle; LCOE about 3.3 times NGCC without capture and about 2 times NGCC with 97 % capture at NH3 USD 0.39/kg; fuel dominates. NETL 2023: 100 % hydrogen LCOE about 2.9 times (no capture) and 1.8 times (97 % capture).
- Cambridge working paper: capital uplift assumed 7.98 % for hydrogen and 11.34 % for ammonia (assumptions, not a cost build-up).
- Ahmad et al.: TCI 179 to 189 MUSD at 43 MW, WACC 10 %, 25 years; capacity factor not stated.
- Capacity factor: NETL runs its sensitivity from 10 % because such plants may back up renewables; its base value was not located. A sourced capacity factor for an ammonia or hydrogen combined cycle was not found.
- Capital cost of a hydrogen-fired against ammonia-fired combined cycle at equal output was not found as a like-for-like number.

## 7. Halim et al. (2025), Applied Energy 386, 125581

Full text not accessible (the repository record offers "request a copy" only; publisher page not opened). Abstract read: direct ammonia use is economically preferable to cracking because cracking has high capital and operating cost; green ammonia is near zero emission either way; coal-derived ammonia could exceed Singapore's grid emissions when cracked; blue ammonia from steam methane reforming is a transitional option. The numbers 60.1 MW, LCOH 15.1 and 10.1 USD/kg, "about 40 per cent cheaper" and "30 to 60 vol% H2 for the H-25" are **not** in the abstract and could not be located. DOI resolves (Crossref). No location can be given for any of them.

## Gaps

- No measured data on cracked-gas or ammonia combined cycles; no F- or H-class cracked-gas simulation; no ammonia SCR reagent cost; no capacity factor base case.
- Publisher pages for Pashchenko 2024, Shen 2023, Su 2023, Ahmad 2024, Jeong and Kim 2025, the Heliyon 2024 study, and Energies 18(15):4103 and 19(15):3606 returned HTTP 403 to automated access; only abstracts or summaries were seen for some.
- Ahmad 2025 Supplementary Material (cracker duty) not available.
