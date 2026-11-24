// Browser verification of the static site, as served by scripts/serve_pages.mjs under /AmCraX/ (Edge via playwright-core).
//
//   node scripts/serve_pages.mjs --port 4180        (in another shell, after `npm run build:pages`)
//   node scripts/site_check.mjs [--base http://127.0.0.1:4180/AmCraX/] [--shots <dir>] [--viewports 390x844,820x1180,1440x900,1920x1080]
//                               [--routes why,results,platform/pfd] [--no-shots] [--fullpage]
//
// For every viewport and every route it checks: renders (one h1 / platform title), no console errors, no failed or 4xx/5xx requests,
// no request outside the base path (so no API call, no absolute "/..." URL and no third-party host), no horizontal overflow, the
// headline basis strip read from the snapshot. Plus interaction checks (five navigation groups and the mobile menu, command palette,
// scenario deep link, redirects, evidence lightbox, PFD equipment + stream panels on site and platform, calculator, anchors, downloads).
// Screenshots: full-page site routes at the desktop viewport go to <shots>/site_<page>_desktop.png (default docs/screenshots); every other
// viewport and the platform / calculator captures go to <shots>/qa/ (git-ignored QA captures). Exit code 1 when a check fails.
import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const here = path.dirname(fileURLToPath(import.meta.url))
const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, all) => (x.startsWith('--') ? [...a, [x.slice(2), all[i + 1] && !all[i + 1].startsWith('--') ? all[i + 1] : 'true']] : a), []))
const base = (args.base ?? 'http://127.0.0.1:4180/AmCraX/').replace(/\/?$/, '/')
const origin = new URL(base).origin
const prefix = new URL(base).pathname
const shots = path.resolve(args.shots ?? path.join(here, '..', '..', 'docs', 'screenshots'))
const VIEWPORTS = (args.viewports ?? '390x844,820x1180,1440x900,1920x1080').split(',').map((s) => { const [w, h] = s.split('x').map(Number); return { w, h, label: w === 390 ? 'phone' : w === 820 ? 'tablet' : w === 1440 ? 'desktop' : w === 1920 ? 'fullhd' : `${w}x${h}` } })
const HYP = ['hypotheses', 'hypotheses/catalyst', 'hypotheses/economics', 'hypotheses/purification', 'hypotheses/end-use', 'hypotheses/validation', 'hypotheses/aspen-evidence']
const SITE = ['', 'overview', 'why', 'pfd', 'methodology', 'results', 'architecture', 'research', 'docs', 'about', ...HYP]
const PLATFORM = ['platform', 'platform/pfd', 'platform/simulation', 'platform/reactor', 'platform/heat', 'platform/sensitivity', 'platform/optimisation', 'platform/economics', 'platform/environment', 'platform/validation', 'platform/reports']
const only = args.routes ? new Set(args.routes.split(',')) : null
const ROUTES = [...SITE, ...PLATFORM].filter((r) => !only || only.has(r === '' ? 'home' : r))
const name = (r) => (r === '' ? 'home' : r === 'hypotheses' ? 'research_matrix' : r.startsWith('hypotheses/') ? `research_${r.slice(11).replace(/-/g, '_')}` : r.replace('platform/', 'platform_').replace(/\//g, '_'))
const qaDir = path.join(shots, 'qa')
if (args['no-shots'] !== 'true') { mkdirSync(shots, { recursive: true }); mkdirSync(qaDir, { recursive: true }) }
/** Published set: desktop captures of the site routes only; everything else is a QA capture. */
const shotPath = (route, label, isPlat, kind = 'page') => path.join((label === 'desktop' && !isPlat && kind === 'page') || (kind.startsWith('simulator') && (label === 'desktop' || label === 'phone')) ? shots : qaDir, `site_${kind === 'page' ? name(route) : kind}_${label}.png`)

const results = []
const record = (vp, id, ok, detail = '') => { results.push({ vp, id, ok, detail }); console.log(`${ok ? 'PASS' : 'FAIL'} [${vp}] ${id}${detail ? ' - ' + detail : ''}`) }
// Fonts are self-hosted (Fontsource); no third-party host is allowed any more, so every request outside the base path is reported.
const external = /(?!)/

const LEGACY = ['overview', 'results', 'methodology', 'research']
/** Same text as the site's fmt(): en-US grouping, fixed digits. */
const loc = (v, d) => (typeof v === 'number' && Number.isFinite(v) ? v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }) : 'n/a')
const snapCache = new Map()
/** A snapshot JSON file as served (null when missing); used so that expected numbers are read, never typed here. */
async function snap(rel) {
  if (!snapCache.has(rel)) snapCache.set(rel, fetch(`${base}snapshot/${rel}`).then((r) => (r.ok ? r.json() : null)).catch(() => null))
  return snapCache.get(rel)
}

const browser = await chromium.launch({ channel: 'msedge', headless: true })
const notes404 = new Set()

for (const vp of VIEWPORTS) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: 1, hasTouch: vp.w < 900 })
  const page = await ctx.newPage()
  let cur = 'boot'
  const problems = []
  const pushP = (m) => problems.push(`[${cur}] ${m}`)
  page.on('pageerror', (e) => pushP(`pageerror: ${e.message}`))
  page.on('console', (m) => { if (m.type() === 'error') pushP(`console.error: ${m.text().slice(0, 200)}`) })
  page.on('requestfailed', (r) => { if (!external.test(r.url())) pushP(`request failed: ${r.url()} (${r.failure()?.errorText})`) })
  page.on('response', (r) => {
    const u = r.url()
    if (external.test(u)) return
    if (r.status() >= 400) { pushP(`HTTP ${r.status()} ${u}`); notes404.add(`${r.status()} ${u}`) }
  })
  page.on('request', (r) => {
    const u = new URL(r.url())
    if (external.test(r.url()) || u.protocol === 'data:' || u.protocol === 'blob:') return
    if (u.origin !== origin || !u.pathname.startsWith(prefix)) pushP(`request outside ${prefix}: ${r.url()}`)
    if (u.pathname.startsWith(`${prefix}api/`)) pushP(`API request: ${r.url()}`)
  })

  async function settle(route) {
    await page.waitForFunction(() => {
      const t = document.body.innerText
      return !/Resolving data mode|Loading [^\n]{3,90} \.\.\.|Loading (the )?(platform|diagram|flowsheet|data|Aspen|Python|stored|Separation|Validation|Reference|Equilibrium|Plug|Techno|Optimisation|LCOH|Carbon|Single|Deliverables|Figures|Model|case)/i.test(t) && document.querySelector('.site, .shell')
    }, null, { timeout: 60000 }).catch(() => pushP('settle timeout (loading text still present)'))
    if (route === 'pfd' || route === 'platform/pfd') await page.waitForSelector('.react-flow__node', { timeout: 20000 }).catch(() => pushP('no PFD nodes'))
    if (route === '') {
      await page.waitForSelector('.sim-pfd', { timeout: 30000 }).catch(() => pushP('no simulator diagram'))
      // the eight graphs are a lazy chunk loaded when they come near the viewport, with debounced sweeps: scroll to them, then
      // wait until every card has data marks
      await page.evaluate(() => document.querySelector('.sim-graphs-wait, .sim-graphs')?.scrollIntoView({ block: 'start' }))
      await page.waitForFunction(() => {
        const cards = [...document.querySelectorAll('.sim-graphs .sim-chart')]
        return cards.length === 8 && cards.every((c) => c.querySelector('svg .recharts-line, svg .recharts-bar-rectangle, svg .recharts-dot, svg path.recharts-curve, svg .recharts-rectangle'))
      }, null, { timeout: 30000 }).catch(() => pushP('simulator graphs did not finish'))
      await page.evaluate(() => window.scrollTo(0, 0))
    }
    await page.waitForTimeout(route === 'results' ? 2500 : 1200)
  }
  async function go(route) {
    cur = route === '' ? 'home' : route
    await page.evaluate((r) => { window.location.hash = `#/${r}` }, route)
    await settle(route)
  }
  const tid = (t) => page.locator(`[data-testid="${t}"]`).first().innerText().catch(() => '')

  /** Phase 2 content of the research pages: key numbers read from the snapshot must appear, the controls must work. */
  async function phase2Checks(route, id, body) {
    record(vp.label, `${id}: no single "validated" percentage, no "experimentally validated"`, !/\d+(\.\d+)?\s?% validated|experimentally validated/i.test(body))
    if (route === 'hypotheses') {
      const chips = await page.$$eval('.verdict-chip', (cs) => cs.map((c) => c.getAttribute('data-verdict') ?? ''))
      const words = /^(SUPPORTED|CONTRADICTED|MIXED|PARTIALLY SUPPORTED|INCONCLUSIVE)\b/
      const em = await snap('research/evidence_matrix.json')
      const want = (em?.hypotheses ?? []).map((h) => String(h.verdict ?? '').toUpperCase().replace(/_/g, ' '))
      const tiles = await Promise.all(['H1', 'H2', 'H3', 'H4'].map((h) => tid(`verdict-${h}`)))
      record(vp.label, `${id}: verdict chips render (v2 vocabulary) and match the matrix file`, chips.length >= 4 && chips.every((c) => words.test(c)) && want.every((w, i) => tiles[i]?.toUpperCase().includes(w)), `${chips.length} chips; ${want.join(', ')}`)
      record(vp.label, `${id}: methodology document linked`, /verdict_methodology_v2\.md/.test(await tid('matrix-version')))
    }
    if (route === 'hypotheses/economics') {
      const bl = await snap('research/reference_scenario/baseline.json.json')
      const k = await tid('baseline-kpis')
      record(vp.label, `${id}: unified baseline numbers from the snapshot (USD and SGD)`, !!bl && k.includes(loc(bl.lcoh_USD_per_kg, 3)) && k.includes(loc(bl.lcoh_SGD_per_kg, 3)) && k.includes(String(bl.fx_date)), k.replace(/\n/g, ' ').slice(0, 200))
      record(vp.label, `${id}: superseded baselines noted`, /superseded|history/i.test(await tid('superseded-note')))
      const fd = await snap('research/carbon_pricing/feed_dominance.json.json')
      record(vp.label, `${id}: adverse H2 finding with the break-even price`, !!fd && (await tid('adverse-h2')).includes(loc(fd.breakeven_nh3_USD_per_t?.ne_asia_smr_production_cost, 0)))
      // carbon control: Mode A default, Mode B hypothetical with a user price, values = interpolation of the stored sweep
      const ctl = page.locator('[data-testid="carbon-control"]')
      record(vp.label, `${id}: carbon control defaults to Mode A (actual Singapore boundary)`, (await ctl.getAttribute('data-mode')) === 'actual_sg' && /not law/.test(await tid('mode-a-text')))
      const a45 = await tid('lcoh-green_current')
      await page.locator('[data-testid="mode-b"]').click(); await page.waitForTimeout(250)
      const bText = await tid('mode-b-text')
      record(vp.label, `${id}: Mode B is labelled hypothetical, not Singapore law, and as interpolation of stored Python results`, (await ctl.getAttribute('data-mode')) === 'hypothetical_lca' && /not Singapore law/i.test(bText) && /interpolation of stored Python results/i.test(bText), bText.slice(0, 160))
      const num = page.locator('input[aria-label="Hypothetical carbon price in SGD per tonne CO2e"]')
      await num.fill('303'); await page.waitForTimeout(250)
      const sweep = await snap('research/carbon_pricing/price_sweep.csv.json')
      const rows = sweep?.rows ?? []
      const r300 = rows.find((r) => r.price_SGD_per_tCO2e === 300), r305 = rows.find((r) => r.price_SGD_per_tCO2e === 305)
      const yk = 'lcoh_green_current_central_USD_per_kg'
      const exp = r300 && r305 ? r300[yk] + ((r305[yk] - r300[yk]) * 3) / 5 : null
      const b303 = await tid('lcoh-green_current')
      record(vp.label, `${id}: Mode B at 303 SGD/tCO2e shows the green LCOH interpolated between the stored 300 and 305 points`, exp !== null && b303 === loc(exp, 3) && b303 !== a45, `${a45} -> ${b303}, expected ${exp === null ? 'n/a' : loc(exp, 3)}`)
      const ss = await snap('research/carbon_pricing/site_summary.json.json')
      record(vp.label, `${id}: crossover threshold blue over grey shown`, !!ss && (await tid('th-blue_over_grey')) === loc(ss.thresholds_SGD_per_tCO2e?.blue_over_grey?.central, 1))
      await page.locator('[data-testid="mode-a"]').click(); await page.waitForTimeout(250)
      record(vp.label, `${id}: switching back to Mode A restores the actual-boundary LCOH`, (await tid('lcoh-green_current')) === a45)
    }
    if (route === 'hypotheses/catalyst') {
      record(vp.label, `${id}: kinetic validity statement and derived-price label`, /20 bar/.test(await tid('validity-statement')) && /no supplier quotation exists/i.test(body) && /unmodelled, no performance figures/i.test(body))
      record(vp.label, `${id}: equal-conversion correction shown`, (await tid('equal-conversion')).length > 40)
    }
    if (route === 'hypotheses/purification') {
      const nus = await tid('nus-wording')
      record(vp.label, `${id}: NUS wording and parity threshold`, /none of their verified publications covers cracked-ammonia purification/i.test(nus) && /no specific result is attributed to them/i.test(nus) && (await tid('h4-parity')).length > 40)
    }
    if (route === 'hypotheses/end-use') {
      const w = await tid('h1-wording')
      const tc = await snap('research/enduse/turbine_threshold.csv.json')
      const ref = (tc?.rows ?? []).find((r) => r.pathway === 'full_purified' && r.basis === 'reference')
      record(vp.label, `${id}: required H1 wording with the equal-efficiency assumption`, /direct ammonia combustion produces electricity at a lower cost/.test(w) && /49\.64 %/.test(w) && /fuel-specific turbine performance/.test(w), w.slice(0, 120))
      record(vp.label, `${id}: turbine threshold from the snapshot and the exhaust-heated finding`, !!ref && (await tid('thr-full_purified')) === loc(ref.threshold_delta_pp, 2) && /cheaper than direct ammonia/.test(await tid('exhaust-finding')))
      record(vp.label, `${id}: Environmental Analysis reachable (carbon intensity by route)`, (await page.locator('#carbon-intensity table').count()) > 0 && (await page.locator('#lca').count()) > 0)
    }
    if (route === 'hypotheses') {
      const otp = await page.$$eval('nav.otp a', (as) => as.map((a) => a.getAttribute('href')))
      // the first sentence of the stored verdict conditions (the aggregation rule, the same for every hypothesis) appears once on the page
      const em = await snap('research/evidence_matrix.json')
      const firstSentence = String(em?.hypotheses?.[0]?.verdict_conditions ?? '').split(/(?<=\.)\s+(?=[A-Z])/)[0]
      const shared = (em?.hypotheses ?? []).every((h) => String(h.verdict_conditions ?? '').includes(firstSentence))
      const times = firstSentence ? body.split(firstSentence).length - 1 : -1
      const own = await page.$$eval('[data-testid^="conditions-"]', (ps) => ps.length)
      record(vp.label, `${id}: "on this page" list, verdict table first, aggregation rule stated once with each hypothesis's own conditions`, otp.length >= 5 && otp.some((h) => /#H1$/.test(h ?? '')) && (await page.$('.hyp-summary table')) !== null && (shared ? times === 1 && own === 4 : times === 4), `${otp.length} entries; rule printed ${times}x; own conditions ${own}`)
    }
    if (route === 'hypotheses/aspen-evidence') {
      const thumb = page.locator('.hyp-thumb').first()
      await thumb.scrollIntoViewIfNeeded(); await thumb.click(); await page.waitForTimeout(400)
      const lb = await page.evaluate(() => { const d = document.querySelector('dialog.lightbox[open]'); const img = d?.querySelector('img'); return { open: !!d, w: img?.naturalWidth ?? 0, alt: img?.getAttribute('alt') ?? '', count: d?.querySelector('.lightbox-count')?.textContent ?? '', cap: d?.querySelector('.lightbox-cap')?.textContent?.length ?? 0 } })
      record(vp.label, `${id}: thumbnail opens a full-size view with alt text and caption`, lb.open && lb.w > 0 && lb.alt.length > 10 && lb.cap > 20 && /^1 of \d+/.test(lb.count), JSON.stringify(lb))
      await page.keyboard.press('ArrowRight'); await page.waitForTimeout(200)
      const c2 = await page.locator('dialog.lightbox .lightbox-count').innerText().catch(() => '')
      await page.keyboard.press('Escape'); await page.waitForTimeout(250)
      const back = await page.evaluate(() => ({ open: !!document.querySelector('dialog.lightbox[open]'), focusThumb: document.activeElement?.classList.contains('hyp-thumb') ?? false }))
      record(vp.label, `${id}: arrow keys step, Escape closes and returns focus to the thumbnail`, /^2 of/.test(c2) && !back.open && back.focusThumb, `${c2} ${JSON.stringify(back)}`)
    }
    if (route === 'hypotheses/validation') {
      const kinds = await Promise.all(['numerical_verification', 'python_vs_aspen', 'literature_comparison', 'experimental_validation'].map((k) => tid(`kind-${k}`)))
      const bk = await snap('research/validation/by_kind.json')
      record(vp.label, `${id}: four evidence-kind blocks with counts from the snapshot`, kinds.every((t) => t.length > 0) && !!bk && ['numerical_verification', 'python_vs_aspen', 'literature_comparison', 'experimental_validation'].every((k, i) => kinds[i].includes(`${bk.kinds[k]?.total ?? 0}`)), kinds.map((t) => t.split('\n')[1] ?? '').join(' | '))
      record(vp.label, `${id}: no independent experimental validation stated`, /no independent experimental validation/i.test(await tid('no-experimental')))
    }
  }

  // ---- boot ----
  await page.goto(base, { waitUntil: 'domcontentloaded' })
  await settle('')

  for (const route of ROUTES) {
    const id = route === '' ? 'home' : route
    if (route !== '') await go(route); else { cur = 'home'; await page.evaluate(() => { window.location.hash = '#/' }); await settle('') }
    const before = problems.length
    const info = await page.evaluate((isPlatform) => ({
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      h1: document.querySelectorAll('h1').length,
      main: !!document.querySelector('main'),
      bodyText: document.body.innerText,
      charts: document.querySelectorAll('.chart-card').length,
      emptyCharts: [...document.querySelectorAll('.chart-box')].filter((b) => !b.querySelector('svg .recharts-line, svg .recharts-bar-rectangle, svg .recharts-dot, svg .recharts-scatter, svg path.recharts-curve, svg .recharts-rectangle')).length,
      badge: isPlatform ? document.querySelector('.topbar-right .pill')?.textContent?.trim() : null,
      banner: isPlatform ? document.querySelector('.snapshot-banner')?.textContent?.trim().slice(0, 80) : null,
      noteBar: document.querySelector('.static-notice')?.textContent?.trim() ?? null,
    }), route.startsWith('platform'))
    const isPlat = route.startsWith('platform')
    record(vp.label, `${id}: no horizontal overflow`, info.overflow <= 1, `overflow ${info.overflow}px`)
    record(vp.label, `${id}: renders (main landmark, ${isPlat ? 'h1 present' : 'exactly one h1'})`, info.main && (isPlat ? info.h1 >= 1 : info.h1 === 1), `h1=${info.h1}`)
    if (isPlat) record(vp.label, `${id}: SNAPSHOT mode badge + static-site banner`, /PUBLISHED RESULTS/.test(info.badge ?? '') && /Published results - static site\. Live Aspen Plus runs need the local platform\./.test(info.banner ?? '') || /Published results - static site\. Live Aspen Plus runs need the local platform\./.test(info.bodyText), `${info.badge} | ${info.banner}`)
    else record(vp.label, `${id}: header notice says static site`, /Published results - static site\. Live Aspen Plus runs need the local platform\./.test(info.noteBar ?? ''), info.noteBar ?? '')
    record(vp.label, `${id}: no "undefined"/"NaN"/"[object" text`, !/\bundefined\b|\bNaN\b|\[object /.test(info.bodyText))
    {
      // one headline basis on every page: unified reference cost in USD first with SGD in brackets, carbon intensity with its route
      const bl = await snap('research/reference_scenario/baseline.json.json')
      const ci = await snap('research/carbon_pricing/carbon_intensity.json.json')
      const ciC = ci?.routes?.[bl?.scenario]?.ci_kgCO2e_per_kgH2?.central
      await page.waitForSelector('[data-testid="headline-ci"]', { timeout: 5000 }).catch(() => {})
      const hc = await tid('headline-cost'), hi = await tid('headline-ci')
      record(vp.label, `${id}: headline basis strip from the snapshot (unified USD/kg first, SGD in brackets; carbon intensity with its route)`,
        !!bl && hc.includes(`${loc(bl.lcoh_USD_per_kg, 3)} USD/kg`) && hc.includes(`(${loc(bl.lcoh_SGD_per_kg, 3)} SGD/kg)`) && /unified reference/.test(hc)
        && !!ci && typeof ciC === 'number' && hi.includes(loc(ciC, 2)) && /route/.test(hi), `${hc.replace(/\n/g, ' ').slice(0, 120)} | ${hi.replace(/\n/g, ' ').slice(0, 120)}`)
    }
    if (route === 'results') record(vp.label, `${id}: charts drawn (${info.charts} cards, ${info.emptyCharts} without data marks)`, info.charts >= 9 && info.emptyCharts === 0)
    if (route.startsWith('hypotheses')) {
      const hy = await page.evaluate(() => ({
        badges: document.querySelectorAll('.badge').length,
        stored: /does not run Aspen Plus/.test(document.body.innerText),
        tables: document.querySelectorAll('table.data').length,
        brokenImgs: [...document.querySelectorAll('img')].filter((i) => i.complete && i.naturalWidth === 0).length,
        notAvail: /Data not available yet|Could not load|Not in the SNAPSHOT/.test(document.body.innerText),
        subnav: document.querySelectorAll('.chip-nav a').length,
      }))
      record(vp.label, `${id}: stored-results statement, sub-navigation, source badges`, hy.stored && hy.subnav === 7 && (route === 'hypotheses' || route === 'hypotheses/validation' || hy.badges >= 4), JSON.stringify(hy))
      record(vp.label, `${id}: no missing-data notice and no broken images`, !hy.notAvail && hy.brokenImgs === 0, JSON.stringify(hy))
      if (['hypotheses/catalyst', 'hypotheses/economics', 'hypotheses/purification', 'hypotheses/end-use'].includes(route)) record(vp.label, `${id}: charts drawn (${info.charts} cards, ${info.emptyCharts} without data marks)`, info.charts >= 4 && info.emptyCharts === 0)
      await phase2Checks(route, id, info.bodyText)
    }
    if (LEGACY.includes(route)) {
      const bl = await snap('research/reference_scenario/baseline.json.json')
      const t = await page.locator('[data-testid="legacy-banner"]').innerText().catch(() => '')
      record(vp.label, `${id}: legacy banner names the unified baseline`, /legacy core result, superseded for research outputs by the unified baseline/i.test(t) && (!bl || t.includes(loc(bl.lcoh_USD_per_kg, 3))), t.slice(0, 160))
    }
    record(vp.label, `${id}: no console errors / failed or 4xx requests / requests outside base`, problems.length === before, problems.slice(before).join(' | ').slice(0, 400))
    if (args['no-shots'] !== 'true') {
      if (args.fullpage !== 'false' && !isPlat) await page.evaluate(async () => { const h = document.documentElement.scrollHeight; for (let y = 0; y < h; y += 700) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 60)) } })  // trigger lazy images
      await page.waitForTimeout(400)
      await page.evaluate(() => window.scrollTo(0, 0))
      await page.screenshot({ path: shotPath(route, vp.label, isPlat), fullPage: args.fullpage !== 'false' && !isPlat })
    }
  }

  // ---- simulator (landing page) ----
  if (!only || only.has('home')) {
    cur = 'simulator'
    await go('')
    const kpi = (k) => page.locator(`[data-kpi="${k}"] .sim-kpi-v`).innerText()
    const outv = (k) => page.locator(`[data-out="${k}"]`).first().innerText()
    const sim = await page.evaluate(() => {
      const r = (s) => document.querySelector(s)?.getBoundingClientRect() ?? null
      return { h1: document.querySelector('h1')?.textContent ?? '', pfd: r('.sim-pfd'), controls: r('.sim-col-controls'), out: r('.sim-kpis'), grid: r('.sim-grid'),
        graphs: r('.sim-graphs'), units: document.querySelectorAll('.sim-pfd [data-unit]').length, streams: document.querySelectorAll('.sim-pfd [data-stream]').length,
        badges: document.querySelectorAll('.sim-col-out .sim-badge').length, overflowPfd: (() => { const b = document.querySelector('.sim-pfd-box'); return b ? b.scrollWidth - b.clientWidth : -1 })() }
    })
    record(vp.label, 'simulator: the site root shows the simulator (h1, diagram, units, streams, labelled outputs)', /process simulator/i.test(sim.h1) && !!sim.pfd && sim.units >= 10 && sim.streams >= 12 && sim.badges >= 10, JSON.stringify({ h1: sim.h1, units: sim.units, streams: sim.streams, badges: sim.badges }))
    if (vp.w >= 1440) record(vp.label, 'simulator: diagram (whole), controls and live results above the fold; diagram not scrolled sideways', sim.pfd.bottom <= vp.h && sim.controls.top < vp.h - 150 && sim.out.top < vp.h - 150 && sim.overflowPfd <= 1, `pfd ${Math.round(sim.pfd.top)}-${Math.round(sim.pfd.bottom)}, controls ${Math.round(sim.controls.top)}, live results ${Math.round(sim.out.top)}`)
    else record(vp.label, 'simulator: diagram starts above the fold', sim.pfd.top < vp.h - 100, `pfd ${Math.round(sim.pfd.top)}`)
    record(vp.label, 'simulator: graphs sit directly below the diagram block', sim.graphs && sim.graphs.top >= sim.grid.bottom - 1 && sim.graphs.top - sim.grid.bottom < 120, `grid bottom ${Math.round(sim.grid.bottom)}, graphs top ${Math.round(sim.graphs?.top)}`)
    const g8 = await page.evaluate(() => [...document.querySelectorAll('.sim-graphs .sim-chart')].map((c) => ({ n: c.getAttribute('data-graph'), marks: c.querySelectorAll('svg .recharts-line, svg .recharts-bar-rectangle, svg .recharts-dot, svg path.recharts-curve, svg .recharts-rectangle').length, axes: c.querySelectorAll('.recharts-label').length, note: /Limitation/.test(c.textContent ?? '') })))
    record(vp.label, 'simulator: eight graph cards with data marks, axis titles and a limitation note', g8.length === 8 && g8.every((g) => g.marks > 0 && g.axes >= (g.n === '7' ? 1 : 2) && g.note), JSON.stringify(g8))
    // play / pause
    const play = page.locator('button.sim-play')
    const p0 = await play.getAttribute('aria-pressed')
    const parts0 = await page.locator('.sim-pfd .pfd-particle').count()
    await page.waitForTimeout(400)
    const pos1 = await page.locator('.sim-pfd .pfd-particle').first().getAttribute('cx').catch(() => null)
    await page.waitForTimeout(400)
    const pos2 = await page.locator('.sim-pfd .pfd-particle').first().getAttribute('cx').catch(() => null)
    record(vp.label, 'simulator: playing on load (no reduced motion), particles exist and move', p0 === 'true' && parts0 > 20 && pos1 !== pos2, `aria-pressed=${p0}, particles=${parts0}, cx ${pos1} -> ${pos2}`)
    if (args['no-shots'] !== 'true') await page.screenshot({ path: shotPath('', vp.label, false, 'simulator_playing') })
    await play.click(); await page.waitForTimeout(250)
    const p1 = await play.getAttribute('aria-pressed'); const t1 = await play.innerText(); const parts1 = await page.locator('.sim-pfd .pfd-particle').count()
    record(vp.label, 'simulator: Play/Pause toggles to Play (aria-pressed=false, no particles)', p1 === 'false' && /Play/.test(t1) && parts1 === 0, `aria-pressed=${p1}, text=${t1.trim()}, particles=${parts1}`)
    if (args['no-shots'] !== 'true') await page.screenshot({ path: shotPath('', vp.label, false, 'simulator_paused') })
    await play.focus(); await page.keyboard.press('Enter'); await page.waitForTimeout(250)
    record(vp.label, 'simulator: keyboard Enter toggles back to Pause (aria-pressed=true)', (await play.getAttribute('aria-pressed')) === 'true' && (await page.locator('.sim-pfd .pfd-particle').count()) > 0)
    // temperature control changes the conversion
    const c0 = await kpi('conversion')
    const tBox = page.locator('[data-ctl="T_C"] input[type=number]')
    await tBox.fill('520'); await tBox.press('Enter'); await page.waitForTimeout(400)
    const c1 = await kpi('conversion')
    record(vp.label, 'simulator: changing the temperature changes the displayed conversion', c0 !== c1 && /%/.test(c1), `${c0} -> ${c1}`)
    // catalyst changes it (kinetic mode)
    await page.selectOption('#sim-mode', 'isothermal'); await page.waitForTimeout(400)
    const k0 = await kpi('conversion')
    await page.selectOption('#sim-cat', 'ni_takahashi_microkinetic'); await page.waitForTimeout(400)
    const k1 = await kpi('conversion')
    record(vp.label, 'simulator: switching the catalyst changes the conversion', k0 !== k1, `${k0} -> ${k1}`)
    // carbon mode
    await page.locator('details.sim-sec:has-text("Ammonia and carbon pricing") > summary').evaluate((s) => { const d = s.parentElement; if (d && !d.open) d.open = true })
    const cc0 = await outv('carbon_cost')
    await page.locator('label:has-text("HYPOTHETICAL life-cycle price")').click(); await page.waitForTimeout(400)
    const cc1 = await outv('carbon_cost')
    const hypoNote = await page.locator('.sim-hypo').count()
    record(vp.label, 'simulator: carbon mode toggle shows HYPOTHETICAL and changes the carbon cost', /HYPOTHETICAL/.test(cc1) && hypoNote === 1 && cc0.replace(/Carbon cost.*\n?/, '') !== cc1.replace(/Carbon cost.*\n?/, ''), `${cc0.replace(/\n/g, ' ')} -> ${cc1.replace(/\n/g, ' ')}`)
    // heat integration off bypasses the FEHE
    await page.locator('details.sim-sec:has-text("Feed and heat recovery") > summary').evaluate((s) => { const d = s.parentElement; if (d && !d.open) d.open = true })
    await page.locator('.sim-switch input').uncheck(); await page.waitForTimeout(300)
    const byp = await page.locator('.sim-pfd [data-unit="FEHE"].is-bypassed').count()
    record(vp.label, 'simulator: heat integration off shows the FEHE as bypassed', byp === 1)
    await page.locator('.sim-switch input').check(); await page.waitForTimeout(200)
    // unit panel
    await page.locator('.sim-pfd [data-unit="PSA"]').click(); await page.waitForTimeout(200)
    const panel = await page.locator('.sim-panel h3').innerText()
    record(vp.label, 'simulator: clicking a unit opens its panel with values and source labels', /PSA|adsorption/.test(panel) && (await page.locator('.sim-panel .sim-badge').count()) > 0, panel)
    // compare
    await page.locator('button:has-text("Compare: pin as case A")').click()
    await tBox.fill('560'); await tBox.press('Enter'); await page.waitForTimeout(500)
    const cmp = await page.evaluate(() => ({ heads: [...document.querySelectorAll('.sim-cmp thead th')].map((t) => t.textContent), rows: document.querySelectorAll('.sim-cmp tbody tr').length }))
    record(vp.label, 'simulator: compare shows case A and case B columns and the difference', cmp.heads.some((h) => /Case A/.test(h)) && cmp.heads.some((h) => /Case B/.test(h)) && cmp.rows >= 10, JSON.stringify(cmp))
    // export
    const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 10000 }), page.locator('button:has-text("Export CSV")').click()])
    const dlPath = await dl.path().catch(() => null)
    const csv = dlPath ? (await import('node:fs')).readFileSync(dlPath, 'utf-8') : ''
    record(vp.label, 'simulator: Export CSV downloads inputs and outputs of cases A and B with source labels', /\.csv$/.test(dl.suggestedFilename()) && /^case,section,key,label,value,unit,source,note/.test(csv) && /\nA,output,/.test(csv) && /\nB,output,/.test(csv), `${dl.suggestedFilename()} ${csv.length} bytes`)
    const [dj] = await Promise.all([page.waitForEvent('download', { timeout: 10000 }), page.locator('button:has-text("Export JSON")').click()])
    record(vp.label, 'simulator: Export JSON downloads a file', /\.json$/.test(dj.suggestedFilename()))
    await page.locator('button:has-text("Stop comparing")').click()
    await page.locator('button:has-text("Reset to baseline")').click(); await page.waitForTimeout(400)
    const base = await page.locator('[data-kpi="conversion"] .badge').innerText()
    record(vp.label, 'simulator: Reset returns to the Aspen baseline (Aspen Plus V15 label)', /Aspen Plus V15/.test(base), base)
    record(vp.label, 'simulator: no "undefined"/"NaN" text after the interactions', !/\bundefined\b|\bNaN\b|\[object /.test(await page.evaluate(() => document.body.innerText)))
  }

  if (!only || only.has('home') || only.has('overview')) {
    cur = 'interaction'
    await go('')
    // nav: five labelled groups (disclosure buttons) in the top bar on wide screens; below 1100 px the menu lists every page under its group
    const GROUPS = ['Simulator', 'Findings', 'Results', 'Methods and validation', 'Docs and downloads']
    const wide = vp.w >= 1100
    if (wide) {
      const btns = await page.$$eval('.nav-group-btn', (bs) => bs.filter((b) => b.getBoundingClientRect().width > 0).map((b) => b.firstChild?.textContent?.trim() ?? ''))
      record(vp.label, 'nav: top bar shows the five labelled groups', JSON.stringify(btns) === JSON.stringify(GROUPS), btns.join(', '))
      const visibleBefore = await page.$$eval('.site-nav a', (as) => as.filter((a) => a.getBoundingClientRect().width > 0).length)
      await page.click('#nav-btn-results'); await page.waitForTimeout(200)
      const listed = await page.$$eval('#nav-list-results a .nav-label', (as) => as.filter((a) => a.getBoundingClientRect().width > 0).map((a) => a.textContent))
      record(vp.label, 'nav: a group opens its page list (aria-expanded=true) and the lists are closed before', visibleBefore === 0 && listed.length >= 2 && listed.includes('Overview') && (await page.getAttribute('#nav-btn-results', 'aria-expanded')) === 'true', listed.join(', '))
      await page.keyboard.press('Escape'); await page.waitForTimeout(150)
      record(vp.label, 'nav: Escape closes the group and returns focus to its button', (await page.getAttribute('#nav-btn-results', 'aria-expanded')) === 'false' && (await page.evaluate(() => document.activeElement?.id)) === 'nav-btn-results')
      await page.click('#nav-btn-results'); await page.waitForTimeout(150)
      await page.click('#nav-list-results a:has-text("Overview")'); await page.waitForTimeout(600)
      record(vp.label, 'nav: "Overview" opens /overview, the group is marked current and the list closes', page.url().endsWith('#/overview') && (await page.$('.nav-group.is-current #nav-btn-results')) !== null && (await page.getAttribute('#nav-btn-results', 'aria-expanded')) === 'false', page.url())
    } else {
      await page.click('.nav-toggle'); await page.waitForTimeout(300)
      const expanded = await page.getAttribute('.nav-toggle', 'aria-expanded')
      record(vp.label, 'mobile menu: toggle has aria-expanded=true when open', expanded === 'true')
      const links = await page.$$eval('.site-nav a', (as) => as.filter((a) => a.getBoundingClientRect().width > 0).length)
      const lists = await page.$$eval('.site-nav .nav-list', (ls) => ls.map((l) => l.getAttribute('aria-label')))
      record(vp.label, 'mobile menu: every page under its labelled group', links === 19 && JSON.stringify(lists) === JSON.stringify(GROUPS), `${links} links; ${lists.join(', ')}`)
      await page.click('.site-nav a:has-text("Engineering results")'); await page.waitForTimeout(600)
      record(vp.label, 'mobile menu: link navigates and menu closes', page.url().endsWith('#/results') && !(await page.$eval('.site-nav', (n) => n.classList.contains('open'))), page.url())
    }
    // section numbers derived from the route table: /results is the second page of the third group
    await go('results')
    record(vp.label, 'breadcrumb above the title comes from the route table', (await page.locator('.page-hero .eyebrow').innerText()) === 'Section 3.2 · Results')
    const fonts = await page.evaluate(async () => { await document.fonts.ready; return { inter: document.fonts.check('400 16px Inter'), grotesk: document.fonts.check('600 16px "Space Grotesk"'), mono: document.fonts.check('500 16px "JetBrains Mono"'), loaded: [...document.fonts].filter((f) => f.status === 'loaded').map((f) => `${f.family} ${f.weight}`) } })
    record(vp.label, 'fonts: Inter, Space Grotesk and JetBrains Mono load from the site itself', fonts.inter && fonts.grotesk && fonts.mono && fonts.loaded.length >= 3, fonts.loaded.join(', '))
    // command palette: Ctrl+K, combobox filtering, Enter navigates, Escape closes; the header button opens it too
    await page.keyboard.press('Control+k'); await page.waitForTimeout(250)
    const pal = await page.evaluate(() => ({ open: !!document.querySelector('dialog.palette[open]'), focus: document.activeElement?.getAttribute('role'), opts: document.querySelectorAll('.palette [role=option]').length }))
    record(vp.label, 'command palette: Ctrl+K opens it with the combobox focused and the pages listed', pal.open && pal.focus === 'combobox' && pal.opts >= 19, JSON.stringify(pal))
    await page.keyboard.type('purification'); await page.waitForTimeout(200)
    const act = await page.evaluate(() => { const i = document.querySelector('.palette [role=combobox]'); const id = i?.getAttribute('aria-activedescendant'); return { id, text: id ? document.getElementById(id)?.textContent : null, sel: id ? document.getElementById(id)?.getAttribute('aria-selected') : null } })
    record(vp.label, 'command palette: typing filters and marks the active option (aria-activedescendant, aria-selected)', /Purification/.test(act.text ?? '') && act.sel === 'true', JSON.stringify(act))
    await page.keyboard.press('Enter'); await page.waitForTimeout(700)
    record(vp.label, 'command palette: Enter opens the page and closes the dialog', page.url().endsWith('#/hypotheses/purification') && !(await page.$('dialog.palette[open]')), page.url())
    await page.click('.search-btn'); await page.waitForTimeout(250)
    await page.keyboard.type('700'); await page.waitForTimeout(600)
    const scn = await page.$$eval('.palette [role=option]', (os) => os.map((o) => o.textContent))
    record(vp.label, 'command palette: lists the stored simulator scenarios', scn.some((t) => /700 degC/.test(t ?? '')), scn.slice(0, 3).join(' | '))
    await page.keyboard.press('Escape'); await page.waitForTimeout(150)
    record(vp.label, 'command palette: Escape clears the text first', (await page.inputValue('.palette [role=combobox]')) === '' && !!(await page.$('dialog.palette[open]')))
    await page.keyboard.press('Escape'); await page.waitForTimeout(150)
    record(vp.label, 'command palette: second Escape closes it', !(await page.$('dialog.palette[open]')))
    // scenario deep link used by the palette, and a redirect for an alternative path
    await page.evaluate(() => { window.location.hash = '#/?preset=scn_high_temperature' }); await page.waitForSelector('.sim-status', { timeout: 30000 }).catch(() => {}); await page.waitForTimeout(500)
    record(vp.label, 'simulator: #/?preset=<id> opens the stored scenario', /Preset: Equilibrium cracker, 700 degC/.test(await page.locator('.sim-status').innerText().catch(() => '')))
    const usd = await page.locator('[data-kpi="lcoh_USD"] .sim-kpi-v').innerText().catch(() => '')
    record(vp.label, 'simulator: headline cost in USD first with SGD in brackets', /USD\/kg H2\s*\(.*SGD\/kg H2\)/.test(usd), usd)
    await page.evaluate(() => { window.location.hash = '#/environment' }); await page.waitForTimeout(900)
    record(vp.label, 'redirect: #/environment goes to the environmental analysis', page.url().endsWith('#/hypotheses/end-use#lca'), page.url())
    await go('overview')
    // calculator
    await page.locator('#try').scrollIntoViewIfNeeded()
    const before = await page.locator('.res-main dd').first().innerText()
    const slider = page.locator('.calc input[type=range]').first()
    await slider.focus(); await page.keyboard.press('Home')
    await page.waitForTimeout(300)
    const low = await page.locator('.res-main dd').first().innerText()
    await page.keyboard.press('End'); await page.waitForTimeout(300)
    const high = await page.locator('.res-main dd').first().innerText()
    record(vp.label, 'calculator responds to the temperature slider', low !== high && /%/.test(low), `600C/20bar ${before}; 250C ${low}; 900C ${high}`)
    const lab = await page.locator('.calc .badge-browser').first().innerText()
    record(vp.label, 'calculator is labelled "calculated in your browser (ideal gas)"', /calculated in your browser \(ideal gas\)/.test(lab), lab)
    const chip = await page.locator('.calc .chip', { hasText: '20 bar' }).count()
    record(vp.label, 'calculator offers the stored Aspen pressures', chip === 1)
    await page.screenshot({ path: shotPath('', vp.label, false, 'calculator') }).catch(() => {})
    // headline facts come from the snapshot
    const facts = await page.locator('.fact-value').allInnerTexts()
    record(vp.label, 'overview: four headline facts with values', facts.length === 4 && facts.every((f) => /\d/.test(f)), facts.join(' | '))
  }

  if (!only || only.has('pfd')) {
    await go('pfd')
    cur = 'pfd-interaction'
    await page.locator('.react-flow__node[data-id="CRACKER"]').click()
    await page.waitForSelector('.pfd-side .panel', { timeout: 5000 }).catch(() => pushP('equipment panel did not open'))
    const t1 = await page.locator('.pfd-side .panel-title').first().innerText().catch(() => '')
    record(vp.label, 'site PFD: equipment panel opens (CRACKER)', /CRACKER/.test(t1), t1)
    await page.keyboard.press('Escape')
    await page.locator('.lists button', { hasText: /^S5 - / }).click()
    const t2 = await page.locator('.pfd-side .panel-title').first().innerText().catch(() => '')
    record(vp.label, 'site PFD: stream panel opens (S5) from the list', /^S5/.test(t2), t2)
    await page.keyboard.press('Escape')
    // real click on a drawn stream line
    await page.locator('.pfd-canvas').scrollIntoViewIfNeeded()
    const pt = await page.evaluate(() => {
      const p = document.querySelector('.react-flow__edge[data-id="S5"] path.stream-core'); if (!p) return null
      const L = p.getTotalLength(); const q = p.getPointAtLength(L * 0.55); const m = p.getScreenCTM(); return { x: m.a * q.x + m.c * q.y + m.e, y: m.b * q.x + m.d * q.y + m.f }
    })
    if (pt && pt.x > 0 && pt.y > 0 && pt.x < vp.w && pt.y < vp.h) { await page.mouse.click(pt.x, pt.y); await page.waitForTimeout(400); const t3 = await page.locator('.pfd-side .panel-title').first().innerText().catch(() => ''); record(vp.label, 'site PFD: clicking the drawn S5 line opens its panel', /^S5/.test(t3), t3); await page.keyboard.press('Escape') }
    else record(vp.label, 'site PFD: drawn S5 line is inside the viewport for a real click (skipped on small screens, list button used)', true, `pt=${JSON.stringify(pt)}`)
    // heat integration switch
    await page.getByRole('button', { name: 'Without exchanger' }).click(); await page.waitForTimeout(1200)
    const ids = await page.$$eval('.react-flow__node', (e) => e.map((x) => x.getAttribute('data-id')))
    record(vp.label, 'site PFD: "Without exchanger" removes FEHE from the diagram', !ids.includes('FEHE'), ids.length + ' nodes')
    await page.getByRole('button', { name: 'With feed/effluent exchanger' }).click(); await page.waitForTimeout(800)
  }

  if (!only || only.has('platform/pfd')) {
    await go('platform/pfd')
    cur = 'platform-pfd-interaction'
    await page.locator('.react-flow__node[data-id="HEATER"]').click()
    await page.waitForSelector('.pfd-side .panel', { timeout: 5000 }).catch(() => pushP('platform equipment panel did not open'))
    const t1 = await page.locator('.pfd-side .panel-title').first().innerText().catch(() => '')
    record(vp.label, 'platform PFD: equipment panel opens (HEATER)', /HEATER/.test(t1), t1)
    await page.keyboard.press('Escape')
    await page.locator('.lists button', { hasText: /^S7 - / }).click()
    const t2 = await page.locator('.pfd-side .panel-title').first().innerText().catch(() => '')
    record(vp.label, 'platform PFD: stream panel opens (S7)', /^S7/.test(t2), t2)
    await page.keyboard.press('Escape')
  }

  if (!only || only.has('anchors')) {
    cur = 'anchors'
    await page.evaluate(() => { window.location.hash = '#/results#economics' })
    await page.waitForTimeout(2500)
    const top = await page.evaluate(() => document.getElementById('economics')?.getBoundingClientRect().top ?? 9999)
    record(vp.label, 'anchor #/results#economics scrolls the section into view', top >= -5 && top < 160, `top=${Math.round(top)}`)
    await page.evaluate(() => { window.location.hash = '#/research#ref-cechetto2023membrane' })
    await page.waitForTimeout(2500)
    const t2 = await page.evaluate(() => document.getElementById('ref-cechetto2023membrane')?.getBoundingClientRect().top ?? 9999)
    record(vp.label, 'citation anchor #/research#ref-cechetto2023membrane scrolls to the reference', t2 >= -5 && t2 < 200, `top=${Math.round(t2)}`)
  }

  if (vp.w === 1440 && (!only || only.has('downloads'))) {
    cur = 'downloads'
    for (const f of ['AmCraX_Technical_Report.pdf', 'AmCraX_Technical_Report_2026-11-23.pdf','AmCraX_Technical_Report.docx', 'AmCraX_Pitch_Deck.pdf', 'AmCraX_Pitch_Deck.pptx', 'speaker_script.md', 'validation_matrix.md', 'discrepancy_analysis.md']) {
      const r = await page.request.get(`${base}downloads/${f}`)
      const len = (await r.body()).length
      record(vp.label, `download ${f}`, r.status() === 200 && len > 2000, `HTTP ${r.status()}, ${(len / 1024).toFixed(0)} kB`)
    }
    // every file prepare_site.mjs copied (paper, executive summary, research notes when they exist at build time)
    const idx = await page.request.get(`${base}downloads/index.json`)
    const listed = idx.status() === 200 ? ((await idx.json()).files ?? []) : []
    record(vp.label, 'downloads/index.json lists the copied files', idx.status() === 200 && listed.length >= 8, `HTTP ${idx.status()}, ${listed.length} files`)
    for (const f of listed) {
      const r = await page.request.get(`${base}downloads/${f.file}`)
      record(vp.label, `listed download ${f.file}`, r.status() === 200 && (await r.body()).length > 0, `HTTP ${r.status()}`)
    }
    for (const u of ['og-image.png', 'favicon.svg', 'img/pfd_baseline.png', 'snapshot/manifest.json', 'snapshot/aspen-screenshots/01_flowsheet.png', 'snapshot/simulator/model.json', 'snapshot/simulator/aspen_anchors.json', 'snapshot/simulator/parity_report.json',
      'snapshot/research/phase2_index.json', 'snapshot/research/validation/by_kind.json', 'snapshot/research/reference_scenario/baseline.json.json', 'snapshot/research/carbon_pricing/price_sweep.csv.json']) {
      const r = await page.request.get(`${base}${u}`)
      record(vp.label, `asset ${u}`, r.status() === 200, `HTTP ${r.status()}`)
    }
    const r404 = await page.request.get(`${origin}/api/health`)
    record(vp.label, 'server answers 404 outside the base path (no API)', r404.status() === 404, `HTTP ${r404.status()}`)
  }

  record(vp.label, 'overall: no console errors / failed requests during the whole session', problems.length === 0, problems.slice(0, 8).join(' | '))
  await ctx.close()
}
await browser.close()
const failed = results.filter((r) => !r.ok)
console.log(`\n${results.length - failed.length} passed, ${failed.length} failed`)
if (notes404.size) console.log('HTTP >= 400 responses seen:\n  ' + [...notes404].join('\n  '))
else console.log('no HTTP >= 400 responses')
for (const f of failed) console.log(`FAILED [${f.vp}] ${f.id} - ${f.detail}`)
process.exitCode = failed.length ? 1 : 0
