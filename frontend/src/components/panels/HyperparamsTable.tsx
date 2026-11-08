import type { JsonValue } from '../../lib/types'

function formatValue(value: JsonValue): string {
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

export function HyperparamsTable({ hyperparams }: { hyperparams: Record<string, JsonValue> }) {
  const entries = Object.entries(hyperparams)
  if (entries.length === 0) return <p className="text-sm text-slate-500">Không có dữ liệu.</p>

  return (
    <table className="w-full text-sm">
      <tbody>
        {entries.map(([key, value]) => (
          <tr key={key} className="border-b border-slate-800/70 last:border-0">
            <th scope="row" className="py-1 pr-3 text-left font-normal text-slate-400">
              {key}
            </th>
            <td className="break-all py-1 text-right tabular-nums text-slate-100">
              {formatValue(value)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
