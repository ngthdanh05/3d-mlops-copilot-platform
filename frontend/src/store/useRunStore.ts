import { create } from 'zustand'
import type { Experiment, RunSummary } from '../lib/types'

interface RunState {
  experiments: Experiment[]
  selectedExperimentId: number | null
  runs: RunSummary[]
  selectedRunId: number | null
  highlightedRunIds: number[]
  /** Stores the list and keeps the current selection, or falls back to the first experiment. */
  setExperiments: (experiments: Experiment[]) => void
  selectExperiment: (experimentId: number) => void
  setRuns: (runs: RunSummary[]) => void
  selectRun: (runId: number | null) => void
  highlightRuns: (runIds: number[]) => void
}

export const useRunStore = create<RunState>()((set) => ({
  experiments: [],
  selectedExperimentId: null,
  runs: [],
  selectedRunId: null,
  highlightedRunIds: [],

  setExperiments: (experiments) =>
    set((state) => ({
      experiments,
      selectedExperimentId: experiments.some((e) => e.id === state.selectedExperimentId)
        ? state.selectedExperimentId
        : (experiments[0]?.id ?? null),
    })),

  selectExperiment: (experimentId) =>
    set((state) =>
      state.selectedExperimentId === experimentId
        ? state
        : {
            selectedExperimentId: experimentId,
            runs: [],
            selectedRunId: null,
            highlightedRunIds: [],
          },
    ),

  setRuns: (runs) => set({ runs }),
  selectRun: (selectedRunId) => set({ selectedRunId }),
  highlightRuns: (highlightedRunIds) => set({ highlightedRunIds }),
}))
