const STORAGE_KEY = 'sql-oj.layout'

export const SPLIT_MIN = 20
export const SPLIT_MAX = 70
export const SPLIT_DEFAULT = 40

export const TOOLBAR_HEIGHT_AUTO = 0
export const TOOLBAR_HEIGHT_MAX_PX = 280
export const TOOLBAR_HEIGHT_MAX_VH = 0.4

export const SIDEBAR_MIN = 180
export const SIDEBAR_MAX = 280
export const SIDEBAR_DEFAULT = 220
export const SIDEBAR_COLLAPSED = 52

export const SETTINGS_NAV_MIN = 160
export const SETTINGS_NAV_MAX = 320
export const SETTINGS_NAV_DEFAULT = 200

export interface LayoutPrefs {
  problemLeftPercent: number
  /** 0 = natural content height; otherwise min-height in px */
  problemToolbarHeight: number
  showStatusMetrics: boolean
  sidebarCollapsed: boolean
  sidebarWidth: number
  settingsNavWidth: number
}

const defaults: LayoutPrefs = {
  problemLeftPercent: SPLIT_DEFAULT,
  problemToolbarHeight: TOOLBAR_HEIGHT_AUTO,
  showStatusMetrics: true,
  sidebarCollapsed: false,
  sidebarWidth: SIDEBAR_DEFAULT,
  settingsNavWidth: SETTINGS_NAV_DEFAULT,
}

export function toolbarHeightMaxPx(): number {
  if (typeof window === 'undefined') return TOOLBAR_HEIGHT_MAX_PX
  return Math.min(TOOLBAR_HEIGHT_MAX_PX, Math.round(window.innerHeight * TOOLBAR_HEIGHT_MAX_VH))
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
      problemToolbarHeight: clampToolbarHeight(
        Math.round(parsed.problemToolbarHeight ?? defaults.problemToolbarHeight),
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

function clampToolbarHeight(value: number): number {
  if (!Number.isFinite(value) || value <= 0) return TOOLBAR_HEIGHT_AUTO
  return clamp(value, 1, toolbarHeightMaxPx())
}
