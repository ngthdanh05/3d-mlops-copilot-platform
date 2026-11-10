import { useEffect, useRef, useState } from 'react'
import { focusRun } from '../../store/syncStores'
import { useRunStore } from '../../store/useRunStore'
import { colorMetric } from '../../utils/color-utils'
import { matchesRunFilter, matchesRunName } from '../../utils/run-filter'
import { RUN_STATUS } from '../../utils/run-status'
import { SkeletonRows } from './SkeletonRows'

export function RunList({ isLoading }: { isLoading: boolean }) {
  const runs = useRunStore((state) => state.runs)
  const runFilter = useRunStore((state) => state.runFilter)
  const selectedRunId = useRunStore((state) => state.selectedRunId)
  const highlightedRunIds = useRunStore((state) => state.highlightedRunIds)
  const [query, setQuery] = useState('')
  const listRef = useRef<HTMLUListElement>(null)

  // Not scrollIntoView: on small screens it would also scroll the page away from the 3D view.
  useEffect(() => {
    const list = listRef.current
    const item = list?.querySelector('[aria-current="true"]')
    if (!list || !item) return
    const listBox = list.getBoundingClientRect()
    const itemBox = item.getBoundingClientRect()
    if (itemBox.top < listBox.top) list.scrollTop -= listBox.top - itemBox.top
    else if (itemBox.bottom > listBox.bottom) list.scrollTop += itemBox.bottom - listBox.bottom
  }, [selectedRunId])

  if (runs.length === 0) {
    if (!isLoading) return null
    return (
      <section aria-label="Danh sách run" className="border-slate-800 p-3 lg:border-t">
        <h2 className="mb-2 hidden text-xs font-medium uppercase text-slate-400 lg:block">Run</h2>
        <SkeletonRows count={6} />
      </section>
    )
  }

  const listedRuns = runs.filter(
    (run) => matchesRunFilter(run, runFilter) && matchesRunName(run, query),
  )

  return (
    <section
      aria-label="Danh sách run"
      className="flex flex-col gap-2 border-slate-800 p-3 lg:min-h-0 lg:flex-1 lg:border-t"
    >
      <h2 className="hidden text-xs font-medium uppercase text-slate-400 lg:block">Run</h2>
      <input
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        aria-label="Tìm run theo tên"
        placeholder="Tìm theo tên..."
        className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs placeholder:text-slate-500"
      />
      {listedRuns.length === 0 ? (
        <p className="text-xs text-slate-500">Không có run nào khớp.</p>
      ) : (
        <ul ref={listRef} className="max-h-48 overflow-y-auto lg:max-h-none lg:min-h-0 lg:flex-1">
          {listedRuns.map((run) => {
            const status = RUN_STATUS[run.status]
            const isSelected = run.id === selectedRunId
            return (
              <li key={run.id}>
                <button
                  type="button"
                  aria-current={isSelected ? 'true' : undefined}
                  onClick={() => focusRun(run.id)}
                  className={`flex w-full items-center gap-2 rounded border-l-2 px-2 py-1 text-left text-xs ${
                    highlightedRunIds.includes(run.id) ? 'border-orange-400' : 'border-transparent'
                  } ${isSelected ? 'bg-slate-800 text-white' : 'text-slate-300 hover:bg-slate-900'}`}
                >
                  <span
                    role="img"
                    aria-label={status.label}
                    title={status.label}
                    className={`w-3 shrink-0 text-center ${status.textClass}`}
                  >
                    {status.symbol}
                  </span>
                  <span className="min-w-0 flex-1 truncate">{run.run_name}</span>
                  <span className="tabular-nums text-slate-400">
                    {colorMetric(run)?.toFixed(3) ?? '—'}
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
