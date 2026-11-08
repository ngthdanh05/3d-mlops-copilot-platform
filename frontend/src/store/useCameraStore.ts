import { create } from 'zustand'

interface CameraState {
  targetRunId: number | null
  /** Bumped on every request, so asking to fly to the same run again still fires. */
  requestId: number
  setTarget: (runId: number | null) => void
}

export const useCameraStore = create<CameraState>()((set) => ({
  targetRunId: null,
  requestId: 0,
  setTarget: (targetRunId) => set((state) => ({ targetRunId, requestId: state.requestId + 1 })),
}))
