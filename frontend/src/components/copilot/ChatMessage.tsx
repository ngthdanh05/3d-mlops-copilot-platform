import Markdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatMessage as Message } from '../../lib/types'

const REMARK_PLUGINS = [remarkGfm]
const HEADING_CLASS = 'mt-3 font-semibold text-slate-100 first:mt-0'

// Tailwind's preflight strips default element styles, so each element is styled here.
const MARKDOWN_COMPONENTS: Components = {
  p: ({ children }) => <p className="mt-2 first:mt-0">{children}</p>,
  h1: ({ children }) => <h3 className={HEADING_CLASS}>{children}</h3>,
  h2: ({ children }) => <h3 className={HEADING_CLASS}>{children}</h3>,
  h3: ({ children }) => <h3 className={HEADING_CLASS}>{children}</h3>,
  ul: ({ children }) => <ul className="mt-2 list-disc space-y-1 pl-5 first:mt-0">{children}</ul>,
  ol: ({ children }) => (
    <ol className="mt-2 list-decimal space-y-1 pl-5 first:mt-0">{children}</ol>
  ),
  strong: ({ children }) => <strong className="font-semibold text-slate-100">{children}</strong>,
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noreferrer" className="text-blue-400 underline">
      {children}
    </a>
  ),
  code: ({ children }) => (
    <code className="rounded bg-slate-800 px-1 py-0.5 font-mono text-xs">{children}</code>
  ),
  pre: ({ children }) => (
    <pre className="mt-2 overflow-x-auto rounded bg-slate-800 p-2 first:mt-0">{children}</pre>
  ),
  table: ({ children }) => (
    <div className="mt-2 overflow-x-auto first:mt-0">
      <table className="w-full border-collapse text-left text-xs">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="whitespace-nowrap border-b border-slate-600 px-2 py-1 font-medium text-slate-100">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="whitespace-nowrap border-b border-slate-800 px-2 py-1">{children}</td>
  ),
}

export function ChatMessage({ message }: { message: Message }) {
  if (message.role === 'user') {
    // The user's own text is shown exactly as typed.
    return (
      <p className="ml-8 whitespace-pre-wrap rounded bg-slate-800 px-3 py-2 text-slate-100">
        {message.content}
      </p>
    )
  }
  return (
    <div className="mr-8 min-w-0 px-3 py-2 text-slate-200">
      <Markdown remarkPlugins={REMARK_PLUGINS} components={MARKDOWN_COMPONENTS}>
        {message.content}
      </Markdown>
    </div>
  )
}
