import type { Experiment, RunDetail, RunSummary } from './types'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) {
    throw new ApiError(response.status, `GET ${path} failed with ${response.status}`)
  }
  return response.json() as Promise<T>
}

export function fetchExperiments(): Promise<Experiment[]> {
  return getJson('/api/experiments')
}

export function fetchRuns(experimentId: number): Promise<RunSummary[]> {
  return getJson(`/api/runs?experiment_id=${experimentId}`)
}

export function fetchRunDetail(runId: number): Promise<RunDetail> {
  return getJson(`/api/runs/${runId}`)
}
