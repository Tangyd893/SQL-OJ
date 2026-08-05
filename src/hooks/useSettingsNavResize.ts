import { useCallback, useEffect } from 'react'
import {
  loadLayoutPrefs,
  saveLayoutPrefs,
  SETTINGS_NAV_MAX,
  SETTINGS_NAV_MIN,
  type LayoutPrefs,
} from '../lib/layoutPrefs'
import { usePointerSize } from './usePointerSize'

export function useSettingsNavResize() {
  const onCommit = useCallback((settingsNavWidth: number) => {
    const prefs: LayoutPrefs = { ...loadLayoutPrefs(), settingsNavWidth }
    saveLayoutPrefs(prefs)
  }, [])

  const {
    value: navWidth,
    dragging,
    setTargetNode,
    syncFromExternal,
    onPointerDown,
    onPointerMove,
    onPointerUp,
  } = usePointerSize({
    initial: loadLayoutPrefs().settingsNavWidth,
    min: SETTINGS_NAV_MIN,
    max: SETTINGS_NAV_MAX,
    axis: 'x',
    bodyClass: 'settings-nav-dragging',
    onCommit,
  })

  useEffect(() => {
    const sync = () => syncFromExternal(loadLayoutPrefs().settingsNavWidth)
    window.addEventListener('sqloj:layout-changed', sync)
    return () => window.removeEventListener('sqloj:layout-changed', sync)
  }, [syncFromExternal])

  return {
    navWidth,
    dragging,
    setNavNode: setTargetNode,
    onPointerDown,
    onPointerMove,
    onPointerUp,
  }
}
