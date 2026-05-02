import { useEffect, useRef, useState, useCallback } from 'react'
import { WsMessage, TaskStep, TaskReport } from '../types'

export function useTaskWebSocket(taskId: string | null) {
  const [steps, setSteps] = useState<TaskStep[]>([])
  const [logs, setLogs] = useState<string[]>([])
  const [report, setReport] = useState<TaskReport | null>(null)
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected')
  const [taskStatus, setTaskStatus] = useState<string>('')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<number | null>(null)
  const taskStatusRef = useRef(taskStatus)
  taskStatusRef.current = taskStatus

  const connect = useCallback(() => {
    if (!taskId) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/tasks/${taskId}`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws
    setWsStatus('connecting')

    ws.onopen = () => setWsStatus('connected')

    ws.onmessage = (event) => {
      const msg: WsMessage = JSON.parse(event.data)
      switch (msg.type) {
        case 'sync':
          setSteps(msg.steps || [])
          setLogs(msg.log_lines || [])
          setReport(msg.report)
          setTaskStatus(msg.status)
          break
        case 'step_start':
          setSteps(prev => prev.map(s =>
            s.step === msg.step ? { ...s, status: 'running' as const } : s
          ))
          break
        case 'step_progress':
          setSteps(prev => prev.map(s =>
            s.step === msg.step ? { ...s, status: 'running' as const, progress_pct: msg.progress_pct, progress_message: msg.message } : s
          ))
          break
        case 'step_complete':
          setSteps(prev => prev.map(s =>
            s.step === msg.step ? { ...s, status: 'completed' as const, elapsed_ms: msg.elapsed_ms } : s
          ))
          break
        case 'log':
          setLogs(prev => [...prev, msg.message])
          break
        case 'task_complete':
          setReport(msg.report)
          setTaskStatus('completed')
          setWsStatus('disconnected')
          ws.close()
          break
        case 'task_error':
          setSteps(prev => prev.map(s =>
            s.step === msg.step ? { ...s, status: 'failed' as const } : s
          ))
          setTaskStatus('failed')
          setWsStatus('disconnected')
          ws.close()
          break
      }
    }

    ws.onclose = () => {
      setWsStatus('disconnected')
      const currentStatus = taskStatusRef.current
      if (currentStatus !== 'completed' && currentStatus !== 'failed') {
        reconnectTimer.current = window.setTimeout(connect, 3000)
      }
    }

    ws.onerror = () => ws.close()
  }, [taskId])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
    }
  }, [connect])

  return { steps, logs, report, wsStatus, taskStatus }
}
