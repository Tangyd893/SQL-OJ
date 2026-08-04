const STORAGE_KEY = 'sql-oj.layout'

export const SPLIT_MIN = 25
export const SPLIT_MAX = 55
export const SPLIT_DEFAULT = 40

export const SIDEBAR_MIN = 180
export const SIDEBAR_MAX = 280
export const SIDEBAR_DEFAULT = 220
export const SIDEBAR_COLLAPSED = 52

export const SETTINGS_NAV_MIN = 160
export const SETTINGS_NAV_MAX = 320
export const SETTINGS_NAV_DEFAULT = 200

export interface LayoutPrefs {
  problemLeftPercent: number
  showStatusMetrics: boolean
  sidebarCollapsed: boolean
  sidebarWidth: number
  settingsNavWidth: number
}

const defaults: LayoutPrefs = {
  problemLeftPercent: SPLIT_DEFAULT,
  showStatusMetrics: true,
  sidebarCollapsed: false,
  sidebarWidth: SIDEBAR_DEFAULT,
  settingsNavWidth: SETTINGS_NAV_DEFAULT,
}

export function loadLayoutPrefs(): LayoutPrefs {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...defaults }
    const parsed = JSON.parse(raw) as Partial<LayoutPrefs>
    return {
      problemLeftPercent: clamp(
        Math.round(parsed.problemLeftPercent ?? defaults.problemLeftPercent),
        SPLIT_MIN,
        SPLIT_MAX,
      ),
      showStatusMetrics: parsed.showStatusMetrics ?? defaults.showStatusMetrics,
      sidebarCollapsed: parsed.sidebarCollapsed ?? defaults.sidebarCollapsed,
      sidebarWidth: clamp(
        Math.round(parsed.sidebarWidth ?? defaults.sidebarWidth),
        SIDEBAR_MIN,
        SIDEBAR_MAX,
      ),
      settingsNavWidth: clamp(
        Math.round(parsed.settingsNavWidth ?? defaults.settingsNavWidth),
        SETTINGS_NAV_MIN,
        SETTINGS_NAV_MAX,
      ),
    }
  } catch {
    return { ...defaults }
  }
}

export function saveLayoutPrefs(prefs: LayoutPrefs): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
  window.dispatchEvent(new CustomEvent('sqloj:layout-changed', { detail: prefs }))
}

export function resetLayoutPrefs(): LayoutPrefs {
  saveLayoutPrefs({ ...defaults })
  return { ...defaults }
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}
