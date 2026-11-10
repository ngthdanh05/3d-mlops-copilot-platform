// Browser half of backend/scripts/benchmark.py. Prints one JSON document on the last line.
import { launchBrowser, openPage, readRenderer, sleep } from './browser.mjs'

const [url, ...nodeCounts] = process.argv.slice(2)
const SETTLE_MS = 2500
const SAMPLE_MS = 6000
const ORBIT_STEP_MS = 16

function recordFrames(page, durationMs) {
  return page.evaluate(
    (duration) =>
      new Promise((resolve) => {
        const times = []
        const onFrame = (now) => {
          times.push(now)
          if (now - times[0] < duration) requestAnimationFrame(onFrame)
          else resolve(times)
        }
        requestAnimationFrame(onFrame)
      }),
    durationMs,
  )
}

/** Drags the camera around for the whole sample, since a still scene is not what users do. */
async function orbitCamera(page, durationMs) {
  const box = await page.locator('canvas').first().boundingBox()
  const centerX = box.x + box.width / 2
  const centerY = box.y + box.height / 2
  await page.mouse.move(centerX, centerY)
  await page.mouse.down()
  const start = Date.now()
  while (Date.now() - start < durationMs) {
    const phase = (Date.now() - start) / 500
    await page.mouse.move(centerX + Math.sin(phase) * 150, centerY + Math.cos(phase) * 60)
    await sleep(ORBIT_STEP_MS)
  }
  await page.mouse.up()
}

function summarize(times) {
  const gaps = times.slice(1).map((time, index) => time - times[index]).sort((a, b) => a - b)
  const elapsed = times.at(-1) - times[0]
  const p95 = gaps[Math.floor(gaps.length * 0.95)]
  return { fps: (gaps.length / elapsed) * 1000, p95FrameMs: p95, frames: gaps.length }
}

const browser = await launchBrowser()
try {
  const page = await openPage(browser, url)
  const results = []
  for (const count of nodeCounts) {
    await page.getByRole('button', { name: `bench-${count}`, exact: true }).click()
    await page.getByText('Tốt nhất trong').waitFor({ timeout: 30_000 })
    await sleep(SETTLE_MS)
    const idle = summarize(await recordFrames(page, SAMPLE_MS))
    const [times] = await Promise.all([recordFrames(page, SAMPLE_MS), orbitCamera(page, SAMPLE_MS)])
    results.push({ nodes: Number(count), idle, orbit: summarize(times) })
    console.error(`[ok] ${count} node: idle ${idle.fps.toFixed(1)} fps`)
  }
  console.log(JSON.stringify({ renderer: await readRenderer(page), results }))
} finally {
  await browser.close()
}
