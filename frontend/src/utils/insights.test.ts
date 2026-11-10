import { describe, expect, it } from 'vitest'
import { makeRun } from '../test/make-run'
import { summarizeBestRuns } from './insights'

const scored = (name: string, accuracy: number, learning_rate: number) =>
  makeRun({ run_name: name, final_val_accuracy: accuracy, hyperparams: { learning_rate } })

const FOUR_RUNS = [scored('a', 0.9, 1), scored('b', 0.8, 1), scored('c', 0.7, 1), scored('d', 0.6, 2)]

describe('summarizeBestRuns', () => {
  it('has nothing to say without completed runs', () => {
    expect(summarizeBestRuns([makeRun({ status: 'running' })], [])).toBeNull()
    expect(summarizeBestRuns([], [])).toBeNull()
  })

  it('names the best run', () => {
    const text = summarizeBestRuns([scored('a', 0.8, 1), scored('b', 0.9, 1)], ['learning_rate'])
    expect(text).toBe('Tốt nhất trong 2 run hoàn thành: b (val_accuracy 0.9).')
  })

  it('falls back to training accuracy in the wording', () => {
    const run = makeRun({ run_name: 'a', final_val_accuracy: null, final_accuracy: 0.7 })
    expect(summarizeBestRuns([run], [])).toBe('Tốt nhất trong 1 run hoàn thành: a (accuracy 0.7).')
  })

  it('adds the axis ranges of the top three when there are more runs', () => {
    const runs = [
      scored('a', 0.9, 0.001),
      scored('b', 0.89, 0.002),
      scored('c', 0.88, 0.004),
      scored('d', 0.5, 0.9),
    ]
    expect(summarizeBestRuns(runs, ['learning_rate'])).toBe(
      'Tốt nhất trong 4 run hoàn thành: a (val_accuracy 0.9). 3 run tốt nhất có learning_rate 0.001 – 0.004.',
    )
  })

  it('shows one value when the top three agree', () => {
    expect(summarizeBestRuns(FOUR_RUNS, ['learning_rate'])).toContain('learning_rate 1.')
  })

  it('stops at the headline when no axis is numeric in the top runs', () => {
    expect(summarizeBestRuns(FOUR_RUNS, ['missing'])).toBe(
      'Tốt nhất trong 4 run hoàn thành: a (val_accuracy 0.9).',
    )
  })
})
