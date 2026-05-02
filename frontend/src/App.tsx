import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import SearchPage from './pages/SearchPage'
import ResultsPage from './pages/ResultsPage'
import TaskDetailPage from './pages/TaskDetailPage'
import TaskListPage from './pages/TaskListPage'
import ConfigSettings from './components/ConfigSettings'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<SearchPage />} />
        <Route path="/results" element={<ResultsPage />} />
        <Route path="/tasks" element={<TaskListPage />} />
        <Route path="/tasks/:id" element={<TaskDetailPage />} />
        <Route path="/config" element={<ConfigSettings />} />
      </Routes>
    </Layout>
  )
}
