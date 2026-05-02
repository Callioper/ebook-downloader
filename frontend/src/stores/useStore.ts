import { create } from 'zustand'
import { BookCandidate, SearchResult, TaskDetail, TaskListItem } from '../types'

interface AppState {
  searchResults: SearchResult | null
  searchLoading: boolean
  tasks: TaskListItem[]
  currentTask: TaskDetail | null

  setSearchResults: (r: SearchResult | null) => void
  setSearchLoading: (v: boolean) => void
  setTasks: (t: TaskListItem[]) => void
  setCurrentTask: (t: TaskDetail | null) => void

  searchBooks: (params: Record<string, string>) => Promise<void>
  createTask: (book: BookCandidate) => Promise<string | null>
  startTask: (taskId: string) => Promise<void>
  fetchTask: (taskId: string) => Promise<TaskDetail | null>
  fetchTasks: () => Promise<void>
}

export const useStore = create<AppState>((set) => ({
  searchResults: null,
  searchLoading: false,
  tasks: [],
  currentTask: null,

  setSearchResults: (r) => set({ searchResults: r }),
  setSearchLoading: (v) => set({ searchLoading: v }),
  setTasks: (t) => set({ tasks: t }),
  setCurrentTask: (t) => set({ currentTask: t }),

  searchBooks: async (params) => {
    set({ searchLoading: true })
    try {
      const qs = new URLSearchParams(params).toString()
      const res = await fetch(`/api/v1/search?${qs}`)
      const data: SearchResult = await res.json()
      set({ searchResults: data, searchLoading: false })
    } catch {
      set({ searchLoading: false })
    }
  },

  createTask: async (book) => {
    const res = await fetch('/api/v1/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        book_id: book.id || book.ss_code || '',
        title: book.title,
        isbn: book.isbn,
        ss_code: book.ss_code,
        source: book.source || 'DX_6.0',
        bookmark: book.bookmark || null,
        authors: book.nlc_authors || book.authors || [],
        publisher: book.nlc_publisher || book.publisher || '',
      }),
    })
    const data = await res.json()
    return data.task_id || null
  },

  startTask: async (taskId) => {
    await fetch(`/api/v1/tasks/${taskId}/start`, { method: 'POST' })
  },

  fetchTask: async (taskId) => {
    const res = await fetch(`/api/v1/tasks/${taskId}`)
    if (!res.ok) return null
    const data: TaskDetail = await res.json()
    return data
  },

  fetchTasks: async () => {
    const res = await fetch('/api/v1/tasks')
    const data = await res.json()
    set({ tasks: data.tasks || [] })
  },
}))
