import { useCallback, useEffect, useState } from 'react'
import {
  getBankStatus,
  getSettings,
  inspectProblemBank,
  pickProblemBankFolder,
  setProblemBankPath,
} from '../api'
import type { BankInspectResult, BankStatus } from '../types'
import { formatBankLabel } from '../lib/bank'

type BusyAction = 'pick' | 'inspect' | 'link' | null

interface BankImportPanelProps {
  variant?: 'setup' | 'settings'
  onLinked?: () => void
}

export function BankImportPanel({
  variant = 'setup',
  onLinked,
}: BankImportPanelProps) {
  const [path, setPath] = useState('')
  const [inspect, setInspect] = useState<BankInspectResult | null>(null)
  const [status, setStatus] = useState<BankStatus | null>(null)
  const [busy, setBusy] = useState<BusyAction>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const refreshStatus = useCallback(async () => {
    const next = await getBankStatus()
    setStatus(next)
    if (next.path) setPath(next.path)
  }, [])

  useEffect(() => {
    void getSettings().then((s) => {
      if (s.problemBankPath) setPath(s.problemBankPath)
    })
    void refreshStatus()
  }, [refreshStatus])

  const runInspect = useCallback(async (targetPath: string) => {
    const trimmed = targetPath.trim()
    if (!trimmed) {
      setError('请先输入或选择题库目录')
      setInspect(null)
      return
    }
    setBusy('inspect')
    setError(null)
    setSuccess(null)
    try {
      const result = await inspectProblemBank(trimmed)
      setInspect(result)
      if (!result.valid && result.error) {
        setError(result.error)
      }
    } catch (e) {
      setInspect(null)
      setError(String(e))
    } finally {
      setBusy(null)
    }
  }, [])

  const onPickFolder = useCallback(async () => {
    setBusy('pick')
    setError(null)
    setSuccess(null)
    try {
      const selected = await pickProblemBankFolder()
      if (selected) {
        setPath(selected)
        await runInspect(selected)
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(null)
    }
  }, [runInspect])

  const onLink = useCallback(async () => {
    const trimmed = path.trim()
    if (!trimmed) {
      setError('请先输入或选择题库目录')
      return
    }
    setBusy('link')
    setError(null)
    setSuccess(null)
    try {
      let preview = inspect
      if (!preview || preview.path !== trimmed) {
        preview = await inspectProblemBank(trimmed)
        setInspect(preview)
      }
      if (!preview.valid) {
        setError(preview.error ?? '题库目录无效')
        return
      }
      await setProblemBankPath(trimmed)
      window.dispatchEvent(new CustomEvent('sqloj:settings-changed'))
      await refreshStatus()
      const label = preview.name ?? '题库'
      setSuccess(`已链接 ${label}，共 ${preview.problemCount} 道题目`)
      onLinked?.()
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(null)
    }
  }, [path, inspect, onLinked, refreshStatus])

  const linkedReady =
    status?.linked && status.pathExists && status.problemCount > 0 && !status.error
  const canLink = Boolean(path.trim()) && busy === null
  const isSetup = variant === 'setup'

  return (
    <div className={`bank-import${isSetup ? ' bank-import-setup' : ''}`}>
      {isSetup ? (
        <>
          <h2 className="bank-import-title">链接外部题库</h2>
          <p className="bank-import-lead">
            SQL OJ 从本地文件夹加载题目，无需导入数据库。首次使用请先指定题库目录。
          </p>
        </>
      ) : (
        <p className="settings-desc">
          选择题库根目录（含 <code>manifest.json</code> 与 <code>problems/</code>）。
          验证通过后再链接，题目列表会自动刷新。
        </p>
      )}

      {status?.linked && (
        <div
          className={`bank-status-card${linkedReady ? ' ready' : status.pathExists ? ' warn' : ' error'}`}
        >
          <div className="bank-status-label">当前链接</div>
          <div className="bank-status-title">{formatBankLabel(status)}</div>
          {status.path && <div className="bank-status-path">{status.path}</div>}
          {status.error && !linkedReady && (
            <div className="bank-status-error">{status.error}</div>
          )}
        </div>
      )}

      <ol className="bank-import-steps">
        <li>选择题库根目录，或手动粘贴路径</li>
        <li>点击「验证目录」检查结构与题目数量</li>
        <li>验证通过后点击「链接题库」加载题目</li>
      </ol>

      <div className="bank-import-path">
        <label htmlFor="bank-import-path">题库目录</label>
        <input
          id="bank-import-path"
          className="fg-input"
          value={path}
          placeholder="例如 D:\workspace\coding\SQL-OJ\banks\pta-150"
          onChange={(e) => {
            setPath(e.target.value)
            setInspect(null)
            setSuccess(null)
            setError(null)
          }}
          onBlur={() => {
            if (path.trim()) void runInspect(path)
          }}
        />
      </div>

      <div className="settings-actions bank-import-actions">
        <button
          type="button"
          className="btn btn-primary"
          disabled={busy !== null}
          onClick={() => void onPickFolder()}
        >
          {busy === 'pick' ? '选择中…' : '选择文件夹…'}
        </button>
        <button
          type="button"
          className="btn"
          disabled={!path.trim() || busy !== null}
          onClick={() => void runInspect(path)}
        >
          {busy === 'inspect' ? '验证中…' : '验证目录'}
        </button>
        <button
          type="button"
          className="btn btn-primary"
          disabled={!canLink}
          onClick={() => void onLink()}
        >
          {busy === 'link' ? '链接中…' : status?.linked ? '更换题库' : '链接题库'}
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert">{success}</div>}

      {inspect && (
        <div className={`bank-preview${inspect.valid ? ' valid' : ' invalid'}`}>
          <div className="bank-preview-header">
            <span>{inspect.valid ? '验证通过' : '验证未通过'}</span>
            {inspect.name && <span className="bank-preview-name">{inspect.name}</span>}
          </div>
          <div className="bank-preview-meta">
            {inspect.version && <span>版本 {inspect.version}</span>}
            <span>{inspect.problemCount} 道题目</span>
            {inspect.warnings.length > 0 && (
              <span>{inspect.warnings.length} 条加载警告</span>
            )}
          </div>
          {inspect.warnings.length > 0 && (
            <ul className="warn-list">
              {inspect.warnings.slice(0, 3).map((w) => (
                <li key={w}>{w}</li>
              ))}
              {inspect.warnings.length > 3 && (
                <li>…另有 {inspect.warnings.length - 3} 条</li>
              )}
            </ul>
          )}
        </div>
      )}

      <details className="bank-import-help">
        <summary>题库目录结构说明</summary>
        <pre className="bank-import-tree">{`your-bank/
  manifest.json      # 题库名称与题目列表
  problems/
    0001-xxx/
      meta.json      # 标题、难度、标签
      schema.sql     # 表结构
      task.md        # 题目描述
      cases.json     # 测试点`}</pre>
        <p className="settings-desc">
          开发环境可使用 <code>banks/pta-150</code>（150 题）或 <code>sample-bank</code>（3 题示例）。
          便携版 exe 需自行携带题库文件夹。
        </p>
      </details>
    </div>
  )
}
