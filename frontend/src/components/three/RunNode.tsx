import { Billboard, useCursor } from '@react-three/drei'
import { useFrame, type ThreeEvent } from '@react-three/fiber'
import { memo, useRef, useState } from 'react'
import { Vector3, type Group } from 'three'
import type { RunStatus } from '../../lib/types'
import { focusRun } from '../../store/syncStores'
import { useRunStore } from '../../store/useRunStore'
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

const moveTarget = new Vector3()

function StatusMark({ status, radius }: { status: RunStatus; radius: number }) {
  if (status === 'running') {
    return (
      <Billboard>
        <mesh>
          <ringGeometry args={[radius + 0.05, radius + 0.11, 32, 1, 0, Math.PI]} />
          <meshBasicMaterial color="#fcd34d" />
        </mesh>
      </Billboard>
    )
  }
  if (status === 'failed') {
    return (
      <Billboard>
        {[Math.PI / 4, -Math.PI / 4].map((rotation) => (
          <mesh key={rotation} position={[0, 0, radius + 0.02]} rotation={[0, 0, rotation]}>
            <planeGeometry args={[radius * 2.6, 0.06]} />
            <meshBasicMaterial color="#f87171" />
          </mesh>
        ))}
      </Billboard>
    )
  }
  return null
}

interface RunNodeProps extends RunVisual {
  axisKeys: string[]
}

export const RunNode = memo(function RunNode({ node, axisKeys, color, radius }: RunNodeProps) {
  const { run, position, isOffGrid } = node
  const isSelected = useRunStore((state) => state.selectedRunId === run.id)
  const isHighlighted = useRunStore((state) => state.highlightedRunIds.includes(run.id))
  const isDimmed = useRunStore(
    (state) =>
      state.highlightedRunIds.length > 0 &&
      !state.highlightedRunIds.includes(run.id) &&
      state.selectedRunId !== run.id,
  )
  const [isHovered, setHovered] = useState(false)
  useCursor(isHovered)

  // The prop stays fixed so three.js does not jump; the frame loop glides to each new position.
  const groupRef = useRef<Group>(null)
  const [initialPosition] = useState(position)
  const appearElapsed = useRef(0)
  useFrame((_, delta) => {
    const group = groupRef.current
    if (!group) return
    if (appearElapsed.current < APPEAR_DURATION) {
      const step = Math.min(delta, APPEAR_MAX_STEP)
      appearElapsed.current = Math.min(appearElapsed.current + step, APPEAR_DURATION)
      group.scale.setScalar(appearScale(appearElapsed.current))
    }
    moveTarget.set(...position)
    if (group.position.equals(moveTarget)) return
    group.position.lerp(moveTarget, 1 - Math.exp(-MOVE_SPEED * delta))
    if (group.position.distanceTo(moveTarget) < ARRIVAL_THRESHOLD) group.position.copy(moveTarget)
  })

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation()
    if (event.delta > CLICK_DRAG_TOLERANCE) return
    focusRun(run.id)
  }

  const opacity = isOffGrid ? OFF_GRID_OPACITY : isDimmed && !isHovered ? DIMMED_OPACITY : 1

  return (
    <group ref={groupRef} position={initialPosition} scale={0}>
      <mesh>
        <sphereGeometry args={[radius, 24, 24]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={isSelected || isHighlighted ? 0.8 : 0.15}
          transparent // constant: three.js does not recompile when this flips at runtime
          opacity={opacity}
          depthWrite={opacity === 1}
        />
      </mesh>
      <mesh
        onClick={handleClick}
        onPointerOver={(event) => {
          event.stopPropagation()
          setHovered(true)
        }}
        onPointerOut={() => setHovered(false)}
      >
        <sphereGeometry args={[Math.max(radius, MIN_HIT_RADIUS), 12, 12]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>
      {!isDimmed && <StatusMark status={run.status} radius={radius} />}
      <RunDecorations
        node={node}
        axisKeys={axisKeys}
        color={color}
        radius={radius}
        isSelected={isSelected}
        isHighlighted={isHighlighted}
        isHovered={isHovered}
      />
    </group>
  )
})
