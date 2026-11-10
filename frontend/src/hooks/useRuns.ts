import { useEffect } from 'react'
import useSWR from 'swr'
import { fetchExperiments, fetchRuns } from '../lib/api'
import { useRunStore } from '../store/useRunStore'

/** The user retries with a button, so SWR need not keep hitting a server that is down. */
const SWR_OPTIONS = { shouldRetryOnError: false }

/** 1: fetching experiments, 2: fetching runs. */
export type LoadStep = 1 | 2

/**
 * Loads experiments and the selected experiment's runs into `useRunStore`.
 * Call it once, in `Workspace`. Panels read the data from the store.
 */
export function useRuns() {
  const selectedExperimentId = useRunStore((state) => state.selectedExperimentId)
  const hasRunsInStore = useRunStore((state) => state.runs.length > 0)
  const setExperiments = useRunStore((state) => state.setExperiments)
  const setRuns = useRunStore((state) => state.setRuns)

  const experiments = useSWR('experiments', fetchExperiments, SWR_OPTIONS)
  const runs = useSWR(
    selectedExperimentId === null ? null : ['runs', selectedExperimentId],
    () => fetchRuns(selectedExperimentId as number),
    SWR_OPTIONS,
  )

  useEffect(() => {
    if (experiments.data) setExperiments(experiments.data)
  }, [experiments.data, setExperiments])

  useEffect(() => {
    if (runs.data) setRuns(runs.data)
  }, [runs.data, setRuns])

  const hasError = Boolean(experiments.error || runs.error)
  // The second half of each check covers the render before the effects above copy the data.
  const isFetchingExperiments =
    experiments.isLoading || (Boolean(experiments.data?.length) && selectedExperimentId === null)
  const isFetchingRuns = runs.isLoading || (Boolean(runs.data?.length) && !hasRunsInStore)

  let loadStep: LoadStep | null = null
  if (!hasError && isFetchingExperiments) loadStep = 1
  else if (!hasError && isFetchingRuns) loadStep = 2

  return {
    loadStep,
    hasError,
    isRetrying: experiments.isValidating || runs.isValidating,
    retry: () => {
      void experiments.mutate()
      void runs.mutate()
    },
  }
}
