import { describe, expect, it } from 'vitest'
import { makeRun } from '../test/make-run'
import { isRunFilterActive, matchesRunFilter, matchesRunName, NO_RUN_FILTER } from './run-filter'

describe('matchesRunName', () => {
  it('ignores case and surrounding spaces', () => {
    expect(matchesRunName(makeRun({ run_name: 'Run-007' }), '  run-00 ')).toBe(true)
  })

  it('rejects another name', () => {
    expect(matchesRunName(makeRun({ run_name: 'run-007' }), 'run-8')).toBe(false)
  })
})

describe('isRunFilterActive', () => {
  it('is off for the empty filter', () => {
    expect(isRunFilterActive(NO_RUN_FILTER)).toBe(false)
  })

  it.each([[{ status: 'failed' as const }], [{ minAccuracy: 0.1 }], [{ maxAccuracy: 0.9 }]])(
    'is on for %j',
    (change) => {
      expect(isRunFilterActive({ ...NO_RUN_FILTER, ...change })).toBe(true)
    },
  )
})

describe('matchesRunFilter', () => {
  it('keeps every run under the empty filter, even one without metrics', () => {
    const run = makeRun({ final_val_accuracy: null, final_accuracy: null })
    expect(matchesRunFilter(run, NO_RUN_FILTER)).toBe(true)
  })

  it('filters by status', () => {
    const filter = { ...NO_RUN_FILTER, status: 'failed' as const }
    expect(matchesRunFilter(makeRun({ status: 'failed' }), filter)).toBe(true)
    expect(matchesRunFilter(makeRun({ status: 'completed' }), filter)).toBe(false)
  })

  it('includes both ends of the accuracy range', () => {
    const filter = { ...NO_RUN_FILTER, minAccuracy: 0.5, maxAccuracy: 0.8 }
    expect(matchesRunFilter(makeRun({ final_val_accuracy: 0.5 }), filter)).toBe(true)
    expect(matchesRunFilter(makeRun({ final_val_accuracy: 0.8 }), filter)).toBe(true)
    expect(matchesRunFilter(makeRun({ final_val_accuracy: 0.81 }), filter)).toBe(false)
    expect(matchesRunFilter(makeRun({ final_val_accuracy: 0.49 }), filter)).toBe(false)
  })

  it('drops a run without metrics once accuracy is limited', () => {
    const run = makeRun({ final_val_accuracy: null, final_accuracy: null })
    expect(matchesRunFilter(run, { ...NO_RUN_FILTER, minAccuracy: 0.1 })).toBe(false)
  })
})
