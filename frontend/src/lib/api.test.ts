import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, fetchRuns, streamCopilotChat } from './api'
import type { CopilotStreamEvent } from './types'

function streamResponse(chunks: string[], status = 200): Response {
  const encoder = new TextEncoder()
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)))
      controller.close()
    },
  })
  return new Response(body, { status })
}

async function collect(chunks: string[]): Promise<CopilotStreamEvent[]> {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(streamResponse(chunks)))
  const events: CopilotStreamEvent[] = []
  await streamCopilotChat('hi', 2, (event) => events.push(event))
  return events
}

afterEach(() => vi.unstubAllGlobals())

describe('streamCopilotChat', () => {
  it('sends the question and the experiment', async () => {
    await collect([])
    const [path, init] = vi.mocked(fetch).mock.calls[0]
    expect(path).toBe('/api/copilot/chat/stream')
    expect(JSON.parse(init?.body as string)).toEqual({ message: 'hi', experiment_id: 2 })
  })

  it('parses several events in one chunk', async () => {
    const events = await collect([
      'data: {"type":"delta","text":"a"}\n\ndata: {"type":"reset"}\n\n',
    ])
    expect(events).toEqual([{ type: 'delta', text: 'a' }, { type: 'reset' }])
  })

  it('reassembles an event split across chunks', async () => {
    const events = await collect(['data: {"type":"del', 'ta","text":"a"}\n', '\n'])
    expect(events).toEqual([{ type: 'delta', text: 'a' }])
  })

  it('throws on an error status', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(streamResponse([], 500)))
    await expect(streamCopilotChat('hi', null, () => undefined)).rejects.toBeInstanceOf(ApiError)
  })
})

describe('fetchRuns', () => {
  it('reports the status of a failed request', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 404 })))
    await expect(fetchRuns(1)).rejects.toMatchObject({ status: 404 })
  })
})
