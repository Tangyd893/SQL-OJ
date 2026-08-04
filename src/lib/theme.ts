export type ThemeMode = 'system' | 'light' | 'dark'
export type ThemePreset = 'none' | 'parchment' | 'slate' | 'midnight'

const STORAGE_KEY = 'sql-oj.appearance'

export interface AppearanceSettings {
  theme: ThemeMode
  themePreset: ThemePreset
}

const defaultAppearance: AppearanceSettings = {
  theme: 'system',
  themePreset: 'parchment',
}

export function applyTheme(theme: ThemeMode, themePreset: ThemePreset = 'parchment'): void {
  const root = document.documentElement
  if (theme === 'light' || theme === 'dark') {
    root.dataset.theme = theme
  } else {
    delete root.dataset.theme
  }
  if (themePreset !== 'none') {
    root.dataset.themePreset = themePreset
  } else {
    delete root.dataset.themePreset
  }
}

export function loadAppearance(): AppearanceSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return defaultAppearance
    return { ...defaultAppearance, ...JSON.parse(raw) }
  } catch {
    return defaultAppearance
  }
}

export function saveAppearance(settings: AppearanceSettings): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
  applyTheme(settings.theme, settings.themePreset)
  window.dispatchEvent(new CustomEvent('sqloj:appearance-changed', { detail: settings }))
}

export function resolveEffectiveTheme(settings: AppearanceSettings = loadAppearance()): 'light' | 'dark' {
  if (settings.theme === 'light' || settings.theme === 'dark') {
    return settings.theme
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function monacoTheme(settings: AppearanceSettings = loadAppearance()): 'vs' | 'vs-dark' {
  return resolveEffectiveTheme(settings) === 'dark' ? 'vs-dark' : 'vs'
}

export function initTheme(): void {
  const settings = loadAppearance()
  applyTheme(settings.theme, settings.themePreset)
}

export function resetAppearanceDefaults(): AppearanceSettings {
  saveAppearance(defaultAppearance)
  return { ...defaultAppearance }
}
