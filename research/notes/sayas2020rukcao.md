# sayas2020rukcao

## Bibliographic data
- Authors: Sayas, S., Morlanes, N., Katikaneni, S. P., Harale, A., Solami, B., & Gascon, J.
- Title: High pressure ammonia decomposition on Ru-K/CaO catalysts
- Journal: Catalysis Science & Technology, 10(15) (2020), 5027-5035. Open access (CC BY 3.0).
- DOI: 10.1039/d0cy00686f (metadata checked via Semantic Scholar and OpenAlex APIs, 23 November 2026; KAUST repository handle 10754/664971)
- APA 7: Sayas, S., Morlanes, N., Katikaneni, S. P., Harale, A., Solami, B., & Gascon, J. (2020). High pressure ammonia decomposition on Ru-K/CaO catalysts. *Catalysis Science & Technology, 10*(15), 5027-5035. https://doi.org/10.1039/d0cy00686f

## Superseded on 24 November 2026: main text read in full

The main article has since been read in full from a copy supplied by the user (not stored in the repository); the
supplementary information was NOT available. See `research/notes/sayas2020_full_text.md` and
`research/data/sayas2020_extract.json`. Corrections to the status below:
- Confirmed in the main text (Table 4, p. 5033): apparent Ea 96 kJ/mol (3%Ru/CaO) and 75 kJ/mol (3%Ru10%K/CaO), H2
  order -1.9 and -1.2, NH3 order 0.8 and 0.5, at 350 degC and 1 atm (differential experiments). The essay statement is
  therefore verified.
- Conditions of the high-pressure tests are now known: 200 mg catalyst, pure NH3, 30 N mL/min, WHSV 9000 mL gcat-1 h-1
  at 10-40 bar (the reference state of "N mL" is not defined). At 550 degC and 40 bar the text says "around 80 %"; the
  plotted point reads about 84 %.
- "K/Ru = 0.9" (abstract) is inconsistent with the stated loadings: 10 wt% K and 3 wt% Ru give about 8.6 mol/mol.
- The "40 times bigger" productivity and TOF in the abstract follow from multiplying the rate by the pressure; the NH3
  converted per gram of catalyst at fixed feed falls with pressure.
- Still missing (supplementary information only): the rate constant (pre-exponential factor), its units, the
  equilibrium term and the fitted ranges. Ru-K/CaO remains NOT implemented; nothing was fitted.

## Access status (23 November 2026, kept for the record)
- FULL TEXT NOT READ. The publisher HTML/PDF and the supplementary PDF returned HTTP 403 or closed the connection for automated access; the KAUST repository copy is behind a bot-protection page. No local copy in research/papers.
- Only the abstract-level statements could be seen in search snippets: optimum 3 wt% Ru with K/Ru = 0.9; tests at 1-40 bar, 250-550 degC, WHSV 9000-30000 mL g^-1 h^-1; conversion about 0.8 at 550 degC and 40 bar; K lowers the apparent Ea (snippets mention about 75-76 kJ/mol in the SI).
- A 2023 Catal. Sci. Technol. modelling paper (DOI 10.1039/d3cy00055a, also not retrievable) is reported in snippets to cite a power law with orders 0.5 (NH3) and -1.2 (H2) for Ru-K/CaO up to 40 bar.

## What is missing for reproducible kinetic modelling
- Pre-exponential factor: not available (not seen).
- Orders and Ea: only unverified snippets; the essay statement "Ea 96 -> 75 kJ/mol with K, H2 order -1.9 vs -1.2" could not be checked against the paper.
- Conditions of the 80 % / 40 bar / 550 degC point (WHSV, dilution, catalyst mass) not verified, so no pre-exponential factor may be derived from it under the project rules.
- Result: Ru-K/CaO is NOT implemented. To implement it, read the paper and its SI (kinetics section and Fig. S6) manually and record orders, Ea and one fully specified data point.
