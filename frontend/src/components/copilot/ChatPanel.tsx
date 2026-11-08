import { useEffect, useRef, useState, type FormEvent } from 'react'
import { sendCopilotMessage } from '../../hooks/useCopilot'
import { useChatStore } from '../../store/useChatStore'

export function ChatPanel() {
  const messages = useChatStore((state) => state.messages)
  const isLoading = useChatStore((state) => state.isLoading)
  const [draft, setDraft] = useState('')
  const historyRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const history = historyRef.current
    if (history) history.scrollTop = history.scrollHeight
  }, [messages, isLoading])

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    const question = draft.trim()
    if (!question || isLoading) return
    setDraft('')
    void sendCopilotMessage(question)
  }

  return (
    <section
      aria-label="Trợ lý AI"
      className="flex min-h-72 flex-1 flex-col border-t border-slate-800 p-4"
    >
      <h2 className="text-xs font-medium uppercase text-slate-400">Trợ lý AI</h2>
      <div ref={historyRef} className="mt-3 min-h-0 flex-1 space-y-2 overflow-y-auto text-sm">
        {messages.map((message) => (
          <p
            key={message.id}
            className={`whitespace-pre-wrap rounded px-3 py-2 ${
              message.role === 'user' ? 'ml-8 bg-slate-800 text-slate-100' : 'mr-8 text-slate-200'
            }`}
          >
            {message.content}
          </p>
        ))}
        {isLoading && (
          <p role="status" className="px-3 py-2 text-slate-400">
            Đang trả lời...
          </p>
        )}
      </div>
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
          className="rounded bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500"
        >
          Gửi
        </button>
      </form>
    </section>
  )
}
