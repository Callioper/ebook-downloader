import { useState } from 'react'

import { FIELDS } from '../constants'

const BASIC_FIELDS = FIELDS.filter(f => f.key !== 'sscode').map(f => ({ value: f.key, label: f.label }))

interface Props {
  onSearch: (params: Record<string, string>) => void
  loading: boolean
}

export default function BasicSearchForm({ onSearch, loading }: Props) {
  const [field, setField] = useState('title')
  const [query, setQuery] = useState('')
  const [fuzzy, setFuzzy] = useState(true)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    const params: Record<string, string> = { field, query: query.trim(), fuzzy: String(fuzzy), page: '1', page_size: '20' }
    onSearch(params)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="flex gap-3 items-end">
        <div className="w-32">
          <label className="block text-xs font-medium text-gray-600 mb-1">搜索字段</label>
          <select
            value={field}
            onChange={e => setField(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          >
            {BASIC_FIELDS.map(f => (
              <option key={f.value} value={f.value}>{f.label}</option>
            ))}
          </select>
        </div>
        <div className="flex-1">
          <label className="block text-xs font-medium text-gray-600 mb-1">关键词</label>
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="输入书名、作者、ISBN 或 SS码..."
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="h-10 px-6 rounded-md bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? '检索中...' : '搜索'}
        </button>
      </div>
      <label className="inline-flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
        <input
          type="checkbox"
          checked={fuzzy}
          onChange={e => setFuzzy(e.target.checked)}
          className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
        />
        模糊搜索
      </label>
    </form>
  )
}
