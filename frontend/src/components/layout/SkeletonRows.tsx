interface SkeletonRowsProps {
  count: number
  className?: string
  rowClassName?: string
}

/** Placeholder rows. Hidden from screen readers: the scene's progress bar announces the load. */
export function SkeletonRows({
  count,
  className = 'space-y-2',
  rowClassName = 'h-5',
}: SkeletonRowsProps) {
  return (
    <div aria-hidden="true" className={className}>
      {Array.from({ length: count }, (_, index) => (
        <div key={index} className={`animate-pulse rounded bg-slate-800 ${rowClassName}`} />
      ))}
    </div>
  )
}
