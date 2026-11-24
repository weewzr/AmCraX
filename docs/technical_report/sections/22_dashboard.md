<!-- cites: -->

# 22 Interactive dashboard

## 22.1 Purpose and structure

The dashboard presents the stored results of Sections 9 to 21 and runs new cases. It is a React 19 and TypeScript single-page application built with Vite; the process flow diagram uses React Flow and the charts use Recharts. It lives under the route prefix `#/platform` and is loaded as a separate code chunk, so visitors of the public site (Section 23) download it only when they open it. A case selector in the header sets the active case, which drives every page.

The eleven pages each answer one question. **Overview**: what does the plant do, and what are the headline KPIs of the active case? **Process Flow Diagram**: what happens in each unit and stream? **Simulation**: what does a new operating point give? **Reactor Analysis**: how far is the cracker from equilibrium, and how much catalyst would a kinetic reactor need? **Heat Integration**: what are the pinch targets? **Sensitivity Analysis**: how do the KPIs respond to one parameter? **Optimisation**: which optima did the Python model find, and did Aspen confirm them? **Techno-Economics**: what does the hydrogen cost and why? **Environment**: what is the carbon intensity under each NH~3~ route and heat source? **Validation**: what has been checked, with what result, and what has not? **Reports**: where are the deliverables, figures, screenshots and references?
<!-- data: frontend/src/platform/PlatformApp.tsx (11 routes); frontend/src/pages/*.tsx lead texts -->

## 22.2 Interactive process flow diagram

The diagram is generated from `config/flowsheet.json`, the same topology file that the Aspen input writer and the Python model read (Section 12). Clicking a unit opens an equipment panel with its Aspen block type, role, status, duty, shaft power and outlet conditions (Figure 22.1); clicking a stream opens a stream panel with temperature, pressure, vapour fraction, flows, enthalpy flow and composition (Figure 22.2). Overlays colour the streams by dominant component or temperature and label them with temperature, pressure, molar or mass flow and main composition. A status bar shows the case, its source, convergence, mass and energy closures and whether the exchanger is present; for a case without heat integration the FEHE and streams S3 and S6 disappear. The PSA carries a "reduced-order model" tag. Keyboard selection (Tab, Enter, Esc) and equipment and stream lists below the canvas make the diagram accessible without a mouse.

![**Figure 22.1.** Process Flow Diagram page with the CRACKER equipment panel open (baseline, LIVE mode). Every value carries its provenance badge, and block status and convergence are shown next to the duty. Actual AmCraX dashboard screenshot. *Source: AmCraX dashboard showing an Aspen Plus V15 simulation.*](../screenshots/dashboard_pfd_equipment_panel.png){width=100%}

![**Figure 22.2.** Stream panel of the hot cracked gas S5 with composition table, and the hover tooltip on the drawn stream. The panel shows the reactor outlet at 600 °C and 20 bar with 0.97 mol% NH~3~ directly from the stored result. Actual AmCraX dashboard screenshot. *Source: AmCraX dashboard showing an Aspen Plus V15 simulation.*](../screenshots/dashboard_pfd_stream_panel.png){width=100%}

## 22.3 Data modes and provenance

The dashboard runs in exactly one of three data modes. It is LIVE when `GET /api/health` answers, SNAPSHOT when the API is unreachable but the exported results mirror exists, and DEMO when neither is available. DEMO data come from a bundled fixture in which every object is labelled `demo`, under a permanent red banner. Modes are never mixed on a page, and a failing live load is shown as an error, never replaced by demonstration data. Every number is rendered through one component that adds its unit and a provenance badge (`aspen_plus_v15`, `python_model`, `literature`, `assumption` or `demo`) and shows "n/a" for a missing value. Actions that need the server are disabled outside LIVE.
<!-- data: frontend/src/data/mode.ts resolveDataMode; frontend/README.md "Two builds, three data modes"; docs/developer_guide.md section 13 -->

## 22.4 Running a simulation

On the Simulation page (Figure 22.3) the user edits the operating conditions, chooses the Aspen Plus V15 or the Python engine and submits a job. The job passes through `queued`, `running` and then `succeeded`, `failed` or `timeout`, and a status panel shows the elapsed and engine times. Aspen jobs run strictly one at a time in a first-in, first-out queue, because the project assumes one licence seat; each runs in a separate worker process under a machine-wide lock. The Aspen engine is offered only when the API reports Aspen as available, a requested Aspen run is never replaced by a Python result, and a failed job stores nothing. A Python result never overwrites an Aspen case.
<!-- data: frontend/src/features/simulation/SimForm.tsx, JobPanel.tsx; docs/api.md "Job life-cycle", "Process isolation of Aspen" -->

![**Figure 22.3.** Simulation page: operating conditions with validated ranges, the engine switch and the stored baseline with its convergence status and export buttons. Actual AmCraX dashboard screenshot. *Source: AmCraX dashboard showing an Aspen Plus V15 simulation.*](../screenshots/dashboard_simulation.png){width=100%}

## 22.5 API and testing

The FastAPI back end documented in `docs/api.md` lists 49 method–path combinations: 47 under `/api` plus the file and figure downloads. Long work runs as jobs, and every error uses one model with a code, a message and a detail field.
<!-- data: docs/api.md Endpoints table (42 rows, 49 backticked paths; /files/{key} and /figures/{file} outside /api) -->

The frontend had 96 unit tests (Vitest) when the dashboard was first documented on 21 November 2026 and 290 unit tests in 30 files at the final check of Phase 2 on 24 November 2026, most of them for the pure functions that shape API payloads into table and chart rows and the browser-model parity tests of Section 39. The strict TypeScript build must finish with no errors. Browser scripts driving headless Microsoft Edge check every page for console errors, failed requests and horizontal overflow, exercise the diagram panels, and run one live Python simulation end to end before deleting the case they created.
<!-- data: docs/internal/fact_sheet.md F18 (96 frontend unit tests); frontend/README.md "Browser checks and screenshots" (diag_pages.mjs, pfd_check.mjs, e2e_sim_run.mjs) -->
