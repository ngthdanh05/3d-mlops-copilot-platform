import { describe, expect, it } from 'vitest'
import { makeRun } from '../test/make-run'
import {
  axisTicks,
  formatNumber,
  isEpochAccuracyLossTrio,
  layoutRuns,
  SCENE_SIZE,
  UNKNOWN_POSITION,
  type Axis,
} from './coordinate-mapper'

const params = (learning_rate: number, batch_size: number, extra = {}) =>
  makeRun({ hyperparams: { learning_rate, batch_size, ...extra } })

describe('layoutRuns positions', () => {
  it('spreads the learning rate on a log10 scale', () => {
    const { nodes, x } = layoutRuns([params(1e-4, 32), params(1e-3, 32), params(1e-2, 32)])
    expect(x.scale).toBe('log10')
    expect(nodes[0].position[0]).toBeCloseTo(0)
    expect(nodes[1].position[0]).toBeCloseTo(SCENE_SIZE / 2)
    expect(nodes[2].position[0]).toBeCloseTo(SCENE_SIZE)
  })

  it('spreads the batch size on a log2 scale', () => {
    const { nodes, y } = layoutRuns([params(1e-3, 16), params(1e-3, 64), params(1e-3, 256)])
    expect(y.scale).toBe('log2')
    expect(nodes.map((node) => node.position[1])).toEqual([0, SCENE_SIZE / 2, SCENE_SIZE])
  })

  it('centers an axis on which every run has the same value', () => {
    const { nodes } = layoutRuns([params(1e-3, 32), params(1e-3, 64)])
    expect(nodes[0].position[0]).toBe(SCENE_SIZE / 2)
  })

  it('puts a run missing an axis key off the grid', () => {
    const missing = makeRun({ hyperparams: { batch_size: 32 } })
    const { nodes, x } = layoutRuns([params(1e-3, 64), missing])
    expect(x.hasMissing).toBe(true)
    expect(nodes[1].position[0]).toBe(UNKNOWN_POSITION)
    expect(nodes[1].isOffGrid).toBe(true)
    expect(nodes[0].isOffGrid).toBe(false)
  })

  it.each([0, -0.1])('treats %d as unusable on a log axis', (value) => {
    const { nodes } = layoutRuns([params(1e-3, 32), params(value, 32)])
    expect(nodes[1].position[0]).toBe(UNKNOWN_POSITION)
    expect(nodes[1].isOffGrid).toBe(true)
  })

  it('treats a non-numeric value as missing', () => {
    const text = makeRun({ hyperparams: { learning_rate: 'high', batch_size: 32 } })
    const { nodes } = layoutRuns([params(1e-3, 64), text])
    expect(nodes[1].position[0]).toBe(UNKNOWN_POSITION)
  })

  it('places accuracy 0 at the start of a metric axis', () => {
    const runs = [0, 0.5, 1].map((final_accuracy) =>
      makeRun({ final_accuracy, hyperparams: { batch_size: 32 } }),
    )
    const { nodes } = layoutRuns(runs, { x: 'final_accuracy' })
    expect(nodes.map((node) => node.position[0])).toEqual([0, SCENE_SIZE / 2, SCENE_SIZE])
    expect(nodes[0].isOffGrid).toBe(false)
  })

  it('places the largest loss at the end of a metric axis, even a huge one', () => {
    const runs = [0, 1e6].map((final_loss) => makeRun({ final_loss }))
    const { nodes } = layoutRuns(runs, { y: 'final_loss' })
    expect(nodes[0].position[1]).toBe(0)
    expect(nodes[1].position[1]).toBe(SCENE_SIZE)
  })

  it('centers a metric axis when every run has accuracy 0', () => {
    const runs = [makeRun({ final_accuracy: 0 }), makeRun({ final_accuracy: 0 })]
    const { nodes } = layoutRuns(runs, { x: 'final_accuracy' })
    expect(nodes[0].position[0]).toBe(SCENE_SIZE / 2)
  })

  it('puts a run without metrics off the grid of a metric axis', () => {
    const runs = [makeRun({ final_accuracy: 0.9 }), makeRun({ final_accuracy: null })]
    const { nodes } = layoutRuns(runs, { x: 'final_accuracy' })
    expect(nodes[1].position[0]).toBe(UNKNOWN_POSITION)
  })

  it('reads a final metric instead of a hyperparameter of the same name', () => {
    const run = makeRun({ final_accuracy: 0.7, hyperparams: { final_accuracy: 'ignored' } })
    const { options, x } = layoutRuns([run], { x: 'final_accuracy' })
    expect(x.min).toBe(0.7)
    expect(options.hyperparams).not.toContain('final_accuracy')
  })

  it('handles no runs at all', () => {
    const layout = layoutRuns([])
    expect(layout.nodes).toEqual([])
    expect(layout.z).toBeNull()
    expect(layout.x.min).toBeNull()
    expect(layout.options).toEqual({ hyperparams: [], metrics: [] })
  })
})

describe('layoutRuns axis choice', () => {
  it('prefers dropout for Z', () => {
    const runs = [
      params(1e-3, 32, { dropout: 0.1, epochs: 5 }),
      params(1e-3, 32, { dropout: 0.5, epochs: 9 }),
    ]
    expect(layoutRuns(runs).z?.key).toBe('dropout')
  })

  it('falls back to epochs when dropout does not vary', () => {
    const runs = [
      params(1e-3, 32, { dropout: 0.1, epochs: 5 }),
      params(1e-3, 32, { dropout: 0.1, epochs: 9 }),
    ]
    expect(layoutRuns(runs).z?.key).toBe('epochs')
  })

  it('then takes the first other key that varies, alphabetically', () => {
    const runs = [
      params(1e-3, 32, { width: 1, momentum: 0.1, seed: 7 }),
      params(1e-3, 32, { width: 2, momentum: 0.9, seed: 7 }),
    ]
    expect(layoutRuns(runs).z?.key).toBe('momentum')
  })

  it('keeps the scene flat when nothing varies', () => {
    const runs = [params(1e-3, 32, { dropout: 0.1 }), params(1e-2, 32, { dropout: 0.1 })]
    const { z, nodes } = layoutRuns(runs)
    expect(z).toBeNull()
    expect(nodes[0].position[2]).toBe(SCENE_SIZE / 2)
  })

  it('honors a Z axis the user turned off', () => {
    const runs = [params(1e-3, 32, { dropout: 0.1 }), params(1e-3, 32, { dropout: 0.5 })]
    expect(layoutRuns(runs, { z: null }).z).toBeNull()
  })

  it('uses the default for a selected key the runs no longer have', () => {
    expect(layoutRuns([params(1e-3, 32)], { x: 'gone' }).x.key).toBe('learning_rate')
  })

  it('lists only numeric keys as options', () => {
    const run = params(1e-3, 32, { optimizer: 'adam', hidden_layers: [64, 32] })
    expect(layoutRuns([run]).options.hyperparams).toEqual(['batch_size', 'learning_rate'])
  })

  it('reports a key used on two axes once', () => {
    const runs = [params(1e-3, 32), params(1e-2, 64)]
    const selection = { x: 'learning_rate', y: 'learning_rate', z: null }
    expect(layoutRuns(runs, selection).axisKeys).toEqual(['learning_rate'])
  })
})

describe('isEpochAccuracyLossTrio', () => {
  it('spots the trio that collapses runs onto a line', () => {
    expect(isEpochAccuracyLossTrio(['epochs', 'final_val_accuracy', 'final_loss'])).toBe(true)
  })

  it.each([
    [['epochs', 'final_accuracy', 'final_val_accuracy']],
    [['learning_rate', 'final_accuracy', 'final_loss']],
  ])('accepts %j', (keys) => {
    expect(isEpochAccuracyLossTrio(keys)).toBe(false)
  })
})

describe('formatNumber', () => {
  it.each([
    [0.00043219, '0.000432'],
    [256, '256'],
    [0.1, '0.1'],
    [0, '0'],
  ])('formats %d as %s', (value, text) => {
    expect(formatNumber(value)).toBe(text)
  })

  it('takes a precision', () => {
    expect(formatNumber(1.23456, 5)).toBe('1.2346')
  })
})

describe('axisTicks', () => {
  const axis = (overrides: Partial<Axis>): Axis => ({
    key: 'k',
    scale: 'linear',
    min: 0,
    max: 1,
    hasMissing: false,
    ...overrides,
  })

  it('marks five even ticks on a linear axis', () => {
    const ticks = axisTicks(axis({}))
    expect(ticks.map((tick) => tick.label)).toEqual(['0', '0.25', '0.5', '0.75', '1'])
    expect(ticks[4].position).toBe(SCENE_SIZE)
  })

  it('marks whole powers on a log axis', () => {
    const ticks = axisTicks(axis({ scale: 'log10', min: -4, max: -2 }))
    expect(ticks.map((tick) => tick.label)).toEqual(['0.0001', '0.001', '0.01'])
  })

  it('marks both ends of a log axis spanning less than two powers', () => {
    const ticks = axisTicks(axis({ scale: 'log2', min: 4.5, max: 5.5 }))
    expect(ticks).toHaveLength(2)
    expect(ticks[0].position).toBe(0)
    expect(ticks[1].position).toBe(SCENE_SIZE)
  })

  it('marks one centered tick when the axis has one value', () => {
    expect(axisTicks(axis({ min: 0.5, max: 0.5 }))).toEqual([
      { label: '0.5', position: SCENE_SIZE / 2 },
    ])
  })

  it('adds digits until the labels of a narrow range differ', () => {
    const labels = axisTicks(axis({ min: 0.98101, max: 0.98109 })).map((tick) => tick.label)
    expect(new Set(labels).size).toBe(5)
  })

  it('has no ticks without data', () => {
    expect(axisTicks(axis({ min: null, max: null }))).toEqual([])
  })

  it('adds a tick for the runs off the grid', () => {
    expect(axisTicks(axis({ hasMissing: true })).at(-1)).toEqual({
      label: 'không xác định',
      position: UNKNOWN_POSITION,
    })
  })
})
