import { useRunStore } from '../../store/useRunStore'
import {
  isEpochAccuracyLossTrio,
  type AxisName,
  type SceneLayout,
} from '../../utils/coordinate-mapper'

const AXES: AxisName[] = ['x', 'y', 'z']
const TRIO_HINT = 'Không dùng epoch, accuracy và loss làm 3 trục cùng lúc'

function KeyOption({ optionKey, isBlocked }: { optionKey: string; isBlocked: boolean }) {
  return (
    <option value={optionKey} disabled={isBlocked} title={isBlocked ? TRIO_HINT : undefined}>
      {optionKey}
    </option>
  )
}

function AxisSelect({ name, layout }: { name: AxisName; layout: SceneLayout }) {
  const setAxis = useRunStore((state) => state.setAxis)
  const { hyperparams, metrics } = layout.options
  const currentKey = layout[name]?.key ?? ''
  const isListed = hyperparams.includes(currentKey) || metrics.includes(currentKey)

  const otherKeys = AXES.filter((axis) => axis !== name).flatMap((axis) => layout[axis]?.key ?? [])
  const isBlocked = (key: string) => isEpochAccuracyLossTrio([key, ...otherKeys])

  return (
    <label className="flex items-center gap-2">
      <span className="w-3 font-medium uppercase text-slate-100">{name}</span>
      <select
        aria-label={`Trục ${name.toUpperCase()}`}
        value={isListed ? currentKey : ''}
        onChange={(event) => setAxis(name, event.target.value || null)}
        className="min-w-0 flex-1 rounded bg-slate-800 px-1.5 py-1 text-slate-100"
      >
        {name === 'z' && <option value="">Không dùng</option>}
        {name !== 'z' && !isListed && (
          <option value="" disabled>
            Không có dữ liệu
          </option>
        )}
        {hyperparams.length > 0 && (
          <optgroup label="Siêu tham số">
            {hyperparams.map((key) => (
              <KeyOption key={key} optionKey={key} isBlocked={isBlocked(key)} />
            ))}
          </optgroup>
        )}
        {metrics.length > 0 && (
          <optgroup label="Metric cuối">
            {metrics.map((key) => (
              <KeyOption key={key} optionKey={key} isBlocked={isBlocked(key)} />
            ))}
          </optgroup>
        )}
      </select>
    </label>
  )
}

export function AxisSelector({ layout }: { layout: SceneLayout }) {
  return (
    <div className="absolute bottom-3 left-3 z-20 flex w-52 flex-col gap-1.5 rounded bg-slate-900/85 p-3 text-xs text-slate-300">
      <div className="font-medium text-slate-100">Chọn trục</div>
      {AXES.map((name) => (
        <AxisSelect key={name} name={name} layout={layout} />
      ))}
    </div>
  )
}
