import { OrbitControls } from '@react-three/drei'
import { Canvas, useFrame } from '@react-three/fiber'
import { useMemo, useRef, useState } from 'react'
import { useFullscreen } from '../../hooks/useFullscreen'
import type { LoadStep } from '../../hooks/useRuns'
import { useCameraStore } from '../../store/useCameraStore'
import { useRunStore } from '../../store/useRunStore'
import { encodeRuns, type RunEncodings } from '../../utils/color-utils'
import {
  CAMERA_HOME,
  layoutRuns,
  SCENE_CENTERING_OFFSET,
  type SceneLayout,
} from '../../utils/coordinate-mapper'
import { summarizeBestRuns } from '../../utils/insights'
import { matchesRunFilter } from '../../utils/run-filter'
import { AxesLabels } from './AxesLabels'
import { AxisSelector } from './AxisSelector'
import { CameraController } from './CameraController'
import { ColorLegend } from './ColorLegend'
import { RunNodes } from './RunNodes'
import { SceneLighting } from './SceneLighting'
import { BackendError, SceneProgress } from './SceneStatus'

/** The first frame compiles the shaders, so the second one is the first the user really sees. */
const FRAMES_UNTIL_READY = 2
const FULLSCREEN_ENTER_ICON = 'M2 6V2h4M10 2h4v4M14 10v4h-4M6 14H2v-4'
const FULLSCREEN_EXIT_ICON = 'M6 2v4H2M14 6h-4V2M10 14v-4h4M2 10h4v4'

interface SceneProps {
  loadStep: LoadStep | null
  hasError: boolean
  isRetrying: boolean
  onRetry: () => void
}

function resetView() {
  const { highlightRuns, selectRun } = useRunStore.getState()
  highlightRuns([])
  selectRun(null)
  useCameraStore.getState().setTarget(null)
}

function ReadySignal({ onReady }: { onReady: () => void }) {
  const frames = useRef(0)
  useFrame(() => {
    frames.current += 1
    if (frames.current === FRAMES_UNTIL_READY) onReady()
  })
  return null
}

function FullscreenButton({
  isFullscreen,
  onToggle,
}: {
  isFullscreen: boolean
  onToggle: () => void
}) {
  const label = isFullscreen ? 'Thoát toàn màn hình' : 'Toàn màn hình'
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label={label}
      title={label}
      className="rounded bg-slate-800 p-1.5 text-slate-100 hover:bg-slate-700"
    >
      <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d={isFullscreen ? FULLSCREEN_EXIT_ICON : FULLSCREEN_ENTER_ICON} />
      </svg>
    </button>
  )
}

function SceneCanvas({ layout, encodings }: { layout: SceneLayout; encodings: RunEncodings }) {
  const [isReady, setReady] = useState(false)

  return (
    <>
      <Canvas flat camera={{ position: CAMERA_HOME.position, fov: 55 }}>
        <ReadySignal onReady={() => setReady(true)} />
        <SceneLighting />
        <OrbitControls makeDefault target={CAMERA_HOME.target} />
        <CameraController nodes={layout.nodes} />
        <group position={[SCENE_CENTERING_OFFSET, SCENE_CENTERING_OFFSET, SCENE_CENTERING_OFFSET]}>
          <AxesLabels layout={layout} />
          <RunNodes layout={layout} encodings={encodings} />
        </group>
      </Canvas>
      {!isReady && <SceneProgress step={3} />}
    </>
  )
}

export function Scene({ loadStep, hasError, isRetrying, onRetry }: SceneProps) {
  const rootRef = useRef<HTMLDivElement>(null)
  const { isFullscreen, toggleFullscreen } = useFullscreen(rootRef)
  const runs = useRunStore((state) => state.runs)
  const axisSelection = useRunStore((state) => state.axisSelection)
  const runFilter = useRunStore((state) => state.runFilter)
  const hasExperiment = useRunStore((state) => state.selectedExperimentId !== null)
  const hasFocus = useRunStore(
    (state) => state.selectedRunId !== null || state.highlightedRunIds.length > 0,
  )

  // Axes and colors come from every run, so filtering hides nodes without moving the others.
  const layout = useMemo(() => layoutRuns(runs, axisSelection), [runs, axisSelection])
  const encodings = useMemo(() => encodeRuns(runs), [runs])
  const visibleRuns = useMemo(
    () => runs.filter((run) => matchesRunFilter(run, runFilter)),
    [runs, runFilter],
  )
  const takeaway = useMemo(
    () => summarizeBestRuns(visibleRuns, layout.axisKeys),
    [visibleRuns, layout],
  )

  let message: string | null = null
  if (!hasError && loadStep === null) {
    if (!hasExperiment) {
      message = 'Chưa có experiment. Chạy: uv run python -m app.utils.seed_data'
    } else if (runs.length === 0) {
      message = 'Experiment này chưa có run.'
    } else if (visibleRuns.length === 0) {
      message = 'Không có run nào khớp bộ lọc.'
    }
  }

  return (
    <div
      ref={rootRef}
      className={`bg-slate-950 ${isFullscreen ? 'fixed inset-0 z-50' : 'relative h-full w-full'}`}
    >
      {runs.length > 0 && (
        <>
          <SceneCanvas layout={layout} encodings={encodings} />
          {takeaway && (
            <p className="pointer-events-none absolute left-4 right-4 top-12 text-sm text-slate-200 sm:right-44 sm:top-3">
              {takeaway}
            </p>
          )}
          <div className="absolute right-3 top-3 flex gap-2">
            {hasFocus && (
              <button
                type="button"
                onClick={resetView}
                className="rounded bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-100 hover:bg-slate-700"
              >
                Xem toàn cảnh
              </button>
            )}
            <FullscreenButton isFullscreen={isFullscreen} onToggle={toggleFullscreen} />
          </div>
          <AxisSelector layout={layout} />
          <ColorLegend legend={encodings.legend} />
        </>
      )}
      {loadStep !== null && runs.length === 0 && <SceneProgress step={loadStep} />}
      {hasError && (
        <BackendError hasStaleData={runs.length > 0} isRetrying={isRetrying} onRetry={onRetry} />
      )}
      {message && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center p-6 text-center text-sm text-slate-400">
          <p role="status">{message}</p>
        </div>
      )}
    </div>
  )
}
