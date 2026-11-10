const STEP_LABELS = ['Đang tải experiment...', 'Đang tải các run...', 'Đang dựng không gian 3D...']

export type SceneLoadStep = 1 | 2 | 3

export function SceneProgress({ step }: { step: SceneLoadStep }) {
  const label = STEP_LABELS[step - 1]

  return (
    <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-2 p-6">
      <p className="text-sm text-slate-400">{label}</p>
      <div
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={STEP_LABELS.length}
        aria-valuenow={step}
        className="h-1 w-48 overflow-hidden rounded bg-slate-800"
      >
        <div
          className="h-full rounded bg-blue-500 transition-[width] duration-300"
          style={{ width: `${(step / STEP_LABELS.length) * 100}%` }}
        />
      </div>
    </div>
  )
}

interface BackendErrorProps {
  /** The chart still shows older data, so the error must not cover it. */
  hasStaleData: boolean
  isRetrying: boolean
  onRetry: () => void
}

export function BackendError({ hasStaleData, isRetrying, onRetry }: BackendErrorProps) {
  const card = (
    <div
      role="alert"
      className="pointer-events-auto flex items-center gap-3 rounded bg-slate-800/95 px-4 py-3 text-sm text-slate-200 shadow"
    >
      <p>
        {hasStaleData
          ? 'Mất kết nối backend, biểu đồ đang là dữ liệu cũ.'
          : 'Không kết nối được backend. Hãy kiểm tra server ở cổng 8000.'}
      </p>
      <button
        type="button"
        disabled={isRetrying}
        onClick={onRetry}
        className="shrink-0 rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
      >
        {isRetrying ? 'Đang thử...' : 'Thử lại'}
      </button>
    </div>
  )

  return hasStaleData ? (
    <div className="pointer-events-none absolute inset-x-4 top-20 z-30 flex justify-center">
      {card}
    </div>
  ) : (
    <div className="absolute inset-0 flex items-center justify-center p-6">{card}</div>
  )
}
