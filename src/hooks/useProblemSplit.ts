import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import {
  loadLayoutPrefs,
  saveLayoutPrefs,
  SPLIT_MAX,
  SPLIT_MIN,
  TOOLBAR_HEIGHT_AUTO,
  toolbarHeightMaxPx,
  type LayoutPrefs,
} from '../lib/layoutPrefs'

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

type DragKind = 'split' | 'toolbar'

export function useProblemSplit() {
  const splitRef = useRef<HTMLDivElement>(null)
  const leftPaneRef = useRef<HTMLElement | null>(null)
  const toolbarRef = useRef<HTMLElement | null>(null)
  const toolbarContentRef = useRef<HTMLDivElement | null>(null)

  const [leftPercent, setLeftPercent] = useState(
    () => loadLayoutPrefs().problemLeftPercent,
  )
  const [toolbarHeight, setToolbarHeight] = useState(
    () => loadLayoutPrefs().problemToolbarHeight,
  )
  const [dragging, setDragging] = useState<DragKind | null>(null)

  const leftPercentRef = useRef(leftPercent)
  const toolbarHeightRef = useRef(toolbarHeight)
  leftPercentRef.current = leftPercent
  toolbarHeightRef.current = toolbarHeight

  const dragState = useRef<{
    kind: DragKind
    pointerId: number
    startClient: number
    startValue: number
    contentMin: number
  } | null>(null)

  const applyLeftWidth = useCallback((percent: number) => {
    const pane = leftPaneRef.current
    if (pane) pane.style.width = `${percent}%`
  }, [])

  const applyToolbarHeight = useCallback((height: number) => {
    const bar = toolbarRef.current
    if (!bar) return
    if (height <= 0) {
      bar.style.minHeight = ''
    } else {
      bar.style.minHeight = `${height}px`
    }
  }, [])

  // Re-apply when committed values change. Skip while dragging so React
  // re-renders (e.g. setDragging) cannot clobber the live DOM size.
  useLayoutEffect(() => {
    if (dragging) return
    applyLeftWidth(leftPercent)
    applyToolbarHeight(toolbarHeight)
  }, [leftPercent, toolbarHeight, dragging, applyLeftWidth, applyToolbarHeight])

  // Mirror usePointerSize: after setDragging, restore live sizes that React
  // style props may have overwritten on the same frame.
  useLayoutEffect(() => {
    if (!dragging) return
    if (dragging === 'split') applyLeftWidth(leftPercentRef.current)
    if (dragging === 'toolbar') applyToolbarHeight(toolbarHeightRef.current)
  }, [dragging, applyLeftWidth, applyToolbarHeight])

  const setLeftPaneNode = useCallback(
    (node: HTMLElement | null) => {
      leftPaneRef.current = node
      if (node) node.style.width = `${leftPercentRef.current}%`
    },
    [],
  )

  const setToolbarNode = useCallback((node: HTMLElement | null) => {
    toolbarRef.current = node
    if (node) {
      const h = toolbarHeightRef.current
      if (h <= 0) node.style.minHeight = ''
      else node.style.minHeight = `${h}px`
    }
  }, [])

  useEffect(() => {
    const sync = () => {
      const prefs = loadLayoutPrefs()
      setLeftPercent(prefs.problemLeftPercent)
      setToolbarHeight(prefs.problemToolbarHeight)
    }
    window.addEventListener('sqloj:layout-changed', sync)
    return () => window.removeEventListener('sqloj:layout-changed', sync)
  }, [])

  /** Natural content height; never larger than the toolbar's current box. */
  const measureToolbarContentMin = useCallback(() => {
    const content = toolbarContentRef.current
    const bar = toolbarRef.current
    if (!bar) return 56
    const barH = bar.getBoundingClientRect().height
    if (!content) return Math.round(barH)
    const styles = getComputedStyle(bar)
    const padY =
      (parseFloat(styles.paddingTop) || 0) + (parseFloat(styles.paddingBottom) || 0)
    const measured = content.getBoundingClientRect().height + padY
    // Cap at current height so a bad measurement cannot jump the bar on grab.
    return Math.round(Math.min(measured, barH) || barH)
  }, [])

  const endDrag = useCallback(() => {
    const state = dragState.current
    dragState.current = null
    setDragging(null)
    document.body.classList.remove('split-dragging', 'toolbar-dragging')

    if (!state) return

    if (state.kind === 'split') {
      const next = clamp(leftPercentRef.current, SPLIT_MIN, SPLIT_MAX)
      const rounded = Math.round(next)
      setLeftPercent(rounded)
      applyLeftWidth(rounded)
      const prefs: LayoutPrefs = {
        ...loadLayoutPrefs(),
        problemLeftPercent: rounded,
      }
      saveLayoutPrefs(prefs)
      return
    }

    const contentMin = state.contentMin
    let next = toolbarHeightRef.current
    if (next <= contentMin + 1) next = TOOLBAR_HEIGHT_AUTO
    else next = Math.round(clamp(next, contentMin, toolbarHeightMaxPx()))
    setToolbarHeight(next)
    applyToolbarHeight(next)
    const prefs: LayoutPrefs = {
      ...loadLayoutPrefs(),
      problemToolbarHeight: next,
    }
    saveLayoutPrefs(prefs)
  }, [applyLeftWidth, applyToolbarHeight])

  const onSplitPointerDown = useCallback((e: React.PointerEvent) => {
    if (e.button !== 0) return
    e.preventDefault()
    e.currentTarget.setPointerCapture(e.pointerId)
    dragState.current = {
      kind: 'split',
      pointerId: e.pointerId,
      startClient: e.clientX,
      startValue: leftPercentRef.current,
      contentMin: 0,
    }
    setDragging('split')
    document.body.classList.add('split-dragging')
  }, [])

  const onToolbarPointerDown = useCallback((e: React.PointerEvent) => {
    if (e.button !== 0) return
    e.preventDefault()
    e.currentTarget.setPointerCapture(e.pointerId)
    const bar = toolbarRef.current
    // Always use live rendered height — never the preference — so the bar
    // does not jump to a different size on press.
    const startHeight = bar?.getBoundingClientRect().height ?? 56
    const contentMin = measureToolbarContentMin()
    dragState.current = {
      kind: 'toolbar',
      pointerId: e.pointerId,
      startClient: e.clientY,
      startValue: startHeight,
      contentMin: Math.min(contentMin, Math.round(startHeight)),
    }
    toolbarHeightRef.current = startHeight
    setDragging('toolbar')
    document.body.classList.add('toolbar-dragging')
    // Do not apply height here — that was causing an immediate jump.
  }, [measureToolbarContentMin])

  const onResizerPointerMove = useCallback(
    (e: React.PointerEvent) => {
      const state = dragState.current
      if (!state || state.pointerId !== e.pointerId) return

      if (state.kind === 'split') {
        const container = splitRef.current
        if (!container) return
        const width = container.getBoundingClientRect().width
        if (width <= 0) return
        const deltaPercent = ((e.clientX - state.startClient) / width) * 100
        const next = clamp(state.startValue + deltaPercent, SPLIT_MIN, SPLIT_MAX)
        leftPercentRef.current = next
        applyLeftWidth(next)
        return
      }

      const maxH = toolbarHeightMaxPx()
      const next = clamp(
        state.startValue + (e.clientY - state.startClient),
        state.contentMin,
        maxH,
      )
      toolbarHeightRef.current = next
      applyToolbarHeight(next)
    },
    [applyLeftWidth, applyToolbarHeight],
  )

  const onResizerPointerUp = useCallback(
    (e: React.PointerEvent) => {
      const state = dragState.current
      if (!state || state.pointerId !== e.pointerId) return
      try {
        e.currentTarget.releasePointerCapture(e.pointerId)
      } catch {
        /* already released */
      }
      endDrag()
    },
    [endDrag],
  )

  return {
    splitRef,
    setLeftPaneNode,
    setToolbarNode,
    toolbarContentRef,
    leftPercent,
    toolbarHeight,
    dragging,
    onSplitPointerDown,
    onToolbarPointerDown,
    onResizerPointerMove,
    onResizerPointerUp,
  }
}
