# hansen2024hysys

## Bibliographic data
- **Authors:** Per Morten Hansen, Chinthaka Attanayake, Vahid Farrokhi, Mohsen Gholizadefalah, Ladan Samaei, Zahra Sanidanesh, Lars Erik Øi (University of South-Eastern Norway).
- **Author-name variant:** this paper spells the third author "Farrokhi". The follow-up paper spells it "Farokhi".
- **Title:** Simulation of Ammonia Cracker Process with Aspen HYSYS.
- **Published in:** Proceedings of SIMS EUROSIM 2024, Oulu, Finland, 11-12 September 2024. Linköping Electronic Conference Proceedings 212, pp. 79-84.
- **DOI:** 10.3384/ecp212.011. Verified through the doi.org handle API (responseCode 1). The DOI resolves to https://ecp.ep.liu.se/index.php/sims/article/view/1069.
- **APA 7 reference:** Hansen, P. M., Attanayake, C., Farrokhi, V., Gholizadefalah, M., Samaei, L., Sanidanesh, Z., & Øi, L. E. (2024). Simulation of ammonia cracker process with Aspen HYSYS. In *Proceedings of SIMS EUROSIM 2024* (Linköping Electronic Conference Proceedings No. 212, pp. 79-84). https://doi.org/10.3384/ecp212.011
- **Page numbering:** "p. N" means page N of the PDF. Proceedings page = 78 + N.

## Scope
The paper simulates a centralised NH3 cracker in Aspen HYSYS V12. The flowsheet follows Restelli et al. (2024).

Two cases are compared:
- a base case;
- an "improved" case, where heat from the H2 and N2 product streams preheats the cracker feed.

The paper has no kinetics, no TEA, and no real PSA model.

## Simulator set-up (p. 3)
- **Property package:** Peng-Robinson. SRK was also tried on the base case and gave no significant difference (p. 6).
- **Cracker:** Gibbs reactor, which represents thermal equilibrium cracking. The authors state "In the absence of catalyst data".
- **Furnace:** a second Gibbs reactor (Assumption 1). The paper notes that NH3 would not combust in the HYSYS furnace operation.
- **Separations:** the NH3 adsorber and the PSA are replaced by component splitters. They separate NH3, H2 and N2 with 100 % efficiency and no pressure or temperature losses (Assumption 3).
- **Feed:** NH3 at 500 kmol/h.
- **Heat exchange:** ideal heaters and coolers, with no heat losses.
- **Improved case:** two coolers bring the H2 and N2 streams to ambient temperature. A recycle manipulator transfers their heat to a heater on the NH3 feed to the cracker.
- **Combustion reaction (Eq. 2):** 4 NH3 + 3 O2 -> 2 N2 + 6 H2O.
- **Cracking reaction (Eq. 1):** 2 NH3 -> N2 + 3 H2.

## Stream specifications (Table 2, p. 3)
| Stream | T (°C) | P (bar) | Flow (kmol/h) | Composition (mole fraction) |
|---|---|---|---|---|
| NH3 | -27.6 | 1.3 | 592.33 | NH3 1 |
| H2 product | 25.5 | 30 | 698.07 | H2 0.999, N2 0.001 |
| Air | 25.0 | 1.01 | 608.13 | N2 0.79, O2 0.21 |
| Flue gas | 139 | 1.01 | 999.28 | H2 0.0003, N2 0.775, H2O 0.191, NO 0.0029, O2 0.0309 |

**Inconsistency:** the NH3 flow of 592.33 kmol/h and the H2 flow of 698.07 kmol/h do not match the 500 kmol/h feed in Tables 3 and 4. They may be inherited from Restelli et al. (2024). The cracker pressure is not stated explicitly.

## Results
### Base case (Table 3, p. 4)
| Quantity | Value |
|---|---|
| NH3 total feed | 500 kmol/h |
| Cracker feed | 375 kmol/h |
| Unreacted NH3 | 4.3 kmol/h |
| NH3 burned in furnace | 129.3 kmol/h (this equals 125 kmol/h fresh NH3 plus 4.3 kmol/h unreacted; the paper does not state this) |
| Cracker conversion | 99.42 % |
| Total conversion | 74.14 % |
| Cracker H2 yield | 98.88 % |
| Total H2 yield | 74.14 % |
| H2 production | 556.1 kmol/h |
| H2/NH3 | 1.11 mol/mol, 0.1316 kg/kg |

Cracker temperature: 437 °C (p. 5).

### Improved case (Table 4, p. 5)
| Quantity | Value |
|---|---|
| Cracker feed | 400 kmol/h |
| Unreacted NH3 | 3.26 kmol/h |
| NH3 burned | 103.3 kmol/h |
| Cracker conversion | 99.6 % |
| Total conversion | 74.35 % as printed |
| Cracker H2 yield | 99.59 % |
| Total H2 yield | 79.35 % |
| H2 production | 595.1 kmol/h |
| H2/NH3 | 1.19 mol/mol, 0.141 kg/kg |

Cracker temperature: 466 °C (p. 5).

The printed total conversion of 74.35 % is probably a typo. The value (400 - 3.26)/500 gives 79.35 %, which matches the printed total H2 yield.

### Comparison with literature (Table 5, p. 5)
| Source | kg H2 / kg NH3 feed |
|---|---|
| This study, base case | 0.131 |
| This study, improved case | 0.141 |
| Restelli et al. 2023 | 0.140 |
| Lee et al. 2023 | 0.127 |
| Devkota et al. 2023 | 0.129 |

The improvement from 0.131 to 0.141 is about 8 %.

## Values from other papers quoted in the literature review (not original to this paper)
- **Equilibrium conversion vs temperature,** from Chiuta et al. 2013, HSC Chemistry 7 (Table 1, p. 2). The pressure is not stated (presumably 1 bar).

  | T (°C) | Conversion (%) |
  |---|---|
  | 250 | 89.2 |
  | 300 | 95.7 |
  | 350 | 98.1 |
  | 400 | 99.1 |
  | 450 | 99.5 |
  | 500 | 99.7 |
  | 600 | 99.9 |
  | 700 | 99.95 |

- **Cha et al. 2021:** Aspen Plus with PR. PSA on activated carbon at 2.5 bar and 20 °C gives 71 % H2 recovery at 99 mol% purity, with about 200 kg activated carbon per kmol of PSA feed. Desorption of the recycled-NH3 adsorbent runs from 31 to 310 °C (p. 2).
- **Devkota et al. 2023:** feed of 4000 kg/h NH3 at 298 K and 10 bar. About 9 % of the fresh feed is burned. Multi-catalytic packed bed with Ru/Al2O3, preheated to 773 K (p. 2).
- **Lee et al. 2023:** induction-heated reactor producing 150 Nm3/h H2. PSA recovery fixed at 79 %. Conversion above 90 % at 600 °C and 7 barg (p. 2).
- **Restelli et al. 2023/2024:** Gibbs reactor at 30 bar and 900 °C (Ni catalyst conditions). PSA separation (pp. 2-3).

## Limitations
- The conversion is an equilibrium value. No kinetics are used. The authors call this optimistic.
- The ideal splitter in place of the PSA overestimates H2 production.
- The NH3 furnace is modelled as a Gibbs reactor because of a HYSYS limitation.
- Heaters and coolers are ideal, with no heat-exchanger design and no pinch analysis.
- The stream table (592.33 kmol/h NH3) is inconsistent with the 500 kmol/h basis.
- There is no TEA.

## Relevance to AmCraX
- It sets a lower bound on model fidelity: a Gibbs-equilibrium cracker, a Gibbs furnace, and ideal splitters.
- It gives yield benchmarks of 0.131-0.141 kg H2/kg NH3 and a fuel fraction of about 21-26 % of the NH3 feed. These are useful for sanity checks on the AmCraX Aspen Plus flowsheet. Because of the optimistic assumptions, a rigorous model should give lower yields.
