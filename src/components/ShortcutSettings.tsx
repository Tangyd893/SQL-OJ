import { useCallback, useEffect, useState } from 'react'
import {
  chordFromEvent,
  findConflict,
  formatChord,
  loadShortcutBindings,
  resetAllShortcuts,
  resetShortcut,
  saveShortcutChord,
  setShortcutRecording,
  type KeyChord,
  type ShortcutBinding,
  type ShortcutId,
} from '../lib/shortcuts'

export function ShortcutSettings() {
  const [bindings, setBindings] = useState<ShortcutBinding[]>(() =>
    loadShortcutBindings(),
  )
  const [recordingId, setRecordingId] = useState<ShortcutId | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(() => {
    setBindings(loadShortcutBindings())
  }, [])

  useEffect(() => {
    const onChange = () => refresh()
    window.addEventListener('sqloj:shortcuts-changed', onChange)
    return () => window.removeEventListener('sqloj:shortcuts-changed', onChange)
  }, [refresh])

  useEffect(() => {
    setShortcutRecording(recordingId !== null)
    if (!recordingId) return

    const onKeyDown = (e: KeyboardEvent) => {
      e.preventDefault()
      e.stopPropagation()
      if (e.key === 'Escape') {
        setRecordingId(null)
        setError(null)
        return
      }
      const chord = chordFromEvent(e)
      if (!chord) return

      const conflict = findConflict(recordingId, chord)
      if (conflict) {
        setError(`与「${conflict.label}」冲突（${formatChord(conflict.chord)}）`)
        return
      }

      setBindings(saveShortcutChord(recordingId, chord))
      setRecordingId(null)
      setError(null)
    }

    window.addEventListener('keydown', onKeyDown, true)
    return () => {
      window.removeEventListener('keydown', onKeyDown, true)
      setShortcutRecording(false)
    }
  }, [recordingId])

  const onResetOne = (id: ShortcutId) => {
    setBindings(resetShortcut(id))
    setError(null)
  }

  const onResetAll = () => {
    setBindings(resetAllShortcuts())
    setError(null)
  }

  return (
    <div className="shortcut-settings">
      <p className="settings-desc">
        点击「录制」后按下新的组合键，Esc 取消。做题页快捷键仅在打开题目时生效。
      </p>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="shortcut-table">
        <div className="shortcut-table-head">
          <span>动作</span>
          <span>快捷键</span>
          <span>操作</span>
        </div>
        {bindings.map((binding) => (
          <div key={binding.id} className="shortcut-row">
            <div>
              <div className="setting-label">{binding.label}</div>
              {binding.hint && <div className="setting-hint">{binding.hint}</div>}
            </div>
            <code className="shortcut-chord">
              {recordingId === binding.id ? '按下组合键…' : formatChord(binding.chord)}
            </code>
            <div className="shortcut-row-actions">
              <button
                type="button"
                className={`btn btn-sm${recordingId === binding.id ? ' btn-primary' : ''}`}
                onClick={() => {
                  setError(null)
                  setRecordingId(binding.id)
                }}
              >
                {recordingId === binding.id ? '录制中' : '录制'}
              </button>
              <button
                type="button"
                className="btn btn-sm"
                disabled={chordsEqual(binding.chord, binding.defaultChord)}
                onClick={() => onResetOne(binding.id)}
              >
                还原
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="settings-actions">
        <button type="button" className="btn" onClick={onResetAll}>
          还原全部快捷键
        </button>
      </div>
    </div>
  )
}

function chordsEqual(a: KeyChord, b: KeyChord): boolean {
  return a.ctrl === b.ctrl && a.shift === b.shift && a.alt === b.alt && a.key === b.key
}
