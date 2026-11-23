// Browser verification of the static site, as served by scripts/serve_pages.mjs under /AmCraX/ (Edge via playwright-core).
//
//   node scripts/serve_pages.mjs --port 4180        (in another shell, after `npm run build:pages`)
//   node scripts/site_check.mjs [--base http://127.0.0.1:4180/AmCraX/] [--shots <dir>] [--viewports 390x844,820x1180,1440x900,1920x1080]
//                               [--routes why,results,platform/pfd] [--no-shots] [--fullpage]
//
// For every viewport and every route it checks: renders (one h1 / platform title), no console errors, no failed or 4xx/5xx requests,
// no request outside the base path (so no API call and no absolute "/..." URL), no horizontal overflow. Plus interaction checks
// (mobile menu, nav reaches ten sections, PFD equipment + stream panels on site and platform, calculator, anchors, downloads).
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
const SITE = ['', 'why', 'pfd', 'methodology', 'results', 'architecture', 'research', 'docs', 'about', ...HYP]
const PLATFORM = ['platform', 'platform/pfd', 'platform/simulation', 'platform/reactor', 'platform/heat', 'platform/sensitivity', 'platform/optimisation', 'platform/economics', 'platform/environment', 'platform/validation', 'platform/reports']
const only = args.routes ? new Set(args.routes.split(',')) : null
const ROUTES = [...SITE, ...PLATFORM].filter((r) => !only || only.has(r === '' ? 'home' : r))
const name = (r) => (r === '' ? 'home' : r === 'hypotheses' ? 'research_matrix' : r.startsWith('hypotheses/') ? `research_${r.slice(11).replace(/-/g, '_')}` : r.replace('platform/', 'platform_').replace(/\//g, '_'))
const qaDir = path.join(shots, 'qa')
if (args['no-shots'] !== 'true') { mkdirSync(shots, { recursive: true }); mkdirSync(qaDir, { recursive: true }) }
/** Published set: desktop captures of the site routes only; everything else is a QA capture. */
const shotPath = (route, label, isPlat, kind = 'page') => path.join(label === 'desktop' && !isPlat && kind === 'page' ? shots : qaDir, `site_${kind === 'page' ? name(route) : kind}_${label}.png`)

const results = []
const record = (vp, id, ok, detail = '') => { results.push({ vp, id, ok, detail }); console.log(`${ok ? 'PASS' : 'FAIL'} [${vp}] ${id}${detail ? ' - ' + detail : ''}`) }
const external = /^https:\/\/(fonts\.googleapis\.com|fonts\.gstatic\.com)\//

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
    await page.waitForTimeout(route === 'results' ? 2500 : 1200)
  }
  async function go(route) {
    cur = route === '' ? 'home' : route
    await page.evaluate((r) => { window.location.hash = `#/${r}` }, route)
    await settle(route)
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
    }
    record(vp.label, `${id}: no console errors / failed or 4xx requests / requests outside base`, problems.length === before, problems.slice(before).join(' | ').slice(0, 400))
    if (args['no-shots'] !== 'true') {
      if (args.fullpage !== 'false' && !isPlat) await page.evaluate(async () => { const h = document.documentElement.scrollHeight; for (let y = 0; y < h; y += 700) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 60)) } })  // trigger lazy images
      await page.waitForTimeout(400)
      await page.evaluate(() => window.scrollTo(0, 0))
      await page.screenshot({ path: shotPath(route, vp.label, isPlat), fullPage: args.fullpage !== 'false' && !isPlat })
    }
  }

  // ---- interaction checks ----
  if (!only || only.has('home')) {
    cur = 'interaction'
    await go('')
    // nav reaches the ten sections
    const nine = vp.w >= 1331
    if (!nine) { await page.click('.nav-toggle'); await page.waitForTimeout(300) }
    const links = await page.$$eval('.site-nav a', (as) => as.filter((a) => a.getBoundingClientRect().width > 0).map((a) => a.textContent))
    record(vp.label, `nav: ${nine ? 'top bar' : 'mobile menu'} shows all ten sections`, links.length === 10, links.join(', '))
    if (!nine) {
      const expanded = await page.getAttribute('.nav-toggle', 'aria-expanded')
      record(vp.label, 'mobile menu: toggle has aria-expanded=true when open', expanded === 'true')
      await page.click('.site-nav a:has-text("Results")'); await page.waitForTimeout(600)
      record(vp.label, 'mobile menu: link navigates and menu closes', page.url().endsWith('#/results') && !(await page.$eval('.site-nav', (n) => n.classList.contains('open'))), page.url())
      await go('')
    }
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
    record(vp.label, 'home: four headline facts with values', facts.length === 4 && facts.every((f) => /\d/.test(f)), facts.join(' | '))
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
    for (const f of ['AmCraX_Technical_Report.pdf', 'AmCraX_Technical_Report.docx', 'AmCraX_Pitch_Deck.pdf', 'AmCraX_Pitch_Deck.pptx', 'speaker_script.md', 'validation_matrix.md', 'discrepancy_analysis.md']) {
      const r = await page.request.get(`${base}downloads/${f}`)
      const len = (await r.body()).length
      record(vp.label, `download ${f}`, r.status() === 200 && len > 2000, `HTTP ${r.status()}, ${(len / 1024).toFixed(0)} kB`)
    }
    for (const u of ['og-image.png', 'favicon.svg', 'img/pfd_baseline.png', 'snapshot/manifest.json', 'snapshot/aspen-screenshots/01_flowsheet.png']) {
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
