import { useState, type FormEvent } from 'react'
import { sendCopilotMessage } from '../../hooks/useCopilot'
import { useChatStore } from '../../store/useChatStore'

export function ChatInput() {
  const isLoading = useChatStore((state) => state.streamingMessageId !== null)
  const [draft, setDraft] = useState('')

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    const question = draft.trim()
    if (!question || isLoading) return
    setDraft('')
    void sendCopilotMessage(question)
  }

  return (
    <form onSubmit={handleSubmit} className="mt-3 flex gap-2">
      <input
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        maxLength={4000}
        aria-label="Câu hỏi cho trợ lý AI"
        placeholder="Run nào tốt nhất?"
        className="min-w-0 flex-1 rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm placeholder:text-slate-500"
      />
      <button
        type="submit"
        disabled={isLoading || draft.trim() === ''}
        className="flex w-12 items-center justify-center rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500"
      >
        {isLoading ? (
          <span
            role="status"
            aria-label="Đang trả lời"
            className="h-5 w-5 animate-spin rounded-full border-2 border-slate-600 border-t-slate-200"
          />
        ) : (
          'Gửi'
        )}
      </button>
    </form>
  )
}
