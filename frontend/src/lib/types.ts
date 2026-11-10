// Mirrors backend/app/schemas. Keep in sync when the API changes.

export type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue }

export type RunStatus = 'running' | 'completed' | 'failed'

export interface Experiment {
  id: number
  name: string
  description: string | null
  created_at: string
}

export interface Run {
  id: number
  experiment_id: number
  run_name: string
  status: RunStatus
  hyperparams: Record<string, JsonValue>
  created_at: string
  finished_at: string | null
}

/** Item of `GET /api/runs`: run + metrics of its last logged epoch. */
export interface RunSummary extends Run {
  final_epoch: number | null
  final_accuracy: number | null
  final_loss: number | null
  final_val_accuracy: number | null
  final_val_loss: number | null
}

export interface Metric {
  id: number
  run_id: number
  epoch: number
  accuracy: number
  loss: number
  val_accuracy: number | null
  val_loss: number | null
  logged_at: string
}

/** `GET /api/runs/{id}`: run + full per-epoch timeline. */
export interface RunDetail extends Run {
  metrics: Metric[]
}

export type CopilotAction =
  | { type: 'highlight_runs'; run_ids: number[] }
  | { type: 'focus_camera'; run_id: number }
  | { type: 'open_inspector'; run_id: number }

export interface CopilotResponse {
  message: string
  actions: CopilotAction[]
}

/** One event of `POST /api/copilot/chat/stream`. `done` carries the authoritative answer. */
export type CopilotStreamEvent =
  | { type: 'delta'; text: string }
  | { type: 'reset' }
  | ({ type: 'done' } & CopilotResponse)

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  /** The question never got an answer from the backend, so it can be sent again. */
  failed?: boolean
}
