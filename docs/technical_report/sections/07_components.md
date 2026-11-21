<!-- cites: cechetto2023membrane, iso2019hydrogen -->

# 7 Component selection

An RGibbs reactor can form only listed species, so the component list defines the chemistry of the cracker and the burner. AmCraX uses the smallest set that closes the N, H and O balances of the reaction, the feed impurity and the combustion (Table 7.1, Figure 7.1).

Table: **Table 7.1.** Components of the AmCraX Aspen Plus model. *Source: aspen/models/baseline.inp (COMPONENTS, DATABANKS); Aspen Plus V15 component form (Figure 7.1).*

| Aspen ID | Component name | CAS number | Role | Where it appears |
|---|---|---|---|---|
| NH3 | Ammonia | 7664-41-7 | Reactant and fuel | Feed, cracker residue, tail gas, burner |
| H2 | Hydrogen | 1333-74-0 | Product and fuel | Cracked gas, H2PROD, tail gas, burner |
| N2 | Nitrogen | 7727-37-9 | Co-product; diluent | Cracked gas, tail gas, air, flue gas |
| H2O | Water | 7732-18-5 | Feed impurity; combustion product | Feed train (inert in CRACKER), tail gas, flue gas |
| O2 | Oxygen | 7782-44-7 | Oxidant | Air, burner, flue gas |

<!-- data: aspen/models/baseline.inp COMPONENTS, DATABANKS, BLOCK CRACKER PROD; aspen/screenshots/02_components.png (CAS numbers) -->

![**Figure 7.1.** Component specification form in Aspen Plus V15: five conventional components with their names, aliases and CAS numbers. Only these species can appear in any stream or be formed by the RGibbs cracker, so the list fixes the chemistry of the model. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/02_components.png){width=95%}

The pure-component parameters (critical constants, acentric factor, ideal-gas heat capacity, enthalpy and Gibbs energy of formation) come from the Aspen Plus V15 databanks in the order PURE41, AQUEOUS, INORGANIC; the PCD databank is excluded. The formation data matter most, because RGibbs minimises the total Gibbs energy: the equilibrium conversion depends directly on the formation data of NH~3~. Section 13 compares them with the independent NASA-7 data.

**Water** represents the water content of commercial ammonia. It raises the dew point of the feed (Section 8.3) and dilutes the reactor gas. It is listed as a possible CRACKER product, but with no oxygen-bearing partner it passes through unchanged (0.2 kmol/h in S4 and S5); the PSA sends it to the tail gas. **Oxygen** enters only with the combustion air (79 mol% N~2~, 21 mol% O~2~) and is not a CRACKER product.
<!-- data: results/simulations/baseline.json streams.S4/S5 component_mole_flow H2O 0.2; aspen/models/baseline.inp STREAM AIR, BLOCK CRACKER PROD -->

**Species deliberately excluded:**

* *Nitrogen oxides.* The RStoic burner converts the fuel completely to N~2~ and H~2~O, so fuel and thermal NO~x~ are not predicted and the stack composition is optimistic (Section 21).
* *Hydrazine and N-H surface intermediates.* Negligible in the gas phase at equilibrium; surface species belong to the kinetic model (Section 14).
* *Argon and other trace air species.* Air is binary N~2~/O~2~; this slightly changes the flue-gas heat capacity but not the process side.
* *Carbon species and catalyst.* The feed contains no carbon, and RGibbs needs no catalyst description.

Without a polishing step, NH~3~ in the product is fixed by the PSA split fraction (zero in the baseline), so compliance with the 0.1 ppm NH~3~ limit of ISO 14687:2019 (ISO, 2019) cannot be predicted by this model (Section 11).
