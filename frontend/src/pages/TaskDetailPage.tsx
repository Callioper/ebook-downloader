import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useTaskWebSocket } from '../hooks/useTaskWebSocket'
import StepProgressBar from '../components/StepProgressBar'
import LogStream from '../components/LogStream'
import TaskReport from '../components/TaskReport'
import { handleRetryTask } from '../utils/statusBadge'

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { steps, logs, report, wsStatus, taskStatus } = useTaskWebSocket(id || null)
  const navigate = useNavigate()
  const [restStatus, setRestStatus] = useState<string>('')
  const displayStatus = taskStatus || restStatus

  useEffect(() => {
    if (!id) return
    fetch(`/api/v1/tasks/${id}`)
      .then(r => r.json())
      .then(data => setRestStatus(data.status || ''))
      .catch(() => {})
  }, [id])

  const handleRetry = async () => {
    if (!id) return
    try {
      const newTaskId = await handleRetryTask(id)
      if (newTaskId) {
        toast.success('已创建重试任务')
        navigate(`/tasks/${newTaskId}`)
      } else {
        toast.error('重试失败')
      }
    } catch { toast.error('重试失败') }
  }

  const wsIndicator = {
    connecting: 'text-yellow-500',
    connected: 'text-green-500',
    disconnected: 'text-gray-400',
  }[wsStatus]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-gray-800">
            任务详情 <span className="text-sm text-gray-400 font-mono">{id}</span>
          </h2>
          {displayStatus === 'failed' && (
            <button
              onClick={handleRetry}
              className="text-xs text-blue-500 hover:text-blue-700 border border-blue-200 rounded px-3 py-1 hover:bg-blue-50"
            >
              重试
            </button>
          )}
        </div>
        <span className={`text-xs font-medium ${wsIndicator}`}>
          ● {wsStatus === 'connected' ? '已连接' : wsStatus === 'connecting' ? '连接中...' : '已断开'}
        </span>
      </div>

      <div className="rounded-lg bg-white p-6 shadow-sm border border-gray-200">
        <h3 className="text-sm font-medium text-gray-600 mb-4">执行进度</h3>
        <StepProgressBar steps={steps} />
      </div>

      <div className="rounded-lg bg-[#1a1a2e] p-4 shadow-sm border border-gray-700">
        <h3 className="text-sm font-medium text-gray-400 mb-3">执行日志</h3>
        <LogStream logs={logs} />
      </div>

      {report && (displayStatus === 'completed' || displayStatus === 'failed') && (
        <div className="rounded-lg bg-white p-6 shadow-sm border border-gray-200">
          <h3 className="text-sm font-medium text-gray-600 mb-4">
            {displayStatus === 'completed' ? '执行报告' : '执行报告（部分失败）'}
          </h3>
          <TaskReport report={report} status={displayStatus} taskId={id || ''} />
        </div>
      )}
    </div>
  )
}
