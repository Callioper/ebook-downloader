import { useState } from 'react'
import { FIELDS as SHARED_FIELDS } from '../constants'

const FIELDS = SHARED_FIELDS.map(f => ({ value: f.key, label: f.label }))

interface Condition {
  field: string
  query: string
  logic: 'AND' | 'OR'
  fuzzy: boolean
}

interface Props {
  onSearch: (params: Record<string, string>) => void
  loading: boolean
}

export default function AdvancedSearchForm({ onSearch, loading }: Props) {
  const [conditions, setConditions] = useState<Condition[]>([
    { field: 'title', query: '', logic: 'AND', fuzzy: true },
  ])

  const updateCondition = (i: number, update: Partial<Condition>) => {
    setConditions(prev => prev.map((c, idx) => idx === i ? { ...c, ...update } : c))
  }

  const addCondition = () => {
    if (conditions.length >= 6) return
    setConditions(prev => [...prev, { field: 'title', query: '', logic: 'AND', fuzzy: true }])
  }

  const removeCondition = (i: number) => {
    if (conditions.length <= 1) return
    setConditions(prev => prev.filter((_, idx) => idx !== i))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const valid = conditions.filter(c => c.query.trim())
    if (valid.length === 0) return
    const params: Record<string, string> = {
      page: '1',
      page_size: '20',
    }
    valid.forEach((c, i) => {
      params[`fields[${i}]`] = c.field
      params[`queries[${i}]`] = c.query.trim()
      params[`fuzzies[${i}]`] = String(c.fuzzy)
      if (i > 0) params[`logics[${i - 1}]`] = c.logic
    })
    onSearch(params)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {conditions.map((c, i) => (
        <div key={i} className="flex gap-2 items-end">
          {i > 0 && (
            <div className="w-16">
              <select
                value={c.logic}
                onChange={e => updateCondition(i, { logic: e.target.value as 'AND' | 'OR' })}
                className="w-full rounded-md border border-gray-300 px-2 py-2 text-xs font-medium"
              >
                <option value="AND">AND</option>
                <option value="OR">OR</option>
              </select>
            </div>
          )}
          {i === 0 && <div className="w-16" />}
          <div className="w-28">
            <select
              value={c.field}
              onChange={e => updateCondition(i, { field: e.target.value })}
              className="w-full rounded-md border border-gray-300 px-2 py-2 text-sm"
            >
              {FIELDS.map(f => (
                <option key={f.value} value={f.value}>{f.label}</option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <input
              type="text"
              value={c.query}
              onChange={e => updateCondition(i, { query: e.target.value })}
              placeholder="输入关键词..."
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <label className="flex items-center gap-1 text-xs text-gray-500 whitespace-nowrap">
            <input
              type="checkbox"
              checked={c.fuzzy}
              onChange={e => updateCondition(i, { fuzzy: e.target.checked })}
              className="rounded border-gray-300 text-indigo-600"
            />
            模糊
          </label>
          <button
            type="button"
            onClick={() => removeCondition(i)}
            disabled={conditions.length <= 1}
            className="px-2 py-2 text-red-500 hover:text-red-700 disabled:opacity-30 text-sm"
          >
            ✕
          </button>
        </div>
      ))}

      <div className="flex gap-3 pt-2">
        <button
          type="button"
          onClick={addCondition}
          disabled={conditions.length >= 6}
          className="px-4 py-2 text-sm border border-dashed border-gray-300 rounded-md text-gray-500 hover:border-indigo-400 hover:text-indigo-600 disabled:opacity-40"
        >
          + 添加条件 ({conditions.length}/6)
        </button>
        <button
          type="submit"
          disabled={loading || conditions.every(c => !c.query.trim())}
          className="px-6 py-2 rounded-md bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? '检索中...' : '搜索'}
        </button>
      </div>
    </form>
  )
}
