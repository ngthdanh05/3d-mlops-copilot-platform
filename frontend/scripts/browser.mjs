import { chromium } from 'playwright-core'

/** Uses a browser already on the machine, so nothing has to be downloaded. */
export async function launchBrowser() {
  const launchOptions = {
    headless: true,
    args: ['--ignore-gpu-blocklist', '--enable-gpu-rasterization', '--use-angle=default'],
  }
  for (const channel of ['chrome', 'msedge']) {
    try {
      return await chromium.launch({ ...launchOptions, channel })
    } catch {
      // Not installed: try the next one.
    }
  }
  throw new Error('Cần cài Chrome hoặc Edge để chạy kiểm tra trên trình duyệt.')
}

export async function openPage(browser, url) {
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } })
  await page.goto(url)
  await page.locator('canvas').first().waitFor({ timeout: 30_000 })
  return page
}

/** The GPU in use, because a software renderer makes FPS numbers meaningless. */
export function readRenderer(page) {
  return page.evaluate(() => {
    const gl = document.createElement('canvas').getContext('webgl2')
    const info = gl?.getExtension('WEBGL_debug_renderer_info')
    return info ? gl.getParameter(info.UNMASKED_RENDERER_WEBGL) : 'không rõ'
  })
}

export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
