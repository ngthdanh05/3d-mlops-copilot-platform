import { useFrame } from '@react-three/fiber'
import { useMemo, useRef, type MutableRefObject } from 'react'
import {
  Matrix4,
  PlaneGeometry,
  RingGeometry,
  Vector3,
  type BufferGeometry,
  type InstancedMesh,
} from 'three'
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js'
import type { RunStatus } from '../../lib/types'
import { useRunStore } from '../../store/useRunStore'
import { appearScale, type RunVisual } from './node-style'

/** Where a node is drawn right now, while it glides and grows towards its target. */
export interface NodeMotion {
  position: Vector3
  appearElapsed: number
}

export type NodeMotions = Map<number, NodeMotion>

interface MarkStyle {
  status: RunStatus
  color: string
  geometry: BufferGeometry
  /** Size of the unit geometry for a sphere of this radius. */
  size: (radius: number) => number
  /** How far towards the camera the mark sits, so the sphere does not cover it. */
  lift: (radius: number) => number
}

const ARC = new RingGeometry(0.92, 1.08, 32, 1, 0, Math.PI)
const CROSS = mergeGeometries([
  new PlaneGeometry(2.6, 0.2).rotateZ(Math.PI / 4),
  new PlaneGeometry(2.6, 0.2).rotateZ(-Math.PI / 4),
])

const MARK_STYLES: MarkStyle[] = [
  {
    status: 'running',
    color: '#fcd34d',
    geometry: ARC,
    size: (radius) => radius + 0.08,
    lift: () => 0,
  },
  {
    status: 'failed',
    color: '#f87171',
    geometry: CROSS,
    size: (radius) => radius,
    lift: (radius) => radius + 0.02,
  },
]

const markPosition = new Vector3()
const markScale = new Vector3()
const towardsCamera = new Vector3()
const markMatrix = new Matrix4()

interface StatusMarksProps {
  style: MarkStyle
  items: RunVisual[]
  capacity: number
  motions: MutableRefObject<NodeMotions>
}

function StatusMarks({ style, items, capacity, motions }: StatusMarksProps) {
  const meshRef = useRef<InstancedMesh>(null)

  // Marks face the camera, so unlike the spheres they are rewritten every frame.
  useFrame(({ camera }) => {
    const mesh = meshRef.current
    if (!mesh) return
    towardsCamera.set(0, 0, 1).applyQuaternion(camera.quaternion)
    let count = 0
    for (const { node, radius } of items) {
      const motion = motions.current.get(node.run.id)
      if (!motion) continue
      const size = style.size(radius) * appearScale(motion.appearElapsed)
      markPosition.copy(motion.position).addScaledVector(towardsCamera, style.lift(radius))
      markMatrix.compose(markPosition, camera.quaternion, markScale.setScalar(size))
      mesh.setMatrixAt(count, markMatrix)
      count += 1
    }
    mesh.count = count
    mesh.instanceMatrix.needsUpdate = true
  })

  return (
    <instancedMesh ref={meshRef} args={[style.geometry, undefined, capacity]} frustumCulled={false}>
      <meshBasicMaterial color={style.color} />
    </instancedMesh>
  )
}

interface InstancedStatusMarksProps {
  items: RunVisual[]
  capacity: number
  motions: MutableRefObject<NodeMotions>
}

export function InstancedStatusMarks({ items, capacity, motions }: InstancedStatusMarksProps) {
  const selectedRunId = useRunStore((state) => state.selectedRunId)
  const highlightedRunIds = useRunStore((state) => state.highlightedRunIds)

  const undimmedItems = useMemo(() => {
    if (highlightedRunIds.length === 0) return items
    const kept = new Set(highlightedRunIds)
    if (selectedRunId !== null) kept.add(selectedRunId)
    return items.filter(({ node }) => kept.has(node.run.id))
  }, [items, highlightedRunIds, selectedRunId])

  return MARK_STYLES.map((style) => (
    <StatusMarks
      key={style.status}
      style={style}
      items={undimmedItems.filter(({ node }) => node.run.status === style.status)}
      capacity={capacity}
      motions={motions}
    />
  ))
}
