import type { Monaco } from '@monaco-editor/react'
import type { editor } from 'monaco-editor'
import type { ThemePreset } from './theme'
import { loadAppearance, resolveEffectiveTheme } from './theme'

export type MonacoThemeId =
  | 'sqloj-light'
  | 'sqloj-dark'
  | 'sqloj-parchment'
  | 'sqloj-slate'
  | 'sqloj-midnight'

interface ThemePalette {
  base: 'vs' | 'vs-dark'
  colors: Record<string, string>
  rules: editor.ITokenThemeRule[]
}

const SYNTAX = {
  light: {
    keyword: '#1d4ed8',
    string: '#15803d',
    number: '#c2410c',
    comment: '#6b7280',
    operator: '#4b5563',
    identifier: '#111827',
    function: '#7c3aed',
    type: '#0e7490',
  },
  dark: {
    keyword: '#93bbfd',
    string: '#4ade80',
    number: '#fb923c',
    comment: '#64748b',
    operator: '#94a3b8',
    identifier: '#f1f5f9',
    function: '#c4b5fd',
    type: '#67e8f9',
  },
  parchment: {
    keyword: '#2d7d74',
    string: '#166534',
    number: '#b45309',
    comment: '#9e9e9e',
    operator: '#757575',
    identifier: '#222222',
    function: '#4a8b71',
    type: '#0f766e',
  },
  slate: {
    keyword: '#4338ca',
    string: '#15803d',
    number: '#c2410c',
    comment: '#6b7280',
    operator: '#4b5563',
    identifier: '#111827',
    function: '#6366f1',
    type: '#0891b2',
  },
  midnight: {
    keyword: '#79c0ff',
    string: '#3fb950',
    number: '#d29922',
    comment: '#8b949e',
    operator: '#8b949e',
    identifier: '#e6edf3',
    function: '#a5d6ff',
    type: '#56d4dd',
  },
} as const

function syntaxRules(s: (typeof SYNTAX)[keyof typeof SYNTAX]): editor.ITokenThemeRule[] {
  return [
    { token: 'keyword', foreground: s.keyword.replace('#', ''), fontStyle: 'bold' },
    { token: 'keyword.sql', foreground: s.keyword.replace('#', ''), fontStyle: 'bold' },
    { token: 'predefined', foreground: s.function.replace('#', '') },
    { token: 'predefined.sql', foreground: s.function.replace('#', '') },
    { token: 'string', foreground: s.string.replace('#', '') },
    { token: 'string.sql', foreground: s.string.replace('#', '') },
    { token: 'number', foreground: s.number.replace('#', '') },
    { token: 'number.sql', foreground: s.number.replace('#', '') },
    { token: 'comment', foreground: s.comment.replace('#', ''), fontStyle: 'italic' },
    { token: 'comment.sql', foreground: s.comment.replace('#', ''), fontStyle: 'italic' },
    { token: 'operator', foreground: s.operator.replace('#', '') },
    { token: 'operator.sql', foreground: s.operator.replace('#', '') },
    { token: 'type', foreground: s.type.replace('#', '') },
    { token: 'type.sql', foreground: s.type.replace('#', '') },
    { token: 'identifier', foreground: s.identifier.replace('#', '') },
    { token: 'identifier.sql', foreground: s.identifier.replace('#', '') },
    { token: 'delimiter', foreground: s.operator.replace('#', '') },
    { token: 'delimiter.sql', foreground: s.operator.replace('#', '') },
  ]
}

const THEME_PALETTES: Record<MonacoThemeId, ThemePalette> = {
  'sqloj-light': {
    base: 'vs',
    colors: {
      'editor.background': '#ffffff',
      'editor.foreground': SYNTAX.light.identifier,
      'editorLineNumber.foreground': '#9ca3af',
      'editorLineNumber.activeForeground': '#6b7280',
      'editor.selectionBackground': '#dbeafe',
      'editor.inactiveSelectionBackground': '#eef2ff',
      'editorCursor.foreground': '#2563eb',
      'editor.lineHighlightBackground': '#f8fafc',
      'editorIndentGuide.background': '#e5e7eb',
      'editorIndentGuide.activeBackground': '#cbd5e1',
    },
    rules: syntaxRules(SYNTAX.light),
  },
  'sqloj-dark': {
    base: 'vs-dark',
    colors: {
      'editor.background': '#1e293b',
      'editor.foreground': SYNTAX.dark.identifier,
      'editorLineNumber.foreground': '#64748b',
      'editorLineNumber.activeForeground': '#94a3b8',
      'editor.selectionBackground': '#1e3a5f',
      'editor.inactiveSelectionBackground': '#152033',
      'editorCursor.foreground': '#60a5fa',
      'editor.lineHighlightBackground': '#152033',
      'editorIndentGuide.background': '#334155',
      'editorIndentGuide.activeBackground': '#475569',
    },
    rules: syntaxRules(SYNTAX.dark),
  },
  'sqloj-parchment': {
    base: 'vs',
    colors: {
      'editor.background': '#fdfcf8',
      'editor.foreground': SYNTAX.parchment.identifier,
      'editorLineNumber.foreground': '#bdbdbd',
      'editorLineNumber.activeForeground': '#9e9e9e',
      'editor.selectionBackground': '#ebf4f0',
      'editor.inactiveSelectionBackground': '#f5f2eb',
      'editorCursor.foreground': '#4a8b71',
      'editor.lineHighlightBackground': '#f5f2eb',
      'editorIndentGuide.background': '#e5e5e5',
      'editorIndentGuide.activeBackground': '#d9d3c7',
    },
    rules: syntaxRules(SYNTAX.parchment),
  },
  'sqloj-slate': {
    base: 'vs',
    colors: {
      'editor.background': '#ffffff',
      'editor.foreground': SYNTAX.slate.identifier,
      'editorLineNumber.foreground': '#9ca3af',
      'editorLineNumber.activeForeground': '#6b7280',
      'editor.selectionBackground': '#eef2ff',
      'editor.inactiveSelectionBackground': '#f0f2f5',
      'editorCursor.foreground': '#6366f1',
      'editor.lineHighlightBackground': '#e8ecf1',
      'editorIndentGuide.background': '#e5e7eb',
      'editorIndentGuide.activeBackground': '#d1d5db',
    },
    rules: syntaxRules(SYNTAX.slate),
  },
  'sqloj-midnight': {
    base: 'vs-dark',
    colors: {
      'editor.background': '#161b22',
      'editor.foreground': SYNTAX.midnight.identifier,
      'editorLineNumber.foreground': '#6e7681',
      'editorLineNumber.activeForeground': '#8b949e',
      'editor.selectionBackground': '#1a2a42',
      'editor.inactiveSelectionBackground': '#12171e',
      'editorCursor.foreground': '#79c0ff',
      'editor.lineHighlightBackground': '#12171e',
      'editorIndentGuide.background': '#30363d',
      'editorIndentGuide.activeBackground': '#484f58',
    },
    rules: syntaxRules(SYNTAX.midnight),
  },
}

export function registerMonacoThemes(monaco: Monaco): void {
  for (const [id, palette] of Object.entries(THEME_PALETTES) as [
    MonacoThemeId,
    ThemePalette,
  ][]) {
    monaco.editor.defineTheme(id, {
      base: palette.base,
      inherit: true,
      rules: palette.rules,
      colors: palette.colors,
    })
  }
}

export function resolveMonacoThemeId(
  preset: ThemePreset = loadAppearance().themePreset,
  mode: 'light' | 'dark' = resolveEffectiveTheme(),
): MonacoThemeId {
  if (preset === 'midnight') return 'sqloj-midnight'
  if (preset === 'parchment') return 'sqloj-parchment'
  if (preset === 'slate') return 'sqloj-slate'
  return mode === 'dark' ? 'sqloj-dark' : 'sqloj-light'
}

export function monacoThemeId(): MonacoThemeId {
  const appearance = loadAppearance()
  return resolveMonacoThemeId(appearance.themePreset, resolveEffectiveTheme(appearance))
}
