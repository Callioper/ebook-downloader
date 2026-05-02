import { useEffect, useRef } from 'react'

interface Props {
  logs: string[]
}

export default function LogStream({ logs }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  return (
    <div className="log-stream h-64 overflow-y-auto font-mono text-xs leading-relaxed">
      {logs.length === 0 ? (
        <p className="text-gray-500">等待日志输出...</p>
      ) : (
        logs.map((line, i) => (
          <div key={i} className="text-green-400 whitespace-pre-wrap break-all">
            {line}
          </div>
        ))
      )}
      <div ref={bottomRef} />
    </div>
  )
}
