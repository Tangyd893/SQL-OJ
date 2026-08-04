import { useEffect } from 'react'
import { TitleBar } from './TitleBar'
import { StatusBar } from './StatusBar'
import { Sidebar } from './Sidebar'
import { useGlobalShortcuts } from '../hooks/useGlobalShortcuts'
import { applyDisplay } from '../lib/display'

export function AppShell({ children }: { children: React.ReactNode }) {
  useGlobalShortcuts()

  useEffect(() => {
    applyDisplay()
  }, [])

  return (
    <div className="app-shell">
      <TitleBar />
      <div className="app-zoom-root">
        <div className="app-body">
          <Sidebar />
          <main className="main-content">{children}</main>
        </div>
        <StatusBar />
      </div>
    </div>
  )
}
