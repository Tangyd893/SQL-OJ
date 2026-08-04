let shortcutRecording = false

export function setShortcutRecording(active: boolean): void {
  shortcutRecording = active
}

export function isShortcutRecording(): boolean {
  return shortcutRecording
}

const STORAGE_KEY = 'sql-oj.shortcuts'

export type ShortcutId =
  | 'zoomIn'
  | 'zoomOut'
  | 'zoomReset'
  | 'appFontIn'
  | 'appFontOut'
  | 'editorFontIn'
  | 'editorFontOut'
  | 'submit'
  | 'preview'

export type ShortcutScope = 'global' | 'problem'

export interface KeyChord {
  ctrl: boolean
  shift: boolean
  alt: boolean
  key: string
}

export interface ShortcutDefinition {
  id: ShortcutId
  label: string
  scope: ShortcutScope
  hint?: string
}

export interface ShortcutBinding extends ShortcutDefinition {
  chord: KeyChord
  defaultChord: KeyChord
}

const CODE_LABELS: Record<string, string> = {
  Enter: 'Enter',
  Equal: '+',
  Minus: '-',
  BracketRight: ']',
  BracketLeft: '[',
  Digit0: '0',
}

export const SHORTCUT_DEFINITIONS: ShortcutDefinition[] = [
  { id: 'zoomIn', label: '界面放大', scope: 'global', hint: '全局' },
  { id: 'zoomOut', label: '界面缩小', scope: 'global' },
  { id: 'zoomReset', label: '重置缩放', scope: 'global' },
  { id: 'appFontIn', label: '应用字号增大', scope: 'global' },
  { id: 'appFontOut', label: '应用字号减小', scope: 'global' },
  { id: 'editorFontIn', label: '编辑器字号增大', scope: 'global' },
  { id: 'editorFontOut', label: '编辑器字号减小', scope: 'global' },
  { id: 'submit', label: '提交判题', scope: 'problem', hint: '做题页' },
  { id: 'preview', label: '试运行', scope: 'problem', hint: '做题页' },
]

const DEFAULT_CHORDS: Record<ShortcutId, KeyChord> = {
  zoomIn: { ctrl: true, shift: false, alt: false, key: 'Equal' },
  zoomOut: { ctrl: true, shift: false, alt: false, key: 'Minus' },
  zoomReset: { ctrl: true, shift: false, alt: false, key: 'Digit0' },
  appFontIn: { ctrl: true, shift: true, alt: false, key: 'Equal' },
  appFontOut: { ctrl: true, shift: true, alt: false, key: 'Minus' },
  editorFontIn: { ctrl: true, shift: false, alt: false, key: 'BracketRight' },
  editorFontOut: { ctrl: true, shift: false, alt: false, key: 'BracketLeft' },
  submit: { ctrl: true, shift: false, alt: false, key: 'Enter' },
  preview: { ctrl: true, shift: true, alt: false, key: 'Enter' },
}

export function loadShortcutBindings(): ShortcutBinding[] {
  let overrides: Partial<Record<ShortcutId, KeyChord>> = {}
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) overrides = JSON.parse(raw) as Partial<Record<ShortcutId, KeyChord>>
  } catch {
    overrides = {}
  }

  return SHORTCUT_DEFINITIONS.map((def) => {
    const defaultChord = DEFAULT_CHORDS[def.id]
    const chord = overrides[def.id] ?? defaultChord
    return { ...def, chord: { ...chord }, defaultChord: { ...defaultChord } }
  })
}

export function saveShortcutChord(id: ShortcutId, chord: KeyChord): ShortcutBinding[] {
  const overrides = readOverrides()
  overrides[id] = chord
  localStorage.setItem(STORAGE_KEY, JSON.stringify(overrides))
  const next = loadShortcutBindings()
  window.dispatchEvent(new CustomEvent('sqloj:shortcuts-changed', { detail: next }))
  return next
}

export function resetShortcut(id: ShortcutId): ShortcutBinding[] {
  const overrides = readOverrides()
  delete overrides[id]
  localStorage.setItem(STORAGE_KEY, JSON.stringify(overrides))
  const next = loadShortcutBindings()
  window.dispatchEvent(new CustomEvent('sqloj:shortcuts-changed', { detail: next }))
  return next
}

export function resetAllShortcuts(): ShortcutBinding[] {
  localStorage.removeItem(STORAGE_KEY)
  const next = loadShortcutBindings()
  window.dispatchEvent(new CustomEvent('sqloj:shortcuts-changed', { detail: next }))
  return next
}

export function getShortcutChord(id: ShortcutId): KeyChord {
  return loadShortcutBindings().find((b) => b.id === id)?.chord ?? DEFAULT_CHORDS[id]
}

export function formatChord(chord: KeyChord): string {
  const parts: string[] = []
  if (chord.ctrl) parts.push('Ctrl')
  if (chord.shift) parts.push('Shift')
  if (chord.alt) parts.push('Alt')
  const label = CODE_LABELS[chord.key] ?? chord.key
  parts.push(label)
  return parts.join('+')
}

export function chordFromEvent(e: KeyboardEvent): KeyChord | null {
  if (['Control', 'Shift', 'Alt', 'Meta'].includes(e.key)) return null
  return {
    ctrl: e.ctrlKey || e.metaKey,
    shift: e.shiftKey,
    alt: e.altKey,
    key: e.code,
  }
}

export function eventMatchesChord(e: KeyboardEvent, chord: KeyChord): boolean {
  const ctrl = e.ctrlKey || e.metaKey
  if (chord.ctrl !== ctrl) return false
  if (chord.shift !== e.shiftKey) return false
  if (chord.alt !== e.altKey) return false
  return e.code === chord.key
}

export function findMatchingShortcut(
  e: KeyboardEvent,
  scope: ShortcutScope | 'any',
): ShortcutBinding | null {
  for (const binding of loadShortcutBindings()) {
    if (scope !== 'any' && binding.scope !== scope && binding.scope !== 'global') {
      if (scope === 'global' && binding.scope === 'problem') continue
    }
    if (eventMatchesChord(e, binding.chord)) return binding
  }
  return null
}

export function chordsConflict(a: KeyChord, b: KeyChord): boolean {
  return (
    a.ctrl === b.ctrl &&
    a.shift === b.shift &&
    a.alt === b.alt &&
    a.key === b.key
  )
}

export function findConflict(
  id: ShortcutId,
  chord: KeyChord,
): ShortcutBinding | null {
  return (
    loadShortcutBindings().find(
      (b) => b.id !== id && chordsConflict(b.chord, chord),
    ) ?? null
  )
}

/** Monaco KeyMod / KeyCode bit mask for editor actions */
export function chordToMonacoKeybinding(chord: KeyChord): number {
  let mod = 0
  if (chord.ctrl) mod |= 2048
  if (chord.shift) mod |= 1024
  if (chord.alt) mod |= 512
  const keyMap: Record<string, number> = {
    Enter: 3,
    Equal: 86,
    Minus: 87,
    BracketRight: 99,
    BracketLeft: 98,
    Digit0: 40,
  }
  return mod | (keyMap[chord.key] ?? 0)
}

function readOverrides(): Partial<Record<ShortcutId, KeyChord>> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    return JSON.parse(raw) as Partial<Record<ShortcutId, KeyChord>>
  } catch {
    return {}
  }
}
