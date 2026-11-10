import type { RunNodeLayout } from '../../utils/coordinate-mapper'

/** What both node renderers draw for one run. */
export interface RunVisual {
  node: RunNodeLayout
  color: string
  radius: number
}

/** Keeps small spheres easy to hit with the pointer. */
export const MIN_HIT_RADIUS = 0.35
/** Pointer travel (px) above which a press counts as orbiting, not a click. */
export const CLICK_DRAG_TOLERANCE = 4
export const DIMMED_OPACITY = 0.18
export const OFF_GRID_OPACITY = 0.3
export const MOVE_SPEED = 6
export const ARRIVAL_THRESHOLD = 0.005
/** Seconds a node takes to grow in when it enters the scene. */
export const APPEAR_DURATION = 0.5
/** Longest step of one frame, so a stall while shaders compile cannot skip the animation. */
export const APPEAR_MAX_STEP = 0.1

/** Scale of a node that has been appearing for `elapsed` seconds. */
export function appearScale(elapsed: number): number {
  return 1 - (1 - elapsed / APPEAR_DURATION) ** 3
}
