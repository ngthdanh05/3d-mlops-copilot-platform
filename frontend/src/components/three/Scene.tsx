import { OrbitControls } from '@react-three/drei'
import { Canvas } from '@react-three/fiber'
import { useMemo } from 'react'
import { useRunStore } from '../../store/useRunStore'
import { encodeRuns } from '../../utils/color-utils'
import { layoutRuns, SCENE_CENTERING_OFFSET } from '../../utils/coordinate-mapper'
import { AxesLabels } from './AxesLabels'
import { CameraController } from './CameraController'
import { ColorLegend } from './ColorLegend'
import { RunNodes } from './RunNodes'
import { SceneLighting } from './SceneLighting'

interface SceneProps {
  isLoading: boolean
  hasError: boolean
}

export function Scene({ isLoading, hasError }: SceneProps) {
  const runs = useRunStore((state) => state.runs)
  const hasExperiment = useRunStore((state) => state.selectedExperimentId !== null)

  const layout = useMemo(() => layoutRuns(runs), [runs])
  const encodings = useMemo(() => encodeRuns(runs), [runs])

  let message: string | null = null
  if (hasError) {
    message = 'Không kết nối được backend. Hãy kiểm tra server ở cổng 8000.'
  } else if (isLoading) {
    message = runs.length === 0 ? 'Đang tải dữ liệu...' : null
  } else if (!hasExperiment) {
    message = 'Chưa có experiment. Chạy: uv run python -m app.utils.seed_data'
  } else if (runs.length === 0) {
    message = 'Experiment này chưa có run.'
  }

  return (
    <div className="relative h-full w-full">
      {runs.length > 0 && (
        <>
          <Canvas flat camera={{ position: [13, 9, 13], fov: 55 }}>
            <SceneLighting />
            <OrbitControls makeDefault target={[0, -1, 0]} />
            <CameraController nodes={layout.nodes} />
            <group
              position={[SCENE_CENTERING_OFFSET, SCENE_CENTERING_OFFSET, SCENE_CENTERING_OFFSET]}
            >
              <AxesLabels layout={layout} />
              <RunNodes nodes={layout.nodes} encodings={encodings} />
            </group>
          </Canvas>
          <ColorLegend legend={encodings.legend} />
        </>
      )}
      {message && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center p-6 text-center text-sm text-slate-400">
          <p role="status">{message}</p>
        </div>
      )}
    </div>
  )
}
