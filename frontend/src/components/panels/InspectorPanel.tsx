import type { RunSummary } from '../../lib/types'
import { useRunStore } from '../../store/useRunStore'
import { RUN_STATUS } from '../../utils/run-status'
import { SkeletonRows } from '../layout/SkeletonRows'
import { HyperparamsTable } from './HyperparamsTable'
import useSWR from 'swr'
import { fetchRunDetail } from '../../lib/api'

function LearningCurves({ run }: { run: RunSummary }) {
  const { data, error } = useSWR(['run-detail', run.id, run.final_epoch, run.status],
    () => fetchRunDetail(run.id), {
      refreshInterval: run.status === 'running' ? 4000 : 0,
      refreshWhenHidden: false, shouldRetryOnError: false,
      refreshWhenOffline: true,
    })
  if (error) return <p role="alert">Không tải được đường cong học.</p>
  if (!data?.metrics.length) return null
  const metrics = data.metrics
  const maxEpoch = Math.max(1, ...metrics.map((m) => m.epoch))
  return <div className="space-y-2 text-xs">
    {data.artifacts && <p>Checkpoint tốt nhất: epoch {data.artifacts.best_epoch},
      val_accuracy {data.artifacts.best_val_accuracy.toFixed(4)} (hòa: chọn epoch sớm nhất).
      {data.artifacts.test_accuracy != null && ` Test accuracy: ${data.artifacts.test_accuracy.toFixed(4)}.`}
    </p>}
    {(['accuracy', 'loss'] as const).map((kind) => {
      const validation = kind === 'accuracy' ? 'val_accuracy' : 'val_loss'
      const maximum = kind === 'accuracy' ? 1 : Math.max(1,
        ...metrics.flatMap((m) => [m[kind], m[validation] ?? 0]))
      return <figure key={kind}>
        <figcaption>{kind}: train (xanh), validation (cam)</figcaption>
        <svg viewBox="0 0 300 110" role="img" aria-label={`Đường cong ${kind}`}>
          <path d="M 10 5 V 100 H 290" fill="none" stroke="#64748b" />
          {metrics.map((m) => [kind, validation].map((key, i) => {
            const value = m[key as typeof kind | typeof validation]
            return value === null ? null : <circle key={`${m.epoch}-${key}`}
              cx={10 + m.epoch / maxEpoch * 280} cy={100 - value / maximum * 90}
              r="2.5" fill={i ? '#fb923c' : '#60a5fa'}>
              <title>epoch {m.epoch}: {value.toFixed(4)}</title>
            </circle>
          }))}
        </svg>
        <p>Epoch 1–{maxEpoch}; thang {kind}: 0–{maximum.toFixed(2)}. Mỗi điểm là một epoch đã ghi.</p>
      </figure>
    })}
  </div>
}

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
      <LearningCurves run={run} />
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
