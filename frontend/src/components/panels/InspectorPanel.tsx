import type { RunSummary } from '../../lib/types'
import { useRunStore } from '../../store/useRunStore'
import { RUN_STATUS } from '../../utils/run-status'
import { SkeletonRows } from '../layout/SkeletonRows'
import { HyperparamsTable } from './HyperparamsTable'

function finalMetrics(run: RunSummary): [string, number | null][] {
  return [
    ['accuracy', run.final_accuracy],
    ['loss', run.final_loss],
    ['val_accuracy', run.final_val_accuracy],
    ['val_loss', run.final_val_loss],
  ]
}

function RunDetails({ run }: { run: RunSummary }) {
  return (
    <div className="mt-3 space-y-4">
      <div>
        <p className="font-medium text-slate-100">{run.run_name}</p>
        <p className="mt-1 text-xs text-slate-400">
          {RUN_STATUS[run.status].symbol} {RUN_STATUS[run.status].label} · {new Date(run.created_at).toLocaleString('vi-VN')}
        </p>
      </div>
      <div>
        <h3 className="mb-1 text-xs text-slate-400">
          Chỉ số cuối{run.final_epoch !== null && ` (epoch ${run.final_epoch})`}
        </h3>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
          {finalMetrics(run).map(([name, value]) => (
            <div key={name} className="flex justify-between gap-2">
              <dt className="text-slate-400">{name}</dt>
              <dd className="tabular-nums text-slate-100">{value?.toFixed(4) ?? '—'}</dd>
            </div>
          ))}
        </dl>
      </div>
      <div>
        <h3 className="mb-1 text-xs text-slate-400">Siêu tham số</h3>
        <HyperparamsTable hyperparams={run.hyperparams} />
      </div>
    </div>
  )
}

export function InspectorPanel({ isLoading }: { isLoading: boolean }) {
  const selectedRun = useRunStore((state) =>
    state.runs.find((run) => run.id === state.selectedRunId),
  )

  return (
    <section aria-label="Chi tiết run" className="min-h-48 flex-1 overflow-y-auto p-4">
      <h2 className="hidden text-xs font-medium uppercase text-slate-400 lg:block">Chi tiết run</h2>
      {selectedRun ? (
        <RunDetails run={selectedRun} />
      ) : isLoading ? (
        <SkeletonRows count={4} className="mt-3 space-y-2" />
      ) : (
        <p className="mt-3 text-sm text-slate-500">Chọn một quả cầu để xem chi tiết.</p>
      )}
    </section>
  )
}
