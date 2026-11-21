// Hero crops of the static site for the README, report and deck (viewport-sized, not full page):
//   docs/screenshots/site_home_desktop.png, site_home_mobile.png, site_results_desktop.png, site_pfd_desktop.png, site_methodology_desktop.png
//
//   node scripts/capture_site.mjs [--base http://127.0.0.1:4180/AmCraX/] [--out DIR]   (serve dist first: node scripts/serve_pages.mjs --port 4180)
import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const here = path.dirname(fileURLToPath(import.meta.url))
const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, all) => (x.startsWith('--') ? [...a, [x.slice(2), all[i + 1]]] : a), []))
const base = (args.base ?? 'http://127.0.0.1:4180/AmCraX/').replace(/\/?$/, '/')
const out = path.resolve(args.out ?? path.join(here, '..', '..', 'docs', 'screenshots'))
mkdirSync(out, { recursive: true })
const SHOTS = [
  { file: 'site_home_desktop.png', route: '', w: 1600, h: 1000 },
  { file: 'site_home_mobile.png', route: '', w: 390, h: 844 },
  { file: 'site_results_desktop.png', route: 'results', w: 1600, h: 1000, scroll: '#conversion' },
  { file: 'site_pfd_desktop.png', route: 'pfd', w: 1600, h: 1000, scroll: '#diagram', click: '.react-flow__node[data-id="CRACKER"]' },
  { file: 'site_methodology_desktop.png', route: 'methodology', w: 1600, h: 1000, scroll: '#aspen' },
]
const browser = await chromium.launch({ channel: 'msedge', headless: true })
for (const s of SHOTS) {
  const page = await (await browser.newContext({ viewport: { width: s.w, height: s.h }, deviceScaleFactor: 1 })).newPage()
  await page.goto(`${base}#/${s.route}`, { waitUntil: 'domcontentloaded' })
  await page.waitForFunction(() => !/Resolving data mode|Loading/i.test(document.body.innerText) && document.querySelector('.site'), null, { timeout: 60000 }).catch(() => {})
  await page.waitForTimeout(s.route === 'results' ? 3500 : 2000)
  if (s.click) { await page.locator(s.click).click(); await page.waitForTimeout(600) }
  if (s.scroll) { await page.evaluate((sel) => { const el = document.querySelector(sel); if (el) window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 70) }, s.scroll); await page.waitForTimeout(800) }
  await page.screenshot({ path: path.join(out, s.file), fullPage: false })
  console.log('wrote', path.join(out, s.file))
  await page.context().close()
}
await browser.close()
