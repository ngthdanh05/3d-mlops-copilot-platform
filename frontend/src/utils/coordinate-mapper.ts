import type { JsonValue, RunSummary } from '../lib/types'

/** Scene coordinates of a plotted axis run from 0 to SCENE_SIZE. */
export const SCENE_SIZE = 10
/** Shifts plotted coordinates so the cube is centered on the world origin. */
export const SCENE_CENTERING_OFFSET = -SCENE_SIZE / 2
export const CAMERA_HOME = {
  position: [13, 9, 13] as [number, number, number],
  target: [0, -1, 0] as [number, number, number],
}
/** Where runs missing an axis key are placed, just outside the plotted range. */
export const UNKNOWN_POSITION = -1.5

export type AxisScale = 'log10' | 'log2' | 'linear'
export type AxisName = 'x' | 'y' | 'z'

/** The user's choice per axis. Unset uses the default; `z: null` keeps the scene flat along Z. */
export type AxisSelection = Partial<Record<AxisName, string | null>>

/** Keys that can be plotted: every one is numeric in at least one run. */
export interface AxisOptions {
  hyperparams: string[]
  metrics: string[]
}

export interface Axis {
  key: string
  scale: AxisScale
  /** Domain in scaled units (e.g. log10 of the value). Null when no run has a usable value. */
  min: number | null
  max: number | null
  hasMissing: boolean
}

export interface AxisTick {
  label: string
  position: number
}

export interface RunNodeLayout {
  run: RunSummary
  position: [number, number, number]
  isOffGrid: boolean
}

export interface SceneLayout {
  x: Axis
  y: Axis
  /** Null when the scene is flat along Z: nothing varies, or the user turned Z off. */
  z: Axis | null
  /** Distinct keys currently used as axes. */
  axisKeys: string[]
  options: AxisOptions
  nodes: RunNodeLayout[]
}

const Z_PREFERRED_KEYS = ['dropout', 'epochs']
const X_KEY = 'learning_rate'
const Y_KEY = 'batch_size'
const KEY_SCALES = new Map<string, AxisScale>([
  [X_KEY, 'log10'],
  [Y_KEY, 'log2'],
])
const FINAL_METRIC_KEYS = [
  'final_accuracy',
  'final_val_accuracy',
  'final_loss',
  'final_val_loss',
] as const
type FinalMetricKey = (typeof FINAL_METRIC_KEYS)[number]

/** Tick labels gain digits until they differ, up to this many significant digits. */
const MAX_TICK_PRECISION = 8

function isFinalMetricKey(key: string): key is FinalMetricKey {
  return (FINAL_METRIC_KEYS as readonly string[]).includes(key)
}

/** What a run holds for an axis key. A final metric wins over a hyperparameter of the same name. */
export function axisValue(run: RunSummary, key: string): JsonValue | undefined {
  return isFinalMetricKey(key) ? run[key] : run.hyperparams[key]
}

function asNumber(value: JsonValue | undefined): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function applyScale(value: number | null, scale: AxisScale): number | null {
  if (value === null) return null
  if (scale === 'linear') return value
  if (value <= 0) return null
  return scale === 'log10' ? Math.log10(value) : Math.log2(value)
}

function distinctValueCount(runs: RunSummary[], key: string): number {
  const values = runs.map((run) => asNumber(run.hyperparams[key])).filter((v) => v !== null)
  return new Set(values).size
}

function pickZKey(runs: RunSummary[]): string | null {
  const otherKeys = [...new Set(runs.flatMap((run) => Object.keys(run.hyperparams)))]
    .filter((key) => key !== X_KEY && key !== Y_KEY && !Z_PREFERRED_KEYS.includes(key))
    .sort()
  const candidates = [...Z_PREFERRED_KEYS, ...otherKeys]
  return candidates.find((key) => distinctValueCount(runs, key) >= 2) ?? null
}

function buildAxisOptions(runs: RunSummary[]): AxisOptions {
  const isNumericSomewhere = (key: string) =>
    runs.some((run) => asNumber(axisValue(run, key)) !== null)
  return {
    hyperparams: [...new Set(runs.flatMap((run) => Object.keys(run.hyperparams)))]
      .filter((key) => !isFinalMetricKey(key) && isNumericSomewhere(key))
      .sort(),
    metrics: FINAL_METRIC_KEYS.filter(isNumericSomewhere),
  }
}

function buildAxis(runs: RunSummary[], key: string): Axis {
  const scale = KEY_SCALES.get(key) ?? 'linear'
  const scaled = runs.map((run) => applyScale(asNumber(axisValue(run, key)), scale))
  const present = scaled.filter((v) => v !== null)
  return {
    key,
    scale,
    min: present.length > 0 ? Math.min(...present) : null,
    max: present.length > 0 ? Math.max(...present) : null,
    hasMissing: present.length < scaled.length,
  }
}

function toPosition(scaled: number, axis: Axis): number {
  const { min, max } = axis
  if (min === null || max === null || min === max) return SCENE_SIZE / 2
  return ((scaled - min) / (max - min)) * SCENE_SIZE
}

function positionOf(run: RunSummary, axis: Axis): number | null {
  const scaled = applyScale(asNumber(axisValue(run, axis.key)), axis.scale)
  return scaled === null ? null : toPosition(scaled, axis)
}

/**
 * Places runs on the selected axes. Anything unselected, or no longer plottable in these runs,
 * uses the defaults described in README ("Thiết kế không gian 3D").
 */
export function layoutRuns(runs: RunSummary[], selection: AxisSelection = {}): SceneLayout {
  const options = buildAxisOptions(runs)
  const plottable = (key: string | null | undefined) =>
    key && (options.hyperparams.includes(key) || options.metrics.includes(key)) ? key : null

  const x = buildAxis(runs, plottable(selection.x) ?? X_KEY)
  const y = buildAxis(runs, plottable(selection.y) ?? Y_KEY)
  const zKey = selection.z === null ? null : (plottable(selection.z) ?? pickZKey(runs))
  const z = zKey === null ? null : buildAxis(runs, zKey)

  const nodes = runs.map((run): RunNodeLayout => {
    const px = positionOf(run, x)
    const py = positionOf(run, y)
    const pz = z === null ? SCENE_SIZE / 2 : positionOf(run, z)
    return {
      run,
      position: [px ?? UNKNOWN_POSITION, py ?? UNKNOWN_POSITION, pz ?? UNKNOWN_POSITION],
      isOffGrid: px === null || py === null || pz === null,
    }
  })

  // A set because the user may plot one key on two axes.
  const axisKeys = [...new Set([x.key, y.key, ...(z ? [z.key] : [])])]
  return { x, y, z, axisKeys, options, nodes }
}

function trioRole(key: string): string | null {
  if (key === 'epochs') return 'epoch'
  if (!isFinalMetricKey(key)) return null
  return key.endsWith('accuracy') ? 'accuracy' : 'loss'
}

/** Accuracy and loss are nearly inverse, so this trio collapses the runs onto one line. */
export function isEpochAccuracyLossTrio(keys: string[]): boolean {
  const roles = new Set(keys.map(trioRole))
  return roles.size === 3 && !roles.has(null)
}

/** Short human form of a number: 0.00043, 256, 0.1. */
export function formatNumber(value: number, precision = 3): string {
  return String(Number(value.toPrecision(precision)))
}

function fromScaled(scaled: number, scale: AxisScale): number {
  if (scale === 'log10') return 10 ** scaled
  if (scale === 'log2') return 2 ** scaled
  return scaled
}

function tickPoints(axis: Axis, min: number, max: number): number[] {
  if (min === max) return [min]
  if (axis.scale !== 'linear') {
    const whole: number[] = []
    for (let exponent = Math.ceil(min); exponent <= Math.floor(max); exponent += 1) {
      whole.push(exponent)
    }
    if (whole.length >= 2) return whole
    return [min, max]
  }
  return Array.from({ length: 5 }, (_, i) => min + ((max - min) * i) / 4)
}

/** Metrics can span a narrow range, where 3 digits would print the same label on every tick. */
function tickLabels(values: number[]): string[] {
  let labels = values.map((value) => formatNumber(value))
  for (let precision = 4; precision <= MAX_TICK_PRECISION; precision += 1) {
    if (new Set(labels).size === labels.length) break
    labels = values.map((value) => formatNumber(value, precision))
  }
  return labels
}

export function axisTicks(axis: Axis): AxisTick[] {
  const points = axis.min === null || axis.max === null ? [] : tickPoints(axis, axis.min, axis.max)
  const labels = tickLabels(points.map((scaled) => fromScaled(scaled, axis.scale)))
  const ticks: AxisTick[] = points.map((scaled, index) => ({
    label: labels[index],
    position: toPosition(scaled, axis),
  }))
  if (axis.hasMissing) ticks.push({ label: 'không xác định', position: UNKNOWN_POSITION })
  return ticks
}
