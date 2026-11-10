import { useCursor } from '@react-three/drei'
import { useFrame, type ThreeEvent } from '@react-three/fiber'
import { useLayoutEffect, useRef, useState } from 'react'
import { Color, Matrix4, Quaternion, SphereGeometry, Vector3, type InstancedMesh } from 'three'
import { focusRun } from '../../store/syncStores'
import { useRunStore } from '../../store/useRunStore'
import type { RunNodeLayout } from '../../utils/coordinate-mapper'
import { InstancedStatusMarks, type NodeMotions } from './InstancedStatusMarks'
import {
  APPEAR_DURATION,
  APPEAR_MAX_STEP,
  appearScale,
  ARRIVAL_THRESHOLD,
  CLICK_DRAG_TOLERANCE,
  DIMMED_OPACITY,
  MIN_HIT_RADIUS,
  MOVE_SPEED,
  OFF_GRID_OPACITY,
  type RunVisual,
} from './node-style'
import { RunDecorations } from './RunDecorations'

/** Sphere detail by the camera's distance from the scene center. The home view is about 20. */
const LOD_LEVELS = [
  { maxDistance: 14, geometry: new SphereGeometry(1, 24, 24) },
  { maxDistance: 32, geometry: new SphereGeometry(1, 16, 12) },
  { maxDistance: Infinity, geometry: new SphereGeometry(1, 8, 6) },
]
const INITIAL_GEOMETRY = LOD_LEVELS[1].geometry
const HIT_GEOMETRY = new SphereGeometry(1, 8, 6)
/** Stands in for the emissive boost a selected node gets when it has its own material. */
const FOCUS_BRIGHTNESS = 1.6

const moveTarget = new Vector3()
const noRotation = new Quaternion()
const instanceScale = new Vector3()
const instanceMatrix = new Matrix4()
const instanceColor = new Color()

/** Moves a node one frame towards its layout position. Returns whether it changed. */
function advanceMotion(motions: NodeMotions, node: RunNodeLayout, delta: number): boolean {
  const motion = motions.get(node.run.id)
  if (!motion) {
    motions.set(node.run.id, { position: new Vector3(...node.position), appearElapsed: 0 })
    return true
  }

  let hasChanged = false
  if (motion.appearElapsed < APPEAR_DURATION) {
    const step = Math.min(delta, APPEAR_MAX_STEP)
    motion.appearElapsed = Math.min(motion.appearElapsed + step, APPEAR_DURATION)
    hasChanged = true
  }
  moveTarget.set(...node.position)
  if (!motion.position.equals(moveTarget)) {
    motion.position.lerp(moveTarget, 1 - Math.exp(-MOVE_SPEED * delta))
    if (motion.position.distanceTo(moveTarget) < ARRIVAL_THRESHOLD) motion.position.copy(moveTarget)
    hasChanged = true
  }
  return hasChanged
}

function setInstance(mesh: InstancedMesh, index: number, position: Vector3, scale: number) {
  instanceMatrix.compose(position, noRotation, instanceScale.setScalar(scale))
  mesh.setMatrixAt(index, instanceMatrix)
}

/** Instance colors feed the diffuse only; this makes the emissive follow them too. */
function tintEmissiveByInstance(shader: { fragmentShader: string }) {
  shader.fragmentShader = shader.fragmentShader.replace(
    '#include <emissivemap_fragment>',
    '#include <emissivemap_fragment>\ntotalEmissiveRadiance *= vColor;',
  )
}

interface InstancedRunNodesProps {
  items: RunVisual[]
  /** Upper bound of `items.length`. Remount with a new key when it changes. */
  capacity: number
  axisKeys: string[]
}

/** Draws every run in one draw call, for scenes too large for one mesh per run. */
export function InstancedRunNodes({ items, capacity, axisKeys }: InstancedRunNodesProps) {
  const sphereRef = useRef<InstancedMesh>(null)
  const hitRef = useRef<InstancedMesh>(null)
  const motions = useRef<NodeMotions>(new Map())
  const hasStaleMatrices = useRef(true)
  const selectedRunId = useRunStore((state) => state.selectedRunId)
  const highlightedRunIds = useRunStore((state) => state.highlightedRunIds)
  const [hoveredRunId, setHoveredRunId] = useState<number | null>(null)
  useCursor(hoveredRunId !== null)

  useLayoutEffect(() => {
    if (!sphereRef.current || !hitRef.current) return
    sphereRef.current.count = items.length
    hitRef.current.count = items.length
    hasStaleMatrices.current = true

    // Forgetting hidden runs makes them grow in again when the filter brings them back.
    const shownRunIds = new Set(items.map(({ node }) => node.run.id))
    for (const runId of motions.current.keys()) {
      if (!shownRunIds.has(runId)) motions.current.delete(runId)
    }
  }, [items])

  useLayoutEffect(() => {
    const sphere = sphereRef.current
    if (!sphere) return
    const highlighted = new Set(highlightedRunIds)
    items.forEach(({ node, color }, index) => {
      const { id } = node.run
      const isFocused = id === selectedRunId || highlighted.has(id)
      const isDimmed = highlighted.size > 0 && !isFocused && id !== hoveredRunId
      const brightness = node.isOffGrid
        ? OFF_GRID_OPACITY
        : isDimmed
          ? DIMMED_OPACITY
          : isFocused
            ? FOCUS_BRIGHTNESS
            : 1
      sphere.setColorAt(index, instanceColor.set(color).multiplyScalar(brightness))
    })
    if (sphere.instanceColor) sphere.instanceColor.needsUpdate = true
  }, [items, selectedRunId, highlightedRunIds, hoveredRunId])

  useFrame(({ camera }, delta) => {
    const sphere = sphereRef.current
    const hit = hitRef.current
    if (!sphere || !hit) return

    const distance = camera.position.length()
    const level = LOD_LEVELS.find(({ maxDistance }) => distance < maxDistance)
    if (level && sphere.geometry !== level.geometry) sphere.geometry = level.geometry

    let hasChanged = hasStaleMatrices.current
    for (const { node } of items) {
      if (advanceMotion(motions.current, node, delta)) hasChanged = true
    }
    if (!hasChanged) return

    hasStaleMatrices.current = false
    items.forEach(({ node, radius }, index) => {
      const motion = motions.current.get(node.run.id)
      if (!motion) return
      const appear = appearScale(motion.appearElapsed)
      setInstance(sphere, index, motion.position, radius * appear)
      setInstance(hit, index, motion.position, Math.max(radius, MIN_HIT_RADIUS) * appear)
    })
    for (const mesh of [sphere, hit]) {
      mesh.instanceMatrix.needsUpdate = true
      mesh.computeBoundingSphere() // frustum culling and raycasting would use a stale one
    }
  })

  const runIdAt = (event: ThreeEvent<PointerEvent | MouseEvent>) =>
    event.instanceId === undefined ? undefined : items[event.instanceId]?.node.run.id

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation()
    const runId = runIdAt(event)
    if (runId !== undefined && event.delta <= CLICK_DRAG_TOLERANCE) focusRun(runId)
  }

  const activeItems = items.filter(
    ({ node: { run } }) =>
      run.id === selectedRunId || run.id === hoveredRunId || highlightedRunIds.includes(run.id),
  )

  return (
    <>
      <instancedMesh ref={sphereRef} args={[INITIAL_GEOMETRY, undefined, capacity]}>
        <meshStandardMaterial
          emissive="#ffffff"
          emissiveIntensity={0.15}
          onBeforeCompile={tintEmissiveByInstance}
        />
      </instancedMesh>
      {/* Hidden, yet still raycast: a coarse, easy to hit stand-in for the spheres. */}
      <instancedMesh
        ref={hitRef}
        args={[HIT_GEOMETRY, undefined, capacity]}
        visible={false}
        onClick={handleClick}
        onPointerOver={(event) => {
          event.stopPropagation()
          setHoveredRunId(runIdAt(event) ?? null)
        }}
        onPointerOut={() => setHoveredRunId(null)}
      />
      <InstancedStatusMarks items={items} capacity={capacity} motions={motions} />
      {activeItems.map(({ node, color, radius }) => (
        <group key={node.run.id} position={node.position}>
          <RunDecorations
            node={node}
            axisKeys={axisKeys}
            color={color}
            radius={radius}
            isSelected={node.run.id === selectedRunId}
            isHighlighted={highlightedRunIds.includes(node.run.id)}
            isHovered={node.run.id === hoveredRunId}
          />
        </group>
      ))}
    </>
  )
}
