# AmCraX technical report - writing and build conventions (binding for all report writers)

## Pipeline

`docs/technical_report/sections/NN_slug.md` (pandoc Markdown, one file per top-level section)
-> `build_report.py` (concatenate, auto-generate appendices and reference list, pandoc -> .docx with
`reference.docx` styles, python-docx post-processing, Word COM -> .pdf)
-> `docs/technical_report/AmCraX_Technical_Report.docx` and `.pdf`.

Writers only write section files. Never edit another writer's section file.

## Required top-level structure (file name -> heading)

| File | Heading | Built from (first edition, kept in `sections_v1/`) |
|---|---|---|
| `01_executive_summary.md` | `# 1 Executive summary` | 01 |
| `02_motivation.md` | `# 2 Motivation and background` | 02 + 03 |
| `03_fundamentals.md` | `# 3 Ammonia-cracking fundamentals` | 04 (reaction, thermodynamic principles, mechanism; the equilibrium model itself moves to 13, kinetics to 14) |
| `04_literature_review.md` | `# 4 Literature review` | 05 |
| `05_process_design.md` | `# 5 Process design and process flow diagram` | 06 |
| `06_aspen_methodology.md` | `# 6 Aspen Plus V15 methodology` | 07 |
| `07_components.md` | `# 7 Component selection` | 08 |
| `08_property_method.md` | `# 8 Thermodynamic property method` | 09 |
| `09_reactor.md` | `# 9 Reactor configuration` | 10 (without 10.5) |
| `10_heat_exchangers.md` | `# 10 Heat exchanger modelling` | 11 |
| `11_separation.md` | `# 11 Separation and purification` | 12 |
| `12_automation.md` | `# 12 Python-Aspen automation` | 13 |
| `13_equilibrium.md` | `# 13 Equilibrium modelling` | new: 04 (derivation), 09.4, 14 (equilibrium comparison) |
| `14_kinetics.md` | `# 14 Catalyst kinetics` | new: 04 (rate laws), 10.5 |
| `15_balances.md` | `# 15 Mass and energy balances` | new: 06 (stream table, closures), appendix A/B, independent physics checks |
| `16_validation.md` | `# 16 Model validation` | 14 |
| `17_sensitivity.md` | `# 17 Sensitivity analysis` | 15 |
| `18_heat_integration.md` | `# 18 Heat integration` | 16 |
| `19_techno_economics.md` | `# 19 Techno-economic assessment` | 17 |
| `20_optimisation.md` | `# 20 Optimisation` | 18 |
| `21_environment.md` | `# 21 Environmental analysis` | 19 |
| `22_dashboard.md` | `# 22 Interactive dashboard` | new |
| `23_website.md` | `# 23 Public website` | new |
| `24_limitations.md` | `# 24 Limitations` | 20 |
| `25_conclusions.md` | `# 25 Conclusions` | 21 |
| (generated) | `# 26 References` | |
| (generated) | `# 27 Appendices` | |
## Markdown rules

* Headings: `# N Title`, `## N.M Title`, `### Title` (numbers typed by hand, matching the table above).
* Numbering is per section: Figure 7.1, Table 7.1, Eq. (7.1). Refer to them by number in the text.
* Figures - path relative to `docs/technical_report/`, caption = alt text, starts with the bold number:
  `![**Figure 7.2.** What is shown. Why the setting or result matters. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/05_reactor_setup.png){width=95%}`
  Only reference image files that exist, except the Aspen screenshots listed in
  `aspen/screenshots/manifest.json` (being captured now; use the planned names `01_flowsheet.png` ... `16_calculator.png`).
  The build drops any figure whose file is missing and reports it, so the surrounding text must still read correctly
  ("Figure 7.2 shows ..." only for files expected to exist).
* Every Aspen screenshot needs: figure number, concise caption, what is shown, why the setting/result matters.
* Tables: pandoc pipe tables preceded by `Table: **Table 7.1.** Caption. *Source: ...*`.
* Equations: display math `$$ ... \qquad (4.1) $$` (LaTeX; rendered as native Word equations). Define every symbol with units.
* Units: SI with °C (write the degree sign in prose; `degC` only inside code and HTML comments) and bar (absolute); kmol/h, kg/h, kW, kJ/mol; write `H~2~`, `NH~3~`, `N~2~` for subscripts in text.

## Scientific integrity

* Every number is traceable. Put an HTML comment after the paragraph naming the file it came from, e.g.
  `<!-- data: results/simulations/baseline.json kpis.nh3_conversion -->`. Copy numbers from the files; never estimate or recall them.
* Label the origin of every result in the prose or caption: **Aspen Plus V15 simulation**, **independent Python calculation**,
  **published literature** (with citation), **engineering assumption**, or **illustrative example**.
* Never present a literature value as an AmCraX result. Never claim validation that is not in `results/validation/`.
* State limitations where they apply (the PSA block is a reduced-order splitter, the reactor is an equilibrium model, costs are
  preliminary estimates, the carbon-intensity accounting is not a full LCA).
* If a needed result does not exist yet, do not invent it: write the section around what exists and list the gap in your report.

## Citations (APA 7th)

* In-text: (Author, Year), (Author & Author, Year), (Author et al., Year), using only entries of `research/references.json`
  (fall back to the per-paper `research/notes/*.json` "apa7" fields if that file is not there yet).
* First line of each section file, list the citation keys used: `<!-- cites: takahashi2016kinetic, cho2026nickel -->`.
  The build script creates the reference list (APA 7th, alphabetical, DOI/URL on the line immediately below each reference)
  from these keys - do not write a reference list yourself.

## Style

Direct, concise academic engineering prose, British spelling (optimisation, vaporiser). No filler openings, no marketing
language, no rhetorical questions. Explain the physical principle and the engineering decision, then the number.
For every Aspen Plus block: what it does, why it matters, how it was configured, what the result means.
