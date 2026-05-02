import { useState, useEffect, useRef, useCallback } from 'react'

interface ServiceStatus {
  reachable: boolean
  dbs?: string[]
  note?: string
  error?: string
}

interface StatusResponse {
  ebookDatabase: ServiceStatus
}

interface ConfigData {
  ebook_db_path: string
  http_proxy: string
  download_dir: string
  finished_dir: string
  tmp_dir: string
  ocr_jobs: number
  ocr_languages: string
  ocr_timeout: number
  ocr_engine: string
  nlc_max_workers: number
  host: string
  port: number
  zlib_remix_userid?: string
  zlib_remix_userkey?: string
  zlib_email?: string
  zlib_password?: string
  aa_membership_key?: string
}

interface PathSuggestion {
  path: string
  dbs: string[]
  exists: boolean
}

interface ProxyStatus {
  annas_archive: { reachable: boolean; latency_ms?: number }
  zlibrary: { configured: boolean; api_reachable?: boolean; api_available: boolean }
}

interface OCRStatus {
  installed: boolean
  version?: string
  engines: Record<string, { available: boolean }>
}

function StatusDot({ state }: { state: 'green' | 'red' | 'yellow' }) {
  const color = state === 'green' ? 'bg-green-500' : state === 'red' ? 'bg-red-500' : 'bg-yellow-400'
  return <span className={`inline-block w-2 h-2 rounded-full mr-1.5 shrink-0 ${color}`} />
}

function BrowseButton({ onPathDetected }: { onPathDetected: (path: string) => void }) {
  const inputRef = useRef<HTMLInputElement>(null)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      const file = files[0] as any
      if (file.path) {
        const dir = file.path.replace(/[\\/][^\\/]+$/, '')
        onPathDetected(dir)
      } else if (file.webkitRelativePath) {
        const parts = file.webkitRelativePath.split('/')
        const dirName = parts.slice(0, -1).join('/')
        if (dirName) {
          onPathDetected(dirName)
        }
      }
    }
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <>
      <input ref={inputRef} type="file" className="hidden" onChange={handleChange} />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        className="px-2 py-1.5 text-xs rounded border border-gray-300 bg-white hover:bg-gray-50 text-gray-500 shrink-0"
        title="选择文件夹"
      >
        [...]
      </button>
    </>
  )
}

export default function ConfigSettings() {
  const [config, setConfig] = useState<ConfigData | null>(null)
  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [detecting, setDetecting] = useState(false)
  const [detectedPaths, setDetectedPaths] = useState<PathSuggestion[]>([])
  const [expandedSection, setExpandedSection] = useState<string | null>('download')

  const [proxyStatus, setProxyStatus] = useState<ProxyStatus | null>(null)
  const [checkingProxy, setCheckingProxy] = useState(false)
  const proxyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [ocrStatus, setOCRStatus] = useState<OCRStatus | null>(null)
  const [checkingOCR, setCheckingOCR] = useState(false)
  const [ocrEngine, setOcrEngine] = useState('tesseract')
  const [ocrInstallMsg, setOcrInstallMsg] = useState('')
  const [checkingEngine, setCheckingEngine] = useState<string | null>(null)
  const [installingEngine, setInstallingEngine] = useState<string | null>(null)

  const [aaMembershipKey, setAaMembershipKey] = useState('')
  const [savingAaKey, setSavingAaKey] = useState(false)
  const [aaKeyMsg, setAaKeyMsg] = useState('')

  const [zlibUserid, setZlibUserid] = useState('')
  const [zlibEmail, setZlibEmail] = useState('')
  const [zlibPassword, setZlibPassword] = useState('')
  const [fetchingZlibTokens, setFetchingZlibTokens] = useState(false)
  const [zlibMsg, setZlibMsg] = useState('')
  const [flareStatus, setFlareStatus] = useState<boolean | null>(null)
  const [zlibQuota, setZlibQuota] = useState<{ downloads_left: number; downloads_limit: number } | null>(null)

  useEffect(() => {
    fetch('/api/v1/config')
      .then(r => r.json())
      .then((data: ConfigData) => {
        setConfig(data)
        setAaMembershipKey(data.aa_membership_key || '')
        setZlibUserid(data.zlib_remix_userid || '')
        setZlibEmail(data.zlib_email || '')
        setZlibPassword(data.zlib_password || '')
        if (data.ocr_engine) setOcrEngine(data.ocr_engine)
        if (data.http_proxy) {
          checkProxy(data.http_proxy)
        }
        if ((data.zlib_remix_userid && data.zlib_remix_userkey) || (data.zlib_email && data.zlib_password)) {
          fetchZlibQuota()
        }
      })
      .catch(() => {})
    fetch('/api/v1/status')
      .then(r => r.json())
      .then(setStatus)
      .catch(() => {})
    fetch('/api/v1/check-flare')
      .then(r => r.json())
      .then((data) => setFlareStatus(data.available ?? false))
      .catch(() => setFlareStatus(false))
    fetch('/api/v1/check-ocr')
      .then(r => r.json())
      .then((data) => {
        setOCRStatus(data)
        if (!data.installed) setExpandedSection(prev => prev || 'ocr')
      })
      .catch(() => {})
  }, [])

  // Auto-expand unconfigured sections when status/data loads
  useEffect(() => {
    if (status && !status.ebookDatabase?.reachable) setExpandedSection(prev => prev || 'db')
  }, [status])
  useEffect(() => {
    if (proxyStatus && !proxyStatus.annas_archive?.reachable) setExpandedSection(prev => prev || 'proxy')
  }, [proxyStatus])
  useEffect(() => {
    if (config && !config.zlib_remix_userid) {
      // Silently keep download expanded if ZL not configured
    }
  }, [config])

  const checkProxy = useCallback(async (proxy: string) => {
    if (!proxy) {
      setProxyStatus(null)
      return
    }
    setCheckingProxy(true)
    try {
      const res = await fetch('/api/v1/check-proxy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ http_proxy: proxy }),
      })
      if (res.ok) {
        const data = await res.json()
        setProxyStatus(data)
      }
    } catch {
      setProxyStatus(null)
    }
    setCheckingProxy(false)
  }, [])

  const handleProxyChange = (value: string) => {
    if (!config) return
    setConfig({ ...config, http_proxy: value })
    setProxyStatus(null)
    if (proxyTimerRef.current) clearTimeout(proxyTimerRef.current)
    if (value) {
      proxyTimerRef.current = setTimeout(() => checkProxy(value), 2000)
    }
  }

  const handleSmartDetect = async () => {
    setDetecting(true)
    setDetectedPaths([])
    try {
      const res = await fetch('/api/v1/detect-paths')
      const data = await res.json()
      setDetectedPaths(data.paths || [])
    } catch {
      setMessage('路径检测失败')
    }
    setDetecting(false)
  }

  const applyPath = (path: string) => {
    if (config) {
      setConfig({ ...config, ebook_db_path: path })
      setDetectedPaths([])
      setMessage(`已应用路径: ${path}`)
      setTimeout(() => setMessage(''), 3000)
    }
  }

  const handleFetchZlibTokens = async () => {
    setFetchingZlibTokens(true)
    setZlibMsg('')
    try {
      const res = await fetch('/api/v1/zlib-fetch-tokens', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: zlibEmail.trim(), password: zlibPassword.trim() }),
      })
      const data = await res.json()
      if (data.success) {
        setZlibUserid(data.remix_userid)
        setZlibMsg('登录成功，Token 已保存')
        fetch('/api/v1/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            zlib_remix_userid: data.remix_userid,
            zlib_remix_userkey: data.remix_userkey,
          }),
        }).then(() => fetchZlibQuota()).catch(() => {})
      } else {
        setZlibMsg(data.error || '获取 Token 失败')
      }
    } catch {
      setZlibMsg('请求失败，请检查网络和代理')
    }
    setFetchingZlibTokens(false)
  }

  const fetchZlibQuota = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/zlib-quota')
      if (res.ok) {
        const data = await res.json()
        setZlibQuota(data)
      }
    } catch {
      setZlibQuota(null)
    }
  }, [])

  const handleSaveAaKey = async () => {
    setSavingAaKey(true)
    setAaKeyMsg('')
    try {
      const res = await fetch('/api/v1/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ aa_membership_key: aaMembershipKey.trim() }),
      })
      if (res.ok) setAaKeyMsg('会员 Key 已保存')
      else setAaKeyMsg('保存失败')
    } catch {
      setAaKeyMsg('保存失败')
    }
    setSavingAaKey(false)
  }

  const handleInstallEngine = async (engine: string) => {
    setInstallingEngine(engine)
    setOcrInstallMsg('')
    try {
      const res = await fetch('/api/v1/install-ocr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ engine }),
      })
      const data = await res.json()
      if (res.ok && data.status === 'ok') {
        setOcrInstallMsg(`${engine} 安装成功`)
      } else if (data.status === 'warning') {
        setOcrInstallMsg(data.message)
      } else {
        setOcrInstallMsg(`安装失败: ${data.message || data.detail || '未知错误'}`)
      }
      const r = await fetch('/api/v1/check-ocr')
      if (r.ok) setOCRStatus(await r.json())
    } catch {
      setOcrInstallMsg('安装请求失败')
    }
    setInstallingEngine(null)
  }

  const handleCheckOCR = async () => {
    setCheckingOCR(true)
    try {
      const res = await fetch('/api/v1/check-ocr')
      if (res.ok) setOCRStatus(await res.json())
    } catch { /* ignore */ }
    setCheckingOCR(false)
  }

  const handleCheckEngine = async (engine: string) => {
    setCheckingEngine(engine)
    try {
      const res = await fetch('/api/v1/check-ocr')
      if (res.ok) setOCRStatus(await res.json())
    } catch { /* ignore */ }
    setCheckingEngine(null)
  }

  const handleSave = async () => {
    setSaving(true)
    setMessage('')
    try {
      const res = await fetch('/api/v1/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
      if (res.ok) setMessage('配置已保存，重启服务后生效')
      else setMessage('保存失败')
    } catch {
      setMessage('保存失败')
    }
    setSaving(false)
  }

  const toggleSection = (section: string) => {
    setExpandedSection(prev => (prev === section ? null : section))
  }

  const dbReachable = status?.ebookDatabase?.reachable ?? false
  const dbNames = status?.ebookDatabase?.dbs?.join(', ') || '未连接'

  const proxySummary = !config?.http_proxy
    ? null
    : proxyStatus
      ? (
        <>
          AA <StatusDot             state={
              !proxyStatus.zlibrary?.configured
                ? 'yellow'
                : proxyStatus.zlibrary?.api_available
                  ? 'green'
                  : proxyStatus.zlibrary?.api_reachable
                    ? 'yellow'
                    : 'red'
            }
          />
          {' '}ZL{' '}
          <StatusDot
            state={
              !proxyStatus.zlibrary?.configured
                ? 'yellow'
                : proxyStatus.zlibrary?.api_available
                  ? 'green'
                  : proxyStatus.zlibrary?.api_reachable
                    ? 'yellow'
                    : 'red'
            }
          />
        </>
      )
      : '检测中...'

  const ocrSummary = ocrStatus
    ? ocrStatus.installed
      ? `已安装 ${ocrStatus.version || ''}`
      : '未安装'
    : '检测中...'

  const downloadConfigured = config?.download_dir && flareStatus === true
  const downloadSummary = config?.download_dir
    ? (flareStatus ? 'FlareSolverr 可用' : 'FlareSolverr 未运行')
    : '未设置下载目录'

  if (!config) {
    return <p className="text-gray-400 text-sm text-center py-8">Loading...</p>
  }

  return (
    <div className="space-y-4 max-w-4xl">
      <div className="space-y-3">

        {/* 数据库 */}
        <div
          className={`rounded-lg bg-white border border-gray-200 cursor-pointer hover:shadow-sm transition-shadow border-l-4 border-l-blue-500`}
          onClick={() => toggleSection('db')}
        >
          <div className="p-4">
            <div className="flex items-center justify-between min-w-0">
              <span className="text-sm font-medium text-gray-700 shrink-0">数据库</span>
              <span className="text-sm text-gray-500 truncate ml-2">
                <StatusDot state={dbReachable ? 'green' : 'red'} />
                {dbReachable ? `已连接 ${dbNames}` : '未连接'}
              </span>
            </div>
          </div>
          {expandedSection === 'db' && (
            <div className="px-4 pb-4 pt-3 mt-3 border-t border-gray-100" onClick={e => e.stopPropagation()}>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">数据库目录</label>
                <div className="flex gap-1">
                  <input
                    type="text"
                    value={config.ebook_db_path || ''}
                    onChange={e => setConfig({ ...config, ebook_db_path: e.target.value })}
                    placeholder="C:\...\EbookDatabase\instance"
                    className="w-full rounded border border-gray-300 px-2 py-1.5 text-xs font-mono focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                  <BrowseButton onPathDetected={(path) => setConfig({ ...config, ebook_db_path: path })} />
                  <button
                    type="button"
                    onClick={handleSmartDetect}
                    disabled={detecting}
                    className="px-2 py-1.5 text-xs rounded border border-indigo-300 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 shrink-0 disabled:opacity-50"
                  >
                    {detecting ? '查找中...' : '智能查找'}
                  </button>
                </div>
                {detectedPaths.length > 0 && (
                  <div className="mt-1 border border-gray-200 rounded bg-white divide-y divide-gray-100 max-h-40 overflow-y-auto">
                    {detectedPaths.map((p, i) => (
                      <div
                        key={i}
                        className={`px-2 py-1 flex items-center justify-between text-xs ${p.exists ? 'hover:bg-green-50 cursor-pointer' : 'opacity-50'}`}
                        onClick={() => p.exists && applyPath(p.path)}
                      >
                        <div>
                          <span className="font-mono text-gray-600">{p.path}</span>
                          {p.dbs.length > 0 && (
                            <span className="ml-2 text-green-600">({p.dbs.join(', ')})</span>
                          )}
                        </div>
                        {p.exists && <span className="text-indigo-500 text-xs ml-2 shrink-0">应用</span>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* 下载 */}
        <div
          className={`rounded-lg bg-white border border-gray-200 cursor-pointer hover:shadow-sm transition-shadow border-l-4 border-l-green-500`}
          onClick={() => toggleSection('download')}
        >
          <div className="p-4">
            <div className="flex items-center justify-between min-w-0">
              <span className="text-sm font-medium text-gray-700 shrink-0">下载</span>
              <span className="text-sm text-gray-500 truncate ml-2">
                <StatusDot state={downloadConfigured ? 'green' : 'yellow'} />
                {downloadSummary}
              </span>
            </div>
          </div>
          {expandedSection === 'download' && (
            <div className="px-4 pb-4 pt-3 mt-3 border-t border-gray-100" onClick={e => e.stopPropagation()}>
              <div className="space-y-3">
                {[
                  { key: 'download_dir', label: '下载目录' },
                  { key: 'finished_dir', label: '保存目录' },
                ].map(({ key, label }) => (
                  <div key={key}>
                    <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
                    <div className="flex gap-1">
                      <input
                        type="text"
                        value={String((config as any)[key] || '')}
                        onChange={e => setConfig({ ...config, [key]: e.target.value })}
                        className="w-full rounded border border-gray-300 px-2 py-1.5 text-xs font-mono focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                      />
                      <BrowseButton onPathDetected={(path) => setConfig({ ...config, [key]: path })} />
                    </div>
                  </div>
                ))}

                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">FlareSolverr 状态</label>
                  <div className="flex items-center gap-2">
                    <StatusDot state={flareStatus === null ? 'yellow' : (flareStatus ? 'green' : 'red')} />
                    <span className="text-xs text-gray-600">
                      {flareStatus === null ? '检测中...' : (flareStatus ? '已连接' : '未运行')}
                    </span>
                    <button
                      type="button"
                      onClick={async () => {
                        setFlareStatus(null)
                        try {
                          const res = await fetch('/api/v1/check-flare')
                          if (res.ok) {
                            const data = await res.json()
                            setFlareStatus(data.available ?? false)
                          }
                        } catch { setFlareStatus(false) }
                      }}
                      className="ml-auto px-2 py-1 text-xs rounded border border-gray-300 bg-white hover:bg-gray-50 text-gray-500 shrink-0"
                    >
                      重新检测
                    </button>
                  </div>
                </div>

                <hr className="border-gray-100" />

                <div>
                  <h4 className="text-xs font-semibold text-gray-700 mb-2">Anna's Archive 会员高速（可选）</h4>
                  <div className="bg-blue-50 border border-blue-200 rounded p-2.5 text-xs text-blue-700 mb-3 space-y-1">
                    <p>
                      注册 Anna's Archive 会员后获取高速下载 Key，下载速度更快。获取方式：
                      <a href="https://annas-archive.gd/donate" className="underline font-medium" target="_blank">
                        https://annas-archive.gd/donate
                      </a>
                    </p>
                  </div>
                  <div className="mb-3">
                    <label className="block text-xs font-medium text-gray-600 mb-1">会员 Key</label>
                    <input
                      type="text"
                      value={aaMembershipKey}
                      onChange={e => setAaMembershipKey(e.target.value)}
                      placeholder="输入 Anna's Archive 会员 Key"
                      className="w-full rounded border border-gray-300 px-2 py-1.5 text-xs font-mono focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={handleSaveAaKey}
                      disabled={savingAaKey}
                      className="px-3 py-1.5 rounded border border-indigo-300 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 text-xs disabled:opacity-50"
                    >
                      {savingAaKey ? '保存中...' : '保存'}
                    </button>
                    {aaKeyMsg && (
                      <span className={`text-xs ${aaKeyMsg.includes('失败') ? 'text-red-500' : 'text-green-600'}`}>
                        {aaKeyMsg}
                      </span>
                    )}
                  </div>
                </div>

                <hr className="border-gray-100" />

                <div>
                  <h4 className="text-xs font-semibold text-gray-700 mb-2">Z-Library 下载凭据（可选）</h4>
                  <div className="bg-blue-50 border border-blue-200 rounded p-2.5 text-xs text-blue-700 mb-3 space-y-1">
                    <p>
                      访问{' '}
                      <a href="https://z-lib.sk" className="underline font-medium" target="_blank">
                        https://z-lib.sk
                      </a>{' '}
                      注册后，使用邮箱和密码登录即可自动获取 Token。
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">邮箱</label>
                      <input
                        type="email"
                        value={zlibEmail}
                        onChange={e => setZlibEmail(e.target.value)}
                        placeholder="user@example.com"
                        className="w-full rounded border border-gray-300 px-2 py-1.5 text-xs font-mono focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">密码</label>
                      <div className="flex gap-1">
                        <input
                          type="password"
                          value={zlibPassword}
                          onChange={e => setZlibPassword(e.target.value)}
                          placeholder="••••••••"
                          className="w-full rounded border border-gray-300 px-2 py-1.5 text-xs font-mono focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                        />
                        <button
                          type="button"
                          onClick={handleFetchZlibTokens}
                          disabled={fetchingZlibTokens || !zlibEmail.trim() || !zlibPassword.trim()}
                          className="px-2 py-1.5 text-xs rounded border border-green-300 bg-green-50 hover:bg-green-100 text-green-600 shrink-0 disabled:opacity-50"
                        >
                          {fetchingZlibTokens ? '获取中...' : '保存'}
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 mt-2 text-xs">
                    <StatusDot state={(zlibUserid || zlibEmail) ? 'green' : 'yellow'} />
                    <span className="text-gray-600">
                      {(zlibUserid || zlibEmail) ? `已登录 (ID: ${zlibUserid || zlibEmail})` : '未登录'}
                    </span>
                  </div>

                  {zlibMsg && (
                    <div className={`mt-2 text-xs p-2 rounded ${zlibMsg.includes('失败') || zlibMsg.includes('错误') ? 'bg-red-50 text-red-500' : 'bg-green-50 text-green-600'}`}>
                      {zlibMsg}
                    </div>
                  )}
                  {zlibQuota && (
                    <div className="mt-2 flex items-center gap-1.5 text-xs">
                      <StatusDot state={zlibQuota.downloads_left > 0 ? 'green' : 'red'} />
                      <span className="text-gray-700">
                        剩余下载额度: {zlibQuota.downloads_left} / {zlibQuota.downloads_limit} 次/天
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 网络代理 */}
        <div
          className={`rounded-lg bg-white border border-gray-200 cursor-pointer hover:shadow-sm transition-shadow border-l-4 border-l-purple-500`}
          onClick={() => toggleSection('proxy')}
        >
          <div className="p-4">
            <div className="flex items-center justify-between min-w-0">
              <span className="text-sm font-medium text-gray-700 shrink-0">网络代理</span>
              <span className="text-sm text-gray-500 truncate ml-2">
                {config.http_proxy ? (
                  proxyStatus ? (
                    proxySummary
                  ) : (
                    <>
                      <StatusDot state="yellow" />
                      检测中...
                    </>
                  )
                ) : (
                  <>
                    <StatusDot state="yellow" />
                    未配置
                  </>
                )}
              </span>
            </div>
          </div>
          {expandedSection === 'proxy' && (
            <div className="px-4 pb-4 pt-3 mt-3 border-t border-gray-100" onClick={e => e.stopPropagation()}>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">代理地址</label>
                  <div className="flex gap-1">
                    <input
                      type="text"
                      value={config.http_proxy || ''}
                      onChange={e => handleProxyChange(e.target.value)}
                      placeholder="http://127.0.0.1:6244"
                      className="w-full rounded border border-gray-300 px-2 py-1.5 text-xs font-mono focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                    />
                    <button
                      type="button"
                      onClick={() => checkProxy(config.http_proxy || '')}
                      disabled={checkingProxy || !config.http_proxy}
                      className="px-2 py-1.5 text-xs rounded border border-gray-300 bg-white hover:bg-gray-50 text-gray-600 shrink-0 disabled:opacity-50"
                    >
                      {checkingProxy ? '检测中...' : '重新检测'}
                    </button>
                  </div>
                </div>
                {proxyStatus && (
                  <div className="space-y-1.5 pt-1">
                    <div className="flex items-center gap-2 text-xs">
                      <StatusDot state={proxyStatus.annas_archive?.reachable ? 'green' : 'red'} />
                      <span className="text-gray-600">
                        Anna's Archive{' '}
                        {proxyStatus.annas_archive?.reachable
                          ? `可达 (${proxyStatus.annas_archive.latency_ms ?? '?'}ms)`
                          : '不可达'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <StatusDot
                        state={
                          !proxyStatus.zlibrary?.configured
                            ? 'yellow'
                            : proxyStatus.zlibrary?.api_available
                              ? 'green'
                              : 'red'
                        }
                      />
                      <span className="text-gray-600">
                        Z-Library{' '}
                        {!proxyStatus.zlibrary?.configured
                          ? '未配置凭据'
                          : proxyStatus.zlibrary?.api_available
                            ? 'API 可用（已登录）'
                            : proxyStatus.zlibrary?.api_reachable
                              ? 'API 可达（检查凭据）'
                              : 'API 不可达'}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* OCR */}
        <div
          className={`rounded-lg bg-white border border-gray-200 cursor-pointer hover:shadow-sm transition-shadow border-l-4 border-l-orange-500`}
          onClick={() => toggleSection('ocr')}
        >
          <div className="p-4">
            <div className="flex items-center justify-between min-w-0">
              <span className="text-sm font-medium text-gray-700 shrink-0">OCR</span>
              <span className="text-sm text-gray-500 truncate ml-2">
                {ocrStatus ? (
                  <>
                    <StatusDot state={ocrStatus.installed ? 'green' : 'red'} />
                    {ocrSummary}
                  </>
                ) : (
                  <>
                    <StatusDot state="yellow" />
                    检测中...
                  </>
                )}
              </span>
            </div>
          </div>
          {expandedSection === 'ocr' && (
            <div className="px-4 pb-4 pt-3 mt-3 border-t border-gray-100" onClick={e => e.stopPropagation()}>
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-xs">
                  {ocrStatus ? (
                    <>
                      <StatusDot state={ocrStatus.installed ? 'green' : 'red'} />
                      <span className="text-gray-600 truncate">
                        {ocrStatus.installed ? `已安装 v${ocrStatus.version || '?'}` : '未安装'}
                      </span>
                    </>
                  ) : (
                    <>
                      <StatusDot state="yellow" />
                      <span className="text-gray-400">检测中...</span>
                    </>
                  )}
                  <button
                    type="button"
                    onClick={handleCheckOCR}
                    disabled={checkingOCR}
                    className="ml-auto px-2 py-1 text-xs rounded border border-gray-300 bg-white hover:bg-gray-50 text-gray-500 disabled:opacity-50 shrink-0"
                  >
                    {checkingOCR ? '检测中...' : '重新检测'}
                  </button>
                  {!ocrStatus?.installed && (
                    <button
                      type="button"
                      onClick={() => handleInstallEngine('tesseract')}
                      disabled={installingEngine === 'tesseract'}
                      className="px-3 py-1 text-xs rounded border border-indigo-300 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 disabled:opacity-50 shrink-0"
                    >
                      {installingEngine === 'tesseract' ? '安装中...' : '一键安装'}
                    </button>
                  )}
                </div>

                <div className="bg-gray-50 rounded border border-gray-200 p-3">
                  <p className="text-xs font-medium text-gray-600 mb-2">引擎</p>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { key: 'tesseract', label: 'Tesseract' },
                      { key: 'paddleocr', label: 'PaddleOCR' },
                      { key: 'easyocr', label: 'EasyOCR' },
                      { key: 'appleocr', label: 'AppleOCR' },
                    ].map(({ key, label }) => {
                      const engineStatus = ocrStatus?.engines?.[key]
                      const available = engineStatus?.available ?? false
                      return (
                        <div key={key} className="flex items-center gap-1.5 bg-white rounded border border-gray-200 px-2 py-1.5">
                          <span className="text-xs font-medium text-gray-700 w-16 shrink-0">{label}</span>
                          <StatusDot state={available ? 'green' : 'red'} />
                          <span className="text-xs text-gray-500">{available ? '可用' : '未安装'}</span>
                          <div className="ml-auto flex gap-1">
                            <button
                              type="button"
                              onClick={() => handleCheckEngine(key)}
                              disabled={checkingEngine === key}
                              className="px-1.5 py-0.5 text-xs rounded border border-gray-300 bg-white hover:bg-gray-50 text-gray-500 disabled:opacity-50"
                            >
                              检测
                            </button>
                            <button
                              type="button"
                              onClick={() => handleInstallEngine(key)}
                              disabled={installingEngine === key}
                              className="px-1.5 py-0.5 text-xs rounded border border-indigo-300 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 disabled:opacity-50"
                            >
                              {installingEngine === key ? '安装中' : '安装'}
                            </button>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">默认引擎</label>
                  <select
                    value={ocrEngine}
                    onChange={e => {
                      const v = e.target.value
                      setOcrEngine(v)
                      fetch('/api/v1/config', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ocr_engine: v }),
                      }).catch(() => {})
                    }}
                    className="w-full rounded border border-gray-300 px-2 py-1.5 text-xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="tesseract">Tesseract</option>
                    <option value="paddleocr">PaddleOCR</option>
                    <option value="easyocr">EasyOCR</option>
                    <option value="appleocr">AppleOCR</option>
                  </select>
                </div>

                {ocrInstallMsg && (
                  <div className={`text-xs p-2 rounded ${ocrInstallMsg.includes('失败') ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'}`}>
                    {ocrInstallMsg}
                  </div>
                )}

                <div className="space-y-2">
                  {[
                    { key: 'ocr_languages', label: 'OCR 语言', type: 'select', options: ['chi_sim+eng', 'chi_sim', 'eng', 'chi_sim+eng+jpn'] },
                    { key: 'ocr_jobs', label: 'OCR 线程', type: 'select', options: ['1', '2', '4'] },
                    { key: 'ocr_timeout', label: 'OCR 超时(秒)', type: 'number', placeholder: '1800' },
                  ].map(({ key, label, type, options, placeholder }) => (
                    <div key={key}>
                      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
                      {type === 'select' ? (
                        <select
                          value={String((config as any)[key] || '')}
                          onChange={e =>
                            setConfig({
                              ...config,
                              [key]: isNaN(Number(e.target.value)) ? e.target.value : Number(e.target.value),
                            })
                          }
                          className="w-full rounded border border-gray-300 px-2 py-1.5 text-xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                        >
                          {options!.map(opt => (
                            <option key={opt} value={opt}>{opt}</option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type="number"
                          value={String((config as any)[key] || '')}
                          onChange={e => setConfig({ ...config, [key]: Number(e.target.value) })}
                          placeholder={placeholder}
                          className="w-full rounded border border-gray-300 px-2 py-1.5 text-xs font-mono focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                        />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 书签 */}
        <div className="rounded-lg bg-white border border-gray-200 border-l-4 border-l-gray-400 p-4 opacity-60">
          <div className="flex items-center justify-between min-w-0">
            <span className="text-sm font-medium text-gray-700 shrink-0">书签</span>
            <span className="text-sm text-gray-400 truncate ml-2 italic">功能开发中...</span>
          </div>
        </div>

      </div>

      <div className="flex items-center gap-3 pt-1">
        <button
          onClick={handleSave}
          disabled={saving || !config}
          className="px-4 py-1.5 rounded bg-indigo-600 text-white text-sm hover:bg-indigo-700 disabled:opacity-50"
        >
          {saving ? '保存中...' : '保存配置'}
        </button>
        <button
          onClick={() =>
            fetch('/api/v1/status')
              .then(r => r.json())
              .then(setStatus)
          }
          className="px-4 py-1.5 rounded border border-gray-300 text-sm text-gray-600 hover:bg-gray-50"
        >
          刷新状态
        </button>
        {message && (
          <span className={`text-xs ${message.includes('失败') ? 'text-red-500' : 'text-green-600'}`}>
            {message}
          </span>
        )}
      </div>
    </div>
  )
}
