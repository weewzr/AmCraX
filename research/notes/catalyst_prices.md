# Catalyst price, lifetime and recovery evidence (Phase 2, task P1)

Access date for all web sources: 23 November 2026. Machine-readable data: `research/data/catalyst_prices.json`.
References: `research/reference_additions/phase2_catalyst_prices.json`. This is economic input data. It is not evidence of kinds (1) to (4) in the Phase 2 brief.

## Headline

1. No industrial supplier quotation (grade A) and no published commercial price (grade B) for any ammonia-cracking catalyst was found. Johnson Matthey, Topsoe and Clariant publish product pages, not prices.
2. Every Ru catalyst price in the peer-reviewed techno-economic studies we read is BELOW the Ru metal-content floor. Example: Cho et al. (2026) give 542 USD/kg for a 3 wt% Ru catalyst, but 3 wt% x Ru at the 2025 annual average (690 USD/oz = 22,184 USD/kg) is already 666 USD/kg, and at the JM Base Price of 20 Nov 2026 (1,850 USD/oz = 59,478 USD/kg) it is 1,784 USD/kg. Other published figures (25 USD/kg for 4 wt% Ru; 24 USD/kg; 22.3 EUR/kg) are more than an order of magnitude below the floor. They must not be used as Ru catalyst prices.
3. Ru metal price roughly tripled in about 18 months (about 560 USD/oz in March 2025 per Reuters; 690 USD/oz 2025 average per USGS; 1,850 USD/oz on 20 Nov 2026). Ru catalyst cost is therefore dominated by metal price and is volatile.
4. Ni catalyst cost is small and not metal-driven: Ni metal at about 15 USD/kg contributes about 1.2 USD/kg to an 8 wt% catalyst. The one sourced finished Ni price (33.4 USD/kg) is mostly support and manufacture.

## Exchange rate

SGD per USD = 1.2801 (Federal Reserve G.5, series EXSIUS, October 2026 monthly average, preliminary). USD per EUR = 1.1198 (G.5, EXUSEU, October 2026). The Monetary Authority of Singapore portal returned no data on the access date (landing page without table; API endpoint serving a maintenance page), so an official equivalent (US Federal Reserve) is used and flagged. Cross-check, not official: AsianBondsOnline SGD per USD 1.290 at close 20 Nov 2026 (0.8% higher). Replace with the MAS value when the reference scenario is frozen. KRW prices are not converted (no sourced rate).

## Scenario table (USD/kg and SGD/kg of finished catalyst)

Formula: `price = (wNi/100) * P_Ni + (wRu/100) * P_Ru + N`. Inputs (all in the JSON, key `inputs`):

| Input | Low | Central | High |
|---|---|---|---|
| P_Ni, USD/kg metal | 15.00 (USGS 2025e avg) | 15.31 (LME cash 20 Nov 2026) | 25.82 (USGS 2022 avg) |
| P_Ru, USD/kg metal | 22,184 (USGS 2025e avg, 690 USD/oz) | 59,478 (JM Base 20 Nov 2026, 1,850 USD/oz) | 59,478 (no sourced higher value) |
| N (support + manufacture), USD/kg | 0 (floor only) | 32.2 = Cho 8 wt% Ni/Al2O3 33.4 minus 0.08 x 15 | 32.2 (no sourced higher value) |

| Catalyst | Loading used (wt%) | Low USD | Central USD | High USD | Low SGD | Central SGD | High SGD |
|---|---|---|---|---|---|---|---|
| Ni/MgO | 30 Ni (project kinetics source) | 4.50 | 36.79 | 39.94 | 5.76 | 47.10 | 51.13 |
| Ru/MgO | 5 Ru (project source) | 1,109 | 3,006 | 3,006 | 1,420 | 3,848 | 3,848 |
| Ru/Al2O3 | 8 Ru (project source) | 1,775 | 4,791 | 4,791 | 2,272 | 6,132 | 6,132 |
| 5Ni1Ru/CeO2 | 5 Ni + 1 Ru | 222.59 | 627.75 | 628.28 | 284.94 | 803.59 | 804.26 |
| 2.5Ni0.5Ru/CeO2 | 2.5 Ni + 0.5 Ru | 111.30 | 329.98 | 330.24 | 142.47 | 422.40 | 422.74 |
| Ni/CeO2 | 5 Ni (ASSUMED) | 0.75 | 32.97 | 33.49 | 0.96 | 42.20 | 42.87 |
| Ru/CeO2 | 1 Ru (ASSUMED) | 221.84 | 626.99 | 626.99 | 283.98 | 802.61 | 802.61 |
| Ru-K/CaO | 3 Ru (Cho et al.) | 665.52 | 1,816.57 | 1,816.57 | 851.93 | 2,325.39 | 2,325.39 |

Grade of every scenario value: derived; metal part grade E, non-metal part grade C-derived. None is a quote. For comparison, the published TEA value for Ru-K/CaO is 542 USD/kg (grade C, below the floor).

Reading the table:
- "Low" is a floor, not a market price (N = 0). Use it only as a lower bound. Ni/MgO low (4.5 USD/kg) in particular is not a credible catalyst price.
- "High" equals "central" for Ru because no higher sourced Ru price exists. The upside risk is real and unquantified.
- N is one paper's "Calculated" price (derivation in its Supplementary S3, not available here), applied to every support. Support-specific manufacture costs for MgO, CeO2 and CaO were not found.
- Ni/CeO2 and Ru/CeO2 loadings are not stated in any project source; they are assumed (monometallic counterparts of 5Ni1Ru) and can be edited in the JSON.
- No Ru recovery credit is deducted (no sourced refining charge; see below).

## Evidence grade distribution (19 price entries)

| Grade | Count | Entries |
|---|---|---|
| A industrial quotation | 0 | none found |
| B commercial catalogue price | 0 | none found (JM, Topsoe, Clariant: no price published; one A/B "not public" finding entry) |
| C TEA price | 7 | Cho Ni 33.4 and Ru-K/CaO 542 USD/kg; Kum 25 USD/kg; Richard 295, 143, 22.3 EUR/kg; Chopra 24 USD/kg |
| D cost method | 1 | step-method paper (no numbers obtained; CatCost not run) |
| E metal price | 6 | Ru x3, Ni x2, CeO2 |
| F lab proxy | 4 | Thermo Scientific Ni on silica-alumina 5 g 41.12 USD (about 8,224 USD/kg); Sigma-Aldrich 208779 100 g 112 USD (about 1,120 USD/kg); Evonik Noblyst P3061 5% Ru/Al2O3 10 g EUR 124 (about 13,886 USD/kg, 4.7x the Ru floor at JM spot); Sigma-Aldrich Korea 206199 KRW 136,416 per 100 mg |

Lab proxies are not used in the scenarios. F1 to F4 prices come from search-result listings; the product pages timed out or returned HTTP 403 to automated requests, so they were not re-read.

## Lifetime, deactivation, regeneration, recovery

- Measured: Ni/Al2O3 lost 13.5% of maximum conversion over 800 h on stream at 534 C; Ni crystallite size grew from 3.5 to 5.0 nm after 1000 h (sintering); no nickel nitride indicated (Purcel et al., 2024, doi 10.1002/ente.202400678). Lab data, not an industrial lifetime.
- Comparable service: steam reforming catalyst changeout cycle is now "four to six years" (Shah, Johnson Matthey, Refining India, Sept 2025, p. 25). Vendor-authored.
- Assumed in TEAs: 2 years (Cho et al.; sensitivity 1 to 4 years), 5 years (Richard et al.). Neither is measured. Cho et al. report that catalyst price and lifetime have "a minor influence" on overall economics compared with energy and NOx costs.
- Not confirmed: a search snippet claiming a Topsoe lifespan above 100,000 h is not on the fetched Topsoe page. Do not use.
- Nitridation, poisoning, regeneration practice and regeneration cost: no sourced figure found (snippet-level mentions of carbon deposition, sulfur poisoning and sintering for steam reforming only).
- Ru recovery: hydrometallurgical recovery 85 to 95% and pyrometallurgical above 98% appear only in search snippets (Sabin Metal/digitalrefining and an environmental-expert case study); the fetched Sabin page did not contain the percentages. Umicore confirms the route (pyrometallurgy plus hydrometallurgy, pure Ru powder, Hoboken) with no rate or fee. Refining charge: not found, and not public.

## What could NOT be found

- Any quotation or list price for JM KATALCO 27-200MQ, Topsoe DNK-20/30 Retake and DNK-2R, Clariant HyProGen 820/821/830/850, BASF, Heraeus or Amogy catalysts.
- Ru refining charge and a primary-source recovery fraction.
- NREL CatCost numbers for any of the eight catalysts.
- Co-based and Fe-based catalyst prices (Topsoe: Fe-Co "reasonable cost", no number).
- Mg and Al precursor prices (negligible relative to N).
- The MAS exchange rate for the date.
- Original Devkota (2024) and Makhloufi (2021) papers: their figures are second-hand.

## Cautions

- The Phase 1 prices (Ni 33.4, Ru-K/CaO 542 USD/kg) used in the project remain valid as "published TEA values" but are not defensible as current Ru prices.
- Ru wt% in the metal-floor calculation is taken as mass of Ru per mass of finished catalyst. No loss, precursor-salt cost or yield is included.
- Ru spot is from a secondary display of the JM Base Price (wallstreet-online.de); the JM page itself was not reachable. Reuters/Kitco (about 1,750 USD/oz, 13 March 2026) is consistent.
- Ni spot is from a secondary aggregator (15,310 USD/t); other sources for early November show 16,100 to 16,300 USD/t.
- DOIs resolve (doi.org handle API, responseCode 1): Cho, Kum, Chopra, Devkota, Purcel, Makhloufi, Atsbha, Yoshida, Richard, and the step-method paper. URLs returning HTTP 200 on direct request: USGS x3, digitalrefining x2, Topsoe, wallstreet-online, Kitco, Tacto, ADB, MAS landing page, Umicore, OSTI, Clariant. Not confirmed by direct request: Fisher (403), Sigma-Aldrich (timeouts), Johnson Matthey (connection aborted), FRED (data read through the fetch tool only).
