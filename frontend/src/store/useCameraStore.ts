import { create } from 'zustand'

interface CameraState {
  targetRunId: number | null
  setTarget: (runId: number | null) => void
}

export const useCameraStore = create<CameraState>()((set) => ({
  targetRunId: null,
  setTarget: (targetRunId) => set({ targetRunId }),
}))
