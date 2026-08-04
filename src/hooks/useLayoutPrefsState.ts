import { useEffect, useState } from 'react'
import { formatZoomPercent, loadDisplay, type DisplaySettings } from '../lib/display'
import { loadLayoutPrefs, type LayoutPrefs } from '../lib/layoutPrefs'

export function useLayoutPrefsState(): LayoutPrefs {
  const [prefs, setPrefs] = useState<LayoutPrefs>(() => loadLayoutPrefs())

  useEffect(() => {
    const sync = () => setPrefs(loadLayoutPrefs())
    window.addEventListener('storage', sync)
    window.addEventListener('sqloj:layout-changed', sync)
    return () => {
      window.removeEventListener('storage', sync)
      window.removeEventListener('sqloj:layout-changed', sync)
    }
  }, [])

  return prefs
}

export function useDisplaySnapshot(): DisplaySettings {
  const [settings, setSettings] = useState<DisplaySettings>(() => loadDisplay())

  useEffect(() => {
    const sync = () => setSettings(loadDisplay())
    window.addEventListener('storage', sync)
    window.addEventListener('sqloj:display-changed', sync)
    return () => {
      window.removeEventListener('storage', sync)
      window.removeEventListener('sqloj:display-changed', sync)
    }
  }, [])

  return settings
}

export function formatStatusMetrics(
  display: DisplaySettings,
  layout: LayoutPrefs,
): string | null {
  if (!layout.showStatusMetrics) return null
  return `缩放 ${formatZoomPercent(display.uiZoom)} · 界面 ${display.appFontSize}px · 编辑器 ${display.editorFontSize}px`
}
