import { useEffect, useRef } from 'react'
import { useChatStore } from '../../store/useChatStore'
import { ChatInput } from './ChatInput'
import { ChatMessage } from './ChatMessage'
import { ChatSuggestions } from './ChatSuggestions'
import useSWR from 'swr'

async function fetchStatus() {
  const response = await fetch('/api/copilot/status')
  if (!response.ok) throw new Error('Status unavailable')
  return response.json() as Promise<{
    provider: string; model: string | null; available: boolean; offline: boolean
  }>
}

export function ChatPanel() {
  const messages = useChatStore((state) => state.messages)
  const isBusy = useChatStore((state) => state.streamingMessageId !== null)
  const clearMessages = useChatStore((state) => state.clearMessages)
  const historyRef = useRef<HTMLDivElement>(null)
  const saveHistory = useChatStore((state) => state.saveHistory)
  const setSaveHistory = useChatStore((state) => state.setSaveHistory)
  const status = useSWR('copilot-status', fetchStatus, { refreshInterval: 15000,
    refreshWhenHidden: false, refreshWhenOffline: true, shouldRetryOnError: false })

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
      <p className="mt-2 text-xs text-slate-400">
        {status.data ? `${status.data.provider} ${status.data.model ?? ''} · ${status.data.available ? 'sẵn sàng' : 'chưa xác minh khả dụng'} · ${status.data.offline ? 'offline' : 'cho phép cloud'}` : 'Chưa lấy được trạng thái AI'}
      </p>
      <label className="mt-2 text-xs text-slate-400">
        <input type="checkbox" checked={saveHistory}
          onChange={(event) => setSaveHistory(event.target.checked)} /> Lưu lịch sử trên trình duyệt
      </label>
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
