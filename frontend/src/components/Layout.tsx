import { Link } from 'react-router-dom'

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" className="text-lg font-bold text-indigo-700 hover:text-indigo-800">
            Agent Ebook Downloader
          </Link>
          <div className="flex gap-4 text-sm">
            <Link to="/" className="text-gray-600 hover:text-indigo-600">检索</Link>
            <Link to="/tasks" className="text-gray-600 hover:text-indigo-600">任务</Link>
            <Link to="/config" className="text-gray-600 hover:text-indigo-600">设置</Link>
          </div>
        </div>
      </nav>
      <main className="max-w-6xl mx-auto px-4 py-6">
        {children}
      </main>
    </div>
  )
}
