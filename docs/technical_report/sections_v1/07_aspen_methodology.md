<!-- cites: cechetto2023membrane -->

# 7 Aspen Plus simulation methodology

## 7.1 Model construction

The Aspen Plus model is not edited by hand. `amcrax.aspen.inp_writer` writes an input-language file (`aspen/models/baseline.inp`) from a validated `CaseInputs` object and `config/flowsheet.json`; the solved model is saved as `baseline.bkp`/`.apw`. The variant without the feed/effluent exchanger (`baseline_no_hi.*`) comes from the same generator with `heat_integration = False`, so a design change is one input value and cannot drift between files. Section 13 describes how the files are run.

Table: **Table 7.1.** Global settings of the generated input file. *Source: aspen/models/baseline.inp.*

| Setting | Value | Purpose |
|---|---|---|
| Units | `IN-UNITS MET`; bar, degC, kW | Units of the AmCraX interface |
| Stream class | `DEF-STREAMS CONVEN ALL` (one MIXED substream) | Vapour-liquid only; catalyst is not a component |
| Run mode | `RUN-MODE MODE=SIM` | Steady-state flowsheet simulation |
| Databanks | `APV150 PURE41`, `AQUEOUS`, `INORGANIC`; `NOASPENPCD` | Pure-component data (Section 8) |
| Property method | `PROPERTIES PENG-ROB`, global | Section 9 |
| Report | Molar and mass flows and fractions, every stream | Full stream extraction |

<!-- data: aspen/models/baseline.inp -->

## 7.2 Solution strategy and robustness

Aspen Plus solves the flowsheet sequential-modularly. There is no material recycle, but the flowsheet is not purely feed-forward: FEHE needs the effluent S5 on its hot side while its cold outlet S3 feeds HEATER and CRACKER, which produce S5, and the calculator TLINK reads a CRACKER variable and writes to the upstream HEATER and FEHE. The input file defines no tear or convergence block; Aspen detected the loop and generated a Wegstein convergence block (`$OLVER01`) that tears the reactor-feed stream S4. The saved model reports `$OLVER01` converged (status "OK") with a final error of zero on every tear variable of S4. The variant without FEHE has the same automatic tear on S4, so the TLINK sequencing alone creates it.

The tear converges without real iteration because every specification that fixes S4 (feed, FEHE cold-outlet and HEATER outlet temperature, pressures) is independent of downstream results. Consequently (i) the tear tolerance does not limit accuracy and the balances close to round-off (Table 6.4); (ii) a run fails only if a single block fails, for example an FEHE temperature cross; (iii) results do not depend on initial guesses, so batch sweeps are smooth and reproducible. Designs with true material recycle (unconverted NH~3~ or product gas as fuel) would need iterated tears and are outside the baseline.

<!-- data: aspen/models/baseline.bkp (CONV-SUM TEAR-SUMMARY CNV_TEAR "S4" ... "$OLVER01"; CONVERGENCE WEGSTEIN $OLVER01 OPT_STAT "OK"; CONV_PLT errors 0.D0); aspen/models/baseline_no_hi.bkp (same tear S4); results/simulations/baseline.json balances, status -->

## 7.3 Feed specification

The feed (Figure 7.1) is set by pressure (1.013 bar) and vapour fraction 0, not by temperature, so Aspen calculates the PENG-ROB bubble point of the 99.8/0.2 mol% NH~3~/H~2~O mixture: -32.96 degC (Aspen Plus V15 simulation). The feed stays exactly saturated whatever the composition or property method.

![**Figure 7.1.** FEED stream specification in Aspen Plus V15: pressure 1.013 bar, vapour fraction 0, total flow 100 kmol/h, mole fractions NH~3~ 0.998 and H~2~O 0.002. Specifying the vapour fraction instead of the temperature makes the feed a saturated liquid at its PENG-ROB bubble point. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/04_feed_stream.png){width=95%}

<!-- data: aspen/models/baseline.inp STREAM FEED; results/simulations/baseline.json streams.FEED.temperature_C = -32.9617036 -->

## 7.4 Calculator blocks

Two Fortran calculator blocks hold relations between variables that would otherwise have to be updated by hand for every case.

**AIRCALC (combustion air).** It reads the H~2~ and NH~3~ molar flows in TAILGAS and writes the AIR molar flow:

$$ F_\mathrm{air} = \frac{(0.5\,F_\mathrm{H_2} + 0.75\,F_\mathrm{NH_3})(1 + e)}{0.21} \qquad (7.1) $$

where $F_\mathrm{air}$ is the air flow (kmol/h), $F_\mathrm{H_2}$ and $F_\mathrm{NH_3}$ are the tail-gas flows of H~2~ and NH~3~ (kmol/h), 0.5 and 0.75 are the stoichiometric O~2~ demands per mole (H~2~ + 0.5 O~2~ -> H~2~O; NH~3~ + 0.75 O~2~ -> 0.5 N~2~ + 1.5 H~2~O), $e = 0.15$ is the excess-air fraction (engineering assumption) and 0.21 is the O~2~ mole fraction of air. Because the tail-gas composition changes with temperature, pressure and recovery, a fixed air flow would give either an O~2~ deficit in RStoic or an arbitrary excess that shifts flame temperature and stack loss. For the baseline AIRCALC sets 68.17 kmol/h of air; 1.87 kmol/h O~2~ remains in the flue gas.

**TLINK (temperature tie).** It reads the CRACKER temperature $T_\mathrm{rx}$ and writes the HEATER outlet ($= T_\mathrm{rx}$) and FEHE cold-outlet temperature ($= T_\mathrm{rx} - 50$ K). Without it, a reactor-temperature change would leave the trim heater at its old set point and break the 50 K approach, so every sensitivity point (Section 7.5) would be a mismatched flowsheet.

![**Figure 7.2.** Calculator block in Aspen Plus V15 with its imported and exported variables and Fortran statements. The calculators keep the air flow and the preheat temperatures consistent with the case being solved. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/16_calculator.png){width=95%}

<!-- data: aspen/models/baseline.inp CALCULATOR AIRCALC, TLINK; results/simulations/baseline.json streams.AIR.mole_flow_kmol_h = 68.1697693, streams.FLUE.component_mole_flow_kmol_h.O2 = 1.8672589 -->

## 7.5 Native sensitivity block STEMP

STEMP varies the CRACKER temperature from 350 to 800 degC in 50 K steps inside Aspen Plus and tabulates the NH~3~ conversion ($1 - F_\mathrm{NH_3}(\mathrm{S5})/F_\mathrm{NH_3}(\mathrm{S4})$, in-block Fortran), the H~2~ product and the CRACKER and HEATER duties; TLINK runs in each pass. It checks the externally driven sweeps of Section 15 with Aspen's own case-study machinery, independently of the Python layer (Table 7.2).

Table: **Table 7.2.** Results of the Aspen-native sensitivity block STEMP (20 bar, baseline flowsheet with FEHE). *Source: Aspen Plus V15 simulation, results/sensitivity/aspen_native_STEMP_baseline.csv.*

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

The 600 degC row reproduces the base case. Conversion rises steeply to about 500 degC and then flattens: from 600 to 800 degC the H~2~ product rises by only 1.83 kmol/h while the CRACKER duty rises by 50.79 kW. The HEATER duty rises because TLINK keeps the trim heater closing the last 50 K. The shape agrees with published RGibbs curves (> 95 % conversion above 500 degC for 1-20 bar; Cechetto et al., 2023), a literature comparison only.

<!-- data: results/sensitivity/aspen_native_STEMP_baseline.csv (126.634221 - 124.803215; 1530.79269 - 1479.99984); research/notes/cechetto2023membrane.md Fig. 2 -->

![**Figure 7.3.** Input form of the sensitivity block STEMP in Aspen Plus V15: the manipulated variable (CRACKER temperature, 350-800 degC, increment 50 K) and the sampled variables. It documents that the temperature study ran inside Aspen and not only through the external automation. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/13_sensitivity_input.png){width=95%}

![**Figure 7.4.** STEMP results table in Aspen Plus V15 (conversion, H~2~ product flow, CRACKER and HEATER duties against reactor temperature). These are the values of Table 7.2 as displayed by Aspen. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/14_sensitivity_results.png){width=95%}

## 7.6 Run status and convergence

The baseline and the variant without FEHE converged with no errors or warnings (engine time 2.042 s for the baseline). The only message is the input-translation information that the Peng-Robinson binary parameters were retrieved from the EOS-LIT databank (quoted in Section 9.2). The run status is stored in each result file and a result is accepted only when converged without errors. Every automated run is re-initialised (`Reinit`) and executed synchronously (`Engine.Run2()`), so results are read only after Aspen has loaded them; an earlier asynchronous run loop produced one stale equilibrium-grid value, which the validation matrix caught (Sections 13.3 and 14.3).

<!-- data: results/simulations/baseline.json status; results/simulations/baseline_no_hi.json status -->

![**Figure 7.5.** Aspen Plus V15 run-status window of the baseline: calculations completed normally, with the EOS-LIT binary-parameter information message. The status is the acceptance criterion for every automated run. The user-name and host-computer fields are masked and labelled "(masked)". *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/15_run_status.png){width=95%}

## 7.7 Stream results

Figure 7.6 shows the stream table from which Table 6.3 was extracted; the values are stored unchanged in `results/simulations/baseline.json`, and KPIs and balances are arithmetic on them.

![**Figure 7.6.** Stream results table in Aspen Plus V15 (temperature, pressure, vapour fraction, molar and mass flows and fractions for each stream). These values are the primary Aspen data behind Tables 6.3 to 6.5. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/10_stream_results.png){width=95%}

<!-- data: results/simulations/baseline.json notes -->
