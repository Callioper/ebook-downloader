import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useStore } from '../stores/useStore'
import { statusBadge, handleDeleteTask, handleClearAllTasks } from '../utils/statusBadge'

export default function TaskListPanel() {
  const tasks = useStore(s => s.tasks)
  const fetchTasks = useStore(s => s.fetchTasks)
  const navigate = useNavigate()

  useEffect(() => { fetchTasks() }, [fetchTasks])

  const handleDelete = async (e: React.MouseEvent, taskId: string) => {
    e.stopPropagation()
    try {
      if (await handleDeleteTask(taskId)) {
        toast.success('任务已删除')
        fetchTasks()
      }
    } catch { toast.error('删除失败') }
  }

  const handleClearAll = async () => {
    if (!confirm('确定清除所有任务？此操作不可恢复。')) return
    try {
      if (await handleClearAllTasks()) {
        toast.success('全部任务已清除')
        fetchTasks()
      }
    } catch { toast.error('清除失败') }
  }

  if (tasks.length === 0) {
    return <p className="text-gray-400 text-sm py-8 text-center">暂无任务</p>
  }

  return (
    <div>
      {tasks.length > 1 && (
        <div className="flex justify-end mb-2">
          <button
            onClick={handleClearAll}
            className="text-xs text-red-500 hover:text-red-700 border border-red-200 rounded px-2 py-0.5 hover:bg-red-50"
          >
            清除全部
          </button>
        </div>
      )}
      <div className="space-y-2">
        {tasks.map(task => (
          <div
            key={task.task_id}
            onClick={() => navigate(`/tasks/${task.task_id}`)}
            className="flex items-center justify-between p-3 rounded-lg border border-gray-200 hover:border-indigo-300 hover:bg-indigo-50/50 cursor-pointer transition-colors group"
          >
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-800 truncate">
                {task.params && typeof task.params === 'object' && 'title' in task.params
                  ? String(task.params.title) : task.task_id}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                {task.current_step_name || '—'} · {task.updated_at?.slice(0, 16)}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {statusBadge(task.status)}
              <button
                onClick={e => handleDelete(e, task.task_id)}
                className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600 text-sm px-1 transition-opacity"
                title="删除任务"
              >
                ✕
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
