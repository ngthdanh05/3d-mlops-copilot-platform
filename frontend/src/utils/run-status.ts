import type { RunStatus } from '../lib/types'

export const RUN_STATUS: Record<RunStatus, { symbol: string; label: string; textClass: string }> = {
  completed: { symbol: '●', label: 'Hoàn thành', textClass: 'text-emerald-400' },
  running: { symbol: '◐', label: 'Đang chạy', textClass: 'text-amber-300' },
  failed: { symbol: '✕', label: 'Lỗi', textClass: 'text-red-400' },
}
