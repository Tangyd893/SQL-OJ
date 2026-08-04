import { useCallback, useEffect, useRef, useState } from 'react'
import {
  loadLayoutPrefs,
  saveLayoutPrefs,
  SPLIT_MAX,
  SPLIT_MIN,
  type LayoutPrefs,
} from '../lib/layoutPrefs'

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

export function useProblemSplit() {
  const splitRef = useRef<HTMLDivElement>(null)
  const [leftPercent, setLeftPercent] = useState(
    () => loadLayoutPrefs().problemLeftPercent,
  )
  const [dragging, setDragging] = useState(false)
  const dragState = useRef<{ startX: number; startPercent: number } | null>(null)

  const onResizeStart = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      dragState.current = { startX: e.clientX, startPercent: leftPercent }
      setDragging(true)
    },
    [leftPercent],
  )

  useEffect(() => {
    if (!dragging) return

    const onMove = (e: MouseEvent) => {
      const container = splitRef.current
      const state = dragState.current
      if (!container || !state) return
      const width = container.getBoundingClientRect().width
      if (width <= 0) return
      const deltaPercent = ((e.clientX - state.startX) / width) * 100
      setLeftPercent(
        clamp(Math.round(state.startPercent + deltaPercent), SPLIT_MIN, SPLIT_MAX),
      )
    }

    const onUp = () => {
      setDragging(false)
      dragState.current = null
      setLeftPercent((current) => {
        const prefs: LayoutPrefs = {
          ...loadLayoutPrefs(),
          problemLeftPercent: current,
        }
        saveLayoutPrefs(prefs)
        return current
      })
      document.body.classList.remove('split-dragging')
    }

    document.body.classList.add('split-dragging')
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
      document.body.classList.remove('split-dragging')
    }
  }, [dragging])

  return { splitRef, leftPercent, dragging, onResizeStart }
}
