import { useRunStore } from '../../store/useRunStore'
import { CollapsibleSection } from './CollapsibleSection'
import { RunFilters } from './RunFilters'
import { RunList } from './RunList'
import { SkeletonRows } from './SkeletonRows'

export function Sidebar({ isLoading }: { isLoading: boolean }) {
  const experiments = useRunStore((state) => state.experiments)
  const selectedExperimentId = useRunStore((state) => state.selectedExperimentId)
  const selectExperiment = useRunStore((state) => state.selectExperiment)
  const hasRuns = useRunStore((state) => state.runs.length > 0)
  const hasRunsOrLoading = hasRuns || isLoading

  return (
    <div className="flex shrink-0 flex-col border-b border-slate-800 lg:w-[250px] lg:border-b-0 lg:border-r">
      <nav
        aria-label="Experiment"
        className="flex shrink-0 gap-1 overflow-x-auto p-2 lg:max-h-56 lg:flex-col lg:overflow-y-auto"
      >
        <h2 className="hidden px-2 py-1 text-xs font-medium uppercase text-slate-400 lg:block">
          Experiment
        </h2>
        {isLoading && experiments.length === 0 && (
          <SkeletonRows
            count={4}
            className="flex gap-1 lg:flex-col"
            rowClassName="h-7 w-28 shrink-0 lg:w-full"
          />
        )}
        {experiments.map((experiment) => {
          const isSelected = experiment.id === selectedExperimentId
          return (
            <button
              key={experiment.id}
              type="button"
              aria-current={isSelected ? 'true' : undefined}
              onClick={() => selectExperiment(experiment.id)}
              className={`shrink-0 truncate rounded px-2 py-1.5 text-left text-sm ${
                isSelected ? 'bg-slate-800 text-white' : 'text-slate-300 hover:bg-slate-900'
              }`}
            >
              {experiment.name}
            </button>
          )
        })}
      </nav>
      {/* Closed on small screens, where anything here pushes the 3D view further down. */}
      {hasRunsOrLoading && (
        <>
          <CollapsibleSection title="Bộ lọc" defaultOpen={false} className="shrink-0">
            <RunFilters />
          </CollapsibleSection>
          <CollapsibleSection title="Run" defaultOpen={false} className="lg:min-h-0 lg:flex-1">
            {/* Keyed so a new experiment starts with an empty search. */}
            <RunList key={selectedExperimentId} isLoading={isLoading} />
          </CollapsibleSection>
        </>
      )}
    </div>
  )
}
