import { useCallback, useEffect, useRef, useState } from 'react'
import {
  loadLayoutPrefs,
  saveLayoutPrefs,
  SIDEBAR_COLLAPSED,
  SIDEBAR_MAX,
  SIDEBAR_MIN,
  type LayoutPrefs,
} from '../lib/layoutPrefs'

export function useSidebarResize(collapsed: boolean) {
  const [width, setWidth] = useState(() => loadLayoutPrefs().sidebarWidth)
  const [dragging, setDragging] = useState(false)
  const dragState = useRef<{ startX: number; startWidth: number } | null>(null)

  useEffect(() => {
    const sync = () => setWidth(loadLayoutPrefs().sidebarWidth)
    window.addEventListener('sqloj:layout-changed', sync)
    return () => window.removeEventListener('sqloj:layout-changed', sync)
  }, [])

  const effectiveWidth = collapsed ? SIDEBAR_COLLAPSED : width

  const onResizeStart = useCallback(
    (e: React.MouseEvent) => {
      if (collapsed) return
      e.preventDefault()
      dragState.current = { startX: e.clientX, startWidth: width }
      setDragging(true)
    },
    [collapsed, width],
  )

  useEffect(() => {
    if (!dragging) return

    const onMove = (e: MouseEvent) => {
      const state = dragState.current
      if (!state) return
      const next = Math.round(state.startWidth + (e.clientX - state.startX))
      setWidth(Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, next)))
    }

    const onUp = () => {
      setDragging(false)
      dragState.current = null
      setWidth((current) => {
        const prefs: LayoutPrefs = {
          ...loadLayoutPrefs(),
          sidebarWidth: current,
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

  return { effectiveWidth, dragging, onResizeStart }
}
