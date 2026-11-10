import { Billboard, Html, Line } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import { useRef } from 'react'
import { AdditiveBlending, CanvasTexture, type Sprite } from 'three'
import type { JsonValue, RunSummary } from '../../lib/types'
import { colorMetric } from '../../utils/color-utils'
import {
  axisValue,
  formatNumber,
  SCENE_SIZE,
  type RunNodeLayout,
} from '../../utils/coordinate-mapper'

const GUIDE_COLOR = '#94a3b8'
const GLOW_MARGIN = 0.9
const GLOW_PULSE_AMOUNT = 0.08
const GLOW_PULSE_SPEED = 2.5

function createGlowTexture(): CanvasTexture {
  const size = 128
  const center = size / 2
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const context = canvas.getContext('2d')
  if (context) {
    const gradient = context.createRadialGradient(center, center, 0, center, center, center)
    gradient.addColorStop(0, 'rgba(255, 255, 255, 0.9)')
    gradient.addColorStop(0.45, 'rgba(255, 255, 255, 0.3)')
    gradient.addColorStop(1, 'rgba(255, 255, 255, 0)')
    context.fillStyle = gradient
    context.fillRect(0, 0, size, size)
  }
  return new CanvasTexture(canvas)
}

const glowTexture = createGlowTexture()

function SelectionGlow({ radius, color }: { radius: number; color: string }) {
  const spriteRef = useRef<Sprite>(null)
  const size = (radius + GLOW_MARGIN) * 2

  useFrame(({ clock }) => {
    const pulse = 1 + GLOW_PULSE_AMOUNT * Math.sin(clock.elapsedTime * GLOW_PULSE_SPEED)
    spriteRef.current?.scale.setScalar(size * pulse)
  })

  return (
    <sprite ref={spriteRef} scale={size}>
      <spriteMaterial
        map={glowTexture}
        color={color}
        blending={AdditiveBlending}
        depthWrite={false}
        transparent
      />
    </sprite>
  )
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

function formatAxisValue(value: JsonValue | undefined): string {
  if (typeof value === 'number') return formatNumber(value)
  return value === undefined || value === null ? 'không có' : String(value)
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
          {key}: {formatAxisValue(axisValue(run, key))}
        </div>
      ))}
    </div>
  )
}

interface RunDecorationsProps {
  node: RunNodeLayout
  axisKeys: string[]
  color: string
  radius: number
  isSelected: boolean
  isHighlighted: boolean
  isHovered: boolean
}

/** Everything drawn around an active node. Must be placed at the node's position. */
export function RunDecorations({
  node,
  axisKeys,
  color,
  radius,
  isSelected,
  isHighlighted,
  isHovered,
}: RunDecorationsProps) {
  const isActive = isHovered || isSelected || isHighlighted

  return (
    <>
      {isSelected && (
        <>
          <SelectionGlow radius={radius} color={color} />
          <Billboard>
            <mesh>
              <ringGeometry args={[radius + 0.14, radius + 0.21, 40]} />
              <meshBasicMaterial color="#ffffff" />
            </mesh>
          </Billboard>
        </>
      )}
      {isHighlighted && (
        <Billboard>
          <mesh>
            <ringGeometry args={[radius + 0.27, radius + 0.36, 40]} />
            <meshBasicMaterial color="#fb923c" />
          </mesh>
        </Billboard>
      )}
      {isActive && !node.isOffGrid && <GuideLines position={node.position} />}
      {isActive && (
        <Html
          position={[radius + 0.5, radius + 0.5, 0]}
          zIndexRange={[50, 40]}
          style={{ pointerEvents: 'none' }}
        >
          <RunCallout run={node.run} axisKeys={axisKeys} />
        </Html>
      )}
    </>
  )
}
