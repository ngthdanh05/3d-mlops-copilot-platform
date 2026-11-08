import type { RunSummary } from '../lib/types'

/** Single-hue ramp for the dark theme: dim = low accuracy, bright = high accuracy. */
export const COLOR_STOPS = ['#2563eb', '#60a5fa', '#eff6ff'] as const
export const NO_METRIC_COLOR = '#64748b'

const MIN_RADIUS = 0.15
const MAX_RADIUS = 0.5
const NO_METRIC_RADIUS = 0.2
const MIN_VALUES_FOR_OUTLIERS = 4

export interface NodeEncoding {
  color: string
  radius: number
}

export interface LegendInfo {
  label: string
  min: number
  max: number
  /** Some runs fall below `min` and are drawn with the lowest color. */
  isClippedLow: boolean
}

export interface RunEncodings {
  byRunId: Map<number, NodeEncoding>
  legend: LegendInfo | null
}

interface Domain {
  min: number
  max: number
}

function colorMetric(run: RunSummary): number | null {
  return run.final_val_accuracy ?? run.final_accuracy
}

function lossMetric(run: RunSummary): number | null {
  return run.final_val_loss ?? run.final_loss
}

/**
 * Min/max of the values, ignoring outliers on the bad side (Tukey fence). One diverged
 * run must not squeeze every healthy run into the same color. The good side is kept,
 * so the best run always gets the extreme of the ramp.
 */
function domainOf(values: (number | null)[], badSide: 'low' | 'high'): Domain | null {
  const sorted = values.filter((v) => v !== null).sort((a, b) => a - b)
  if (sorted.length === 0) return null

  let kept = sorted
  if (sorted.length >= MIN_VALUES_FOR_OUTLIERS) {
    const q1 = sorted[Math.floor(sorted.length * 0.25)]
    const q3 = sorted[Math.floor(sorted.length * 0.75)]
    const fence = 1.5 * (q3 - q1)
    kept = sorted.filter((v) => (badSide === 'low' ? v >= q1 - fence : v <= q3 + fence))
  }
  return { min: kept[0], max: kept[kept.length - 1] }
}

/** Position of value within domain, clamped to 0..1. A one-value domain maps to the middle. */
function normalize(value: number, { min, max }: Domain): number {
  if (min === max) return value < min ? 0 : value > max ? 1 : 0.5
  return Math.min(1, Math.max(0, (value - min) / (max - min)))
}

function hexToRgb(hex: string): [number, number, number] {
  const n = Number.parseInt(hex.slice(1), 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

export function colorAt(t: number): string {
  const scaled = Math.min(1, Math.max(0, t)) * (COLOR_STOPS.length - 1)
  const index = Math.min(Math.floor(scaled), COLOR_STOPS.length - 2)
  const from = hexToRgb(COLOR_STOPS[index])
  const to = hexToRgb(COLOR_STOPS[index + 1])
  const mixed = from.map((channel, i) => Math.round(channel + (to[i] - channel) * (scaled - index)))
  return `#${mixed.map((channel) => channel.toString(16).padStart(2, '0')).join('')}`
}

/**
 * Colors and sizes runs. Domains come from completed runs so that a diverged or
 * half-finished run does not wash out the differences between the finished ones.
 */
export function encodeRuns(runs: RunSummary[]): RunEncodings {
  const completed = runs.filter((run) => run.status === 'completed')
  const hasCompletedMetrics = completed.some((run) => colorMetric(run) !== null)
  const reference = hasCompletedMetrics ? completed : runs

  const colorDomain = domainOf(reference.map(colorMetric), 'low')
  const lossDomain = domainOf(reference.map(lossMetric), 'high')

  const byRunId = new Map<number, NodeEncoding>()
  for (const run of runs) {
    const accuracy = colorMetric(run)
    const loss = lossMetric(run)
    byRunId.set(run.id, {
      color:
        accuracy === null || colorDomain === null
          ? NO_METRIC_COLOR
          : colorAt(normalize(accuracy, colorDomain)),
      radius:
        loss === null || lossDomain === null
          ? NO_METRIC_RADIUS
          : MAX_RADIUS - normalize(loss, lossDomain) * (MAX_RADIUS - MIN_RADIUS),
    })
  }

  const usesValidation = runs.some((run) => run.final_val_accuracy !== null)
  return {
    byRunId,
    legend: colorDomain && {
      label: usesValidation ? 'val_accuracy' : 'accuracy',
      ...colorDomain,
      isClippedLow: runs.some((run) => (colorMetric(run) ?? Infinity) < colorDomain.min),
    },
  }
}
