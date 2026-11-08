import { useRunStore } from '../../store/useRunStore'

export function Sidebar() {
  const experiments = useRunStore((state) => state.experiments)
  const selectedExperimentId = useRunStore((state) => state.selectedExperimentId)
  const selectExperiment = useRunStore((state) => state.selectExperiment)

  return (
    <nav
      aria-label="Experiment"
      className="flex shrink-0 gap-1 overflow-x-auto border-b border-slate-800 p-2 lg:w-[250px] lg:flex-col lg:overflow-y-auto lg:border-b-0 lg:border-r"
    >
      <h2 className="hidden px-2 py-1 text-xs font-medium uppercase text-slate-400 lg:block">
        Experiment
      </h2>
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
  )
}
