import { create } from 'zustand'
import type { Experiment, RunSummary } from '../lib/types'
import type { AxisName, AxisSelection } from '../utils/coordinate-mapper'
import { NO_RUN_FILTER, type RunFilter } from '../utils/run-filter'

interface RunState {
  experiments: Experiment[]
  selectedExperimentId: number | null
  runs: RunSummary[]
  selectedRunId: number | null
  highlightedRunIds: number[]
  axisSelection: AxisSelection
  runFilter: RunFilter
  /** Stores the list and keeps the current selection, or falls back to the first experiment. */
  setExperiments: (experiments: Experiment[]) => void
  selectExperiment: (experimentId: number) => void
  setRuns: (runs: RunSummary[]) => void
  selectRun: (runId: number | null) => void
  highlightRuns: (runIds: number[]) => void
  setAxis: (axis: AxisName, key: string | null) => void
  /** Also clears the selection and highlights, which may point at runs the filter hides. */
  setRunFilter: (runFilter: RunFilter) => void
}

export const useRunStore = create<RunState>()((set) => ({
  experiments: [],
  selectedExperimentId: null,
  runs: [],
  selectedRunId: null,
  highlightedRunIds: [],
  axisSelection: {},
  runFilter: NO_RUN_FILTER,

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
            axisSelection: {},
            runFilter: NO_RUN_FILTER,
          },
    ),

  setRuns: (runs) => set({ runs }),
  selectRun: (selectedRunId) => set({ selectedRunId }),
  highlightRuns: (highlightedRunIds) => set({ highlightedRunIds }),
  setAxis: (axis, key) =>
    set((state) => ({ axisSelection: { ...state.axisSelection, [axis]: key } })),
  setRunFilter: (runFilter) => set({ runFilter, selectedRunId: null, highlightedRunIds: [] }),
}))
