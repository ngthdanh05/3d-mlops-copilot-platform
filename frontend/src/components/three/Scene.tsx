import { OrbitControls } from '@react-three/drei'
import { Canvas } from '@react-three/fiber'
import { useMemo } from 'react'
import { useCameraStore } from '../../store/useCameraStore'
import { useRunStore } from '../../store/useRunStore'
import { encodeRuns } from '../../utils/color-utils'
import {
  CAMERA_HOME,
  layoutRuns,
  SCENE_CENTERING_OFFSET,
} from '../../utils/coordinate-mapper'
import { summarizeBestRuns } from '../../utils/insights'
import { AxesLabels } from './AxesLabels'
import { AxisSelector } from './AxisSelector'
import { CameraController } from './CameraController'
import { ColorLegend } from './ColorLegend'
import { RunNodes } from './RunNodes'
import { SceneLighting } from './SceneLighting'

interface SceneProps {
  isLoading: boolean
  hasError: boolean
}

function resetView() {
  const { highlightRuns, selectRun } = useRunStore.getState()
  highlightRuns([])
  selectRun(null)
  useCameraStore.getState().setTarget(null)
}

export function Scene({ isLoading, hasError }: SceneProps) {
  const runs = useRunStore((state) => state.runs)
  const axisSelection = useRunStore((state) => state.axisSelection)
  const hasExperiment = useRunStore((state) => state.selectedExperimentId !== null)
  const hasFocus = useRunStore(
    (state) => state.selectedRunId !== null || state.highlightedRunIds.length > 0,
  )

  const layout = useMemo(() => layoutRuns(runs, axisSelection), [runs, axisSelection])
  const encodings = useMemo(() => encodeRuns(runs), [runs])
  const takeaway = useMemo(() => summarizeBestRuns(runs, layout.axisKeys), [runs, layout])

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
          <Canvas flat camera={{ position: CAMERA_HOME.position, fov: 55 }}>
            <SceneLighting />
            <OrbitControls makeDefault target={CAMERA_HOME.target} />
            <CameraController nodes={layout.nodes} />
            <group
              position={[SCENE_CENTERING_OFFSET, SCENE_CENTERING_OFFSET, SCENE_CENTERING_OFFSET]}
            >
              <AxesLabels layout={layout} />
              <RunNodes layout={layout} encodings={encodings} />
            </group>
          </Canvas>
          {takeaway && (
            <p className="pointer-events-none absolute left-4 right-40 top-3 text-sm text-slate-200">
              {takeaway}
            </p>
          )}
          {hasFocus && (
            <button
              type="button"
              onClick={resetView}
              className="absolute right-3 top-3 rounded bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-100 hover:bg-slate-700"
            >
              Xem toàn cảnh
            </button>
          )}
          <AxisSelector layout={layout} />
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
