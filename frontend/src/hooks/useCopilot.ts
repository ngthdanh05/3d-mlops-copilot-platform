import { postCopilotChat } from '../lib/api'
import type { ChatMessage, CopilotAction } from '../lib/types'
import { useCameraStore } from '../store/useCameraStore'
import { useChatStore } from '../store/useChatStore'
import { useRunStore } from '../store/useRunStore'

/** AI actions change the UI only through the stores, never the scene directly. */
function applyActions(actions: CopilotAction[]) {
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
  const { isLoading, addMessage, setLoading } = useChatStore.getState()
  if (isLoading) return

  const { selectedExperimentId, highlightRuns } = useRunStore.getState()
  addMessage(newMessage('user', content))
  highlightRuns([])
  setLoading(true)
  try {
    const response = await postCopilotChat(content, selectedExperimentId)
    addMessage(newMessage('assistant', response.message))
    applyActions(response.actions)
  } catch {
    addMessage(newMessage('assistant', 'Không gửi được câu hỏi. Hãy kiểm tra backend rồi thử lại.'))
  } finally {
    setLoading(false)
  }
}
