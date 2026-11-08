import { useChatStore } from '../../store/useChatStore'

export function ChatPanel() {
  const messages = useChatStore((state) => state.messages)

  return (
    <section
      aria-label="Trợ lý AI"
      className="flex min-h-72 flex-1 flex-col border-t border-slate-800 p-4"
    >
      <h2 className="text-xs font-medium uppercase text-slate-400">Trợ lý AI</h2>
      <div className="mt-3 flex-1 space-y-2 overflow-y-auto text-sm">
        {messages.map((message) => (
          <p key={message.id} className={message.role === 'user' ? 'text-right' : undefined}>
            {message.content}
          </p>
        ))}
      </div>
      <input
        disabled
        aria-label="Câu hỏi cho trợ lý AI"
        placeholder="Trợ lý AI chưa sẵn sàng"
        className="mt-3 rounded border border-slate-800 bg-slate-900 px-3 py-2 text-sm placeholder:text-slate-500 disabled:cursor-not-allowed"
      />
    </section>
  )
}
