import { useRunStore } from '../../store/useRunStore'

interface SceneProps {
  isLoading: boolean
  hasError: boolean
}

/** Placeholder until the R3F canvas lands (P2-T04). */
export function Scene({ isLoading, hasError }: SceneProps) {
  const runCount = useRunStore((state) => state.runs.length)
  const hasExperiment = useRunStore((state) => state.selectedExperimentId !== null)

  let message = `Đã tải ${runCount} run. Không gian 3D sẽ hiển thị ở đây.`
  if (hasError) {
    message = 'Không kết nối được backend. Hãy kiểm tra server ở cổng 8000.'
  } else if (isLoading) {
    message = 'Đang tải dữ liệu...'
  } else if (!hasExperiment) {
    message = 'Chưa có experiment. Chạy: uv run python -m app.utils.seed_data'
  }

  return (
    <div className="flex h-full items-center justify-center p-6 text-center text-sm text-slate-400">
      <p role="status">{message}</p>
    </div>
  )
}
