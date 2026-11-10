import type { RunSummary } from '../lib/types'

let nextId = 1

export function makeRun(overrides: Partial<RunSummary> = {}): RunSummary {
  const id = overrides.id ?? nextId++
  return {
    id,
    experiment_id: 1,
    run_name: `run-${id}`,
    status: 'completed',
    hyperparams: {},
    created_at: '2026-11-01T00:00:00Z',
    finished_at: '2026-11-01T00:10:00Z',
    final_epoch: 10,
    final_accuracy: 0.9,
    final_loss: 0.3,
    final_val_accuracy: 0.85,
    final_val_loss: 0.4,
    ...overrides,
  }
}
