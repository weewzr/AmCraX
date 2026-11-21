// Create the two share images from genuine screenshots of the running app (Edge headless through playwright-core):
//   public/img/pfd_baseline.png  - the interactive PFD (canvas + legend) of the baseline case, used as the hero picture
//   public/og-image.png          - 1200x630 social preview: wordmark, one line, and that screenshot
//
//   node scripts/make_site_images.mjs [--base http://127.0.0.1:4180/AmCraX/]      (serve dist first, or use the dev server)
import { mkdirSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const here = path.dirname(fileURLToPath(import.meta.url))
const pub = path.join(here, '..', 'public')
const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, all) => (x.startsWith('--') ? [...a, [x.slice(2), all[i + 1]]] : a), []))
const base = (args.base ?? 'http://127.0.0.1:4180/AmCraX/').replace(/\/?$/, '/')
mkdirSync(path.join(pub, 'img'), { recursive: true })

const browser = await chromium.launch({ channel: 'msedge', headless: true })
const page = await (await browser.newContext({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 })).newPage()
await page.goto(`${base}#/platform/pfd`, { waitUntil: 'domcontentloaded' })
await page.waitForSelector('.react-flow__node[data-id="CRACKER"]', { timeout: 60000 })
await page.waitForTimeout(1500)
// stream labels on (T and P) so that the picture shows real numbers
await page.getByLabel('T', { exact: true }).check().catch(() => {})
await page.getByLabel('P', { exact: true }).check().catch(() => {})
await page.waitForTimeout(600)
const box = await page.locator('.pfd-canvas').boundingBox()
const heroPath = path.join(pub, 'img', 'pfd_baseline.png')
await page.screenshot({ path: heroPath, clip: { x: box.x, y: box.y, width: box.width, height: box.height } })
console.log('wrote', heroPath, `${Math.round(box.width)}x${Math.round(box.height)}`)

const img = readFileSync(heroPath).toString('base64')
const og = await browser.newPage({ viewport: { width: 1200, height: 630 } })
await og.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>
  *{box-sizing:border-box}body{margin:0;width:1200px;height:630px;background:#0b1020;color:#eef2fb;font-family:Inter,'Segoe UI',system-ui,sans-serif;position:relative;overflow:hidden}
  .left{position:absolute;left:64px;top:64px;width:470px}
  .mark{font:700 76px/1 'Space Grotesk','Segoe UI',sans-serif;letter-spacing:-1px}.mark b{color:#38bdf8;font-weight:700}.mark i{color:#ff7a3d;font-style:normal}
  .tag{margin-top:26px;font-size:30px;line-height:1.25;color:#c3cce3;font-weight:500}
  .pts{margin-top:34px;font-size:21px;line-height:1.5;color:#8e9bbd}
  .pts span{display:block}.pts span:before{content:'';display:inline-block;width:8px;height:8px;border-radius:50%;background:#ff7a3d;margin-right:12px;vertical-align:middle}
  .url{position:absolute;left:64px;bottom:48px;font:500 22px 'JetBrains Mono',Consolas,monospace;color:#38bdf8}
  .shot{position:absolute;left:560px;top:150px;width:600px;height:318px;border:1px solid #3b4a75;border-radius:14px;overflow:hidden;background:#121a2f;box-shadow:0 20px 60px rgba(0,0,0,.5)}
  .shot img{display:block;width:100%;height:100%}
</style></head><body>
  <div class="left"><div class="mark">Am<b>Cra</b><i>X</i></div>
  <div class="tag">Ammonia cracking simulation and optimisation platform</div>
  <div class="pts"><span>Aspen Plus V15 flowsheet</span><span>Independent Python models</span><span>Interactive process flow diagram</span></div></div>
  <div class="url">weewzr.github.io/AmCraX</div>
  <div class="shot"><img src="data:image/png;base64,${img}" alt=""></div>
</body></html>`)
await og.waitForTimeout(800)
const ogPath = path.join(pub, 'og-image.png')
await og.screenshot({ path: ogPath, clip: { x: 0, y: 0, width: 1200, height: 630 } })
console.log('wrote', ogPath)
await browser.close()
