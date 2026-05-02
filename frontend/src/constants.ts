export const FIELDS = [
  { key: 'title', label: '书名' },
  { key: 'author', label: '作者' },
  { key: 'publisher', label: '出版社' },
  { key: 'isbn', label: 'ISBN' },
  { key: 'sscode', label: 'SS码' },
]

export const STATUS_LABELS: Record<string, string> = {
  pending: '等待中',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
}

export const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-600',
  running: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
  cancelled: 'bg-yellow-100 text-yellow-700',
}
