import type { RunEncodings } from '../../utils/color-utils'
import type { SceneLayout } from '../../utils/coordinate-mapper'
import { RunNode } from './RunNode'

interface RunNodesProps {
  layout: SceneLayout
  encodings: RunEncodings
}

export function RunNodes({ layout, encodings }: RunNodesProps) {
  return (
    <>
      {layout.nodes.map((node) => {
        const encoding = encodings.byRunId.get(node.run.id)
        if (!encoding) return null
        return <RunNode key={node.run.id} node={node} axisKeys={layout.axisKeys} {...encoding} />
      })}
    </>
  )
}
