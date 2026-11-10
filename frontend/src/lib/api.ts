import type { CopilotStreamEvent, Experiment, RunDetail, RunSummary } from './types'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) {
    throw new ApiError(response.status, `GET ${path} failed with ${response.status}`)
  }
  return response.json() as Promise<T>
}

export function fetchExperiments(): Promise<Experiment[]> {
  return getJson('/api/experiments')
}

export function fetchRuns(experimentId: number): Promise<RunSummary[]> {
  return getJson(`/api/runs?experiment_id=${experimentId}`)
}

export function fetchRunDetail(runId: number): Promise<RunDetail> {
  return getJson(`/api/runs/${runId}`)
}

/** Resolves when the stream ends. EventSource cannot send a POST, so this reads it by hand. */
export async function streamCopilotChat(
  message: string,
  experimentId: number | null,
  onEvent: (event: CopilotStreamEvent) => void,
): Promise<void> {
  const path = '/api/copilot/chat/stream'
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, experiment_id: experimentId }),
  })
  if (!response.ok || !response.body) {
    throw new ApiError(response.status, `POST ${path} failed with ${response.status}`)
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) return
    buffer += value
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() ?? ''
    for (const block of blocks) {
      if (block.startsWith('data: ')) onEvent(JSON.parse(block.slice(6)) as CopilotStreamEvent)
    }
  }
}
