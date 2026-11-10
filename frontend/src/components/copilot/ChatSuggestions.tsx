import { sendCopilotMessage } from '../../hooks/useCopilot'
import { useChatStore } from '../../store/useChatStore'
import { useRunStore } from '../../store/useRunStore'
import { compareQuestion, overfittingQuestion } from '../../utils/suggestions'

interface SuggestionButtonProps {
  label: string
  /** Null leaves the button disabled, with `hint` explaining why. */
  question: string | null
  hint?: string
}

function SuggestionButton({ label, question, hint }: SuggestionButtonProps) {
  const isBusy = useChatStore((state) => state.streamingMessageId !== null)

  return (
    <button
      type="button"
      disabled={isBusy || question === null}
      title={question ?? hint}
      onClick={() => {
        if (question !== null) void sendCopilotMessage(question)
      }}
      className="max-w-full truncate rounded-full border border-slate-700 px-2.5 py-1 text-xs text-slate-200 hover:bg-slate-800 disabled:cursor-not-allowed disabled:text-slate-500"
    >
      {label}
    </button>
  )
}

function QuickActions() {
  const runs = useRunStore((state) => state.runs)
  const selectedRun = useRunStore((state) =>
    state.runs.find((run) => run.id === state.selectedRunId),
  )
  const hasRuns = runs.length > 0

  return (
    <>
      <SuggestionButton
        label="🏆 Tìm run tốt nhất"
        question={hasRuns ? 'Run nào tốt nhất trong experiment này?' : null}
        hint="Experiment này chưa có run"
      />
      <SuggestionButton
        label="🔍 So sánh run đang chọn"
        question={selectedRun && runs.length > 1 ? compareQuestion(selectedRun, runs) : null}
        hint="Hãy chọn một run trước"
      />
      <SuggestionButton
        label="⚠️ Kiểm tra overfitting"
        question={hasRuns ? overfittingQuestion(selectedRun) : null}
        hint="Experiment này chưa có run"
      />
    </>
  )
}

/** Questions about the run just picked, otherwise the standing quick actions. */
export function ChatSuggestions() {
  const suggestions = useChatStore((state) => state.suggestions)

  return (
    <div role="group" aria-label="Câu hỏi gợi ý" className="mt-3 flex flex-wrap gap-1.5">
      {suggestions.length > 0 ? (
        suggestions.map((question) => (
          <SuggestionButton key={question} label={question} question={question} />
        ))
      ) : (
        <QuickActions />
      )}
    </div>
  )
}
