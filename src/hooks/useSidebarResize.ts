import { useCallback, useEffect } from 'react'
import {
  loadLayoutPrefs,
  saveLayoutPrefs,
  SIDEBAR_COLLAPSED,
  SIDEBAR_MAX,
  SIDEBAR_MIN,
  type LayoutPrefs,
} from '../lib/layoutPrefs'
import { usePointerSize } from './usePointerSize'

export function useSidebarResize(collapsed: boolean) {
  const onCommit = useCallback((sidebarWidth: number) => {
    const prefs: LayoutPrefs = { ...loadLayoutPrefs(), sidebarWidth }
    saveLayoutPrefs(prefs)
  }, [])

  const {
    value: width,
    dragging,
    setTargetNode,
    syncFromExternal,
    onPointerDown,
    onPointerMove,
    onPointerUp,
  } = usePointerSize({
    initial: loadLayoutPrefs().sidebarWidth,
    min: SIDEBAR_MIN,
    max: SIDEBAR_MAX,
    axis: 'x',
    bodyClass: 'sidebar-dragging',
    onCommit,
  })

  useEffect(() => {
    const sync = () => syncFromExternal(loadLayoutPrefs().sidebarWidth)
    window.addEventListener('sqloj:layout-changed', sync)
    return () => window.removeEventListener('sqloj:layout-changed', sync)
  }, [syncFromExternal])

  const effectiveWidth = collapsed ? SIDEBAR_COLLAPSED : width

  return {
    effectiveWidth,
    dragging: !collapsed && dragging,
    setSidebarNode: setTargetNode,
    onPointerDown: collapsed ? undefined : onPointerDown,
    onPointerMove: collapsed ? undefined : onPointerMove,
    onPointerUp: collapsed ? undefined : onPointerUp,
  }
}
