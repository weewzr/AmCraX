::: {custom-style="Front Heading"}
Abbreviations and nomenclature
:::

Table: **Table N.1.** Abbreviations.

| Abbreviation | Meaning |
|---|---|
| AACE | Association for the Advancement of Cost Engineering (estimate classes) |
| AmCraX | Ammonia Cracking Simulation and Optimisation Platform |
| API | Application programming interface |
| APA | American Psychological Association (citation style, 7th edition) |
| CAPEX / OPEX | Capital / operating expenditure |
| CAS | Chemical Abstracts Service (registry number) |
| CCGT | Combined-cycle gas turbine |
| CCS | Carbon capture and storage |
| CEPCI | Chemical Engineering Plant Cost Index |
| CI | Carbon intensity (kg CO~2~e per kg H~2~; simplified accounting, not an LCA) |
| CO~2~e | Carbon dioxide equivalent |
| COM | Component Object Model (Windows automation interface of Aspen Plus) |
| CRF | Capital recovery factor |
| EOS | Equation of state |
| EOS-LIT | Aspen Plus literature databank of equation-of-state binary parameters |
| FEHE | Feed/effluent heat exchanger |
| FS, FS-PRIMARY | Flowsheet cross-check items of the validation matrix (all key KPIs; reaction-section quantities only) |
| G&A | General and administrative cost |
| GRI-Mech 3.0 | Gas Research Institute reaction mechanism, source of the NASA-7 and transport data |
| GHSV | Gas hourly space velocity of NH~3~ at standard conditions per bed volume (h^-1^) |
| GUI | Graphical user interface |
| GWP | Global-warming potential |
| H1 to H4 | The four research hypotheses tested in Sections 24 to 30 and 33 to 40 |
| HeatX, Heater, Pump, Sep | Aspen Plus heat-exchanger, heater/cooler, pump and component-splitter blocks |
| IEA | International Energy Agency |
| ISO | International Organization for Standardization |
| KPI | Key performance indicator |
| LCA | Life-cycle assessment |
| LHHW | Langmuir-Hinshelwood-Hougen-Watson rate expression (Aspen Plus reaction class) |
| LCOH | Levelised cost of hydrogen |
| LHV | Lower heating value |
| LMTD | Logarithmic-mean temperature difference |
| MUSD | Million US dollars |
| NASA-7 | Seven-coefficient NASA polynomial format for ideal-gas thermochemical data |
| NIST-JANAF | NIST-JANAF thermochemical tables (National Institute of Standards and Technology) |
| NO~x~ | Nitrogen oxides (NO and NO~2~) |
| PEM | Proton-exchange membrane (fuel cell) |
| PENG-ROB | Peng-Robinson property method of Aspen Plus |
| PFR | Plug-flow reactor |
| POWERLAW | Aspen Plus power-law reaction class |
| pp | Percentage point(s) |
| PR | Peng-Robinson equation of state (Python implementation) |
| PSA / TSA | Pressure-swing / temperature-swing adsorption |
| REC | Reconversion cost: LCOH minus the ammonia feed cost (USD/kg H~2~) |
| REquil, RGibbs, RPlug, RStoic | Aspen Plus equilibrium, Gibbs-minimisation, plug-flow and stoichiometric reactor blocks (RPLUG, RGIBBS in Aspen input files) |
| RFNBO | Renewable fuel of non-biological origin (EU definition) |
| SLSQP | Sequential least-squares quadratic programming |
| SMR | Steam methane reforming |
| TEA | Techno-economic assessment |
| TRL | Technology readiness level |
| UA | Overall heat-transfer coefficient times area |
| USD, EUR | US dollar, euro |

Symbols are defined with their units where they are first used. The main ones are listed below; where a letter has two meanings, the section is given.

Table: **Table N.2.** Main symbols.

| Symbol | Meaning (unit) |
|---|---|
| $X$, $X_\mathrm{eq}$ | NH~3~ conversion, equilibrium conversion (-) |
| $\xi$ | Extent of reaction (kmol/h or mol) |
| $K$, $K_p$, $K_{eq}$ | Equilibrium constant per mol NH~3~, standard state 1 bar (-); $K_{eq}$ in Eq. (14.1) per 2 mol NH~3~ |
| $\Delta H_\mathrm{r}$, $\Delta G_\mathrm{r}^\circ$ | Reaction enthalpy, standard Gibbs energy of reaction (kJ/mol NH~3~) |
| $\delta G$ | Equivalent Gibbs-energy offset between two data sets (J/mol NH~3~), Eq. (13.8) |
| $c_{p,i}$, $\Delta c_p$ | Ideal-gas heat capacity of species $i$, heat-capacity change of reaction (J/(mol K)) |
| $T$, $P$ | Temperature (°C or K), pressure (bar absolute; Pa in Eqs. (8.1) to (8.4)) |
| $p_i$, $p^\circ$ | Partial pressure of species $i$ (bar), standard pressure 1 bar |
| $y_i$, $x_i$ | Mole fraction of species $i$ in the gas, in a phase (-) |
| $n_i$, $F_i$ | Molar flow of species $i$ (kmol/h; mol/s in Section 14) |
| $\hat{\varphi}_i$ | Fugacity coefficient of species $i$ (-) |
| $a$, $b$, $\alpha$, $\kappa$, $\omega$, $k_{ij}$ | Peng-Robinson attraction and co-volume parameters, alpha function, its slope, acentric factor, binary interaction parameter |
| $T_c$, $P_c$ | Critical temperature (K), critical pressure (Pa) |
| $R$ | Gas constant 8.314 J/(mol K); PSA H~2~ recovery (-) in Section 20 |
| $R_0$ | PSA recovery at which the net fuel heat deficit is zero (-), Eq. (17.1) |
| $e$ | Excess-air fraction (-) |
| $F_\mathrm{air}$ | Combustion-air flow (kmol/h); $F$ alone is the LMTD correction factor in Eq. (10.2) |
| $Q$ | Heat duty (kW; positive = added to the process); reaction quotient (-) in Eq. (14.5) |
| $W$ | Pump power (kW); catalyst mass (kg) in Section 14 |
| $H$, $\dot{H}_\mathrm{LHV}$ | Enthalpy flow (kW), LHV flow (kW) |
| $\Delta T_\mathrm{lm}$, $\Delta T_\mathrm{min}$, $\Delta T_\mathrm{app}$ | Log-mean temperature difference, minimum approach in the pinch analysis, FEHE hot-end approach (K) |
| $UA$, $U$ | Heat-transfer coefficient times area (kW/K), overall heat-transfer coefficient (W/(m^2^ K)) |
| $\eta_\mathrm{LHV}$ | LHV efficiency (-), Eq. (18.1) |
| $r$, $k_0$, $E_a$, $\beta$ | Reaction rate (mol NH~3~/(g~cat~ s) or per kg~cat~), pre-exponential factor, activation energy (J/mol), Temkin exponent (-) |
| $\theta$ | Fractional surface coverage (-) |
| $C_i$, $K_1$, $K_4$, $E_k$ | Concentration of species $i$ (mol/m^3^), NH~3~ adsorption constant (m^3^/mol), H~2~ adsorption constant (mol/m^3^), activation energy of the Lucentini law (kJ/mol), Eq. (25.2) |
| $\phi$ | Equilibrium approach factor $1 - Q/K_p$ (-), Eq. (25.3) |
| $T_\mathrm{op}$, $T_\mathrm{opt}$ | Lowest temperature for 95 % conversion with 100 kg catalyst; LCOH-optimal temperature (°C), Section 26 |
| $A$ | Arrhenius pre-exponential factor; total tube cross-section (m^2^) in Eq. (14.6) |
| $G$ | Total Gibbs energy in Eq. (9.1); gas mass flux (kg/(m^2^ s)) in Eq. (14.7) |
| $\varepsilon_b$, $\rho$, $d_p$, $D_t$, $\mu$ | Bed voidage (-), density (kg/m^3^), particle diameter (m), tube diameter (m), gas viscosity (Pa s) |
| $J$, $Pe$, $\delta$ | Membrane H~2~ flux (mol/(m^2^ s)), permeability (mol/(m s Pa^0.5^)), membrane thickness (m) |
| $C_\mathrm{cap}$, $C_\mathrm{fix}$, $C_\mathrm{var}$ | CAPEX (USD), fixed and variable operating cost (USD/yr) |
| $i$, $n$, $t_\mathrm{op}$ | Discount rate (-), plant life (yr), operating hours (h/yr) in Eq. (19.1) |
| $g_1$ to $g_4$ | Optimisation constraints, satisfied when $g \ge 0$, Eq. (20.1) |
