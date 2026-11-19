// Live local smoke: real curves, polling, privacy and blocked browser egress.
import { mkdirSync, writeFileSync } from 'node:fs'
import { launchBrowser } from './browser.mjs'

const url = process.argv[2] ?? 'http://127.0.0.1:5173'
const output = process.argv[3] ?? '../backend/artifacts/browser'
const shouldChat = process.argv.includes('--chat')
mkdirSync(output, { recursive: true })
const browser = await launchBrowser()
const blocked = [], errors = []
let fixtureExperiment
const api = async (path, options = {}) => {
  const response = await fetch(`http://127.0.0.1:8000/api${path}`, {
    ...options, headers: { 'Content-Type': 'application/json' },
  })
  if (!response.ok) throw new Error(`${path}: ${response.status}`)
  return response.status === 204 ? null : response.json()
}
async function until(page, predicate, argument, timeout = 15000) {
  const deadline = Date.now() + timeout
  while (Date.now() < deadline) {
    if (await page.evaluate(predicate, argument)) return
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error('Browser state did not meet the expected condition before timeout')
}
try {
  const context = await browser.newContext({ viewport: { width: 1600, height: 900 } })
  // Offline Windows may report navigator.onLine=false while loopback remains usable.
  await context.addInitScript(() => Object.defineProperty(navigator, 'onLine', { get: () => false }))
  await context.route('**/*', async (route) => {
    const target = new URL(route.request().url())
    if (!['127.0.0.1', 'localhost', '[::1]'].includes(target.hostname)) {
      blocked.push(target.origin)
      return route.abort()
    }
    return route.continue()
  })
  const page = await context.newPage()
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto(url)
  await page.locator('canvas').first().waitFor()
  await page.getByRole('button', { name: 'real-cifar10', exact: true }).click()
  await until(page, async () => {
    const { useRunStore } = await import('/src/store/useRunStore.ts')
    return useRunStore.getState().runs.some((r) => r.hyperparams.dataset?.includes('CIFAR10'))
  })
  const detail = await page.evaluate(async () => {
    const { useRunStore } = await import('/src/store/useRunStore.ts')
    const run = useRunStore.getState().runs.find((r) => r.artifacts)
    useRunStore.getState().selectRun(run.id)
    return { id: run.id, experiment_id: run.experiment_id, name: run.run_name }
  })
  await page.getByRole('img', { name: 'Đường cong accuracy' }).waitFor()
  await page.getByText(/Checkpoint tốt nhất:/).waitFor()
  await page.getByRole('checkbox', { name: 'Lưu lịch sử trên trình duyệt' }).uncheck()
  await page.evaluate(async () => {
    const { useChatStore } = await import('/src/store/useChatStore.ts')
    useChatStore.getState().addMessage({ id: 'private-smoke', role: 'user', content: 'private-smoke' })
    const saved = JSON.parse(localStorage.getItem('copilot-chat'))
    if (saved.state.messages.length) throw new Error('Privacy: message persisted')
    useChatStore.getState().clearMessages()
  })
  if (shouldChat) {
    const runs = await api(`/runs?experiment_id=${detail.experiment_id}`)
    const best = runs.filter((r) => r.status === 'completed' && r.final_val_accuracy != null)
      .sort((a, b) => b.final_val_accuracy - a.final_val_accuracy)[0]
    await page.getByRole('textbox', { name: 'Câu hỏi cho trợ lý AI' })
      .fill('Run nào tốt nhất theo val_accuracy?')
    await page.getByRole('button', { name: 'Gửi', exact: true }).click()
    await until(page, async () => {
      const { useChatStore } = await import('/src/store/useChatStore.ts')
      const chat = useChatStore.getState()
      return chat.messages.length >= 2 && chat.messages.at(-1).content.trim().length > 0
        && !chat.streamingMessageId
    }, null, 600000)
    const result = await page.evaluate(async () => {
      const { useChatStore } = await import('/src/store/useChatStore.ts')
      const { useRunStore } = await import('/src/store/useRunStore.ts')
      const { useCameraStore } = await import('/src/store/useCameraStore.ts')
      return { answer: useChatStore.getState().messages.at(-1).content,
        highlighted: useRunStore.getState().highlightedRunIds,
        selected: useRunStore.getState().selectedRunId,
        camera: useCameraStore.getState().targetRunId }
    })
    if (!result.highlighted.includes(best.id) || result.selected !== best.id || result.camera !== best.id) {
      throw new Error(`Local chat did not focus the DB's best run: ${JSON.stringify(result)}`)
    }
    writeFileSync(`${output}/local-chat.json`, JSON.stringify(result, null, 2))
  }
  await page.screenshot({ path: `${output}/real-cifar10.png` })
  const source = await api(`/runs/${detail.id}`)
  fixtureExperiment = await api('/experiments', { method: 'POST', body: JSON.stringify({
    name: `acceptance-polling-${Date.now()}`, description: 'Temporary UI fixture using real observed metrics',
  }) })
  const run = await api('/runs', { method: 'POST', body: JSON.stringify({
    experiment_id: fixtureExperiment.id, run_name: 'polling-fixture', hyperparams: {},
  }) })
  await page.getByRole('button', { name: 'Làm mới dữ liệu' }).click()
  await page.getByRole('button', { name: fixtureExperiment.name, exact: true }).click()
  await until(page, (id) => import('/src/store/useRunStore.ts').then(
    ({ useRunStore }) => useRunStore.getState().runs.some((r) => r.id === id)), run.id)
  const observed = source.metrics.at(-1)
  await api(`/runs/${run.id}/metrics`, { method: 'POST', body: JSON.stringify({ epoch: 1,
    accuracy: observed.accuracy, loss: observed.loss,
    val_accuracy: observed.val_accuracy, val_loss: observed.val_loss,
  }) })
  await until(page, (id) => import('/src/store/useRunStore.ts').then(
    ({ useRunStore }) => useRunStore.getState().runs.find((r) => r.id === id)?.final_epoch === 1),
  run.id)
  await api(`/runs/${run.id}`, { method: 'PUT', body: '{"status":"completed"}' })
  await until(page, (id) => import('/src/store/useRunStore.ts').then(
    ({ useRunStore }) => useRunStore.getState().runs.find((r) => r.id === id)?.status === 'completed'),
  run.id)
  await page.getByRole('button', { name: 'real-cifar10', exact: true }).click()
  await until(page, (id) => import('/src/store/useRunStore.ts').then(
    ({ useRunStore }) => useRunStore.getState().selectedExperimentId === id), detail.experiment_id)
  if (blocked.length || errors.length) throw new Error(JSON.stringify({ blocked, errors }))
  writeFileSync(`${output}/result.json`, JSON.stringify({ passed: true, blocked, errors,
    local_chat_checked: shouldChat,
    checked: ['real curves', 'best checkpoint', 'no saved chat', 'poll epoch while navigator offline', 'completed', 'switch experiment'],
  }, null, 2))
  console.log('PASS: CIFAR browser smoke; no external browser requests or page errors')
} finally {
  if (fixtureExperiment) await api(`/experiments/${fixtureExperiment.id}`, { method: 'DELETE' })
  await browser.close()
}
