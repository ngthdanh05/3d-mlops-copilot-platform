import { Html, Line } from '@react-three/drei'
import type { ReactNode } from 'react'
import { axisTicks, SCENE_SIZE, type Axis, type SceneLayout } from '../../utils/coordinate-mapper'

type Vec3 = [number, number, number]

const S = SCENE_SIZE
const AXIS_COLOR = '#64748b'

interface LabelProps {
  position: Vec3
  children: ReactNode
  className: string
}

function Label({ position, children, className }: LabelProps) {
  return (
    <Html center position={position} zIndexRange={[10, 0]} style={{ pointerEvents: 'none' }}>
      <span className={`whitespace-nowrap ${className}`}>{children}</span>
    </Html>
  )
}

interface AxisGuideProps {
  axis: Axis
  from: Vec3
  to: Vec3
  tickAt: (position: number) => Vec3
  titleAt: Vec3
}

function AxisGuide({ axis, from, to, tickAt, titleAt }: AxisGuideProps) {
  return (
    <>
      <Line points={[from, to]} color={AXIS_COLOR} lineWidth={1.5} />
      {axisTicks(axis).map((tick) => (
        <Label key={tick.label} position={tickAt(tick.position)} className="text-[10px] text-slate-400">
          {tick.label}
        </Label>
      ))}
      <Label position={titleAt} className="text-xs font-medium text-slate-200">
        {axis.scale === 'linear' ? axis.key : `${axis.key} (${axis.scale})`}
      </Label>
    </>
  )
}

export function AxesLabels({ layout }: { layout: SceneLayout }) {
  return (
    <>
      <gridHelper args={[S, 10, '#334155', '#1e293b']} position={[S / 2, 0, S / 2]} />
      <AxisGuide
        axis={layout.x}
        from={[0, 0, S]}
        to={[S, 0, S]}
        tickAt={(p) => [p, -0.5, S + 0.4]}
        titleAt={[S / 2, -1.3, S + 1]}
      />
      <AxisGuide
        axis={layout.y}
        from={[0, 0, S]}
        to={[0, S, S]}
        tickAt={(p) => [-0.7, p, S]}
        titleAt={[-0.7, S + 0.9, S]}
      />
      {layout.z && (
        <AxisGuide
          axis={layout.z}
          from={[S, 0, 0]}
          to={[S, 0, S]}
          tickAt={(p) => [S + 0.4, -0.5, p]}
          titleAt={[S + 1, -1.3, S / 2]}
        />
      )}
    </>
  )
}
