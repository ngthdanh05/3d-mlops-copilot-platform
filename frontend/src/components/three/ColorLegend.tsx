import { COLOR_STOPS, type LegendInfo } from '../../utils/color-utils'

export function ColorLegend({ legend }: { legend: LegendInfo | null }) {
  return (
    <div className="pointer-events-none absolute bottom-3 right-3 rounded bg-slate-900/80 p-3 text-xs text-slate-300">
      {legend && (
        <div className="mb-2 w-44">
          <div className="mb-1 font-medium text-slate-100">Màu: {legend.label}</div>
          <div
            className="h-2 rounded"
            style={{ background: `linear-gradient(to right, ${COLOR_STOPS.join(', ')})` }}
          />
          <div className="mt-1 flex justify-between tabular-nums text-slate-400">
            <span>
              {legend.isClippedLow && '≤ '}
              {legend.min.toFixed(3)}
            </span>
            <span>{legend.max.toFixed(3)}</span>
          </div>
        </div>
      )}
      <div>Cầu to: loss thấp</div>
      <div className="mt-1 text-slate-400">● hoàn thành · ◐ đang chạy · ✕ lỗi</div>
    </div>
  )
}
