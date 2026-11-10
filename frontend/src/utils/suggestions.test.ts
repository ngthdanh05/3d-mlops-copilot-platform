import { describe, expect, it } from 'vitest'
import { makeRun } from '../test/make-run'
import { compareQuestion, overfittingQuestion, suggestQuestions } from './suggestions'

const best = makeRun({ run_name: 'best', final_val_accuracy: 0.95 })
const worse = makeRun({ run_name: 'worse', final_val_accuracy: 0.7 })

describe('compareQuestion', () => {
  it('compares a weaker run with the best one', () => {
    expect(compareQuestion(worse, [best, worse])).toBe('So sánh worse với run tốt nhất')
  })

  it('compares the best run with the runner-up', () => {
    expect(compareQuestion(best, [best, worse])).toBe('So sánh best với run tốt thứ hai')
  })
})

describe('overfittingQuestion', () => {
  it('asks about the given run', () => {
    expect(overfittingQuestion(worse)).toBe('worse có bị overfitting không?')
  })

  it('asks about the best run when none is given', () => {
    expect(overfittingQuestion(undefined)).toBe('Run tốt nhất có bị overfitting không?')
  })
})

describe('suggestQuestions', () => {
  it('offers a comparison and an overfitting check for a weaker completed run', () => {
    expect(suggestQuestions(worse, [best, worse])).toEqual([
      'So sánh worse với run tốt nhất',
      'worse có bị overfitting không?',
    ])
  })

  it('offers a summary for the best run', () => {
    expect(suggestQuestions(best, [best, worse])[0]).toBe('Tóm tắt kết quả của best')
  })

  it('offers a summary for a run still in progress', () => {
    const running = makeRun({ run_name: 'live', status: 'running', final_val_accuracy: 0.1 })
    expect(suggestQuestions(running, [best, running])[0]).toBe('Tóm tắt kết quả của live')
  })

  it('skips the overfitting check without validation metrics', () => {
    const noVal = makeRun({ final_val_accuracy: null })
    expect(suggestQuestions(noVal, [noVal])).toHaveLength(1)
  })
})
