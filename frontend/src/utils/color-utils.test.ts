import { describe, expect, it } from 'vitest'
import { makeRun } from '../test/make-run'
import { colorAt, colorMetric, COLOR_STOPS, encodeRuns, NO_METRIC_COLOR } from './color-utils'

describe('colorAt', () => {
  it('returns the stops at 0, 0.5 and 1', () => {
    expect([colorAt(0), colorAt(0.5), colorAt(1)]).toEqual([...COLOR_STOPS])
  })

  it('clamps values outside 0..1', () => {
    expect(colorAt(-3)).toBe(COLOR_STOPS[0])
    expect(colorAt(3)).toBe(COLOR_STOPS[2])
  })

  it('mixes neighboring stops', () => {
    expect(colorAt(0.25)).toBe('#4384f3')
  })
})

describe('colorMetric', () => {
  it('prefers validation accuracy', () => {
    expect(colorMetric(makeRun({ final_val_accuracy: 0.8, final_accuracy: 0.9 }))).toBe(0.8)
  })

  it('falls back to training accuracy', () => {
    expect(colorMetric(makeRun({ final_val_accuracy: null, final_accuracy: 0.9 }))).toBe(0.9)
  })
})

describe('encodeRuns', () => {
  it('gives the best run the top color and the worst the bottom one', () => {
    const worst = makeRun({ final_val_accuracy: 0.5 })
    const best = makeRun({ final_val_accuracy: 0.9 })
    const { byRunId } = encodeRuns([worst, best])
    expect(byRunId.get(best.id)?.color).toBe(COLOR_STOPS[2])
    expect(byRunId.get(worst.id)?.color).toBe(COLOR_STOPS[0])
  })

  it('makes a low loss bigger than a high loss', () => {
    const low = makeRun({ final_val_loss: 0.1 })
    const high = makeRun({ final_val_loss: 0.9 })
    const { byRunId } = encodeRuns([low, high])
    expect(byRunId.get(low.id)?.radius).toBe(0.5)
    expect(byRunId.get(high.id)?.radius).toBeCloseTo(0.15)
  })

  it('maps a single run to the middle of both scales', () => {
    const run = makeRun()
    expect(encodeRuns([run]).byRunId.get(run.id)).toEqual({ color: COLOR_STOPS[1], radius: 0.325 })
  })

  it('does not let one diverged run squeeze the healthy ones', () => {
    const healthy = [0.9, 0.91, 0.92, 0.93, 0.94].map((v) => makeRun({ final_val_accuracy: v }))
    const diverged = makeRun({ final_val_accuracy: 0.1 })
    const { byRunId, legend } = encodeRuns([...healthy, diverged])

    expect(legend?.min).toBe(0.9)
    expect(legend?.isClippedLow).toBe(true)
    expect(byRunId.get(diverged.id)?.color).toBe(COLOR_STOPS[0])
    expect(byRunId.get(healthy[4].id)?.color).toBe(COLOR_STOPS[2])
  })

  it('takes the domain from completed runs only', () => {
    const completed = [0.8, 0.9].map((v) => makeRun({ final_val_accuracy: v }))
    const running = makeRun({ status: 'running', final_val_accuracy: 0.2 })
    expect(encodeRuns([...completed, running]).legend).toMatchObject({ min: 0.8, max: 0.9 })
  })

  it('uses every run while none has completed', () => {
    const runs = [0.2, 0.4].map((v) => makeRun({ status: 'running', final_val_accuracy: v }))
    expect(encodeRuns(runs).legend).toMatchObject({ min: 0.2, max: 0.4 })
  })

  it('draws a run without metrics in neutral gray', () => {
    const run = makeRun({
      status: 'running',
      final_accuracy: null,
      final_val_accuracy: null,
      final_loss: null,
      final_val_loss: null,
    })
    const { byRunId, legend } = encodeRuns([run])
    expect(byRunId.get(run.id)).toEqual({ color: NO_METRIC_COLOR, radius: 0.2 })
    expect(legend).toBeNull()
  })

  it('labels the legend after the metric in use', () => {
    expect(encodeRuns([makeRun()]).legend?.label).toBe('val_accuracy')
    expect(encodeRuns([makeRun({ final_val_accuracy: null })]).legend?.label).toBe('accuracy')
  })
})
