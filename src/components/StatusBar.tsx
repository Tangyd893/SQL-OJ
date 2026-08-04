import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getBankStatus } from '../api'
import {
  formatStatusMetrics,
  useDisplaySnapshot,
  useLayoutPrefsState,
} from '../hooks/useLayoutPrefsState'
import { formatBankLabel } from '../lib/bank'
import type { BankStatus } from '../types'

export function StatusBar() {
  const [bankStatus, setBankStatus] = useState<BankStatus | null>(null)
  const display = useDisplaySnapshot()
  const layout = useLayoutPrefsState()
  const metrics = formatStatusMetrics(display, layout)

  useEffect(() => {
    const refresh = () => {
      void getBankStatus().then(setBankStatus)
    }
    refresh()
    window.addEventListener('sqloj:settings-changed', refresh)
    return () => window.removeEventListener('sqloj:settings-changed', refresh)
  }, [])

  const bankLabel = bankStatus
    ? formatBankLabel(bankStatus)
    : '未链接'

  return (
    <footer className="statusbar" data-fg-surface data-fg-chrome>
      <span className="statusbar-item">桌面版 · Tauri + Rust</span>
      <Link
        to="/settings"
        className={`statusbar-item statusbar-bank${bankStatus?.linked && bankStatus.pathExists ? '' : ' warn'}`}
        title={bankStatus?.path ?? '点击前往设置链接题库'}
      >
        题库: {bankLabel}
      </Link>
      {metrics && (
        <span className="statusbar-item statusbar-metrics">{metrics}</span>
      )}
    </footer>
  )
}
