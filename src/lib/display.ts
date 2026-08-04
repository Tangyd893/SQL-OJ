const STORAGE_KEY = 'sql-oj.display'

export const ZOOM_STEP = 0.25
export const ZOOM_MIN = 0.5
export const ZOOM_MAX = 3
export const APP_FONT_MIN = 11
export const APP_FONT_MAX = 20
export const EDITOR_FONT_MIN = 10
export const EDITOR_FONT_MAX = 24

export type FontFamilyPreset = 'system' | 'yahei' | 'sans' | 'serif'

export const FONT_PRESET_OPTIONS: { v: FontFamilyPreset; label: string }[] = [
  { v: 'system', label: '系统默认' },
  { v: 'yahei', label: '微软雅黑 / 苹方' },
  { v: 'sans', label: '无衬线（Inter）' },
  { v: 'serif', label: '衬线' },
]

const FONT_STACKS: Record<FontFamilyPreset, string> = {
  system: "'Segoe UI Variable', 'Segoe UI', system-ui, sans-serif",
  yahei: '"Microsoft YaHei UI", "PingFang SC", "Segoe UI", sans-serif',
  sans: 'Inter, "Segoe UI", system-ui, sans-serif',
  serif: 'Georgia, "Noto Serif SC", "Songti SC", serif',
}

export interface DisplaySettings {
  uiZoom: number
  appFontSize: number
  editorFontSize: number
  fontFamily: FontFamilyPreset
}

const defaults: DisplaySettings = {
  uiZoom: 1,
  appFontSize: 13,
  editorFontSize: 14,
  fontFamily: 'yahei',
}

export function loadDisplay(): DisplaySettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...defaults }
    const parsed = JSON.parse(raw) as Partial<DisplaySettings>
    return {
      uiZoom: snapZoom(parsed.uiZoom ?? defaults.uiZoom),
      appFontSize: clamp(
        Math.round(parsed.appFontSize ?? defaults.appFontSize),
        APP_FONT_MIN,
        APP_FONT_MAX,
      ),
      editorFontSize: clamp(
        Math.round(parsed.editorFontSize ?? defaults.editorFontSize),
        EDITOR_FONT_MIN,
        EDITOR_FONT_MAX,
      ),
      fontFamily: isFontPreset(parsed.fontFamily)
        ? parsed.fontFamily
        : defaults.fontFamily,
    }
  } catch {
    return { ...defaults }
  }
}

export function saveDisplay(settings: DisplaySettings): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
  applyDisplay(settings)
}

export function applyDisplay(settings: DisplaySettings = loadDisplay()): void {
  document.documentElement.style.setProperty(
    '--app-font-size',
    `${settings.appFontSize}px`,
  )
  document.documentElement.style.setProperty(
    '--fg-font-ui',
    FONT_STACKS[settings.fontFamily],
  )
  applyUiZoom(settings.uiZoom)
  window.dispatchEvent(
    new CustomEvent('sqloj:display-changed', { detail: settings }),
  )
}

export function applyUiZoom(zoom: number): void {
  const root = document.querySelector('.app-zoom-root') as HTMLElement | null
  if (root) {
    root.style.zoom = String(zoom)
  }
}

export function initDisplay(): void {
  applyDisplay(loadDisplay())
}

export function formatZoomPercent(zoom: number): string {
  return `${Math.round(zoom * 100)}%`
}

export function adjustUiZoom(delta: number): DisplaySettings {
  const current = loadDisplay()
  const next = {
    ...current,
    uiZoom: snapZoom(current.uiZoom + delta),
  }
  saveDisplay(next)
  return next
}

export function resetUiZoom(): DisplaySettings {
  const current = loadDisplay()
  const next = { ...current, uiZoom: 1 }
  saveDisplay(next)
  return next
}

export function adjustAppFont(delta: number): DisplaySettings {
  const current = loadDisplay()
  const next = {
    ...current,
    appFontSize: clamp(current.appFontSize + delta, APP_FONT_MIN, APP_FONT_MAX),
  }
  saveDisplay(next)
  return next
}

export function adjustEditorFont(delta: number): DisplaySettings {
  const current = loadDisplay()
  const next = {
    ...current,
    editorFontSize: clamp(
      current.editorFontSize + delta,
      EDITOR_FONT_MIN,
      EDITOR_FONT_MAX,
    ),
  }
  saveDisplay(next)
  return next
}

export function resetDisplayDefaults(): DisplaySettings {
  saveDisplay({ ...defaults })
  return { ...defaults }
}

function snapZoom(value: number): number {
  return clamp(roundZoom(value), ZOOM_MIN, ZOOM_MAX)
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

function roundZoom(value: number): number {
  return Math.round(value / ZOOM_STEP) * ZOOM_STEP
}

function isFontPreset(value: unknown): value is FontFamilyPreset {
  return (
    value === 'system' ||
    value === 'yahei' ||
    value === 'sans' ||
    value === 'serif'
  )
}
