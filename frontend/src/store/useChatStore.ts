import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ChatMessage } from '../lib/types'

const MAX_SAVED_MESSAGES = 100

interface ChatState {
  messages: ChatMessage[]
  /** The answer being written. Non-null means the chat is busy. */
  streamingMessageId: string | null
  suggestions: string[]
  addMessage: (message: ChatMessage) => void
  appendToMessage: (id: string, text: string) => void
  setMessageContent: (id: string, content: string) => void
  failMessage: (id: string, content: string) => void
  /** Drops the last question and its answer. */
  removeLastExchange: () => void
  setStreamingMessageId: (id: string | null) => void
  setSuggestions: (suggestions: string[]) => void
  clearMessages: () => void
}

function updateMessage(
  messages: ChatMessage[],
  id: string,
  content: (current: string) => string,
): ChatMessage[] {
  return messages.map((m) => (m.id === id ? { ...m, content: content(m.content) } : m))
}

const MESSAGES_PER_EXCHANGE = 2

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      messages: [],
      streamingMessageId: null,
      suggestions: [],
      addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
      appendToMessage: (id, text) =>
        set((state) => ({
          messages: updateMessage(state.messages, id, (current) => current + text),
        })),
      setMessageContent: (id, content) =>
        set((state) => ({ messages: updateMessage(state.messages, id, () => content) })),
      failMessage: (id, content) =>
        set((state) => ({
          messages: state.messages.map((m) => (m.id === id ? { ...m, content, failed: true } : m)),
        })),
      removeLastExchange: () =>
        set((state) => ({ messages: state.messages.slice(0, -MESSAGES_PER_EXCHANGE) })),
      setStreamingMessageId: (streamingMessageId) => set({ streamingMessageId }),
      setSuggestions: (suggestions) => set({ suggestions }),
      clearMessages: () => set({ messages: [] }),
    }),
    {
      name: 'copilot-chat',
      version: 1,
      // An unfinished answer is left out: after a refresh nothing would ever complete it.
      partialize: (state) => ({
        messages: state.messages
          .filter((message) => message.id !== state.streamingMessageId)
          .slice(-MAX_SAVED_MESSAGES),
      }),
    },
  ),
)
