import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import {
  adjustAppFont,
  adjustEditorFont,
  adjustUiZoom,
  resetUiZoom,
  ZOOM_STEP,
} from '../lib/display'
import { invokeShortcut } from '../lib/shortcutHandlers'
import {
  eventMatchesChord,
  isShortcutRecording,
  loadShortcutBindings,
  type ShortcutBinding,
  type ShortcutId,
} from '../lib/shortcuts'

function isTypingInField(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  const tag = target.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true
  return target.isContentEditable && !target.closest('.monaco-editor')
}

function runGlobalAction(id: ShortcutId): void {
  switch (id) {
    case 'zoomIn':
      adjustUiZoom(ZOOM_STEP)
      break
    case 'zoomOut':
      adjustUiZoom(-ZOOM_STEP)
      break
    case 'zoomReset':
      resetUiZoom()
      break
    case 'appFontIn':
      adjustAppFont(1)
      break
    case 'appFontOut':
      adjustAppFont(-1)
      break
    case 'editorFontIn':
      adjustEditorFont(1)
      break
    case 'editorFontOut':
      adjustEditorFont(-1)
      break
    default:
      break
  }
}

function handleBinding(binding: ShortcutBinding, onProblemPage: boolean): boolean {
  if (binding.id === 'submit' || binding.id === 'preview') {
    if (!onProblemPage) return false
    return invokeShortcut(binding.id)
  }
  if (binding.scope === 'global') {
    runGlobalAction(binding.id)
    return true
  }
  return false
}

export function useGlobalShortcuts() {
  const location = useLocation()

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (isShortcutRecording()) return
      if (isTypingInField(e.target)) return

      const bindings = loadShortcutBindings()
      const onProblemPage = /^\/problems\/[^/]+/.test(location.pathname)

      for (const binding of bindings) {
        if (!eventMatchesChord(e, binding.chord)) continue
        if (handleBinding(binding, onProblemPage)) {
          e.preventDefault()
          e.stopPropagation()
        }
        return
      }
    }

    window.addEventListener('keydown', onKeyDown, true)
    return () => window.removeEventListener('keydown', onKeyDown, true)
  }, [location.pathname])
}
