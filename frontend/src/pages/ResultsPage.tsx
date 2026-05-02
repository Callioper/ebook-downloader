import { useStore } from '../stores/useStore'
import BookCard from '../components/BookCard'

export default function ResultsPage() {
  const results = useStore(s => s.searchResults)
  const loading = useStore(s => s.searchLoading)

  const searchTimeMs = results?.searchTimeMs || 0
  const total = results?.totalRecords || 0
  const books = results?.books || []
  const externalBooks = results?.external_books || []
  const dbError = results?.error
  const serviceStatus = results?.serviceStatus
  const dbReachable = serviceStatus?.ebookDatabase?.reachable

  return (
    <div>
      <div className="flex items-center gap-4 mb-4">
        <h2 className="text-lg font-semibold text-gray-800">搜索结果</h2>
        {loading && <span className="text-sm text-indigo-500">检索中...</span>}
        {!loading && (
          <span className="text-sm text-gray-500">
            共 {total} 条，耗时 {(searchTimeMs / 1000).toFixed(2)}s
          </span>
        )}
      </div>

      {!loading && books.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <p className="text-lg mb-2">暂无结果</p>
          {dbError && !dbReachable && (
            <div className="max-w-md mx-auto mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-left">
              <p className="text-xs font-medium text-red-700 mb-1">SQLite 数据库无法连接</p>
              <p className="text-xs text-red-600 break-all">{dbError}</p>
            </div>
          )}
          {dbError && dbReachable && (
            <div className="max-w-md mx-auto mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-left">
              <p className="text-xs font-medium text-yellow-700 mb-1">数据库搜索出错</p>
              <p className="text-xs text-yellow-600 break-all">{dbError}</p>
            </div>
          )}
          {!dbError && (
            <p className="text-sm mt-2">请前往「环境配置」Tab 确认 SQLite 数据库目录正确</p>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {books.map((book, i) => (
          <BookCard key={book.id || book.ss_code || i} book={book} />
        ))}
      </div>

      {!loading && externalBooks.length > 0 && (
        <>
          {(() => {
            const aaBooks = externalBooks.filter(b => b.source === 'annas_archive')
            const zlBooks = externalBooks.filter(b => b.source === 'zlibrary')
            return (
              <>
                {aaBooks.length > 0 && (
                  <>
                    <h3 className="text-base font-semibold text-gray-700 mt-6 mb-3">
                      外部来源 - Anna's Archive
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {aaBooks.map((book, i) => (
                        <BookCard key={book.id || i} book={book} />
                      ))}
                    </div>
                  </>
                )}
                {zlBooks.length > 0 && (
                  <>
                    <h3 className="text-base font-semibold text-gray-700 mt-6 mb-3">
                      外部来源 - Z-Library
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {zlBooks.map((book, i) => (
                        <BookCard key={book.id || i} book={book} />
                      ))}
                    </div>
                  </>
                )}
              </>
            )
          })()}
        </>
      )}
    </div>
  )
}
