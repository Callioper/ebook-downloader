import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStore } from '../stores/useStore'
import BasicSearchForm from '../components/BasicSearchForm'
import AdvancedSearchForm from '../components/AdvancedSearchForm'
import TaskListPanel from '../components/TaskListPanel'

export default function SearchPage() {
  const [tab, setTab] = useState<'basic' | 'advanced'>('basic')
  const navigate = useNavigate()
  const searchBooks = useStore(s => s.searchBooks)
  const searchLoading = useStore(s => s.searchLoading)

  const doSearch = async (params: Record<string, string>) => {
    await searchBooks(params)
    const qs = new URLSearchParams(params).toString()
    navigate(`/results?${qs}`)
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg bg-white p-6 shadow-lg">
        <div className="flex border-b border-gray-200 mb-6">
          {[
            ['basic', '基础检索'],
            ['advanced', '高级检索'],
          ].map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key as typeof tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                tab === key
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === 'basic' && <BasicSearchForm onSearch={doSearch} loading={searchLoading} />}
        {tab === 'advanced' && <AdvancedSearchForm onSearch={doSearch} loading={searchLoading} />}
      </div>

      <div className="rounded-lg bg-white p-6 shadow-lg">
        <h2 className="text-base font-semibold text-gray-800 mb-4">最近任务</h2>
        <TaskListPanel />
      </div>
    </div>
  )
}