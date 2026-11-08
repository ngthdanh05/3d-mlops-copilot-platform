import type { RunEncodings } from '../../utils/color-utils'
import type { RunNodeLayout } from '../../utils/coordinate-mapper'
import { RunNode } from './RunNode'

interface RunNodesProps {
  nodes: RunNodeLayout[]
  encodings: RunEncodings
}

export function RunNodes({ nodes, encodings }: RunNodesProps) {
  return (
    <>
      {nodes.map((node) => {
        const encoding = encodings.byRunId.get(node.run.id)
        if (!encoding) return null
        return <RunNode key={node.run.id} node={node} {...encoding} />
      })}
    </>
  )
}
