import { useState, type ReactNode } from 'react'

interface CollapsibleSectionProps {
  title: string
  defaultOpen: boolean
  className?: string
  children: ReactNode
}

/** Folds below the desktop breakpoint, where panels stack. On desktop it is always open. */
export function CollapsibleSection({
  title,
  defaultOpen,
  className = '',
  children,
}: CollapsibleSectionProps) {
  const [isOpen, setOpen] = useState(defaultOpen)

  return (
    <div className={`flex flex-col ${className}`}>
      <button
        type="button"
        aria-expanded={isOpen}
        onClick={() => setOpen(!isOpen)}
        className="flex items-center justify-between border-t border-slate-800 px-3 py-2.5 text-xs font-medium uppercase text-slate-300 hover:bg-slate-900 lg:hidden"
      >
        {title}
        <span aria-hidden="true" className={`transition-transform ${isOpen ? 'rotate-180' : ''}`}>
          ▾
        </span>
      </button>
      <div className={`${isOpen ? 'flex' : 'hidden'} min-h-0 flex-1 flex-col lg:flex`}>
        {children}
      </div>
    </div>
  )
}
