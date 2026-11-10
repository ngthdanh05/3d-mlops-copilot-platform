import { beforeEach, describe, expect, it, vi } from 'vitest'
import { streamCopilotChat } from '../lib/api'
import type { CopilotStreamEvent } from '../lib/types'
import { useCameraStore } from '../store/useCameraStore'
import { useChatStore } from '../store/useChatStore'
import { useRunStore } from '../store/useRunStore'
import { makeRun } from '../test/make-run'
import { NO_RUN_FILTER } from '../utils/run-filter'
import { retryLastQuestion, sendCopilotMessage } from './useCopilot'

vi.mock('../lib/api', () => ({ streamCopilotChat: vi.fn() }))

const stream = vi.mocked(streamCopilotChat)

function replyWith(...events: CopilotStreamEvent[]) {
  stream.mockImplementationOnce(async (_message, _experimentId, onEvent) => {
    events.forEach(onEvent)
  })
}

const chatMessages = () => useChatStore.getState().messages
const lastAnswer = () => chatMessages().at(-1)

beforeEach(() => {
  localStorage.clear()
  stream.mockReset()
  useRunStore.setState(useRunStore.getInitialState(), true)
  useCameraStore.setState(useCameraStore.getInitialState(), true)
  useChatStore.setState(useChatStore.getInitialState(), true)
})

describe('sendCopilotMessage', () => {
  it('asks about the selected experiment', async () => {
    useRunStore.setState({ selectedExperimentId: 3 })
    replyWith({ type: 'done', message: 'ok', actions: [] })
    await sendCopilotMessage('Run nào tốt nhất?')
    expect(stream).toHaveBeenCalledWith('Run nào tốt nhất?', 3, expect.any(Function))
  })

  it('shows the answer as it streams and is busy until it ends', async () => {
    const seen: (string | null | undefined)[] = []
    stream.mockImplementationOnce(async (_message, _experimentId, onEvent) => {
      onEvent({ type: 'delta', text: 'Xin ' })
      onEvent({ type: 'delta', text: 'chào' })
      seen.push(lastAnswer()?.content, useChatStore.getState().streamingMessageId, lastAnswer()?.id)
      onEvent({ type: 'done', message: 'Xin chào!', actions: [] })
    })

    await sendCopilotMessage('hi')

    expect(seen[0]).toBe('Xin chào')
    expect(seen[1]).toBe(seen[2])
    expect(chatMessages().map((m) => m.role)).toEqual(['user', 'assistant'])
    expect(lastAnswer()?.content).toBe('Xin chào!')
    expect(useChatStore.getState().streamingMessageId).toBeNull()
  })

  it('discards streamed text on a reset', async () => {
    let afterReset: string | undefined
    stream.mockImplementationOnce(async (_message, _experimentId, onEvent) => {
      onEvent({ type: 'delta', text: 'draft' })
      onEvent({ type: 'reset' })
      afterReset = lastAnswer()?.content
      onEvent({ type: 'done', message: 'final', actions: [] })
    })
    await sendCopilotMessage('hi')
    expect(afterReset).toBe('')
    expect(lastAnswer()?.content).toBe('final')
  })

  it('applies AI actions through the stores', async () => {
    useRunStore.setState({ runs: [makeRun({ id: 7 }), makeRun({ id: 8 })] })
    replyWith({
      type: 'done',
      message: 'ok',
      actions: [
        { type: 'highlight_runs', run_ids: [7, 8] },
        { type: 'focus_camera', run_id: 7 },
        { type: 'open_inspector', run_id: 8 },
      ],
    })

    await sendCopilotMessage('hi')

    expect(useRunStore.getState()).toMatchObject({ highlightedRunIds: [7, 8], selectedRunId: 8 })
    expect(useCameraStore.getState()).toMatchObject({ targetRunId: 7, requestId: 1 })
  })

  it('clears a filter that would hide a run the AI points at', async () => {
    useRunStore.setState({
      runs: [makeRun({ id: 7, status: 'completed' })],
      runFilter: { ...NO_RUN_FILTER, status: 'failed' },
    })
    replyWith({ type: 'done', message: 'ok', actions: [{ type: 'highlight_runs', run_ids: [7] }] })

    await sendCopilotMessage('hi')

    expect(useRunStore.getState()).toMatchObject({
      runFilter: NO_RUN_FILTER,
      highlightedRunIds: [7],
    })
  })

  it('keeps a filter that hides nothing the AI points at', async () => {
    const runFilter = { ...NO_RUN_FILTER, status: 'completed' as const }
    useRunStore.setState({ runs: [makeRun({ id: 7 })], runFilter })
    replyWith({ type: 'done', message: 'ok', actions: [{ type: 'focus_camera', run_id: 7 }] })

    await sendCopilotMessage('hi')

    expect(useRunStore.getState().runFilter).toBe(runFilter)
  })

  it('clears the previous highlights and suggestions when asking', async () => {
    useRunStore.setState({ highlightedRunIds: [1] })
    useChatStore.setState({ suggestions: ['old'] })
    replyWith({ type: 'done', message: 'ok', actions: [] })

    await sendCopilotMessage('hi')

    expect(useRunStore.getState().highlightedRunIds).toEqual([])
    expect(useChatStore.getState().suggestions).toEqual([])
  })

  it('ignores a question while another is being answered', async () => {
    useChatStore.setState({ streamingMessageId: 'busy' })
    await sendCopilotMessage('hi')
    expect(stream).not.toHaveBeenCalled()
    expect(chatMessages()).toEqual([])
  })

  it('reports a failed request and frees the chat', async () => {
    stream.mockRejectedValueOnce(new Error('offline'))
    await sendCopilotMessage('hi')
    expect(lastAnswer()).toMatchObject({ failed: true })
    expect(useChatStore.getState().streamingMessageId).toBeNull()
  })

  it('reports a stream that ends without an answer', async () => {
    replyWith({ type: 'delta', text: 'partial' })
    await sendCopilotMessage('hi')
    expect(lastAnswer()).toMatchObject({ failed: true })
  })

  it('keeps the answer when the connection fails after it was delivered', async () => {
    stream.mockImplementationOnce(async (_message, _experimentId, onEvent) => {
      onEvent({ type: 'done', message: 'final', actions: [] })
      throw new Error('connection lost')
    })
    await sendCopilotMessage('hi')
    expect(lastAnswer()).toMatchObject({ content: 'final' })
    expect(lastAnswer()?.failed).toBeUndefined()
  })
})

describe('retryLastQuestion', () => {
  it('replaces a failed answer with a new attempt', async () => {
    stream.mockRejectedValueOnce(new Error('offline'))
    await sendCopilotMessage('hi')
    replyWith({ type: 'done', message: 'ok', actions: [] })

    retryLastQuestion()
    await vi.waitFor(() => expect(lastAnswer()?.content).toBe('ok'))

    expect(chatMessages().map((m) => m.content)).toEqual(['hi', 'ok'])
    expect(stream).toHaveBeenCalledTimes(2)
  })

  it('does nothing when the last answer did not fail', async () => {
    replyWith({ type: 'done', message: 'ok', actions: [] })
    await sendCopilotMessage('hi')
    retryLastQuestion()
    expect(stream).toHaveBeenCalledTimes(1)
  })
})
