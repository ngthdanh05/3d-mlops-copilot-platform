import type { RunStatus, RunSummary } from '../lib/types'
import { colorMetric } from './color-utils'

export interface RunFilter {
  status: RunStatus | null
  minAccuracy: number
  maxAccuracy: number
}

export const NO_RUN_FILTER: RunFilter = { status: null, minAccuracy: 0, maxAccuracy: 1 }

function limitsAccuracy(filter: RunFilter): boolean {
  return (
    filter.minAccuracy > NO_RUN_FILTER.minAccuracy ||
    filter.maxAccuracy < NO_RUN_FILTER.maxAccuracy
  )
}

export function isRunFilterActive(filter: RunFilter): boolean {
  return filter.status !== null || limitsAccuracy(filter)
}

export function matchesRunName(run: RunSummary, query: string): boolean {
  return run.run_name.toLowerCase().includes(query.trim().toLowerCase())
}

/** Uses the metric the scene colors by. Runs without one only match a full accuracy range. */
export function matchesRunFilter(run: RunSummary, filter: RunFilter): boolean {
  if (filter.status !== null && run.status !== filter.status) return false
  if (!limitsAccuracy(filter)) return true
  const accuracy = colorMetric(run)
  return accuracy !== null && accuracy >= filter.minAccuracy && accuracy <= filter.maxAccuracy
}
