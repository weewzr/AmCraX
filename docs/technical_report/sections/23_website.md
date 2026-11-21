<!-- cites: smith_grimech30, goodwin2018cantera -->

# 23 Public website

## 23.1 Scope

The public website presents AmCraX to readers who have neither Aspen Plus nor the local platform. It is a static GitHub Pages build of the same React application as the dashboard (Section 22), with nine sections in front of it: Overview, Why cracking, Process flow, Methodology, Results, Architecture, Research, Docs and About (Figure 23.1). The site is built to be served at https://weewzr.github.io/AmCraX/; the source is in the repository https://github.com/weewzr/AmCraX.
<!-- data: frontend/src/site/routes.ts SITE_ROUTES (9 entries); frontend/README.md; frontend/package.json build:pages (base /AmCraX/) -->

<!-- DEPLOYMENT-STATEMENT -->

The static build shows only published results. It never runs Aspen Plus and never contacts an API or Aspen: the dashboard pages open in SNAPSHOT mode with the exported results, and actions that need a server stay disabled. A banner on every page says "Published results - static site. Live Aspen Plus runs need the local platform." Live runs require the local platform of Section 22.
<!-- data: frontend/src/components/Shell.tsx STATIC_SITE_NOTICE -->

Table: **Table 23.1.** The two builds of the AmCraX front end. *Source: frontend/README.md, frontend/package.json, docs/internal/fact_sheet.md F19.*

| Property | Local platform (`npm run dev` / `npm run build`) | Public site (`npm run build:pages`) |
|---|---|---|
| Base path | `/` | `/AmCraX/` |
| Data | LIVE from the API when it answers, otherwise SNAPSHOT or DEMO | Published results only (SNAPSHOT) |
| Aspen Plus runs | Yes, through the API worker, with a licence | Never |
| API requests | Yes | None |
| Calculation in the browser | Ideal-gas equilibrium calculator | Ideal-gas equilibrium calculator |

![**Figure 23.1.** Landing page of the public site (1440 × 900 px): static-site banner, navigation to the nine sections, a picture of the process flow diagram and headline facts read from the exported results. Actual AmCraX website screenshot. *Source: AmCraX public site in static build showing Aspen Plus V15 results.*](../screenshots/site_home_desktop.png){width=100%}

## 23.2 How results reach the site

`scripts/export_snapshot.py` copies the stored results, verbatim or in the exact form the API returns them, into `frontend/public/snapshot/`, a mirror that is committed to the repository. `npm run build:pages` first copies the report, deck and validation documents into the download folder, then compiles the strict TypeScript and builds the site with the base path `/AmCraX/`. The GitHub Actions workflow `.github/workflows/deploy-pages.yml` is configured to run on a push to the main branch: it installs the locked packages, runs the unit tests, builds the site and uploads it to GitHub Pages. It needs neither Python nor Aspen Plus, so the site is only as current as the last export.
<!-- data: scripts/export_snapshot.py docstring; frontend/package.json scripts (prebuild:pages, build:pages); .github/workflows/deploy-pages.yml -->

## 23.3 In-browser equilibrium calculator

The only calculation that runs in the visitor's browser is the ideal-gas equilibrium of a pure NH~3~ feed. It is a TypeScript port of the Python model with the same GRI-Mech 3.0 NASA-7 data (Smith et al., n.d.), taken from Cantera (Goodwin et al., 2018). The conversion follows the closed form derived in Section 13:

$$ X_\mathrm{eq} = \left(1 + \frac{3\sqrt{3}}{4}\,\frac{P/P^\circ}{K(T)}\right)^{-1/2} \qquad (23.1) $$

where $X_\mathrm{eq}$ (–) is the equilibrium NH~3~ conversion, $P$ (bar) the pressure, $P^\circ$ = 1 bar the standard pressure and $K(T)$ (–) the equilibrium constant per mole of NH~3~ at temperature $T$ (K). Unit tests compare the port with nine points of the Python grid between 250 and 900 °C and 1 and 40 bar, requiring agreement within 10^−4^ in conversion and mole fractions and 10^−5^ (relative) in K. The curve is labelled "calculated in your browser (ideal gas)", and the stored Aspen RGibbs points beside it "Aspen Plus V15 result (pre-computed)" (Figure 23.2).
<!-- data: frontend/src/calc/equilibrium.ts; frontend/src/calc/equilibrium.test.ts (9 REF rows from results/validation/equilibrium_python_grid.csv; tolerances 1e-4, 1e-5, 5e-3 kJ/mol); frontend/src/site/ui.tsx badge texts -->

![**Figure 23.2.** Results section of the public site: Aspen Plus V15 conversion and duty sweeps, with the ideal-gas curve calculated in the browser and each series carrying its source badge. Actual AmCraX website screenshot. *Source: AmCraX public site showing Aspen Plus V15 results and an in-browser calculation.*](../screenshots/site_results_desktop.png){width=100%}

## 23.4 Automated checks, accessibility and responsiveness

`frontend/scripts/site_check.mjs` tests the built site, served by a local script exactly as GitHub Pages would serve it (under `/AmCraX/` only). It drives headless Microsoft Edge through all nine site routes and the eleven dashboard routes at four viewports: 390 × 844, 820 × 1180, 1440 × 900 and 1920 × 1080 px. On every route it requires no console error, no failed request, no request outside the base path (hence no API call) and no horizontal overflow; further checks cover the mobile menu, the calculator, the diagram panels, anchors and downloads. For accessibility, each site page has one main heading, a skip link and focus on the main content after navigation, and the diagram and menu work from the keyboard.
<!-- data: frontend/scripts/site_check.mjs (SITE 9 routes, PLATFORM 11 routes, VIEWPORTS default list, checks); frontend/src/site/SiteLayout.tsx -->
