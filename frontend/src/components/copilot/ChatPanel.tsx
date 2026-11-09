import { useEffect, useRef } from 'react'
import { useChatStore } from '../../store/useChatStore'
import { ChatInput } from './ChatInput'
import { ChatMessage } from './ChatMessage'

export function ChatPanel() {
  const messages = useChatStore((state) => state.messages)
  const historyRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const history = historyRef.current
    if (history) history.scrollTop = history.scrollHeight
  }, [messages])

  return (
    <section
      aria-label="Trợ lý AI"
      className="flex min-h-72 flex-1 flex-col border-t border-slate-800 p-4"
    >
      <h2 className="text-xs font-medium uppercase text-slate-400">Trợ lý AI</h2>
      <div ref={historyRef} className="mt-3 min-h-0 flex-1 space-y-2 overflow-y-auto text-sm">
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
      </div>
      <ChatInput />
    </section>
  )
}
