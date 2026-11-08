import { Billboard, Html, useCursor } from '@react-three/drei'
import type { ThreeEvent } from '@react-three/fiber'
import { memo, useState } from 'react'
import type { RunStatus } from '../../lib/types'
import { useCameraStore } from '../../store/useCameraStore'
import { useRunStore } from '../../store/useRunStore'
import type { RunNodeLayout } from '../../utils/coordinate-mapper'

/** Keeps small spheres easy to hit with the pointer. */
const MIN_HIT_RADIUS = 0.35
/** Pointer travel (px) above which a press counts as orbiting, not a click. */
const CLICK_DRAG_TOLERANCE = 4

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

interface RunNodeProps {
  node: RunNodeLayout
  color: string
  radius: number
}

export const RunNode = memo(function RunNode({ node, color, radius }: RunNodeProps) {
  const { run, position, isOffGrid } = node
  const isSelected = useRunStore((state) => state.selectedRunId === run.id)
  const isHighlighted = useRunStore((state) => state.highlightedRunIds.includes(run.id))
  const selectRun = useRunStore((state) => state.selectRun)
  const setCameraTarget = useCameraStore((state) => state.setTarget)
  const [isHovered, setHovered] = useState(false)
  useCursor(isHovered)

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation()
    if (event.delta > CLICK_DRAG_TOLERANCE) return
    selectRun(run.id)
    setCameraTarget(run.id)
  }

  return (
    <group position={position}>
      <mesh>
        <sphereGeometry args={[radius, 24, 24]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={isSelected || isHighlighted ? 0.8 : 0.15}
          transparent={isOffGrid}
          opacity={isOffGrid ? 0.3 : 1}
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
      <StatusMark status={run.status} radius={radius} />
      {isSelected && (
        <Billboard>
          <mesh>
            <ringGeometry args={[radius + 0.14, radius + 0.21, 40]} />
            <meshBasicMaterial color="#ffffff" />
          </mesh>
        </Billboard>
      )}
      {isHighlighted && (
        <Billboard>
          <mesh>
            <ringGeometry args={[radius + 0.27, radius + 0.36, 40]} />
            <meshBasicMaterial color="#fb923c" />
          </mesh>
        </Billboard>
      )}
      {isHovered && (
        <Html
          center
          position={[0, radius + 0.55, 0]}
          zIndexRange={[50, 40]}
          style={{ pointerEvents: 'none' }}
        >
          <div className="whitespace-nowrap rounded bg-slate-800 px-2 py-1 text-xs text-slate-100 shadow">
            {run.run_name}
            {(run.final_val_accuracy ?? run.final_accuracy) !== null &&
              ` · ${(run.final_val_accuracy ?? run.final_accuracy)?.toFixed(4)}`}
          </div>
        </Html>
      )}
    </group>
  )
})
