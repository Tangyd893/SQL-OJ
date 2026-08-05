import { useEffect, useState, type ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  APP_FONT_MAX,
  APP_FONT_MIN,
  EDITOR_FONT_MAX,
  EDITOR_FONT_MIN,
  FONT_PRESET_OPTIONS,
  formatZoomPercent,
  loadDisplay,
  resetDisplayDefaults,
  saveDisplay,
  ZOOM_MAX,
  ZOOM_MIN,
  ZOOM_STEP,
  type DisplaySettings,
  type FontFamilyPreset,
} from '../lib/display'
import {
  loadAppearance,
  saveAppearance,
  type AppearanceSettings,
  type ThemeMode,
  type ThemePreset,
} from '../lib/theme'
import {
  loadLayoutPrefs,
  saveLayoutPrefs,
  type LayoutPrefs,
} from '../lib/layoutPrefs'
import { resetAllPreferences } from '../lib/preferences'
import { BankImportPanel } from '../components/BankImportPanel'
import { ShortcutSettings } from '../components/ShortcutSettings'
import { StepperControl } from '../components/StepperControl'
import { useSettingsNavResize } from '../hooks/useSettingsNavResize'

const THEME_OPTIONS: { v: ThemeMode; label: string }[] = [
  { v: 'system', label: '跟随系统' },
  { v: 'light', label: '浅色' },
  { v: 'dark', label: '深色' },
]

const PRESET_OPTIONS: { v: ThemePreset; label: string }[] = [
  { v: 'parchment', label: 'Parchment' },
  { v: 'slate', label: 'Slate' },
  { v: 'midnight', label: 'Midnight' },
  { v: 'none', label: '默认' },
]

const SECTIONS = [
  { id: 'appearance', label: '外观' },
  { id: 'display', label: '显示' },
  { id: 'editor', label: '编辑器' },
  { id: 'shortcuts', label: '快捷键' },
  { id: 'bank', label: '题库' },
  { id: 'about', label: '关于' },
] as const

type SectionId = (typeof SECTIONS)[number]['id']

const APP_VERSION = '0.1.0'

function SettingRow({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: ReactNode
}) {
  return (
    <div className="setting-row">
      <div>
        <div className="setting-label">{label}</div>
        {hint && <div className="setting-hint">{hint}</div>}
      </div>
      {children}
    </div>
  )
}

export function SettingsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const section = (searchParams.get('section') as SectionId | null) ?? 'appearance'
  const [saved, setSaved] = useState(false)
  const [appearance, setAppearance] = useState<AppearanceSettings>(loadAppearance)
  const [display, setDisplay] = useState<DisplaySettings>(loadDisplay)
  const [layout, setLayout] = useState<LayoutPrefs>(loadLayoutPrefs)
  const { navWidth, dragging, setNavNode, onPointerDown, onPointerMove, onPointerUp } =
    useSettingsNavResize()

  useEffect(() => {
    const onDisplay = () => setDisplay(loadDisplay())
    const onAppearance = () => setAppearance(loadAppearance())
    const onLayout = () => setLayout(loadLayoutPrefs())
    window.addEventListener('sqloj:display-changed', onDisplay)
    window.addEventListener('sqloj:appearance-changed', onAppearance)
    window.addEventListener('sqloj:layout-changed', onLayout)
    return () => {
      window.removeEventListener('sqloj:display-changed', onDisplay)
      window.removeEventListener('sqloj:appearance-changed', onAppearance)
      window.removeEventListener('sqloj:layout-changed', onLayout)
    }
  }, [])

  const setSection = (id: SectionId) => {
    setSearchParams({ section: id }, { replace: true })
  }

  const setTheme = (theme: ThemeMode) => {
    const next = { ...appearance, theme }
    setAppearance(next)
    saveAppearance(next)
  }

  const setPreset = (themePreset: ThemePreset) => {
    const next = { ...appearance, themePreset }
    setAppearance(next)
    saveAppearance(next)
  }

  const patchDisplay = (patch: Partial<DisplaySettings>) => {
    const next = { ...display, ...patch }
    setDisplay(next)
    saveDisplay(next)
  }

  const patchLayout = (patch: Partial<LayoutPrefs>) => {
    const next = { ...layout, ...patch }
    setLayout(next)
    saveLayoutPrefs(next)
  }

  const onResetDisplay = () => {
    setDisplay(resetDisplayDefaults())
  }

  const onResetAll = () => {
    resetAllPreferences()
    setAppearance(loadAppearance())
    setDisplay(loadDisplay())
    setLayout(loadLayoutPrefs())
  }

  const onBankLinked = () => {
    setSaved(true)
  }

  return (
    <div className="settings-page">
      <h1 className="page-title settings-page-title">设置</h1>
      {saved && <div className="alert settings-alert">题库已更新</div>}

      <div className="settings-layout">
        <aside
          className="settings-nav"
          ref={setNavNode}
          style={{ width: navWidth }}
        >
          {SECTIONS.map((s) => (
            <button
              key={s.id}
              type="button"
              className={`settings-nav-item${section === s.id ? ' active' : ''}`}
              onClick={() => setSection(s.id)}
            >
              {s.label}
            </button>
          ))}
        </aside>
        <div
          className={`settings-nav-resizer${dragging ? ' dragging' : ''}`}
          role="separator"
          aria-orientation="vertical"
          aria-label="调整设置导航宽度"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
        />
        <div className="settings-content">
          {section === 'appearance' && (
            <div className="settings-panel">
              <h2 className="settings-section-title">外观</h2>
              <div className="settings-block">
                <SettingRow label="明暗模式">
                  <div className="theme-chips settings-inline-chips">
                    {THEME_OPTIONS.map((opt) => (
                      <button
                        key={opt.v}
                        type="button"
                        className={`theme-chip${appearance.theme === opt.v ? ' active' : ''}`}
                        onClick={() => setTheme(opt.v)}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </SettingRow>
                <SettingRow label="主题预设">
                  <div className="theme-chips settings-inline-chips">
                    {PRESET_OPTIONS.map((opt) => (
                      <button
                        key={opt.v}
                        type="button"
                        className={`theme-chip${appearance.themePreset === opt.v ? ' active' : ''}`}
                        onClick={() => setPreset(opt.v)}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </SettingRow>
              </div>
            </div>
          )}

          {section === 'display' && (
            <div className="settings-panel">
              <h2 className="settings-section-title">显示</h2>
              <SettingRow
                label="界面缩放"
                hint="50%–300%，步长 25% · Ctrl + + / Ctrl + - / Ctrl + 0"
              >
                <StepperControl
                  value={display.uiZoom}
                  min={ZOOM_MIN}
                  max={ZOOM_MAX}
                  step={ZOOM_STEP}
                  format={formatZoomPercent}
                  onChange={(uiZoom) => patchDisplay({ uiZoom })}
                />
              </SettingRow>
              <SettingRow
                label="界面字体"
                hint="影响列表、设置等界面文字风格"
              >
                <select
                  className="fg-input settings-select"
                  value={display.fontFamily}
                  onChange={(e) =>
                    patchDisplay({ fontFamily: e.target.value as FontFamilyPreset })
                  }
                >
                  {FONT_PRESET_OPTIONS.map((opt) => (
                    <option key={opt.v} value={opt.v}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </SettingRow>
              <SettingRow
                label="应用字号"
                hint="列表、设置等界面文字大小 · Ctrl + Shift + + / -"
              >
                <StepperControl
                  value={display.appFontSize}
                  min={APP_FONT_MIN}
                  max={APP_FONT_MAX}
                  step={1}
                  format={(v) => `${v}px`}
                  onChange={(appFontSize) => patchDisplay({ appFontSize })}
                />
              </SettingRow>
              <SettingRow label="状态栏指标" hint="在底部状态栏显示缩放与字号">
                <label className="setting-toggle">
                  <input
                    type="checkbox"
                    checked={layout.showStatusMetrics}
                    onChange={(e) => patchLayout({ showStatusMetrics: e.target.checked })}
                  />
                  <span>{layout.showStatusMetrics ? '显示' : '隐藏'}</span>
                </label>
              </SettingRow>
              <p className="font-preview">
                字体预览：SQL 查询是数据分析师的基本功，SELECT * FROM practice;
              </p>
              <div className="settings-actions">
                <button type="button" className="btn" onClick={onResetDisplay}>
                  恢复显示默认
                </button>
                <button type="button" className="btn" onClick={onResetAll}>
                  恢复全部默认
                </button>
              </div>
            </div>
          )}

          {section === 'editor' && (
            <div className="settings-panel">
              <h2 className="settings-section-title">编辑器</h2>
              <SettingRow label="代码字号" hint="Monaco 编辑器 · Ctrl + ] / Ctrl + [">
                <StepperControl
                  value={display.editorFontSize}
                  min={EDITOR_FONT_MIN}
                  max={EDITOR_FONT_MAX}
                  step={1}
                  format={(v) => `${v}px`}
                  onChange={(editorFontSize) => patchDisplay({ editorFontSize })}
                />
              </SettingRow>
            </div>
          )}

          {section === 'shortcuts' && (
            <div className="settings-panel">
              <h2 className="settings-section-title">快捷键</h2>
              <ShortcutSettings />
            </div>
          )}

          {section === 'bank' && (
            <div className="settings-panel">
              <h2 className="settings-section-title">外部题库</h2>
              <BankImportPanel variant="settings" onLinked={onBankLinked} />
            </div>
          )}

          {section === 'about' && (
            <div className="settings-panel">
              <h2 className="settings-section-title">关于</h2>
              <p className="settings-desc">
                SQL OJ {APP_VERSION} · 桌面 SQL 判题 · Tauri + Rust
              </p>
              <p className="settings-desc">
                提交记录与设置保存在本机用户目录，与 exe 位置无关。
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
