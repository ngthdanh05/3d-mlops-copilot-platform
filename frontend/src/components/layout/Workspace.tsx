import { useEffect } from 'react'
import { useRuns } from '../../hooks/useRuns'
import { startStoreSync } from '../../store/syncStores'
import { ChatPanel } from '../copilot/ChatPanel'
import { InspectorPanel } from '../panels/InspectorPanel'
import { Scene } from '../three/Scene'
import { CollapsibleSection } from './CollapsibleSection'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'

export function Workspace() {
  const { loadStep, hasError, isRetrying, retry } = useRuns()
  useEffect(() => startStoreSync(), [])

  const isLoading = loadStep !== null

  return (
    <div className="flex h-dvh flex-col bg-slate-950 text-slate-100">
      <TopBar />
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto lg:flex-row lg:overflow-hidden">
        <Sidebar isLoading={isLoading} />
        <main className="min-h-[50vh] min-w-0 flex-1 lg:min-h-0">
          <Scene loadStep={loadStep} hasError={hasError} isRetrying={isRetrying} onRetry={retry} />
        </main>
        <aside className="flex w-full shrink-0 flex-col border-t border-slate-800 lg:w-[350px] lg:border-l lg:border-t-0">
          <CollapsibleSection title="Chi tiết run" defaultOpen className="lg:min-h-0 lg:flex-1">
            <InspectorPanel isLoading={isLoading} />
          </CollapsibleSection>
          <CollapsibleSection title="Trợ lý AI" defaultOpen className="lg:min-h-0 lg:flex-1">
            <ChatPanel />
          </CollapsibleSection>
        </aside>
      </div>
    </div>
  )
}
