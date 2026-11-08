import { create } from 'zustand'
import type { ChatMessage } from '../lib/types'

interface ChatState {
  messages: ChatMessage[]
  isLoading: boolean
  addMessage: (message: ChatMessage) => void
  setLoading: (isLoading: boolean) => void
}

export const useChatStore = create<ChatState>()((set) => ({
  messages: [],
  isLoading: false,
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  setLoading: (isLoading) => set({ isLoading }),
}))
