# Unified techno-economic baseline (Phase 2)

Status: version 1.0.0 of the AmCraX reference scenario, 23 November 2026.
Single source of truth: `backend/amcrax/data/reference_scenario.yaml`, loaded by `amcrax.economics.reference`.
Authoritative numbers: `results/research/reference_scenario/baseline.json`.
Changed numbers: `results/research/reference_scenario/supersession.json`.
CAPEX comparison: `results/research/reference_scenario/capex_audit.json`.

## Why this was needed

In Phase 1 the same Aspen baseline plant (600 degC, 20 bar, 99.8 kmol/h NH3, 251.6 kg/h H2) carried two different
costs:

- 3.61 USD/kg H2 in the Singapore economics (H2 and H3). This used a feed-scaled CAPEX of 2.78 MUSD.
- 3.92 USD/kg H2 in the end-use and purification studies (H1 and H4) and in the core stored results. This used the
  legacy plant-level correlation, with a CAPEX of 6.50 MUSD.

The purification study also priced electricity at 0.084 USD/kWh. The other studies used 0.140 USD/kWh. Absolute
costs could not be compared across hypotheses. All research cost paths now read one reference scenario.

## Audit of the two Phase 1 CAPEX methods

| | Legacy correlation (`lcoh.py`) | Phase 1 "equipment" method (`singapore.py`) |
|---|---|---|
| Equation | CAPEX = 18.171 x S^0.7451 MUSD, S in t H2/h | TCI = 1,702 kUSD x (F/500)^0.8 x 5.93, F = NH3 feed in kmol/h |
| Source | Ahmad et al. (2025), Fig. 6. This adapts data from Cesaro et al. (2021). | Farokhi et al. (2025), Table 5: PEC at 500 kmol/h, and TCI/PEC = 10,096/1,702 |
| How it was derived | Fit (R2 0.92) to SMR and cracker plant data | One published plant point |
| Scaling | 0.7451 on H2 capacity | 0.8 on NH3 feed (Chopra et al. 2026, Eq. 5) |
| Installation and indirect costs | Inside the correlation, not stated | Inside the factor 5.93, which includes working capital |
| Equipment covered | Not itemised. The Chopra shares are shown for information only. | Not truly itemised: the Chopra TCI shares (PSA 26, cracker 21, HX 5, adsorber 4) split a total that depends only on feed |
| Cost year and CEPCI | Not stated; no escalation | Not stated; the kUSD unit is inferred; no escalation |
| Responds to design variables | Capacity only | Capacity only |
| On the AmCraX baseline | 6.50 MUSD | 2.78 MUSD |

Neither method is itemised. Neither responds to reactor size, exchanger area or PSA size. Both cost years are unknown.

## Selection criteria (fixed before the outcomes were compared)

1. Traceability. Each cost item must trace to a stated source item with a page and table, and the cost year must be stated.
2. Completeness of scope. Inside and outside battery limits, engineering and contingency must be included, with the
   items listed so that items the AmCraX flowsheet lacks can be removed.
3. Response to the design variables that the hypotheses need: capacity, reactor (catalyst inventory), exchangers,
   PSA and adsorber, each separately.
4. Agreement with independent published plant costs at a comparable scale. Criterion 4 was used only to check
   plausibility. A method was not chosen because its number agreed with another number.

## Choice: `cho2026_itemised_v1`

The reference method uses the itemised unit CAPEX of the Cho et al. (2026) Ni-24.34 bar plant (Table 7, Fig. 8,
2024 USD, 630 kg/h NH3, derived 82.3 kg/h H2). The steps are:

- Each item is converted to an installed cost: I = u x m_H2 x 8000 h / CRF(8.5 %, 25 y). These are Cho's own
  hours, discount rate and life.
- The ISBL items are boiler or furnace (0.126 USD/kg), heat exchangers (0.098), T/PSA (0.084, split 26:4 into PSA
  and adsorber using Chopra Fig. 5a), reactor (0.036), and the 0.015 of ISBL that the table does not itemise.
- The 180 bar product compressor (0.050) is removed, because AmCraX has no product compression.
- Each item is scaled as (S/S_ref)^0.8 (Chopra Eq. 5). S is the NH3 feed by default. The reactor can follow the
  catalyst inventory instead (`reactor_size_driver = "catalyst_mass"`). Any item accepts a size ratio supplied by
  the caller, for example an exchanger-area ratio.
- The total is TCI = ISBL x (1 + 0.12 OSBL) x (1 + 0.10 engineering + 0.18 contingency), as in Cho Table 4.

How the method meets each criterion:

- Criterion 1: every item and factor traces to one primary paper with a stated cost year.
- Criterion 2: it is the only library source that lists OSBL, engineering and contingency.
- Criterion 3: it is the only option that can respond item by item.

**Rejected: the legacy correlation.** Criteria 1 and 3 fail. The cost year is unknown and the data are SMR
analogies. It is a single plant-level curve.

**Rejected: the Phase 1 equipment method.** Criteria 1 and 3 fail. The kUSD unit is inferred and the cost year is
unknown. The shares come from a 400 kg/d plant and are applied to a PEC from another paper. Criterion 4 is also
weak: it is the lowest estimate, at about 0.4 times the reference.

Both rejected methods can still be selected (`capex_mode = "legacy"` or `"equipment"`) for comparison.

### Comparison with published plant costs (normalised to 251.6 kg/h H2; exponents 0.6 to 0.8)

| Source | Normalised CAPEX, MUSD | Independent of the reference? |
|---|---|---|
| Reference method (this scenario) | 7.67 | - |
| Cho 2026 without the compressor, scaled on H2 | 6.78-8.47 | no (it is the basis) |
| Ahmad 2025 correlation | 6.50 | yes |
| Chopra 2026, 400 kg/d; compressor share and India factor removed | 3.12-5.37 | yes |
| Farokhi 2025, 500 kmol/h | 3.12-4.19 | yes |
| Mehr 2026, terminal scale | 58-108 | yes, but the paper is internally inconsistent; information only |

Kum 2026 could not be compared, because the paper gives no total FCI and no PEC coefficients. Deka 2025 and
Makhloufi and Kezibri 2021 are not in the library: their primary sources were not obtained. Lee et al. 2022 covers
ammonia production, not cracking.

**Finding.** The reference CAPEX is at or above the top of the independent range (3.1 to 6.5 MUSD). The four
independent estimates span a factor of about 2. The choice is therefore conservative: it does not favour cracking.
The CAPEX uncertainty is explicit:

| CAPEX case | CAPEX, MUSD | LCOH, USD/kg |
|---|---|---|
| Lowest independent estimate | 3.12 | 3.64 |
| Highest independent estimate | 6.50 | 3.92 |
| Reference | 7.67 | 4.02 |
| Cho total including the compressor | 9.65 | 4.18 |

This is a comparison with published literature (evidence kind 3), not validation.

## Reference scenario

| Input | Value | Source (source type) |
|---|---|---|
| Plant | 99.8 kmol/h NH3, 251.588 kg/h H2 | stored Aspen Plus V15 baseline (aspen) |
| Operating hours | 8000 h/yr (capacity factor 0.913) | Cho 2026 Table 4 (literature) |
| Discount rate, life | 10 %, 25 yr | Kum 2026 Table 5; Cho 2026 (literature) |
| Maintenance, insurance | 3 %, 1.5 % of TCI per year | Chopra 2026 Table 2 (literature) |
| Labour, overhead, G&A | 109,756 USD/yr; 25 % of labour and maintenance; 6 % | Chopra 2026; Cho 2026 (literature) |
| Electricity | 0.1402 USD/kWh | USEP 2025 mean plus SP Group network and fees, divided by FX (derived) |
| NH3 scenarios | grey 450, blue 487, green 1000 / 709 (2030) / 463 (2050) USD/t | Cho 2026; S&P Global snippet for blue (literature or secondary web) |
| FX | 1.288444 SGD per USD, 20 Nov 2026 | ECB reference rates 1.4160 SGD and 1.0990 USD per EUR, cross rate read at source on 23 Nov 2026 (derived) |
| USD per EUR | 1.0990 | ECB, 20 Nov 2026 (official) |
| Carbon pricing | 45 SGD/t, Scope 1, 25,000 t threshold | NEA (official). This is the actual Singapore boundary. |
| H2 selling price (NPV only) | 3.06 USD/kg | Argus NE Asia SMR marker (secondary web) |
| CAPEX method | cho2026_itemised_v1, exponent 0.8, location factor 1.0 | Cho 2026; Chopra 2026; assumption (no Singapore factor sourced) |
| Power plant (H1) | 8000 h; Ahmad reproduction 7200 h and 480 USD/t; scale exponent 0.67; cracker O&M 4.5 % of TCI | named fields, `power_plant` block |
| Cho reconstruction (H3) | 8.5 %, 0.084 USD/kWh, 25 yr | named field `literature_reproduction.cho2026` |

The price year is mixed nominal USD: CAPEX in 2024 USD and Singapore prices in 2026. No escalation index is applied,
because the CEPCI values in the library conflict.

## Unified baseline (grey, heat integration on, plant gate, H2 at 19.5 bar)

| Item | USD/kg H2 | SGD/kg H2 |
|---|---|---|
| Ammonia feed | 3.040 | 3.917 |
| Capital (CRF 0.1102) | 0.420 | 0.541 |
| Fixed operating cost | 0.284 | 0.366 |
| Heat (supplementary NH3) | 0.268 | 0.345 |
| Catalyst, electricity, cooling water | 0.004 | 0.005 |
| Carbon tax | 0 | 0 |
| **LCOH** | **4.015** | **5.174** |
| REC (LCOH minus feed) | 0.975 | 1.257 |

Further results for the same case:

- CAPEX is 7.67 MUSD (9.88 MSGD). By item, in MUSD: boiler 2.69, heat exchangers 2.09, PSA 1.56, adsorber 0.24,
  reactor 0.77, other 0.32. OSBL, engineering and contingency are allocated pro rata.
- NPV at 3.06 USD/kg is -17.5 MUSD. No IRR exists at that price.
- With heat integration off, the LCOH is 4.229 USD/kg.
- By NH3 scenario, the LCOH is: blue 4.287, green current 8.058, green 2030 5.919, green 2050 4.111 USD/kg.

## What changed and what did not

The table below shows the main changes. Every changed headline value, with its old and new value, is in
`supersession.json`.

| Quantity | Old | New |
|---|---|---|
| Baseline LCOH | 3.613 (H2, H3) and 3.919 (H1, H4) USD/kg | 4.015 USD/kg in every workstream |
| REC | 0.573 USD/kg | 0.975 USD/kg |
| Purification, PSA_AMCRAX, industrial 30 bar | 3.937 USD/kg | 4.046 USD/kg |
| Purification electricity | 0.084 USD/kWh | 0.140 USD/kWh |
| Purification membrane cost conversion | EUR at parity | 1.099 USD per EUR |
| Purification upstream cost | excluded pump electricity | includes pump electricity |
| FX | 1.290 SGD per USD | 1.288444 SGD per USD |
| H1 power pathways | cracker CAPEX from the legacy correlation | reference method, sized on the NH3 passing through the cracker |

Checks on the new basis:

- In the purification study, the PSA_AMCRAX configuration reproduces the baseline annual cost exactly once its two
  named extra items are removed: compression to the delivery pressure, and the heat recalculated from its own tail
  gas.
- The H1 hydrogen pathway equals the baseline to better than 1e-6.

What did not change:

- `amcrax.economics.lcoh` and the core stored results in `results/simulations` and `results/optimisation` remain
  the legacy version 1 basis. They still give 3.919 USD/kg, and their tests pass.
- No physics, kinetics, heat-integration or Aspen result changed.
- The H4 Grade D ranking (membrane cheaper than PSA, on paper: 4.33 against 4.46 USD/kg) and the H2 finding (feed
  NH3 dominates, about 76 % of LCOH) keep their direction.

Two rankings changed and need attention:

- **H4, industrial 99.9 %.** The ranking reversed. PSA_AMCRAX now costs 4.05 USD/kg and the 1 bar membrane without
  polishing costs 4.11 USD/kg. In Phase 1 they were 3.94 and 3.79 USD/kg. The cause is that membrane prices are now
  converted at 1.099 USD per EUR instead of at parity, and compression electricity is priced at 0.140 USD/kWh.
- **H1, power.** The exhaust-heated, unpurified full cracker gives 255.6 USD/MWh at 450 USD/t (248.2 before). Direct
  NH3 combustion gives 258.9 USD/MWh, unchanged. Direct use is therefore now only about 1.3 % dearer, against 4 % in
  Phase 1. At 40 vol% H2, partial cracking equals direct use.

## Limitations

- The reference rests on one primary plant (Cho 2026, about 82 kg/h H2). It is scaled 2.7-fold to the AmCraX
  baseline, and more than 30-fold for the H1 power plant. The exponent 0.8 is a generic equipment value.
  Exponent 0.6 gives 6.29 MUSD and an LCOH of 3.90 USD/kg.
- Cho states that ISBL is the "equipment purchase cost" but also sums installed costs (Eq. 19). If the table holds
  purchase costs, installation is missing and the CAPEX is low.
- The itemised unit CAPEX values come from research/notes/cho2026nickel.md (Table 7 and Fig. 8). Cho's
  installed-cost correlations are in its SI, which is not available. The 0.015 USD/kg of ISBL that the table does
  not itemise is carried as "other_isbl".
- The design-variable response exists in the method, but the defaults scale every item on feed. Heat-integration
  exchanger area and catalyst inventory affect CAPEX only when a workstream passes them.
- There is no Singapore location factor, labour rate, WACC or gas price. Labour is an Indian small-plant figure.
  The ammonia prices are international scenarios, not Singapore transaction prices.
- The electricity price is derived, not an industrial contract price. Its effect on the LCOH is below 0.1 %.
