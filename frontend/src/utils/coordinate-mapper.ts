import type { JsonValue, RunSummary } from '../lib/types'

/** Scene coordinates of a plotted axis run from 0 to SCENE_SIZE. */
export const SCENE_SIZE = 10
/** Shifts plotted coordinates so the cube is centered on the world origin. */
export const SCENE_CENTERING_OFFSET = -SCENE_SIZE / 2
/** Where runs missing an axis key are placed, just outside the plotted range. */
export const UNKNOWN_POSITION = -1.5

export type AxisScale = 'log10' | 'log2' | 'linear'

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
  /** Null when no numeric hyperparameter varies: the scene is flat along Z. */
  z: Axis | null
  nodes: RunNodeLayout[]
}

const Z_PREFERRED_KEYS = ['dropout', 'epochs']
const X_KEY = 'learning_rate'
const Y_KEY = 'batch_size'

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

function buildAxis(runs: RunSummary[], key: string, scale: AxisScale): Axis {
  const scaled = runs.map((run) => applyScale(asNumber(run.hyperparams[key]), scale))
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
  const scaled = applyScale(asNumber(run.hyperparams[axis.key]), axis.scale)
  return scaled === null ? null : toPosition(scaled, axis)
}

/** Places runs using the default axes described in README ("Thiết kế không gian 3D"). */
export function layoutRuns(runs: RunSummary[]): SceneLayout {
  const x = buildAxis(runs, X_KEY, 'log10')
  const y = buildAxis(runs, Y_KEY, 'log2')
  const zKey = pickZKey(runs)
  const z = zKey === null ? null : buildAxis(runs, zKey, 'linear')

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

  return { x, y, z, nodes }
}

function formatValue(value: number, scale: AxisScale): string {
  if (scale === 'log10') return value.toExponential(0).replace('e+', 'e')
  return String(Number(value.toPrecision(3)))
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

export function axisTicks(axis: Axis): AxisTick[] {
  const ticks: AxisTick[] =
    axis.min === null || axis.max === null
      ? []
      : tickPoints(axis, axis.min, axis.max).map((scaled) => ({
          label: formatValue(fromScaled(scaled, axis.scale), axis.scale),
          position: toPosition(scaled, axis),
        }))
  if (axis.hasMissing) ticks.push({ label: 'không xác định', position: UNKNOWN_POSITION })
  return ticks
}
