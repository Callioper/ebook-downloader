import { STATUS_LABELS, STATUS_COLORS } from '../constants'

export function statusBadge(status: string) {
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[status] || ''}`}>
      {STATUS_LABELS[status] || status}
    </span>
  )
}

export async function handleDeleteTask(taskId: string): Promise<boolean> {
  const res = await fetch(`/api/v1/tasks/${taskId}`, { method: 'DELETE' })
  return res.ok
}

export async function handleClearAllTasks(): Promise<boolean> {
  const res = await fetch('/api/v1/tasks', { method: 'DELETE' })
  return res.ok
}

export async function handleDeleteCompletedTasks(): Promise<number> {
  const res = await fetch('/api/v1/tasks/completed', { method: 'DELETE' })
  if (!res.ok) return 0
  const data = await res.json()
  return data.count || 0
}

export async function handleRetryTask(taskId: string): Promise<string | null> {
  const res = await fetch(`/api/v1/tasks/${taskId}/retry`, { method: 'POST' })
  if (!res.ok) return null
  const data = await res.json()
  return data.task_id || null
}
