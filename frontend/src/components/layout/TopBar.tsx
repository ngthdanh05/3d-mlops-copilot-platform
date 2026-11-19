export function TopBar({ onRefresh }: { onRefresh: () => void }) {
  return (
    <header className="flex h-12 shrink-0 items-center border-b border-slate-800 px-4">
      <h1 className="text-sm font-semibold tracking-wide">3D-MLOps Copilot</h1>
      <button type="button" onClick={onRefresh}
        className="ml-auto text-xs text-slate-400 hover:text-white">Làm mới dữ liệu</button>
    </header>
  )
}
