import { useCallback, useEffect, useRef, useState } from 'react'
import {
  loadLayoutPrefs,
  saveLayoutPrefs,
  SETTINGS_NAV_MAX,
  SETTINGS_NAV_MIN,
  type LayoutPrefs,
} from '../lib/layoutPrefs'

export function useSettingsNavResize() {
  const [navWidth, setNavWidth] = useState(() => loadLayoutPrefs().settingsNavWidth)
  const [dragging, setDragging] = useState(false)
  const dragState = useRef<{ startX: number; startWidth: number } | null>(null)

  useEffect(() => {
    const sync = () => setNavWidth(loadLayoutPrefs().settingsNavWidth)
    window.addEventListener('sqloj:layout-changed', sync)
    return () => window.removeEventListener('sqloj:layout-changed', sync)
  }, [])

  const onResizeStart = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      dragState.current = { startX: e.clientX, startWidth: navWidth }
      setDragging(true)
    },
    [navWidth],
  )

  useEffect(() => {
    if (!dragging) return

    const onMove = (e: MouseEvent) => {
      const state = dragState.current
      if (!state) return
      const next = Math.round(state.startWidth + (e.clientX - state.startX))
      setNavWidth(Math.min(SETTINGS_NAV_MAX, Math.max(SETTINGS_NAV_MIN, next)))
    }

    const onUp = () => {
      setDragging(false)
      dragState.current = null
      setNavWidth((current) => {
        const prefs: LayoutPrefs = {
          ...loadLayoutPrefs(),
          settingsNavWidth: current,
        }
        saveLayoutPrefs(prefs)
        return current
      })
      document.body.classList.remove('split-dragging')
    }

    document.body.classList.add('split-dragging')
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
      document.body.classList.remove('split-dragging')
    }
  }, [dragging])

  return { navWidth, dragging, onResizeStart }
}
