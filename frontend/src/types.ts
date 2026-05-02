export interface BookCandidate {
  id: string
  title: string
  authors: string[]
  publisher: string
  publish_date: string
  isbn: string
  ss_code: string
  dxid: string
  source: string
  has_cover: boolean
  can_download: boolean
  nlc_verified: boolean
  nlc_authors: string[]
  nlc_publisher: string
  nlc_pubdate: string
  nlc_comments: string
  nlc_tags: string[]
  bookmark_status: string
  bookmark_preview: string | null
  bookmark: string | null
  _fallback?: boolean
  language?: string
  format?: string
  size?: string
}

export interface SearchResult {
  books: BookCandidate[]
  external_books: BookCandidate[]
  totalPages: number
  totalRecords: number
  searchTimeMs: number
  error?: string
  serviceStatus?: {
    ebookDatabase: {
      reachable: boolean
      path: string
      dbs: string[]
    }
  }
}

export interface TaskStep {
  step: number
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  elapsed_ms?: number
  progress_pct?: number
  progress_message?: string
}

export interface TaskDetail {
  task_id: string
  status: string
  current_step: number
  current_step_name: string
  steps: TaskStep[]
  log_lines: string[]
  report: TaskReport | null
  error: string | null
  params: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface TaskListItem {
  task_id: string
  status: string
  current_step: number
  current_step_name: string
  params: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface TaskReport {
  title: string
  authors: string[]
  publisher: string
  isbn: string
  ss_code: string
  direct_link_internal: string
  direct_link_external: string
  filename: string
  file_size_mb: number
  finished_path: string
  steps_completed: number[]
  errors: { step: number; error: string }[]
  status?: string
  steps?: { step: number; name: string; status: string; elapsed_ms?: number }[]
}

export type WsMessage =
  | { type: 'sync'; task_id: string; status: string; steps: TaskStep[]; log_lines: string[]; report: TaskReport | null }
  | { type: 'step_start'; task_id: string; step: number; step_name: string }
  | { type: 'step_progress'; task_id: string; step: number; step_name: string; progress_pct: number; message: string }
  | { type: 'step_complete'; task_id: string; step: number; step_name: string; elapsed_ms: number; output?: unknown }
  | { type: 'log'; task_id: string; message: string }
  | { type: 'task_complete'; task_id: string; report: TaskReport }
  | { type: 'task_error'; task_id: string; step: number; error: string }
