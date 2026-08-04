import { useEffect, useState } from 'react'
import { loadDisplay, type DisplaySettings } from '../lib/display'

export function useDisplaySettings(): DisplaySettings {
  const [settings, setSettings] = useState<DisplaySettings>(() => loadDisplay())

  useEffect(() => {
    const sync = () => setSettings(loadDisplay())
    sync()
    window.addEventListener('storage', sync)
    window.addEventListener('sqloj:display-changed', sync)
    return () => {
      window.removeEventListener('storage', sync)
      window.removeEventListener('sqloj:display-changed', sync)
    }
  }, [])

  return settings
}
