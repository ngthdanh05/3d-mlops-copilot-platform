import { streamCopilotChat } from '../lib/api'
import type { ChatMessage, CopilotAction, CopilotStreamEvent } from '../lib/types'
import { useCameraStore } from '../store/useCameraStore'
import { useChatStore } from '../store/useChatStore'
import { useRunStore } from '../store/useRunStore'
import { matchesRunFilter, NO_RUN_FILTER } from '../utils/run-filter'

const SEND_FAILED_MESSAGE = 'Không gửi được câu hỏi. Hãy kiểm tra backend rồi thử lại.'

function actionRunIds(action: CopilotAction): number[] {
  return action.type === 'highlight_runs' ? action.run_ids : [action.run_id]
}

/** A run the AI points at must be on screen, or its highlight and camera move show nothing. */
function revealRuns(runIds: number[]) {
  const { runs, runFilter, setRunFilter } = useRunStore.getState()
  const isHidden = runs.some((run) => runIds.includes(run.id) && !matchesRunFilter(run, runFilter))
  if (isHidden) setRunFilter(NO_RUN_FILTER)
}

/** AI actions change the UI only through the stores, never the scene directly. */
function applyActions(actions: CopilotAction[]) {
  revealRuns(actions.flatMap(actionRunIds))
  const { highlightRuns, selectRun } = useRunStore.getState()
  const { setTarget } = useCameraStore.getState()
  for (const action of actions) {
    switch (action.type) {
      case 'highlight_runs':
        highlightRuns(action.run_ids)
        break
      case 'focus_camera':
        setTarget(action.run_id)
        break
      case 'open_inspector':
        selectRun(action.run_id)
        break
    }
  }
}

function newMessage(role: ChatMessage['role'], content: string): ChatMessage {
  return { id: crypto.randomUUID(), role, content }
}

export async function sendCopilotMessage(content: string) {
  const chat = useChatStore.getState()
  if (chat.streamingMessageId !== null) return

  const { selectedExperimentId, highlightRuns } = useRunStore.getState()
  const answer = newMessage('assistant', '')
  chat.addMessage(newMessage('user', content))
  chat.setSuggestions([])
  highlightRuns([])
  chat.addMessage(answer)
  chat.setStreamingMessageId(answer.id)

  let isFinished = false
  const handleEvent = (event: CopilotStreamEvent) => {
    switch (event.type) {
      case 'delta':
        chat.appendToMessage(answer.id, event.text)
        break
      case 'reset':
        chat.setMessageContent(answer.id, '')
        break
      case 'done':
        isFinished = true
        chat.setMessageContent(answer.id, event.message)
        applyActions(event.actions)
        break
    }
  }

  // A stream that fails after `done` already delivered its answer, so only `done` decides.
  await streamCopilotChat(content, selectedExperimentId, handleEvent).catch(() => undefined)
  if (!isFinished) chat.failMessage(answer.id, SEND_FAILED_MESSAGE)
  chat.setStreamingMessageId(null)
}

/** Sends the last question again, replacing its failed answer. */
export function retryLastQuestion() {
  const { messages, streamingMessageId, removeLastExchange } = useChatStore.getState()
  const answer = messages[messages.length - 1]
  const question = messages[messages.length - 2]
  if (streamingMessageId !== null || !answer?.failed || question?.role !== 'user') return
  removeLastExchange()
  void sendCopilotMessage(question.content)
}
