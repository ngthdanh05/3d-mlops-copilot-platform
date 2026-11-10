// Browser half of backend/scripts/smoke_test.py. Needs the Vite dev server, because it reads
// the same Zustand stores as the app by importing them from Vite.
import { mkdirSync } from 'node:fs'
import { join } from 'node:path'
import { launchBrowser, openPage, readRenderer, sleep } from './browser.mjs'

const [url, flag, screenshotDir] = process.argv.slice(2)
const shouldSave = flag === '--screenshots'
const ANIMATION_MS = 2000
const COPILOT_TIMEOUT_MS = 60_000
const CLICK_GRID_STEP = 16

function check(condition, message) {
  if (!condition) throw new Error(message)
}

function report(step) {
  console.log(`[ok] ${step}`)
}

async function saveScreenshot(page, name) {
  if (shouldSave) await page.screenshot({ path: join(screenshotDir, name) })
}

const readRunState = (page) =>
  page.evaluate(async () => {
    const { useRunStore } = await import('/src/store/useRunStore.ts')
    const { selectedRunId, highlightedRunIds, runs } = useRunStore.getState()
    const selected = runs.find((run) => run.id === selectedRunId)
    return { selectedRunId, highlightedRunIds, runCount: runs.length, selectedName: selected?.run_name }
  })

const readCameraTarget = (page) =>
  page.evaluate(async () => {
    const { useCameraStore } = await import('/src/store/useCameraStore.ts')
    return useCameraStore.getState().targetRunId
  })

const readChat = (page) =>
  page.evaluate(async () => {
    const { useChatStore } = await import('/src/store/useChatStore.ts')
    const { messages, streamingMessageId } = useChatStore.getState()
    return { isBusy: streamingMessageId !== null, last: messages.at(-1) }
  })

/** Clicks across the middle of the scene until a click lands on a node. */
async function clickFirstNode(page) {
  const box = await page.locator('canvas').first().boundingBox()
  for (let y = box.y + box.height * 0.25; y < box.y + box.height * 0.8; y += CLICK_GRID_STEP) {
    for (let x = box.x + box.width * 0.2; x < box.x + box.width * 0.8; x += CLICK_GRID_STEP) {
      await page.mouse.click(x, y)
      if ((await readRunState(page)).selectedRunId !== null) return
    }
  }
  throw new Error('Không click trúng node nào trong không gian 3D.')
}

async function waitForAnswer(page) {
  const deadline = Date.now() + COPILOT_TIMEOUT_MS
  while (Date.now() < deadline) {
    const { isBusy, last } = await readChat(page)
    if (!isBusy && last?.role === 'assistant') return last
    await sleep(200)
  }
  throw new Error('Copilot không trả lời kịp.')
}

if (shouldSave) mkdirSync(screenshotDir, { recursive: true })
const browser = await launchBrowser()
const problems = []
try {
  const page = await openPage(browser, url)
  page.on('console', (message) => {
    if (message.type() === 'error') problems.push(message.text())
  })
  page.on('pageerror', (error) => problems.push(error.message))

  await page.getByText('Tốt nhất trong').waitFor({ timeout: 30_000 })
  await sleep(ANIMATION_MS)
  const { runCount } = await readRunState(page)
  check(runCount > 0, 'Store không có run nào.')
  report(`Không gian 3D tải ${runCount} run (${await readRenderer(page)})`)
  await saveScreenshot(page, '01-overview.png')

  await clickFirstNode(page)
  const { selectedName } = await readRunState(page)
  const inspector = page.getByRole('region', { name: 'Chi tiết run' })
  await inspector.getByText(selectedName, { exact: true }).waitFor({ timeout: 5000 })
  await inspector.getByText('Chỉ số cuối').waitFor({ timeout: 5000 })
  report(`Click node: Inspector hiện ${selectedName}`)
  await sleep(ANIMATION_MS)
  await saveScreenshot(page, '02-inspector.png')

  await page.getByRole('button', { name: 'Xem toàn cảnh' }).click()
  await page.getByLabel('Câu hỏi cho trợ lý AI').fill('Run nào tốt nhất?')
  await page.keyboard.press('Enter')
  const answer = await waitForAnswer(page)
  check(!answer.failed && answer.content.length > 0, `Copilot lỗi: ${answer.content}`)
  const { highlightedRunIds } = await readRunState(page)
  check(highlightedRunIds.length > 0, `Copilot không làm nổi bật run nào: ${answer.content}`)
  const cameraTarget = await readCameraTarget(page)
  check(highlightedRunIds.includes(cameraTarget), 'Camera không bay tới run được làm nổi bật.')
  report(`Copilot trả lời, làm nổi bật run ${highlightedRunIds.join(', ')} và bay camera tới`)
  await sleep(ANIMATION_MS)
  await saveScreenshot(page, '03-copilot.png')

  check(problems.length === 0, `Console có lỗi:\n${problems.join('\n')}`)
  report('Console không có lỗi')
} finally {
  await browser.close()
}
