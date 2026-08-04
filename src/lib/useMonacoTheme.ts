import { useEffect, useState } from 'react'
import { monacoThemeId, type MonacoThemeId } from '../lib/monacoThemes'
import { loadAppearance } from '../lib/theme'

export function useMonacoTheme(): MonacoThemeId {
  const [theme, setTheme] = useState<MonacoThemeId>(() => monacoThemeId())

  useEffect(() => {
    const sync = () => setTheme(monacoThemeId())
    sync()
    window.addEventListener('storage', sync)
    window.addEventListener('sqloj:appearance-changed', sync)
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    mq.addEventListener('change', sync)
    return () => {
      window.removeEventListener('storage', sync)
      window.removeEventListener('sqloj:appearance-changed', sync)
      mq.removeEventListener('change', sync)
    }
  }, [])

  return theme
}

export function notifyAppearanceChanged(settings: ReturnType<typeof loadAppearance>): void {
  window.dispatchEvent(
    new CustomEvent('sqloj:appearance-changed', { detail: settings }),
  )
}
