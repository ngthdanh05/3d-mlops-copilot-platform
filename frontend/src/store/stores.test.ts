import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import type { ChatMessage, Experiment } from '../lib/types'
import { makeRun } from '../test/make-run'
import { NO_RUN_FILTER } from '../utils/run-filter'
import { focusRun, startStoreSync } from './syncStores'
import { useCameraStore } from './useCameraStore'
import { useChatStore } from './useChatStore'
import { useRunStore } from './useRunStore'

const experiment = (id: number): Experiment => ({
  id,
  name: `exp-${id}`,
  description: null,
  created_at: '2026-11-01T00:00:00Z',
})
const message = (id: string, role: ChatMessage['role'] = 'user'): ChatMessage => ({
  id,
  role,
  content: id,
})
const STATUS_FILTER = { ...NO_RUN_FILTER, status: 'failed' as const }

beforeEach(() => {
  localStorage.clear()
  useRunStore.setState(useRunStore.getInitialState(), true)
  useCameraStore.setState(useCameraStore.getInitialState(), true)
  useChatStore.setState(useChatStore.getInitialState(), true)
})

describe('useRunStore', () => {
  it('selects the first experiment when none is selected', () => {
    useRunStore.getState().setExperiments([experiment(4), experiment(5)])
    expect(useRunStore.getState().selectedExperimentId).toBe(4)
  })

  it('keeps a selected experiment that still exists', () => {
    useRunStore.setState({ selectedExperimentId: 5 })
    useRunStore.getState().setExperiments([experiment(4), experiment(5)])
    expect(useRunStore.getState().selectedExperimentId).toBe(5)
  })

  it('moves on when the selected experiment is gone', () => {
    useRunStore.setState({ selectedExperimentId: 9 })
    useRunStore.getState().setExperiments([experiment(4)])
    expect(useRunStore.getState().selectedExperimentId).toBe(4)
  })

  it('selects nothing when there are no experiments', () => {
    useRunStore.setState({ selectedExperimentId: 9 })
    useRunStore.getState().setExperiments([])
    expect(useRunStore.getState().selectedExperimentId).toBeNull()
  })

  it('clears everything tied to the old experiment on a switch', () => {
    useRunStore.setState({
      selectedExperimentId: 1,
      runs: [makeRun()],
      selectedRunId: 3,
      highlightedRunIds: [3],
      axisSelection: { x: 'dropout' },
      runFilter: STATUS_FILTER,
    })

    useRunStore.getState().selectExperiment(2)

    expect(useRunStore.getState()).toMatchObject({
      selectedExperimentId: 2,
      runs: [],
      selectedRunId: null,
      highlightedRunIds: [],
      axisSelection: {},
      runFilter: NO_RUN_FILTER,
    })
  })

  it('keeps the state when the same experiment is chosen again', () => {
    const runs = [makeRun()]
    useRunStore.setState({ selectedExperimentId: 1, runs, selectedRunId: 3 })
    useRunStore.getState().selectExperiment(1)
    expect(useRunStore.getState()).toMatchObject({ runs, selectedRunId: 3 })
  })

  it('sets one axis without touching the others', () => {
    useRunStore.getState().setAxis('x', 'dropout')
    useRunStore.getState().setAxis('z', null)
    expect(useRunStore.getState().axisSelection).toEqual({ x: 'dropout', z: null })
  })

  it('clears the selection and highlights when the filter changes', () => {
    useRunStore.setState({ selectedRunId: 3, highlightedRunIds: [3] })
    useRunStore.getState().setRunFilter(STATUS_FILTER)
    expect(useRunStore.getState()).toMatchObject({
      runFilter: STATUS_FILTER,
      selectedRunId: null,
      highlightedRunIds: [],
    })
  })
})

describe('useCameraStore', () => {
  it('fires again for the same target', () => {
    useCameraStore.getState().setTarget(7)
    useCameraStore.getState().setTarget(7)
    expect(useCameraStore.getState()).toMatchObject({ targetRunId: 7, requestId: 2 })
  })
})

describe('useChatStore', () => {
  it('builds an answer from pieces', () => {
    const chat = useChatStore.getState()
    chat.addMessage({ ...message('a', 'assistant'), content: '' })
    chat.appendToMessage('a', 'Xin ')
    chat.appendToMessage('a', 'chào')
    expect(useChatStore.getState().messages[0].content).toBe('Xin chào')
  })

  it('replaces only the targeted message', () => {
    const chat = useChatStore.getState()
    chat.addMessage(message('a'))
    chat.addMessage(message('b'))
    chat.setMessageContent('b', 'new')
    expect(useChatStore.getState().messages.map((m) => m.content)).toEqual(['a', 'new'])
  })

  it('marks a failed answer', () => {
    const chat = useChatStore.getState()
    chat.addMessage(message('a', 'assistant'))
    chat.failMessage('a', 'error')
    expect(useChatStore.getState().messages[0]).toMatchObject({ content: 'error', failed: true })
  })

  it('removes the last question and answer only', () => {
    const chat = useChatStore.getState()
    for (const id of ['q1', 'a1', 'q2', 'a2']) chat.addMessage(message(id))
    chat.removeLastExchange()
    expect(useChatStore.getState().messages.map((m) => m.id)).toEqual(['q1', 'a1'])
  })

  it('clears the history', () => {
    useChatStore.getState().addMessage(message('a'))
    useChatStore.getState().clearMessages()
    expect(useChatStore.getState().messages).toEqual([])
  })

  const saved = (): { state: { messages: ChatMessage[] } } =>
    JSON.parse(localStorage.getItem('copilot-chat') ?? 'null')

  it('saves the history but not the unfinished answer or transient state', () => {
    const chat = useChatStore.getState()
    chat.addMessage(message('question'))
    chat.addMessage(message('answer', 'assistant'))
    chat.setStreamingMessageId('answer')
    chat.setSuggestions(['anything'])

    expect(saved().state).toEqual({ messages: [message('question')] })
  })

  it('saves only the most recent messages', () => {
    const chat = useChatStore.getState()
    for (let i = 0; i < 105; i += 1) chat.addMessage(message(`m${i}`))
    const { messages } = saved().state
    expect(messages).toHaveLength(100)
    expect(messages[0].id).toBe('m5')
  })

  it('restores the saved history', async () => {
    localStorage.setItem(
      'copilot-chat',
      JSON.stringify({ state: { messages: [message('old')] }, version: 1 }),
    )
    await useChatStore.persist.rehydrate()
    expect(useChatStore.getState().messages.map((m) => m.id)).toEqual(['old'])
  })
})

describe('store sync', () => {
  let stop: () => void

  beforeEach(() => {
    stop = startStoreSync()
  })

  afterEach(() => stop())

  it('selects a run and flies to it', () => {
    focusRun(6)
    expect(useRunStore.getState().selectedRunId).toBe(6)
    expect(useCameraStore.getState()).toMatchObject({ targetRunId: 6, requestId: 1 })
  })

  it('suggests questions for a newly selected run', () => {
    const run = makeRun({ run_name: 'run-x' })
    useRunStore.setState({ runs: [run] })
    useRunStore.getState().selectRun(run.id)
    expect(useChatStore.getState().suggestions).toContain('run-x có bị overfitting không?')
  })

  it('drops the suggestions when the selection is cleared', () => {
    const run = makeRun()
    useRunStore.setState({ runs: [run] })
    useRunStore.getState().selectRun(run.id)
    useRunStore.getState().selectRun(null)
    expect(useChatStore.getState().suggestions).toEqual([])
  })

  it('resets the camera when a filter clears a focus', () => {
    useRunStore.setState({ selectedRunId: 1 })
    useRunStore.getState().setRunFilter(STATUS_FILTER)
    expect(useCameraStore.getState()).toMatchObject({ targetRunId: null, requestId: 1 })
  })

  it('leaves the camera alone when a filter clears nothing', () => {
    useRunStore.getState().setRunFilter(STATUS_FILTER)
    expect(useCameraStore.getState().requestId).toBe(0)
  })

  it('stops reacting once stopped', () => {
    stop()
    useRunStore.setState({ selectedRunId: 1 })
    useRunStore.getState().setRunFilter(STATUS_FILTER)
    expect(useCameraStore.getState().requestId).toBe(0)
  })
})
