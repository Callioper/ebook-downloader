import { TaskReport as TaskReportType } from '../types'

interface Props {
  report: TaskReportType
  status: string
  taskId: string
}

export default function TaskReport({ report, status, taskId }: Props) {
  if (!report) return null

  const isPartial = status === 'failed'
  const isComplete = status === 'completed'

  return (
    <div className="space-y-3 text-sm">
      {isPartial && (
        <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md text-yellow-800 text-xs">
          部分步骤执行失败，以下为已完成步骤的信息
        </div>
      )}

      <div className="grid grid-cols-2 gap-x-4 gap-y-2">
        <div>
          <span className="text-gray-400">书名：</span>
          <span className="font-medium text-gray-800">{report.title || '—'}</span>
        </div>
        <div>
          <span className="text-gray-400">ISBN：</span>
          <span className="font-mono text-gray-600">{report.isbn || '—'}</span>
        </div>
        <div>
          <span className="text-gray-400">作者：</span>
          <span className="text-gray-700">{report.authors?.join(', ') || '—'}</span>
        </div>
        <div>
          <span className="text-gray-400">出版社：</span>
          <span className="text-gray-700">{report.publisher || '—'}</span>
        </div>
      </div>

      {isComplete && (
        <div className="flex gap-2 pt-2">
          <button
            onClick={() => window.open(`/api/v1/tasks/${taskId}/open`, '_blank')}
            className="px-3 py-1.5 text-xs font-medium rounded border border-indigo-300 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition-colors"
          >
            Open PDF
          </button>
          <button
            onClick={() => window.open(`/api/v1/tasks/${taskId}/open-folder`, '_blank')}
            className="px-3 py-1.5 text-xs font-medium rounded border border-gray-300 bg-gray-50 text-gray-700 hover:bg-gray-100 transition-colors"
          >
            Open Folder
          </button>
        </div>
      )}

      {(report.direct_link_internal || report.direct_link_external) && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-md">
          <p className="text-xs font-medium text-green-800 mb-2">下载链接</p>
          {report.direct_link_internal && (
            <div className="mb-1">
              <span className="text-xs text-gray-400">内网：</span>
              <a
                href={report.direct_link_internal}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-indigo-600 hover:text-indigo-800 break-all font-mono"
              >
                {report.direct_link_internal}
              </a>
            </div>
          )}
          {report.direct_link_external && (
            <div>
              <span className="text-xs text-gray-400">外网：</span>
              <a
                href={report.direct_link_external}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-indigo-600 hover:text-indigo-800 break-all font-mono"
              >
                {report.direct_link_external}
              </a>
            </div>
          )}
          {report.filename && (
            <p className="text-xs text-gray-400 mt-1">
              文件: {report.filename} · {report.file_size_mb} MB
            </p>
          )}
        </div>
      )}

      {report.errors && report.errors.length > 0 && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-xs font-medium text-red-800 mb-1">错误信息</p>
          {report.errors.map((err, i) => (
            <p key={i} className="text-xs text-red-600">
              步骤 {err.step}: {err.error}
            </p>
          ))}
        </div>
      )}
    </div>
  )
}
