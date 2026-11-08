import { useRuns } from '../../hooks/useRuns'
import { ChatPanel } from '../copilot/ChatPanel'
import { InspectorPanel } from '../panels/InspectorPanel'
import { Scene } from '../three/Scene'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'

export function Workspace() {
  const { isLoading, hasError } = useRuns()

  return (
    <div className="flex h-dvh flex-col bg-slate-950 text-slate-100">
      <TopBar />
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto lg:flex-row lg:overflow-hidden">
        <Sidebar />
        <main className="min-h-[50vh] min-w-0 flex-1 lg:min-h-0">
          <Scene isLoading={isLoading} hasError={hasError} />
        </main>
        <aside className="flex w-full shrink-0 flex-col border-t border-slate-800 lg:w-[350px] lg:border-l lg:border-t-0">
          <InspectorPanel />
          <ChatPanel />
        </aside>
      </div>
    </div>
  )
}
