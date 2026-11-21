// Capture every routed dashboard page (and the PFD side panels) with Microsoft Edge headless.
//
// Dashboard pages live under #/platform (the public site is at #/).
//   node frontend/scripts/capture_dashboard.mjs                       -> starts its own Vite dev server on :5176 (needs the API on :8000 for LIVE)
//   node frontend/scripts/capture_dashboard.mjs --base http://127.0.0.1:5176
//   options: --out <dir> (default docs/screenshots)  --width 1600 --height 1000  --pages pfd,overview  --case baseline
//
// Output: docs/screenshots/dashboard_<page>.png, dashboard_pfd_equipment_panel.png, dashboard_pfd_stream_panel.png
import { spawn } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const here = path.dirname(fileURLToPath(import.meta.url))
const frontend = path.resolve(here, '..')
const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, all) => (x.startsWith('--') ? [...a, [x.slice(2), all[i + 1] && !all[i + 1].startsWith('--') ? all[i + 1] : 'true']] : a), []))
const W = Number(args.width ?? 1600)
const H = Number(args.height ?? 1000)
const outDir = path.resolve(args.out ?? path.join(frontend, '..', 'docs', 'screenshots'))
const PAGES = [
  ['overview', '/platform'], ['pfd', '/platform/pfd'], ['simulation', '/platform/simulation'], ['reactor', '/platform/reactor'], ['heat', '/platform/heat'],
  ['sensitivity', '/platform/sensitivity'], ['optimisation', '/platform/optimisation'], ['economics', '/platform/economics'], ['environment', '/platform/environment'],
  ['validation', '/platform/validation'], ['reports', '/platform/reports'],
]
const only = args.pages ? new Set(args.pages.split(',')) : null
mkdirSync(outDir, { recursive: true })

let server = null
let base = args.base
async function up(url) { try { return (await fetch(url)).ok } catch { return false } }
if (!base) {
  base = 'http://127.0.0.1:5176'
  if (!(await up(base))) {
    server = spawn(process.execPath, [path.join(frontend, 'node_modules', 'vite', 'bin', 'vite.js'), '--port', '5176', '--strictPort', '--host', '127.0.0.1'], { cwd: frontend, stdio: 'ignore' })
    for (let i = 0; i < 60 && !(await up(base)); i++) await new Promise((r) => setTimeout(r, 500))
    if (!(await up(base))) { server.kill(); throw new Error('dev server did not start') }
  }
}

const browser = await chromium.launch({ channel: 'msedge', headless: true })
const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 })
const page = await ctx.newPage()
const problems = []
page.on('pageerror', (e) => problems.push(`pageerror: ${e.message}`))
page.on('console', (m) => { if (m.type() === 'error') problems.push(`console: ${m.text().slice(0, 200)}`) })

/** wait until no loading indicator / spinner text remains and the DOM is quiet */
async function settle(extra) {
  await page.waitForFunction(() => {
    const t = document.body.innerText
    return !/Resolving data mode|Loading|Fetching|Running\.\.\./i.test(t) && document.querySelector('.shell') !== null
  }, null, { timeout: 45000 }).catch(() => problems.push('settle timeout (loading text still present)'))
  if (extra) await page.waitForSelector(extra, { timeout: 20000 }).catch(() => problems.push(`selector missing: ${extra}`))
  await page.waitForTimeout(1200)
}
async function shot(name) {
  const file = path.join(outDir, `${args.prefix ?? 'dashboard'}_${name}.png`)
  await page.screenshot({ path: file, fullPage: false }) // viewport-sized hero shot
  console.log('wrote', file)
  if (args.full === 'true') await page.screenshot({ path: path.join(outDir, `${args.prefix ?? 'dashboard'}_${name}_full.png`), fullPage: true })
}

await page.goto(`${base}/${args.query ?? ''}#/platform`, { waitUntil: 'domcontentloaded' })
await settle()
if (args.case) { await page.selectOption('.case-select select', args.case); await page.waitForTimeout(500) }
const mode = await page.locator('.topbar-right .pill').first().innerText().catch(() => '?')
console.log('data mode badge:', mode.trim())

for (const [name, route] of PAGES) {
  if (only && !only.has(name) && !(name === 'pfd' && (only.has('pfd_equipment_panel') || only.has('pfd_stream_panel')))) continue
  await page.evaluate((r) => { window.location.hash = '#' + r }, route)
  await settle(name === 'pfd' ? '.react-flow__node' : null)
  if (!only || only.has(name)) { await page.evaluate(() => window.scrollTo(0, 0)); await shot(name) }
  if (name === 'pfd') {
    // equipment panel: real click on the cracker node
    await page.locator('.react-flow__node[data-id="CRACKER"]').click()
    await page.waitForSelector('.pfd-side .panel', { timeout: 5000 })
    await page.waitForTimeout(500)
    await shot('pfd_equipment_panel')
    await page.keyboard.press('Escape')
    // stream panel: real mouse click on the S5 line (midpoint of its longest drawn path)
    const pt = await page.evaluate(() => {
      const p = document.querySelector('.react-flow__edge[data-id="S5"] path.stream-core')
      if (!p) return null
      const L = p.getTotalLength(); const q = p.getPointAtLength(L * 0.55); const m = p.getScreenCTM()
      return { x: m.a * q.x + m.c * q.y + m.e, y: m.b * q.x + m.d * q.y + m.f }
    })
    if (pt) { await page.mouse.click(pt.x, pt.y); await page.waitForSelector('.pfd-side .panel', { timeout: 5000 }).catch(() => problems.push('stream click did not open a panel')) }
    else problems.push('S5 edge not found')
    await page.mouse.move(5, 5)
    await page.waitForTimeout(500)
    await shot('pfd_stream_panel')
    await page.keyboard.press('Escape')
  }
}
await browser.close()
if (server) server.kill()
if (problems.length) { console.log('PROBLEMS:'); for (const p of [...new Set(problems)]) console.log(' -', p); process.exitCode = 0 }
else console.log('no console errors, no settle timeouts')



