import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useStore } from '../stores/useStore'
import { statusBadge, handleDeleteTask, handleClearAllTasks, handleDeleteCompletedTasks, handleRetryTask } from '../utils/statusBadge'

export default function TaskListPage() {
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

  const handleClearCompleted = async () => {
    try {
      const count = await handleDeleteCompletedTasks()
      if (count > 0) {
        toast.success(`已清除 ${count} 个已完成/失败任务`)
        fetchTasks()
      } else {
        toast('无可清除的任务')
      }
    } catch { toast.error('清除失败') }
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

  const handleRetryAllFailed = async () => {
    const failedTasks = tasks.filter(t => t.status === 'failed')
    if (failedTasks.length === 0) {
      toast('没有可重试的失败任务')
      return
    }
    let successCount = 0
    for (const task of failedTasks) {
      try {
        const newId = await handleRetryTask(task.task_id)
        if (newId) successCount++
      } catch { /* continue */ }
    }
    if (successCount > 0) {
      toast.success(`已重试 ${successCount}/${failedTasks.length} 个失败任务`)
      fetchTasks()
    } else {
      toast.error('重试失败')
    }
  }

  const hasCompletedOrFailed = tasks.some(t => t.status === 'completed' || t.status === 'failed')
  const hasFailed = tasks.some(t => t.status === 'failed')

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800">历史任务</h2>
        {tasks.length > 0 && (
          <div className="flex gap-2">
            {hasCompletedOrFailed && (
              <button
                onClick={handleClearCompleted}
                className="text-xs text-orange-500 hover:text-orange-700 border border-orange-200 rounded px-3 py-1 hover:bg-orange-50"
              >
                清除已完成
              </button>
            )}
            {hasFailed && (
              <button
                onClick={handleRetryAllFailed}
                className="text-xs text-blue-500 hover:text-blue-700 border border-blue-200 rounded px-3 py-1 hover:bg-blue-50"
              >
                重试失败
              </button>
            )}
            <button
              onClick={handleClearAll}
              className="text-xs text-red-500 hover:text-red-700 border border-red-200 rounded px-3 py-1 hover:bg-red-50"
            >
               清空全部
            </button>
          </div>
        )}
      </div>
      <div className="rounded-lg bg-white shadow-sm border border-gray-200 overflow-hidden">
        {tasks.length === 0 ? (
          <p className="text-gray-400 text-sm py-12 text-center">暂无任务记录</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">任务 ID</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">书名</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">状态</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">步骤</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">时间</th>
                <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 w-12">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tasks.map(task => (
                <tr
                  key={task.task_id}
                  onClick={() => navigate(`/tasks/${task.task_id}`)}
                  className="hover:bg-indigo-50/50 cursor-pointer transition-colors group"
                >
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{task.task_id}</td>
                  <td className="px-4 py-3 text-gray-800 truncate max-w-[200px]">
                    {task.params && typeof task.params === 'object' && 'title' in task.params
                      ? String(task.params.title) : '—'}
                  </td>
                  <td className="px-4 py-3">{statusBadge(task.status)}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{task.current_step_name || '—'}</td>
                  <td className="px-4 py-3 text-xs text-gray-400">{task.updated_at?.slice(0, 16) || '—'}</td>
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={e => handleDelete(e, task.task_id)}
                      className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600 text-sm transition-opacity"
                      title="删除"
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
