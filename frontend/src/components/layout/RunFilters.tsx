import type { RunStatus } from '../../lib/types'
import { useRunStore } from '../../store/useRunStore'
import { isRunFilterActive, matchesRunFilter, NO_RUN_FILTER } from '../../utils/run-filter'

const STATUS_OPTIONS: { value: RunStatus | null; label: string }[] = [
  { value: null, label: 'Tất cả' },
  { value: 'completed', label: 'Hoàn thành' },
  { value: 'running', label: 'Đang chạy' },
  { value: 'failed', label: 'Lỗi' },
]

export function RunFilters() {
  const runs = useRunStore((state) => state.runs)
  const filter = useRunStore((state) => state.runFilter)
  const setRunFilter = useRunStore((state) => state.setRunFilter)

  if (runs.length === 0) return null

  const visibleCount = runs.filter((run) => matchesRunFilter(run, filter)).length

  return (
    <section aria-label="Bộ lọc run" className="space-y-2 border-slate-800 p-3 text-xs lg:border-t">
      <div className="flex items-center justify-between">
        <h2 className="hidden font-medium uppercase text-slate-400 lg:block">Bộ lọc</h2>
        <div className="ml-auto flex gap-2">
          {isRunFilterActive(filter) && (
            <button
              type="button"
              onClick={() => setRunFilter(NO_RUN_FILTER)}
              className="text-slate-300 underline hover:text-white"
            >
              Bỏ lọc
            </button>
          )}
          <span className="tabular-nums text-slate-400">
            {visibleCount}/{runs.length} run
          </span>
        </div>
      </div>
      <div className="flex flex-wrap gap-1">
        {STATUS_OPTIONS.map(({ value, label }) => (
          <button
            key={label}
            type="button"
            aria-pressed={filter.status === value}
            onClick={() => setRunFilter({ ...filter, status: value })}
            className={`rounded px-2 py-1 ${
              filter.status === value
                ? 'bg-slate-700 text-white'
                : 'text-slate-300 hover:bg-slate-900'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      <div>
        <p className="mb-1 tabular-nums text-slate-300">
          Accuracy {filter.minAccuracy.toFixed(2)} – {filter.maxAccuracy.toFixed(2)}
        </p>
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={filter.minAccuracy}
          aria-label="Accuracy thấp nhất"
          onChange={(event) =>
            setRunFilter({
              ...filter,
              minAccuracy: Math.min(Number(event.target.value), filter.maxAccuracy),
            })
          }
          className="block w-full accent-blue-500"
        />
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={filter.maxAccuracy}
          aria-label="Accuracy cao nhất"
          onChange={(event) =>
            setRunFilter({
              ...filter,
              maxAccuracy: Math.max(Number(event.target.value), filter.minAccuracy),
            })
          }
          className="block w-full accent-blue-500"
        />
      </div>
    </section>
  )
}
