import { Billboard, Html, Line, useCursor } from '@react-three/drei'
import type { ThreeEvent } from '@react-three/fiber'
import { memo, useState } from 'react'
import type { JsonValue, RunStatus, RunSummary } from '../../lib/types'
import { useCameraStore } from '../../store/useCameraStore'
import { useRunStore } from '../../store/useRunStore'
import { colorMetric } from '../../utils/color-utils'
import { formatNumber, SCENE_SIZE, type RunNodeLayout } from '../../utils/coordinate-mapper'

/** Keeps small spheres easy to hit with the pointer. */
const MIN_HIT_RADIUS = 0.35
/** Pointer travel (px) above which a press counts as orbiting, not a click. */
const CLICK_DRAG_TOLERANCE = 4
const DIMMED_OPACITY = 0.18
const OFF_GRID_OPACITY = 0.3
const GUIDE_COLOR = '#94a3b8'

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

/** Drops from the sphere to the floor, then runs to the X and Z axes to read its position. */
function GuideLines({ position }: { position: RunNodeLayout['position'] }) {
  const [x, y, z] = position
  const floor: [number, number, number] = [0, -y, 0]
  const lines: [number, number, number][] = [
    [0, 0, 0],
    [0, -y, SCENE_SIZE - z],
    [SCENE_SIZE - x, -y, 0],
  ]
  return (
    <>
      {lines.map((end) => (
        <Line
          key={end.join()}
          points={[end, floor]}
          color={GUIDE_COLOR}
          lineWidth={1}
          dashed
          dashSize={0.2}
          gapSize={0.12}
        />
      ))}
    </>
  )
}

function formatHyperparam(value: JsonValue | undefined): string {
  if (typeof value === 'number') return formatNumber(value)
  return value === undefined ? 'không có' : String(value)
}

function RunCallout({ run, axisKeys }: { run: RunSummary; axisKeys: string[] }) {
  const accuracy = colorMetric(run)
  return (
    <div className="whitespace-nowrap rounded bg-slate-800/95 px-2.5 py-1.5 text-xs text-slate-300 shadow">
      <div className="font-medium text-white">{run.run_name}</div>
      {accuracy !== null && (
        <div>
          {run.final_val_accuracy !== null ? 'val_accuracy' : 'accuracy'}: {accuracy.toFixed(4)}
        </div>
      )}
      {axisKeys.map((key) => (
        <div key={key} className="text-slate-400">
          {key}: {formatHyperparam(run.hyperparams[key])}
        </div>
      ))}
    </div>
  )
}

interface RunNodeProps {
  node: RunNodeLayout
  axisKeys: string[]
  color: string
  radius: number
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

  const isActive = isHovered || isSelected || isHighlighted
  const opacity = isOffGrid ? OFF_GRID_OPACITY : isDimmed && !isHovered ? DIMMED_OPACITY : 1

  return (
    <group position={position}>
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
      {isActive && !isOffGrid && <GuideLines position={position} />}
      {isActive && (
        <Html
          position={[radius + 0.5, radius + 0.5, 0]}
          zIndexRange={[50, 40]}
          style={{ pointerEvents: 'none' }}
        >
          <RunCallout run={run} axisKeys={axisKeys} />
        </Html>
      )}
    </group>
  )
})
