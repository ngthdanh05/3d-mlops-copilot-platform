import type { RunSummary } from '../lib/types'
import { colorMetric } from './color-utils'

function hasBetterRun(run: RunSummary, runs: RunSummary[]): boolean {
  const accuracy = colorMetric(run) ?? -Infinity
  return runs.some(
    (other) => other.status === 'completed' && (colorMetric(other) ?? -Infinity) > accuracy,
  )
}

export function compareQuestion(run: RunSummary, runs: RunSummary[]): string {
  const target = hasBetterRun(run, runs) ? 'run tốt nhất' : 'run tốt thứ hai'
  return `So sánh ${run.run_name} với ${target}`
}

export function overfittingQuestion(run: RunSummary | undefined): string {
  return `${run?.run_name ?? 'Run tốt nhất'} có bị overfitting không?`
}

/** Questions the copilot's tools can answer about one run. */
export function suggestQuestions(run: RunSummary, runs: RunSummary[]): string[] {
  const questions = [
    run.status === 'completed' && hasBetterRun(run, runs)
      ? compareQuestion(run, runs)
      : `Tóm tắt kết quả của ${run.run_name}`,
  ]
  if (run.final_val_accuracy !== null) questions.push(overfittingQuestion(run))
  return questions
}
