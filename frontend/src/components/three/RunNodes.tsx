import { useMemo } from 'react'
import { useRunStore } from '../../store/useRunStore'
import type { RunEncodings } from '../../utils/color-utils'
import type { SceneLayout } from '../../utils/coordinate-mapper'
import { matchesRunFilter } from '../../utils/run-filter'
import { InstancedRunNodes } from './InstancedRunNodes'
import type { RunVisual } from './node-style'
import { RunNode } from './RunNode'

/** Above this many runs the scene switches to instancing, which cannot fade single nodes. */
const MAX_RUNS_WITH_OWN_MESH = 100

interface RunNodesProps {
  layout: SceneLayout
  encodings: RunEncodings
}

export function RunNodes({ layout, encodings }: RunNodesProps) {
  const runFilter = useRunStore((state) => state.runFilter)

  const items = useMemo(
    () =>
      layout.nodes.flatMap((node): RunVisual[] => {
        const encoding = encodings.byRunId.get(node.run.id)
        return encoding && matchesRunFilter(node.run, runFilter) ? [{ node, ...encoding }] : []
      }),
    [layout, encodings, runFilter],
  )

  // Decided on all runs, so moving a filter never swaps the renderer under the user.
  const capacity = layout.nodes.length
  if (capacity > MAX_RUNS_WITH_OWN_MESH) {
    return (
      <InstancedRunNodes
        key={capacity}
        items={items}
        capacity={capacity}
        axisKeys={layout.axisKeys}
      />
    )
  }

  return items.map((item) => (
    <RunNode key={item.node.run.id} {...item} axisKeys={layout.axisKeys} />
  ))
}
