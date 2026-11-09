import { COLOR_STOPS, type LegendInfo } from '../../utils/color-utils'

export function ColorLegend({ legend }: { legend: LegendInfo | null }) {
  return (
    <div className="pointer-events-none absolute bottom-3 right-3 z-20 w-48 rounded bg-slate-900/85 p-3 text-xs leading-relaxed text-slate-300">
      <div className="mb-1 font-medium text-slate-100">Cách đọc đồ thị</div>
      <div>Mỗi quả cầu là một lần huấn luyện.</div>
      <div>Vị trí: theo 3 trục đang chọn.</div>
      {legend && (
        <div className="my-1.5">
          <div>Càng sáng: {legend.label} càng cao</div>
          <div
            className="mt-1 h-2 rounded"
            style={{ background: `linear-gradient(to right, ${COLOR_STOPS.join(', ')})` }}
          />
          <div className="mt-0.5 flex justify-between tabular-nums text-slate-400">
            <span>
              {legend.isClippedLow && '≤ '}
              {legend.min.toFixed(3)}
            </span>
            <span>{legend.max.toFixed(3)}</span>
          </div>
        </div>
      )}
      <div>Càng to: loss càng thấp</div>
      <div className="mt-1 text-slate-400">● xong · ◐ đang chạy · ✕ lỗi</div>
    </div>
  )
}
