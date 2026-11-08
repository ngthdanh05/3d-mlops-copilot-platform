import { useEffect } from 'react'
import useSWR from 'swr'
import { fetchExperiments, fetchRuns } from '../lib/api'
import { useRunStore } from '../store/useRunStore'

/**
 * Loads experiments and the selected experiment's runs into `useRunStore`.
 * Call it once, in `Workspace`. Panels read the data from the store.
 */
export function useRuns() {
  const selectedExperimentId = useRunStore((state) => state.selectedExperimentId)
  const setExperiments = useRunStore((state) => state.setExperiments)
  const setRuns = useRunStore((state) => state.setRuns)

  const experiments = useSWR('experiments', fetchExperiments)
  const runs = useSWR(selectedExperimentId === null ? null : ['runs', selectedExperimentId], () =>
    fetchRuns(selectedExperimentId as number),
  )

  useEffect(() => {
    if (experiments.data) setExperiments(experiments.data)
  }, [experiments.data, setExperiments])

  useEffect(() => {
    if (runs.data) setRuns(runs.data)
  }, [runs.data, setRuns])

  return {
    isLoading: experiments.isLoading || runs.isLoading,
    hasError: Boolean(experiments.error || runs.error),
  }
}
