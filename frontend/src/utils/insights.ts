import type { RunSummary } from '../lib/types'
import { colorMetric } from './color-utils'
import { formatNumber } from './coordinate-mapper'

const TOP_RUN_COUNT = 3

function rangeText(runs: RunSummary[], key: string): string | null {
  const values = runs.map((run) => run.hyperparams[key]).filter((v) => typeof v === 'number')
  if (values.length === 0) return null
  const low = formatNumber(Math.min(...values))
  const high = formatNumber(Math.max(...values))
  return `${key} ${low === high ? low : `${low} – ${high}`}`
}

/** One-sentence takeaway of the chart, computed from the data. */
export function summarizeBestRuns(runs: RunSummary[], axisKeys: string[]): string | null {
  const ranked = runs
    .filter((run) => run.status === 'completed' && colorMetric(run) !== null)
    .sort((a, b) => (colorMetric(b) as number) - (colorMetric(a) as number))
  if (ranked.length === 0) return null

  const best = ranked[0]
  const metricName = best.final_val_accuracy !== null ? 'val_accuracy' : 'accuracy'
  const headline = `Tốt nhất trong ${ranked.length} run hoàn thành: ${best.run_name} (${metricName} ${formatNumber(colorMetric(best) as number)}).`
  if (ranked.length <= TOP_RUN_COUNT) return headline

  const ranges = axisKeys
    .map((key) => rangeText(ranked.slice(0, TOP_RUN_COUNT), key))
    .filter((text) => text !== null)
  return ranges.length > 0
    ? `${headline} ${TOP_RUN_COUNT} run tốt nhất có ${ranges.join(', ')}.`
    : headline
}
