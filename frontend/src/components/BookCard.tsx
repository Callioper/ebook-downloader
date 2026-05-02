import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { BookCandidate } from '../types'
import { useStore } from '../stores/useStore'

interface Props {
  book: BookCandidate
}

export default function BookCard({ book }: Props) {
  const [showDetail, setShowDetail] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const createTask = useStore(s => s.createTask)
  const startTask = useStore(s => s.startTask)
  const navigate = useNavigate()

  const handleDownload = async () => {
    setSubmitting(true)
    try {
      const taskId = await createTask(book)
      if (taskId) {
        await startTask(taskId)
        toast.success('下载任务已创建')
        navigate(`/tasks/${taskId}`)
      } else {
        toast.error('创建任务失败')
      }
    } catch {
      toast.error('创建任务失败')
    } finally {
      setSubmitting(false)
    }
  }

  const isExternal = book.source === 'annas_archive' || book.source === 'zlibrary'

  const metaTags = [
    book.publish_date || null,
    book.format || null,
    book.size || null,
    book.language || null,
    book.isbn ? `ISBN ${book.isbn}` : null,
  ].filter(Boolean) as string[]

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-semibold text-gray-800 truncate">{book.title}</h3>
          {isExternal ? (
            <>
              <p className="text-sm text-gray-500 mt-0.5">
                {book.authors?.join(', ') || '佚名'}
              </p>
              {metaTags.length > 0 && (
                <p className="text-xs text-gray-400 mt-1 flex flex-wrap gap-1">
                  {metaTags.map((tag, i) => (
                    <span key={i} className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">
                      {tag}
                    </span>
                  ))}
                </p>
              )}
            </>
          ) : (
            <>
              <p className="text-sm text-gray-500 mt-0.5">
                {book.nlc_authors?.join(', ') || book.authors?.join(', ') || '佚名'}
                {book.nlc_publisher ? ` / ${book.nlc_publisher}` : book.publisher ? ` / ${book.publisher}` : ''}
              </p>
              <p className="text-xs text-gray-400 mt-0.5 flex flex-wrap gap-x-3 gap-y-0.5">
                {book.publish_date ? <span>{book.publish_date}</span> : null}
                {book.format ? <span>{book.format}</span> : null}
                {book.size ? <span>{book.size}</span> : null}
                <span>ISBN: {book.isbn || '—'}</span>
                {book.ss_code ? <span>SS: {book.ss_code}</span> : null}
                <span>来源: {book.source || '—'}</span>
              </p>
            </>
          )}
        </div>
        <div className="flex flex-col items-end gap-1 ml-3">
          {book.nlc_verified ? (
            <span className="text-green-600 text-xs font-medium" title="NLC 已收录">NLC ✓</span>
          ) : (
            <span className="text-gray-300 text-xs">NLC —</span>
          )}
          {book.bookmark_status === 'ok' && (
            <span className="text-blue-600 text-xs font-medium">书葵网 ✓</span>
          )}
        </div>
      </div>

      {book.nlc_comments && (
        <div className="mt-2">
          <button
            onClick={() => setShowDetail(!showDetail)}
            className="text-xs text-indigo-600 hover:text-indigo-800"
          >
            {showDetail ? '收起内容提要 ▲' : '展开内容提要 ▼'}
          </button>
          {showDetail && (
            <p className="text-xs text-gray-500 mt-1 leading-relaxed">{book.nlc_comments}</p>
          )}
        </div>
      )}

      {book.bookmark_preview && (
        <div className="mt-2">
          <p className="text-xs text-gray-400">目录预览:</p>
          <p className="text-xs text-gray-500 font-mono mt-0.5 whitespace-pre-wrap line-clamp-3">
            {book.bookmark_preview}
          </p>
        </div>
      )}

      <div className="mt-3 flex gap-2">
        <button
          onClick={handleDownload}
          disabled={submitting}
          className="px-4 py-1.5 rounded-md bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {submitting ? '提交中...' : isExternal ? '开始任务' : '开始下载'}
        </button>
      </div>
    </div>
  )
}
