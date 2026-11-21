# purcel2024stability

## Bibliographic data
- Purcel, M., Müller, A. S., Diehl, P., Kappis, K., Trunschke, A., & Muhler, M. (2025). Long-term stability of ammonia decomposition over nickel-based catalysts. *Energy Technology, 13*(2), 2400678. https://doi.org/10.1002/ente.202400678
- The PDF footer says "© 2024" and "Energy Technol. 2025, 13, 2400678". The article was published online in 2024 and assigned to the 2025 volume. The citekey keeps 2024, matching the file name; APA uses the issue year 2025.
- Open access (CC BY).
- DOI verified: `https://doi.org/api/handles/10.1002/ente.202400678` returned responseCode 1.
- Type: research article, 8 pages.
- Affiliations: MPI CEC Mülheim, Ruhr University Bochum, FHI Berlin. Funded by BMBF TransHyDE/AmmoRef, grant 03HY203A.

## Scope
The paper reports 800 h isothermal long-term stability tests of NH3 decomposition at **534 °C and atmospheric pressure in 98 % NH3**. Two catalysts were tested:
1. an industrial Ni-based reference catalyst supplied by Clariant, **composition not disclosed**;
2. a coprecipitated Ni/Al2O3 catalyst with **51.2 wt% Ni by XRF** (nominal 50 wt%).

Ni/Al2O3 deactivation was characterised by XRD, BET/BJH and TPR. **No kinetic model or rate parameters are given.**

## Reactor and conditions (pp. 2, 4–6)
**Reactor**
- Integral PFR: ½″ stainless-steel tube with **ID 10.1 mm** and total length 43 cm, coated with Silcolloy.
- A central ⅛″ thermowell holds 4 type-K thermocouples at 1, 3, 5 and 7 cm.
- Three-zone furnace. A three-point cascade controller adjusts the furnace setpoint in 1 °C steps to hold the bed within ±0.5 °C (p. 2, Fig. 1; p. 6, Fig. 6).
- The furnace setpoint ran at about 680–690 °C to hold a 534 °C bed (Fig. 1, read from figure). This reflects the large endothermic heat demand.

**Bed**
- **500 mg catalyst, sieve fraction 200–300 µm, diluted with 4.5 g SiC.**
- **Bed height 2.6 cm**, placed in the isothermal zone at 5.4–8 cm. With SiC filler the axial profile varies by ≤1 °C over the upper 3.5 cm and by 10 °C at most overall (p. 5, Fig. 5b).

**Feed and space velocity**
- Feed: **490 mL·min⁻¹ NH3 + 10 mL·min⁻¹ Ar**, i.e. y_NH3,0 = 0.98. Normal conditions are 273 K and 1 bar (p. 4).
- GHSV: **60,000 mL·g⁻¹·h⁻¹** at 500 mL·min⁻¹, 36,000 at 300 mL·min⁻¹ and 12,000 at 100 mL·min⁻¹ (Fig. 2 legend, p. 2).

**Activation and analysis**
- Reduction followed the manufacturer's instructions; **conditions not given**.
- Analysis by GC-TCD with Ar internal standard, plus an IR/TCD multichannel analyser.

**Derived by this agent, not stated in the paper**
- The NH3 feed is 490 mL/min at 273.15 K and 1 bar, i.e. about 3.59×10⁻⁴ mol·s⁻¹.
- Hence W/F_NH3 ≈ 0.5 g / 3.59×10⁻⁴ mol·s⁻¹ ≈ 1.39×10³ g·s·mol⁻¹. This uses ideal gas and treats "normal conditions" as 273.15 K and 1 bar, as stated on p. 4.

## Equations
- (1) 2NH3 ⇌ 3H2 + N2, ΔH⁰ = +92 kJ mol⁻¹ (p. 1). This is per 2 mol NH3 and is quoted without a citation.
- (2) Conversion with volume expansion (p. 2; checked against the rendered PDF): X_NH3 = (1 − y_NH3/y_NH3,0) / (1 + y_NH3).
  - y_NH3,0 is the inlet NH3 mole fraction (0.98) and y_NH3 the effluent NH3 mole fraction.
  - This is algebraically X = (y0 − y)/(y0(1 + y)) for 2NH3 → N2 + 3H2.

## Results (stated values)
**Reference catalyst at 534 °C, 60,000 mL·g⁻¹·h⁻¹ (pp. 2–4, Fig. 3)**
- X was about 80 % directly after reduction and 91.3 % within the first hour. The conclusion on p. 4 says 90.1 %, an internal inconsistency.
- X reached a maximum of **91.9 % at 250 h TOS**, then fell to **90.4 % after 800 h TOS**.
- That drop is described as "1.5 %" activity loss relative to the maximum. Numerically it is 1.5 percentage points.
- Relative to X at 4 h TOS, the decrease over 796 h was 1.1 %.
- Deactivation appears linear but may plateau beyond 800 h.
- The deactivation window is described as both "550 h" and "496 h" (p. 2 vs p. 4), another internal inconsistency.

**Ni/Al2O3 (51.2 wt% Ni) at 534 °C (same conditions)**
- Maximum X was **54.1 %**, followed by continuous deactivation.
- Total loss was **13.5 % relative to maximum over 800 h TOS** (p. 2). It is ambiguous whether this means relative % or percentage points; the paper's wording "relative to the maximum conversion" suggests relative %.

**Ni/Al2O3 characterisation (p. 3, Table 1)**

| Stage | BET [m²/g] | Pore volume [mL/g] | Pore diameter [nm] |
|---|---|---|---|
| NiO–Al2O3 precursor | 275 | 0.604 | 5.4 |
| Reduced/passivated | 169 | 0.296 | 4.7 |
| After 1000 h TOS | 150 | 0.319 | 5.4 |

- Reduction cost 61 % of the BET area, and 1000 h TOS cost a further 11 %.
- Ni crystallite size (Scherrer, 52° reflection) grew from **3.5 nm fresh to 5.0 nm after 1000 h TOS**. The paper attributes this to sintering of both the Ni⁰ particles and the Al2O3 matrix.
- No nickel nitride was detected.
- TPR showed a single NiO → Ni⁰ reduction peak with maximum at 640 °C.

**Transient light-off of the reference catalyst** (Fig. 2, p. 2; 1 °C/min ramp; read from figure, approximate ±5 °C)

| GHSV [mL·g⁻¹·h⁻¹] | T at X = 50 % | T at X = 90 % |
|---|---|---|
| 12,000 | ≈ 460 °C | ≈ 495 °C |
| 36,000 | ≈ 480 °C | ≈ 527 °C |
| 60,000 | ≈ 485 °C | 534 °C (stated) |

At all three GHSV, X is about 100 % at ≥ 580 °C.

## Literature stability tests (Table 2, p. 4; cited, not measured)

| Catalyst | Duration | Conditions | Ref |
|---|---|---|---|
| Nix(MgyAlzOn) from layered double hydroxides | 150 h | 550 and 620 °C, 100 % NH3 | [21] |
| 90 mol% Ni on Al2O3 | 72 h | 600 °C, 100 % NH3 | [22] |
| 40 wt% Ni/Y2O3 | 50 h | 550 °C, 100 % NH3 | [18] Okura et al. |
| La-modified Ni/Al2O3 | 15 h | 700 °C | [23] |
| 40 wt% Ni/BaZrO3 | 35 h | 550 °C | [24] |
| CeO2-modified Ni/Al2O3 | 180 h | 500 °C, 15 % NH3 | [25] |
| Ni/Zr-doped Al2O3 | 5 h | 800 °C | [26] |
| NiO/Al2O3 | 20 h | 600 °C | [27] |
| Ni/Al2O3 | 24 h | 600 °C | [28] |

Yamazaki et al. [20] ran Ru/MgO for up to 4000 h and found a linear activity decrease (p. 4). The full reference strings were not extracted (see open issue 9).

## Limitations
- The industrial catalyst's composition, Ni loading, pellet form and reduction protocol are undisclosed, so its activity cannot be tied to a kinetic model.
- Only one temperature (534 °C) and **atmospheric pressure** were tested. No pressure, H2-cofeed or temperature-cycling data.
- 800 h is far shorter than an industrial catalyst life.
- Internal inconsistencies in the text: 91.3 vs 90.1 % at 1 h; 550 vs 496 h deactivation window.
- Deactivation is reported as % without a clear statement of relative vs absolute basis.

## Relevance to AmCraX
1. **Catalyst stability evidence** for Ni.
   - Industrial Ni loses about 1.5 percentage points of conversion over about 550 h at 534 °C and 1 atm.
   - A derived linear rate is about 2.7×10⁻³ %-points/h. This is computed as (91.9 − 90.4)/(800 − 250). It is a derived value and must not be extrapolated beyond 800 h without labelling it an assumption.
   - Unpromoted coprecipitated Ni/Al2O3 sinters, losing 13.5 % in 800 h.
   - This supports a catalyst-replacement interval assumption in economics, which must be labelled an assumption.
2. **Validation point with known catalyst mass, unlike takahashi2016kinetic.**
   - Integral PFR at 534 °C, 1 atm, 500 mg catalyst, 0.98 NH3 at 490 mL/min.
   - Results: X = 91.9 % (industrial Ni) and 54.1 % (Ni/Al2O3).
   - The catalysts differ from Takahashi's 30 wt% Ni/MgO, so only an order-of-magnitude comparison is legitimate.
3. **Practical heat-demand evidence:** the furnace ran at about 680–690 °C to hold a 534 °C bed, which supports modelling the cracker heat-supply approach temperature.
