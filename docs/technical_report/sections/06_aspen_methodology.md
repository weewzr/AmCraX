<!-- cites: cechetto2023membrane -->

# 6 Aspen Plus V15 methodology

This section describes how the Aspen Plus V15 model is built and solved, step by step. For each step it states what the setting is, why it matters, how it was set and what the result shows. The unit-operation models are treated in depth in Sections 9 to 11 and the automation that drives Aspen in Section 12.

## 6.1 Model generation and global settings

**What and why.** The Aspen model is never edited by hand. The module `amcrax.aspen.inp_writer` writes an Aspen input-language file from a validated `CaseInputs` object and the topology file `config/flowsheet.json`. A design change is therefore one input value, and the Aspen model, the Python model and the dashboard cannot drift apart. The baseline is `aspen/models/baseline.inp`; the variant without heat integration (`baseline_no_hi.inp`) comes from the same generator with `heat_integration = False`, and every scenario and optimisation case is stored with its own generated file in `aspen/models/cases/` (18 files). Solved models are saved as `.bkp` backups with the Windows user and host names removed.

**How it was set.** Table 6.1 lists the global settings of the generated file.

Table: **Table 6.1.** Global settings of the generated Aspen input file. *Source: aspen/models/baseline.inp.*

| Setting | Value | Purpose |
|---|---|---|
| Units | `IN-UNITS MET` with bar, degC, kW | Units of the AmCraX data interface |
| Stream class | `DEF-STREAMS CONVEN ALL` (one MIXED substream) | Vapour and liquid only; the catalyst is not a component |
| Run mode | `RUN-MODE MODE=SIM` | Steady-state flowsheet simulation |
| Databanks | `APV150 PURE41`, `AQUEOUS`, `INORGANIC`; `NOASPENPCD` | Pure-component data in a fixed search order (Section 7) |
| Property method | `PROPERTIES PENG-ROB`, global | One equation of state for all streams (Section 8) |
| Stream report | Molar and mass flows and fractions | Complete stream extraction |

<!-- data: aspen/models/baseline.inp; aspen/models/cases/ (18 .inp files, 2026-11-21) -->

## 6.2 Feed specification

**What and why.** The feed fixes the basis to which every KPI is normalised. It is refrigerated liquid ammonia drawn from atmospheric storage, so its temperature is the bubble point of the mixture, not a free choice.

**How it was set.** FEED is specified by pressure (1.013 bar) and vapour fraction 0, not by temperature (Figure 6.1). Aspen then computes the PENG-ROB bubble point of the 99.8/0.2 mol% NH~3~/H~2~O mixture. This keeps the feed exactly saturated whatever the composition or property method; a fixed temperature would give a subcooled or two-phase feed as soon as either changed.

**Result.** The feed enters at -32.96 degC (**Aspen Plus V15 simulation**), close to the -33.28 degC of the independent Python model (Section 8.3).
<!-- data: aspen/models/baseline.inp STREAM FEED (PRES=1.013 VFRAC=0. MOLE-FLOW=100.); results/simulations/baseline.json streams.FEED.temperature_C = -32.9617; results/simulations/python_baseline.json streams.FEED.temperature_C = -33.2807 -->

![**Figure 6.1.** FEED stream input in Aspen Plus V15: flash type pressure and vapour fraction (1.013 bar, 0), total flow 100 kmol/h, mole fractions NH~3~ 0.998 and H~2~O 0.002; the temperature field is left empty. Specifying the vapour fraction makes the feed a saturated liquid at its PENG-ROB bubble point. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/04_feed_stream.png){width=95%}

## 6.3 Unit-operation blocks

Table 6.2 lists the block specifications as generated. Each block uses the simplest Aspen model that represents its duty at flowsheet level; the reasons are given in Section 5.3 and in Sections 9 to 11.

Table: **Table 6.2.** Aspen block models and specifications of the baseline. *Source: aspen/models/baseline.inp; all values are engineering assumptions except where a calculator overwrites them.*

| Block | Aspen model | Specification |
|---|---|---|
| PUMP | Pump | Outlet 21 bar, efficiency 0.75 |
| VAPORIZR | Heater | 20.8 bar, 10 K superheat above the dew point |
| FEHE | HeatX, shortcut, design mode | Cold outlet 550 degC (written by TLINK), 0.3 bar drop per side |
| HEATER | Heater | 600 degC (written by TLINK), 20.2 bar |
| CRACKER | RGibbs | 600 degC, 20 bar; possible products NH~3~, H~2~, N~2~, H~2~O |
| COOLER | Heater | 40 degC, 19.5 bar |
| PSA | Sep | Split to H2PROD: H~2~ 0.85, N~2~ 0.001, others 0; H2PROD 19 bar, TAILGAS 1.3 bar |
| BURNER | RStoic | 1.2 bar, duty 0; H~2~ + ½O~2~ → H~2~O and NH~3~ + ¾O~2~ → ½N~2~ + 1.5H~2~O, conversion 1 |
| FLUEHX | Heater | 150 degC, 1.1 bar |

<!-- data: aspen/models/baseline.inp BLOCK sections -->

## 6.4 Calculator blocks

**What and why.** Two Fortran calculator blocks keep relations between variables that would otherwise have to be re-entered by hand for every case. Without them every sensitivity point would be a mismatched flowsheet.

**AIRCALC (combustion air).** It imports the H~2~ and NH~3~ molar flows of TAILGAS and exports the AIR molar flow (Figure 6.2):

$$ F_\mathrm{air} = \frac{(0.5\,F_\mathrm{H_2} + 0.75\,F_\mathrm{NH_3})(1 + e)}{0.21} \qquad (6.1) $$

where $F_\mathrm{air}$ is the air flow (kmol/h), $F_\mathrm{H_2}$ and $F_\mathrm{NH_3}$ are the tail-gas flows of H~2~ and NH~3~ (kmol/h), 0.5 and 0.75 are the stoichiometric O~2~ demands of the two burner reactions (mol O~2~/mol), $e$ = 0.15 is the excess-air fraction (engineering assumption) and 0.21 is the O~2~ mole fraction of air. The tail-gas composition changes with reactor temperature, pressure and PSA recovery; a fixed air flow would give either an O~2~ deficit, which RStoic cannot handle, or an arbitrary excess that shifts the flame temperature and the stack loss. In the baseline AIRCALC replaces the placeholder of 100 kmol/h in the input file with 68.17 kmol/h; 1.87 kmol/h O~2~, exactly the 15 % excess, leaves in the flue gas.
<!-- data: aspen/models/baseline.inp CALCULATOR AIRCALC, STREAM AIR MOLE-FLOW=100.; aspen/models/baseline.bkp AIRCALC DEFV_SUM (FH2 22.0241, FNH3 1.91513, FAIR 100 -> 68.1698); results/simulations/baseline.json streams.AIR.mole_flow_kmol_h 68.1697693, streams.FLUE O2 1.8672589 (= 0.15 x 12.448 kmol/h stoichiometric O2) -->

**TLINK (temperature tie).** It reads the CRACKER temperature $T_\mathrm{rx}$ and writes the two preheat set points:

$$ T_\mathrm{HEATER} = T_\mathrm{rx}, \qquad T_\mathrm{FEHE,cold\,out} = T_\mathrm{rx} - 50\ \mathrm{K} \qquad (6.2) $$

Without TLINK a change of reactor temperature would leave the trim heater at its old set point and break the 50 K hot-end approach of the exchanger. In the baseline TLINK writes 600 and 550 degC, the values of Table 6.2.
<!-- data: aspen/models/baseline.inp CALCULATOR TLINK; aspen/models/baseline.bkp TLINK DEFV_SUM (TRX 600, THT 600, TFE 550) -->

![**Figure 6.2.** Define tab of the calculator AIRCALC in Aspen Plus V15: imported variables FH2 and FNH3 (TAILGAS component molar flows, kmol/h) and exported variable FAIR (AIR molar flow). The calculator keeps the burner at 15 % excess air whatever the tail-gas flow; TLINK, listed below it in the navigation tree, is built the same way. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/16_calculator.png){width=95%}

## 6.5 Tear stream and convergence

**What and why.** Aspen solves the flowsheet sequential-modularly, block by block. There is no material recycle, but the flowsheet is not purely feed-forward: FEHE needs the reactor effluent S5 on its hot side while its cold outlet S3 feeds HEATER and CRACKER, which produce S5, and TLINK reads a CRACKER variable and writes to the upstream HEATER and FEHE. Such an information loop must be broken by a tear stream and converged iteratively.

**How it was set.** The input file defines no tear stream and no convergence block. Aspen detected the loop and generated a Wegstein convergence block (`$OLVER01`) that tears the reactor-feed stream S4. The variant without FEHE has the same tear on S4, so the TLINK sequencing alone creates it.

**Result.** The saved baseline reports `$OLVER01` converged (status "OK") with a final error of zero on every tear variable of S4 (total and component flows, pressure and enthalpy). The tear converges without effective iteration because every specification that fixes S4 (feed, FEHE cold-outlet and HEATER outlet temperatures, pressures) is independent of downstream results: TLINK reads an input specification of CRACKER, not a calculated result. Consequently the tear tolerance does not limit accuracy and the balances close to round-off (Section 15), a run fails only if a single block fails (for example a temperature cross in FEHE), and results do not depend on initial guesses, so sweeps are smooth and reproducible. A design with real material recycle, such as recycled unconverted NH~3~, would need an iterated tear and is outside the baseline.
<!-- data: aspen/models/baseline.bkp (CONV-SUM TEAR-SUMMARY CNV_TEAR "S4" ... "$OLVER01"; CONVERGENCE WEGSTEIN $OLVER01 OPT_STAT "OK"; CONV_PLT errors 0.D0 for S4 total and component mole flows, pressure, mass enthalpy); aspen/models/baseline_no_hi.bkp (same tear S4, OPT_STAT "OK") -->

## 6.6 Native sensitivity block STEMP

**What and why.** Most AmCraX studies drive Aspen from Python (Section 12). The Sensitivity block STEMP repeats the reactor-temperature study with Aspen's own case-study machinery, as an internal-consistency check on the external automation.

**How it was set.** STEMP varies the CRACKER temperature from 350 to 800 degC in steps of 50 K (Figure 6.3) and tabulates the NH~3~ conversion, computed by in-block Fortran as $1 - F_\mathrm{NH_3}(\mathrm{S5})/F_\mathrm{NH_3}(\mathrm{S4})$, the H~2~ product flow and the CRACKER and HEATER duties. TLINK runs in every pass, so each point is a consistent flowsheet.

**Result.** All ten points converged (Figure 6.4, Table 6.3). The 600 degC row reproduces the base case. Conversion rises steeply up to about 500 degC and then flattens: from 600 to 800 degC the H~2~ product rises by only 1.83 kmol/h (1.5 %) while the CRACKER duty rises by 50.79 kW. The HEATER duty rises because TLINK keeps the trim heater closing the last 50 K at a higher temperature level. The STEMP values agree with the Python-driven Aspen temperature sweep at the nine common temperatures to a relative deviation of 4.8 × 10^-10^ (validation item STEMP-baseline, Section 16). The shape agrees with published RGibbs curves, which exceed 95 % conversion above 500 degC for 1-20 bar (Cechetto et al., 2023, p. 10777); this is a literature comparison, not a validation.
<!-- data: results/sensitivity/aspen_native_STEMP_baseline.csv (126.634221 - 124.803215 = 1.831; 1530.79269 - 1479.99984 = 50.79); results/validation/validation_matrix.json STEMP-baseline value 4.82e-10; research/notes/cechetto2023membrane.md Fig. 2 (p. 3) -->

![**Figure 6.3.** Vary tab of the sensitivity block STEMP in Aspen Plus V15: manipulated variable Block-Var CRACKER TEMP, equidistant from 350 to 800 degC with an increment of 50 degC. It documents that the temperature study was also run inside Aspen, independently of the external automation. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/13_sensitivity_input.png){width=95%}

![**Figure 6.4.** STEMP results table in Aspen Plus V15: status OK for all ten cases, with NH~3~ conversion, H~2~ product flow (kmol/h) and CRACKER and HEATER duties (kW) against reactor temperature. These are the values of Table 6.3 as displayed by Aspen. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/14_sensitivity_results.png){width=95%}

Table: **Table 6.3.** Results of the Aspen-native sensitivity block STEMP (20 bar, baseline flowsheet with FEHE). *Source: Aspen Plus V15 simulation, results/sensitivity/aspen_native_STEMP_baseline.csv.*

| Reactor T (degC) | NH~3~ conversion | H~2~ product (kmol/h) | CRACKER duty (kW) | HEATER duty (kW) |
|---|---|---|---|---|
| 350 | 0.7575 | 96.38 | 1094.98 | 64.63 |
| 400 | 0.8604 | 109.48 | 1256.48 | 66.39 |
| 450 | 0.9195 | 117.00 | 1355.63 | 68.19 |
| 500 | 0.9521 | 121.15 | 1415.94 | 70.01 |
| 550 | 0.9703 | 123.47 | 1454.22 | 71.84 |
| 600 | 0.9808 | 124.80 | 1480.00 | 73.66 |
| 650 | 0.9871 | 125.60 | 1498.37 | 75.45 |
| 700 | 0.9910 | 126.10 | 1512.06 | 77.20 |
| 750 | 0.9935 | 126.42 | 1522.58 | 78.91 |
| 800 | 0.9952 | 126.63 | 1530.79 | 80.55 |

<!-- data: results/sensitivity/aspen_native_STEMP_baseline.csv -->

## 6.7 Run status and stream results

**What and why.** A result is accepted only if Aspen reports a converged run without errors. Every automated run is re-initialised (`Reinit`) and executed synchronously (`Engine.Run2()`), so values are read only after Aspen has loaded them. An earlier asynchronous run loop returned one stale heat duty in the equilibrium grid; the validation matrix caught it, and the fix is now guarded by repeatability and stale-value checks (Sections 12 and 16).

**Result.** The baseline and the variant without FEHE converged with no errors or warnings, in an engine time of 2.042 s for the baseline (Figure 6.5). The only message is the input-translation information that the Peng-Robinson binary parameters were retrieved from the EOS-LIT databank (Section 8.2). The run status is stored with every result file.
<!-- data: results/simulations/baseline.json status (converged true, has_errors false, has_warnings false, engine_time_s 2.042, messages EOS-LIT); results/simulations/baseline_no_hi.json status (engine_time_s 2.108) -->

![**Figure 6.5.** Run-status summary of the baseline in Aspen Plus V15: "Calculations were completed normally", Aspen Plus version 41.0 (V15), run title, date and time. The user-name and host-computer fields are masked in this image and labelled "(masked)"; nothing else was altered. Convergence without errors is the acceptance criterion for every automated run. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/15_run_status.png){width=95%}

Figure 6.6 shows the Aspen stream table from which the stream results of Sections 5 and 15 were extracted. The values are stored unchanged in `results/simulations/baseline.json`, and the KPIs and balance closures are arithmetic on them.

![**Figure 6.6.** Material stream table of the converged baseline in Aspen Plus V15 (source and destination block, phase, temperature, pressure, vapour fraction, enthalpy and entropy per stream; flows and compositions further down the table). These values are the primary Aspen data behind Tables 5.3 and 5.4. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/10_stream_results.png){width=95%}
