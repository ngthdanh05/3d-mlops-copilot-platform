import { useEffect, useRef } from 'react'
import { useChatStore } from '../../store/useChatStore'
import { ChatInput } from './ChatInput'
import { ChatMessage } from './ChatMessage'
import { ChatSuggestions } from './ChatSuggestions'

export function ChatPanel() {
  const messages = useChatStore((state) => state.messages)
  const isBusy = useChatStore((state) => state.streamingMessageId !== null)
  const clearMessages = useChatStore((state) => state.clearMessages)
  const historyRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const history = historyRef.current
    if (history) history.scrollTop = history.scrollHeight
  }, [messages])

  return (
    <section
      aria-label="Trợ lý AI"
      className="flex min-h-72 flex-1 flex-col border-slate-800 p-4 lg:border-t"
    >
      <div className="flex items-center justify-between">
        <h2 className="hidden text-xs font-medium uppercase text-slate-400 lg:block">Trợ lý AI</h2>
        {messages.length > 0 && (
          <button
            type="button"
            disabled={isBusy}
            onClick={clearMessages}
            className="ml-auto text-xs text-slate-400 underline hover:text-white disabled:cursor-not-allowed disabled:text-slate-600"
          >
            Xoá lịch sử
          </button>
        )}
      </div>
      <div
        ref={historyRef}
        className="mt-3 max-h-96 min-h-0 flex-1 space-y-2 overflow-y-auto text-sm lg:max-h-none"
      >
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
      </div>
      <ChatSuggestions />
      <ChatInput />
    </section>
  )
}
