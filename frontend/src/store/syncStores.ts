import { suggestQuestions } from '../utils/suggestions'
import { useCameraStore } from './useCameraStore'
import { useChatStore } from './useChatStore'
import { useRunStore } from './useRunStore'

/** Selects a run and flies the camera to it, from the 3D node or the sidebar alike. */
export function focusRun(runId: number) {
  useRunStore.getState().selectRun(runId)
  useCameraStore.getState().setTarget(runId)
}

/** Keeps state that spans several stores consistent. Returns the function that stops it. */
export function startStoreSync(): () => void {
  return useRunStore.subscribe((state, previous) => {
    if (state.selectedRunId !== previous.selectedRunId) {
      const run = state.runs.find((candidate) => candidate.id === state.selectedRunId)
      useChatStore.getState().setSuggestions(run ? suggestQuestions(run, state.runs) : [])
    }

    // Only a filter that cleared a focus moves the camera, so tuning one keeps the user's view.
    const hadFocus = previous.selectedRunId !== null || previous.highlightedRunIds.length > 0
    if (state.runFilter !== previous.runFilter && hadFocus) {
      useCameraStore.getState().setTarget(null)
    }
  })
}
