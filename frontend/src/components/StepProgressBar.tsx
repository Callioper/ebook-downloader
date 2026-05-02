import { TaskStep } from '../types'

interface Props {
  steps: TaskStep[]
}

const statusIcon = (status: string) => {
  switch (status) {
    case 'completed': return '✓'
    case 'running': return '◌'
    case 'failed': return '✗'
    default: return '○'
  }
}

const statusColor = (status: string) => {
  switch (status) {
    case 'completed': return 'bg-green-500 border-green-500 text-white'
    case 'running': return 'bg-blue-500 border-blue-500 text-white animate-pulse'
    case 'failed': return 'bg-red-500 border-red-500 text-white'
    default: return 'bg-gray-200 border-gray-300 text-gray-500'
  }
}

export default function StepProgressBar({ steps }: Props) {
  if (steps.length === 0) {
    return <p className="text-sm text-gray-400">等待任务开始...</p>
  }

  return (
    <div className="flex items-start gap-0 overflow-x-auto pb-2">
      {steps.map((step, i) => (
        <div key={step.step} className="flex items-start" style={{ minWidth: step.status === 'running' && step.progress_pct !== undefined ? '180px' : '110px' }}>
          <div className="flex flex-col items-center">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 ${statusColor(step.status)}`}
              title={step.name}
            >
              {step.status === 'running' && step.progress_pct !== undefined ? `${step.progress_pct}%` : statusIcon(step.status)}
            </div>
          </div>
          <div className="ml-2 flex flex-col min-w-0 flex-1">
            <span className="text-xs font-medium text-gray-700 truncate">{step.name}</span>
            {step.status === 'running' && step.progress_pct !== undefined && (
              <div className="mt-1 w-full">
                <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-2 bg-blue-500 rounded-full transition-all duration-500"
                    style={{ width: `${step.progress_pct}%` }}
                  />
                </div>
                {step.progress_message && (
                  <p className="text-xs text-gray-500 mt-1 truncate">{step.progress_message}</p>
                )}
              </div>
            )}
            {step.elapsed_ms != null && step.elapsed_ms > 0 && (
              <span className="text-xs text-gray-400">{(step.elapsed_ms / 1000).toFixed(1)}s</span>
            )}
          </div>
          {i < steps.length - 1 && (
            <div className={`flex-1 h-0.5 mt-4 mx-1 ${step.status === 'completed' ? 'bg-green-400' : 'bg-gray-200'}`} />
          )}
        </div>
      ))}
    </div>
  )
}
