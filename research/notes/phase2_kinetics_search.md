# phase2_kinetics_search

Phase 2 search (task K1 item 2) for complete, published ammonia-decomposition rate laws missing from AmCraX:
Ni/CeO2, Ru/CeO2, Ru-K/CaO (Sayas et al. 2020 and follow-up work from the same group), and any catalyst whose
kinetics were fitted at elevated pressure (5 to 40 bar). Access date for everything below: 23 November 2026.
Rule applied: a law is usable only if every parameter (pre-exponential factor with units and basis, activation
energy, orders or adsorption terms) is published or derivable from published numbers without fitting digitised
points. No parameter was estimated.

## Searches and outcomes

| # | Query or URL | Outcome |
|---|---|---|
| 1 | Web search "Sayas Ru-K/CaO high pressure ammonia decomposition kinetics rate expression Catalysis Science Technology 2020" | Found the article landing pages, open-access HTML/PDF links and the SI link. Snippets only: 1-40 bar, 250-550 degC, WHSV 9000-30000 mL g-1 h-1, X about 0.8 at 550 degC and 40 bar, apparent Ea about 75 kJ/mol in SI Arrhenius plots. No pre-exponential factor in any snippet. |
| 2 | https://pubs.rsc.org/en/content/articlehtml/2020/cy/d0cy00686f (fetch tool) | HTTP 403 Forbidden. |
| 3 | https://pubs.rsc.org/en/content/articlepdf/2020/cy/d0cy00686f (fetch tool, then a direct request with a generic User-Agent) | HTTP 403 Forbidden (both). |
| 4 | https://www.rsc.org/suppdata/d0/cy/d0cy00686f/d0cy00686f1.pdf (fetch tool, then direct request) | HTTP 404 (fetch tool); connection closed (direct request). |
| 5 | Web search for a KAUST repository copy | Only the KAUST group publication listing (advcm.kaust.edu.sa) and library catalogue records; no retrievable full text. Phase 1 found the repository copy behind bot protection. |
| 6 | Web search "ammonia decomposition kinetics elevated pressure 10-40 bar rate expression fitted Ru catalyst kinetic parameters" | No source with a complete rate law fitted at 5-40 bar. Results: Sayas 2020 SI (not retrievable), a 2023 Catal. Sci. Technol. modelling paper (DOI 10.1039/d3cy00055a; PDF links on pubs.rsc.org, which returns 403 to automated access), Politecnico di Milano repository items for a commercial Ru/Al2O3 LHHW fit at up to 3 bar (below the 5 bar threshold), a LiOH-Ru/Al2O3 kinetics record (no parameters in the record). |
| 7 | Web search "Ni/CeO2 ammonia decomposition kinetic model rate expression activation energy pre-exponential reaction orders fitted" | No complete law for Ni/CeO2 or Ru/CeO2. Closest: lucentini2021nirukinetic (Ni-Ru/CeO2, already implemented), a Ni/Ce-Zr mixed-oxide paper (MDPI Catalysts 2025; different support, only Ea quoted in the snippet), and a Ru/CeO2 isotope study (apparent Ea only). |

Earlier Phase 1 result kept: lucentini2019ceo2 has no rate law, Ea, orders or pre-exponential factor for Ni/CeO2 or
Ru/CeO2 (research/notes/lucentini2019ceo2.md).

## Result
- No new law was added to kinetics.yaml, the Python reactor or Aspen. Ni/CeO2, Ru/CeO2 and Ru-K/CaO stay
  `unmodelled` in results/research/kinetics/validity_classification.json.
- Sayas et al. (2020) is open access (CC BY 3.0) but could not be read by automated access. To add Ru-K/CaO, a person
  must download the article and SI in a browser and record: the rate form, the orders in NH3 and H2, Ea, a
  pre-exponential factor with units and basis, and one fully specified data point (catalyst mass, WHSV, feed, T, P,
  conversion) to check the units. The essay values (Ea 96 to 75 kJ/mol, H2 order -1.9 vs -1.2) remain NOT VERIFIED.
- Update of 24 November 2026: the main text of Sayas et al. (2020) has been read from a copy supplied by the user
  (`research/notes/sayas2020_full_text.md`). The essay values (Ea 96 to 75 kJ/mol, H2 order -1.9 vs -1.2) are now
  VERIFIED (Table 4, 350 degC, 1 atm). The pre-exponential factor, its units and the equilibrium term are only in the
  supplementary information, which was not obtained, so Ru-K/CaO stays `unmodelled` and nothing was fitted. The 15
  measured conversions at 10-40 bar are stored as literature comparison points that no model uses
  (`results/research/kinetics/validity_classification.json`, key `literature_comparison_points_sayas2020`).
- DOIs 10.1039/d0cy00686f and 10.1039/d3cy00055a were confirmed registered through https://doi.org/api/handles/
  (responseCode 1) on 23 November 2026.
