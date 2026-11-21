# AmCraX dependencies and licences

AmCraX itself is released under the MIT licence ([../LICENSE](../LICENSE)). The versions below are those installed on the development machine at version 0.1.0 (`pip list`,
`node_modules/*/package.json`, `<tool> --version`). Licence strings are copied from package metadata (`importlib.metadata`, the `license` field of each
`package.json`) or from the licence file shipped with the tool; where the installed copy does not state a licence this is said
explicitly rather than filled in from memory. This is an engineering inventory, not legal advice. No third-party code is vendored in the repository.

Reproducible pins: `requirements.txt` (Python), `frontend/package-lock.json` and `docs/pitch_deck/package-lock.json` (npm).
Third-party software survey (public projects that were read for context, none vendored): [reference_projects/github_survey.md](reference_projects/github_survey.md).

## 1. Python packages (project venv, Python 3.12.10)

| Package | Version | Purpose in AmCraX | Licence (package metadata) |
|---|---|---|---|
| numpy | 2.5.5 | arrays for all models | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| scipy | 1.18.1 | root finding (`brentq`), ODE integration (PFR), optimisation (differential evolution, SLSQP) | BSD (licence text in metadata: "BSD License") |
| pandas | 3.1.1 | CSV handling in studies and the validation matrix | BSD-3-Clause |
| matplotlib | 3.11.2 | all report / deck figures (`amcrax.plotstyle`) | Python Software Foundation License (matplotlib licence agreement) |
| cantera | 3.2.0 | GRI-Mech 3.0 NASA-7 data, transport properties, cross-check of equilibrium | BSD-3-Clause |
| CoolProp | 8.0.0 | reference equation of state of liquid / vaporising ammonia in the Python process model | MIT |
| PyYAML | 6.0.4 | `backend/amcrax/data/*.yaml` parameter files | MIT |
| pydantic | 2.14.4 | data contract `amcrax.schemas` | MIT |
| fastapi | 0.165.0 | HTTP API | MIT |
| starlette | 1.10.0 (pulled in by FastAPI; imported directly by the API) | ASGI toolkit | BSD-3-Clause |
| uvicorn[standard] | 0.54.0 | ASGI server | BSD-3-Clause |
| httpx | 0.28.1 | FastAPI `TestClient` (tests, `export_snapshot.py`) | BSD-3-Clause |
| openpyxl | 3.1.5 | `.xlsx` export of a case | MIT |
| pywin32 | 312 | `win32com` / `pythoncom`: Aspen Plus, Word and PowerPoint COM automation | PSF (package metadata) |
| pywinauto | 0.6.9 | UI Automation for genuine Aspen GUI screenshots (`aspen/automation/capture_screenshots.py`) | BSD 3-clause |
| pillow | 13.0.0 | image post-processing | MIT-CMU |
| pytest | 9.2.0 | test suite | MIT |
| python-docx | 1.2.0 | report post-processing (`build_report.py`) | MIT |
| python-pptx | 1.0.2 | deck builder (`build_deck.py`) | MIT |
| pymupdf | 2.1 | PDF text extraction (`scripts/extract_papers.py`) and report page checks (`build_report.py`) | **Dual licensed: GNU AGPL 3.0 or Artifex commercial licence** (package metadata). Used only as an offline documentation and research tool (`scripts/extract_papers.py`, `build_report.py`), never in the served application and not needed to run the platform. Check the licence terms before redistributing a build that bundles it |

The development environment also contains packages that project code does not use and that are left out of `requirements.txt` (for example pyomo, plotly, kaleido,
networkx, onnxruntime, pymupdf4llm, pypdf, ruamel.yaml, psutil, mss and tabulate; `comtypes` is a dependency of pywinauto). A fresh `scripts\setup.ps1` does not install them.

## 2. npm packages

### `frontend/package.json` (dashboard; installed versions from `node_modules`)

| Package | Installed | Purpose | Licence |
|---|---|---|---|
| react, react-dom | 19.3.1 | UI | MIT |
| react-router-dom | 7.18.6 | hash routing between dashboard sections | MIT |
| @xyflow/react | 13.0.2 | React Flow process flow diagram | MIT |
| recharts | 3.11.0 | charts | MIT |
| vite | 8.3.8 | dev server (proxy to the API) and build | MIT |
| @vitejs/plugin-react | 6.3.0 | JSX transform | MIT |
| typescript | 7.0.2 | strict type checking (`npm run build`) | Apache-2.0 |
| vitest | 5.1.1 | frontend unit tests (`npm test`) | MIT |
| oxlint | 1.94.0 | linter (`npm run lint`) | MIT |
| playwright-core | 1.65.1 | drives Microsoft Edge for `frontend/scripts/capture_dashboard.mjs` | Apache-2.0 |
| @types/node, @types/react, @types/react-dom | 24.19.2 / 19.3.0 / 19.3.0 | type declarations | MIT |

Transitive npm packages are pinned in `frontend/package-lock.json`; their licences were not individually audited here
(`npm ls --all` and the lock file list them).

### `docs/pitch_deck/package.json` (deck layout only)

| Package | Installed | Purpose | Licence |
|---|---|---|---|
| pptxgenjs | 3.12.0 | lays out the editable `.pptx` from `build/deck_data.json` (`deck_layout.js`) | MIT |

## 3. External tools

| Tool | Version | Used for | Required for | Licence |
|---|---|---|---|---|
| Aspen Plus | V15.0 (COM ProgID `Apwn.Document.41.0`; folder `C:\Program Files\AspenTech\...V15.0`) | rigorous flowsheet simulation, RGibbs equilibrium, sensitivity studies | **only** live simulation and regenerating the Aspen results; everything else uses stored results | commercial AspenTech licence (one seat; not part of this repository) |
| Python | 3.12.10 (per-user install) | runtime for backend, scripts, tests | everything | PSF licence (not re-checked from the installer here) |
| Node.js | 24.22.3 LTS (portable zip in `%LOCALAPPDATA%\AmCraX-tools\node`), npm 11.19.1 | frontend dev server and build, deck layout, dashboard screenshots | dashboard | MIT-style terms in the `LICENSE` file shipped with the distribution ("Node.js is licensed for use as follows" ... MIT text; bundled third-party notices follow in the same file) |
| Git (MinGit) | 2.56.1.windows.1 | version control | optional | GPL v2 (`LICENSE.txt` of the MinGit distribution) |
| pandoc | 3.14 | Markdown -> docx conversion of the technical report | rebuilding the report | the installed binary prints only "free software; see the source for copying conditions"; the pandoc project licence (GPL-2.0-or-later) was **not** verified from the installed files |
| Microsoft Word / PowerPoint | 16.0.20625 (Office 16) | COM export of the report PDF (table of contents update) and of the deck PDF / slide PNGs | rebuilding report / deck PDF only | commercial Microsoft licence |
| Microsoft Edge | 157.0.4341.60 | headless browser for `frontend/scripts/capture_dashboard.mjs` | refreshing dashboard screenshots only | proprietary Microsoft freeware |

## 4. Data and literature

Numerical parameters come from the peer-reviewed / reference sources cited per value in `backend/amcrax/data/*.yaml`,
`research/references.json` and `research/references.bib`. The research PDFs are copyrighted, are excluded from version control
(`.gitignore`: `*.pdf` except under `docs/`) and are not redistributed. NIST-JANAF values parsed into
`backend/amcrax/thermodynamics/reference/janaf.json` are used only as a cross-check of the thermochemical data (see
`docs/validation/discrepancy_analysis.md`).
