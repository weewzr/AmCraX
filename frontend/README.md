# AmCraX frontend

React 19 + TypeScript (strict) + Vite, `@xyflow/react` (React Flow) for the process flow diagram, Recharts for charts,
hash routes. Plain CSS with custom properties (`src/index.css`, `src/pfd/pfd.css`, `src/site/site.css`); dark theme by default, light theme toggle.

One app, two areas (see `src/App.tsx`):

| Area | Routes | What |
|---|---|---|
| Public website | `#/` (interactive process simulator), `#/hypotheses` and `#/hypotheses/{catalyst,economics,purification,end-use,validation,aspen-evidence}`, `#/overview`, `#/why`, `#/pfd`, `#/methodology`, `#/results`, `#/architecture`, `#/research`, `#/docs`, `#/about` | Eleven sections with top navigation, footer, the simulator as first page, the hypothesis pages, interactive PFD, charts rendered from the snapshot, equilibrium calculator, downloads. Code in `src/site/` (hypothesis pages in `src/site/hyp/`), the simulator page in `src/simulator/` and its browser model in `src/sim/`. |
| Engineering platform | `#/platform` and `#/platform/{pfd,simulation,reactor,heat,sensitivity,optimisation,economics,environment,validation,reports}` | The eleven-page dashboard (`src/pages/`, shell in `src/components/Shell.tsx`, routes in `src/platform/PlatformApp.tsx`, lazy-loaded). Build every dashboard link with `platformPath()` from `src/site/routes.ts`. |

The site's primary call to action goes to `#/platform/pfd`. Anchors inside a page are `#/results#economics` (the router reads the second hash).

## Run, build, test

From the project root (PowerShell; nothing is on PATH, so dot-source the environment script first):

```powershell
. .\scripts\env.ps1
cd frontend
npm install            # first time only
npm run dev            # http://localhost:5173 (proxies /api, /figures, /files, /aspen-screenshots, /dashboard-screenshots to http://127.0.0.1:8000); predev copies the downloads
npm run build          # local build: tsc + vite build, base "/", zero TypeScript errors required
npm run build:pages    # GitHub Pages build: prebuild:pages (prepare_site.mjs) + tsc + vite build --mode pages, base "/AmCraX/"
npm test               # vitest (npx vitest run)
node scripts/serve_pages.mjs --port 4180    # serve dist exactly as GitHub Pages would: only under /AmCraX/, 404 elsewhere, no API
```

Start the API in another shell for LIVE mode: `scripts\start_api_dev.ps1` (stop: `scripts\stop_api_dev.ps1`; neither starts Aspen Plus).

## Two builds, three data modes

| Build | Base | API |
|---|---|---|
| `npm run dev` / `npm run build` | `/` | LIVE when `GET /api/health` answers, otherwise SNAPSHOT, otherwise DEMO |
| `npm run build:pages` (`--mode pages`) | `/AmCraX/` | never contacted: always SNAPSHOT from the bundled mirror; the header says "Published results - static site. Live Aspen Plus runs need the local platform." |

| Mode | Condition | Source |
|---|---|---|
| LIVE | `GET /api/health` answers | the FastAPI backend |
| SNAPSHOT | API unreachable (or `?mode=snapshot`, or the Pages build) and `snapshot/manifest.json` exists | static mirror `public/snapshot/`, written by `python scripts/export_snapshot.py` |
| DEMO | neither | bundled fixture `src/demo/fixture.ts`, every object `source: "demo"`, permanent red banner |

Code keeps using logical paths (`/api/...`, `/snapshot/...`, `/figures/...`, `/downloads/...`). Every non-API URL goes through `withBase()`
(`src/api/url.ts`, uses `import.meta.env.BASE_URL`); in SNAPSHOT mode the fetch wrapper (`src/api/client.ts`) answers read-only GETs from the mirror
(cases, `/api/data/...`, scenarios, validation, references, reports, figures) and returns 503 for anything that needs the server
(simulations, sweeps, optimisation, parametric economics and carbon queries). A reachable API or snapshot that fails to load shows an error; it never falls back to demo data.
The snapshot is a copy made at export time: re-export (`python scripts/export_snapshot.py`) to update both the platform and the site.

Every number goes through `<Value>` (`src/components/ui.tsx`): unit, provenance badge (`aspen_plus_v15`, `python_model`, `literature`, `assumption`, `demo`) and `n/a` for null.
On the public site the one live calculation, the ideal-gas equilibrium calculator (`src/calc/equilibrium.ts`, NASA-7 data of GRI-Mech 3.0 via Cantera copied to `src/data/nasa7.json`),
is labelled "calculated in your browser (ideal gas)" and stored Aspen results "Aspen Plus V15 result (pre-computed)". It is unit-tested against `results/validation/equilibrium_python_grid.csv`.

## Downloads and the snapshot

- `scripts/prepare_site.mjs` copies into `public/downloads/` (skips missing files; portable; run by `predev` and `prebuild:pages`): the technical report (PDF, DOCX) and the preserved 23 November 2026 release PDF, the pitch deck (PDF, PPTX) and speaker script, the two validation documents, the Phase 2 research documents (`verdict_methodology_v2.md`, `unified_baseline.md`, `uncertainty_quantification.md`, `methodology_transfer_matrix.md`, `phase2_findings_changed.md`, `limitations_and_future_work.md`) and every PDF in `docs/paper/build/` (the research paper and the executive summary, built by `python docs/paper/build_paper.py`). The fixed list is mirrored in `src/site/downloads.ts`.
- `public/snapshot/` is the committed static mirror. `public/img/pfd_baseline.png` and `public/og-image.png` are made from real screenshots by `scripts/make_site_images.mjs`.
- Deployment: `.github/workflows/deploy-pages.yml` (npm ci, npm test, build:pages, 404.html, upload, deploy; no Python, no Aspen).

## Layout

- `src/api/` typed fetchers, snapshot fetch wrapper, `url.ts` (base-path helper); `src/data/` mode resolver, dataset context, formatting, metric labels, `nasa7.json`.
- `src/site/` public site: `SiteLayout`, `pages/`, `EquilibriumCalculator`, `ArchitectureDiagram` (original SVG), `results.ts` (chart data shaping), `cite.ts` (citations from `references.json`), `routes.ts`, `downloads.ts`.
- `src/sim/` browser process model of the simulator (a port of the Python models, tested against the Python test vectors written by `scripts/research/export_simulator_data.py`; record in `results/research/simulator/parity_report.json`); `src/simulator/` the simulator page (controls, outputs, graphs).
- `src/calc/` browser equilibrium model. `src/pfd/` flowsheet -> React Flow mapping, symbols, panels (`PfdExplorer` is shared by the platform and the site).
- `src/components/` shell, `ui.tsx`, `DataTable.tsx`, `charts.tsx`. `src/features/` per-page building blocks; `src/pages/` the eleven platform pages.

## Browser checks and screenshots (Microsoft Edge headless through playwright-core)

```powershell
node scripts/site_check.mjs [--base http://127.0.0.1:4180/AmCraX/] [--viewports 390x844,820x1180,1440x900,1920x1080] [--routes why,results] [--shots DIR]   # static site: every route, interactions, downloads, no console errors / 404s / overflow
node scripts/capture_dashboard.mjs [--base http://127.0.0.1:5173] [--out DIR] [--pages a,b] [--case id] [--full] [--query ?mode=snapshot --prefix snapshot]   # dashboard_<page>.png (1600x1000)
node scripts/diag_pages.mjs [--base URL] [--width 1440] [--shots DIR] [--query ?mode=snapshot]     # platform: console errors, failed requests, overflow
node scripts/pfd_check.mjs [baseUrl]            # interactive PFD checks (platform)
node scripts/e2e_sim_run.mjs                     # LIVE Simulation page run (Python engine, T = 650), then deletes the case it made
node scripts/make_site_images.mjs [--base URL]   # hero picture and 1200x630 social preview
```

`site_check.mjs` writes full-page `docs/screenshots/site_<page>_desktop.png` for the site routes; phone, tablet, full-HD, platform and calculator captures go to `docs/screenshots/qa/` (git-ignored). `capture_site.mjs` then overwrites four of the desktop files and `site_home_mobile.png` with viewport-sized hero crops. Typical release check:
`npm run build:pages; node scripts/serve_pages.mjs --port 4180` (second shell) `; node scripts/site_check.mjs`.
