<!-- cites: cechetto2023membrane, iso2019hydrogen -->

# 8 Component selection

RGibbs can form only listed species, so the component list defines the chemistry of the cracker and the burner. AmCraX uses the minimum set that closes the N, H and O balances of reaction, feed impurity and combustion (Table 8.1).

Table: **Table 8.1.** Components of the AmCraX Aspen Plus model. *Source: aspen/models/baseline.inp (COMPONENTS, DATABANKS), config/flowsheet.json; roles from the flowsheet definition.*

| Aspen ID | Formula / alias | Databanks searched | Role | Where it appears |
|---|---|---|---|---|
| NH3 | H3N | APV150 PURE41, AQUEOUS, INORGANIC | Reactant and fuel | Feed, cracker (equilibrium residue), tail gas, burner |
| H2 | H2 | as above | Main product and fuel | Cracked gas, H2PROD, tail gas, burner |
| N2 | N2 | as above | Co-product; diluent in air and flue gas | Cracked gas, tail gas, air, flue gas |
| H2O | H2O | as above | Feed impurity (0.2 mol%); combustion product | Feed train (inert in CRACKER), tail gas, flue gas |
| O2 | O2 | as above | Oxidant | Air, burner, flue gas (excess O~2~) |

<!-- data: aspen/models/baseline.inp COMPONENTS, DATABANKS, BLOCK CRACKER PROD; results/simulations/baseline.json inputs.feed_h2o_mole_frac -->

The pure-component parameters (critical constants, acentric factor, ideal-gas heat capacity, standard enthalpy and Gibbs energy of formation) come from the APV150 databanks in the order given in `DATABANKS` (PURE41 first). The PCD databank is excluded. The enthalpy and Gibbs energy of formation matter most here: RGibbs minimises the total Gibbs energy, so the equilibrium conversion depends directly on the formation data of NH~3~ (Section 14 compares it with the independent NASA-7 data).

![**Figure 8.1.** Component specification form in Aspen Plus V15 with the five components, their types, component names and formulae. Only these species can be formed by the RGibbs cracker or appear in any stream. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/02_components.png){width=95%}

**Role of water.** H~2~O stands for the water content of commercial ammonia. It changes the feed bubble and dew points (Section 9) and dilutes the reactor gas. In the CRACKER product list (NH~3~, H~2~, N~2~, H~2~O) water is allowed, but with no oxygen-bearing co-reactant it passes through unchanged (0.2 kmol/h in S4 and S5). In the PSA it is sent completely to the tail gas.

**Role of oxygen.** O~2~ enters only with the combustion air, modelled as 79 mol% N~2~ and 21 mol% O~2~. O~2~ is not in the CRACKER product list, so it cannot appear in the cracker.

**Species deliberately excluded and what that excludes.**

* *Nitrogen oxides (NO, NO~2~, N~2~O).* The burner is an RStoic block with complete combustion to N~2~ and H~2~O, so no NOx is formed even at the 1368.90 degC adiabatic flame temperature. Fuel-NOx from the NH~3~ in the tail gas and thermal NOx are therefore not predicted, and the stack composition (N~2~, H~2~O, O~2~ only) is optimistic for emissions. Section 19 treats NOx qualitatively.
* *Hydrazine (N~2~H~4~), amide/imide radicals and other N-H intermediates.* At equilibrium under cracking conditions they are negligible in the gas phase. Surface intermediates belong to the kinetic model (Section 10), not to the component list.
* *Argon and other trace air constituents.* Air is treated as binary N~2~/O~2~. This slightly changes the flue-gas heat capacity and composition. It has no effect on the cracker, because air never contacts the process side.
* *Carbon species (CO, CO~2~, CH~4~).* The feed contains no carbon. Carbon-containing make-up fuel or lubricant contamination is outside the scope.
* *Catalyst and solids.* The catalyst is not a component. RGibbs is an equilibrium model and needs no catalyst description.

<!-- data: aspen/models/baseline.inp STREAM AIR, BLOCK BURNER, BLOCK PSA FRACS; results/simulations/baseline.json streams.S4/S5 H2O = 0.2, streams.FLUE.temperature_C = 1368.90092 -->

Without an NH~3~ polishing step, product NH~3~ is set by the PSA split fraction (zero in the baseline), so the ISO 14687:2019 limits (Section 3.4; ISO, 2019, as cited in Cechetto et al., 2023) can be checked only against assumed split fractions.

<!-- data: research/notes/cechetto2023membrane.md (ISO 14687:2019 limits) -->
