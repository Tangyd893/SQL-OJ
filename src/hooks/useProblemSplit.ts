import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import {
  loadLayoutPrefs,
  saveLayoutPrefs,
  SPLIT_MAX,
  SPLIT_MIN,
  TOOLBAR_HEIGHT_AUTO,
  toolbarHeightMaxPx,
} from '../lib/layoutPrefs'

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

type DragKind = 'split' | 'brief'

/** Collapsed / hidden brief strip. */
export const BRIEF_HEIGHT_MIN = 0
/** Comfortable default when 目标/提示 exist and no saved preference. */
export const BRIEF_HEIGHT_DEFAULT = 120

export function useProblemSplit(hasBriefContent: boolean) {
  const splitRef = useRef<HTMLDivElement>(null)
  const leftPaneRef = useRef<HTMLElement | null>(null)
  const briefRef = useRef<HTMLElement | null>(null)

  const [leftPercent, setLeftPercent] = useState(
    () => loadLayoutPrefs().problemLeftPercent,
  )
  const [briefHeight, setBriefHeight] = useState(() => {
    const saved = loadLayoutPrefs().problemToolbarHeight
    if (saved > 0) return saved
    return hasBriefContent ? BRIEF_HEIGHT_DEFAULT : TOOLBAR_HEIGHT_AUTO
  })
  const [dragging, setDragging] = useState<DragKind | null>(null)

  const leftPercentRef = useRef(leftPercent)
  const briefHeightRef = useRef(briefHeight)
  leftPercentRef.current = leftPercent
  briefHeightRef.current = briefHeight

  const dragState = useRef<{
    kind: DragKind
    pointerId: number
    startClient: number
    startValue: number
  } | null>(null)

  const applyLeftWidth = useCallback((percent: number) => {
    const pane = leftPaneRef.current
    if (pane) pane.style.width = `${percent}%`
  }, [])

  const applyBriefHeight = useCallback((height: number) => {
    const el = briefRef.current
    if (!el) return
    // Use explicit height (not minHeight) so drag delta maps 1:1 to the bar.
    el.style.height = `${Math.max(0, height)}px`
  }, [])

  useLayoutEffect(() => {
    if (dragging) return
    applyLeftWidth(leftPercent)
    applyBriefHeight(briefHeight)
  }, [leftPercent, briefHeight, dragging, applyLeftWidth, applyBriefHeight])

  useLayoutEffect(() => {
    if (!dragging) return
    if (dragging === 'split') applyLeftWidth(leftPercentRef.current)
    if (dragging === 'brief') applyBriefHeight(briefHeightRef.current)
  }, [dragging, applyLeftWidth, applyBriefHeight])

  // When brief content appears and height is still 0, open to default once.
  useEffect(() => {
    if (!hasBriefContent) return
    if (briefHeightRef.current > 0) return
    const saved = loadLayoutPrefs().problemToolbarHeight
    if (saved > 0) return
    const next = BRIEF_HEIGHT_DEFAULT
    briefHeightRef.current = next
    setBriefHeight(next)
    applyBriefHeight(next)
  }, [hasBriefContent, applyBriefHeight])

  const setLeftPaneNode = useCallback((node: HTMLElement | null) => {
    leftPaneRef.current = node
    if (node) node.style.width = `${leftPercentRef.current}%`
  }, [])

  const setBriefNode = useCallback(
    (node: HTMLElement | null) => {
      briefRef.current = node
      if (node) applyBriefHeight(briefHeightRef.current)
    },
    [applyBriefHeight],
  )

  useEffect(() => {
    const sync = () => {
      const prefs = loadLayoutPrefs()
      setLeftPercent(prefs.problemLeftPercent)
      const h =
        prefs.problemToolbarHeight > 0
          ? prefs.problemToolbarHeight
          : hasBriefContent
            ? BRIEF_HEIGHT_DEFAULT
            : TOOLBAR_HEIGHT_AUTO
      setBriefHeight(h)
    }
    window.addEventListener('sqloj:layout-changed', sync)
    return () => window.removeEventListener('sqloj:layout-changed', sync)
  }, [hasBriefContent])

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
      saveLayoutPrefs({
        ...loadLayoutPrefs(),
        problemLeftPercent: rounded,
      })
      return
    }

    let next = Math.round(
      clamp(briefHeightRef.current, BRIEF_HEIGHT_MIN, toolbarHeightMaxPx()),
    )
    if (next <= 1) next = TOOLBAR_HEIGHT_AUTO
    briefHeightRef.current = next
    setBriefHeight(next)
    applyBriefHeight(next)
    saveLayoutPrefs({
      ...loadLayoutPrefs(),
      problemToolbarHeight: next,
    })
  }, [applyLeftWidth, applyBriefHeight])

  const onSplitPointerDown = useCallback((e: React.PointerEvent) => {
    if (e.button !== 0) return
    e.preventDefault()
    e.currentTarget.setPointerCapture(e.pointerId)
    dragState.current = {
      kind: 'split',
      pointerId: e.pointerId,
      startClient: e.clientX,
      startValue: leftPercentRef.current,
    }
    setDragging('split')
    document.body.classList.add('split-dragging')
  }, [])

  const onBriefPointerDown = useCallback((e: React.PointerEvent) => {
    if (e.button !== 0) return
    e.preventDefault()
    e.currentTarget.setPointerCapture(e.pointerId)
    const el = briefRef.current
    // Live height only — never preference — so press cannot jump.
    const startHeight = el?.getBoundingClientRect().height ?? briefHeightRef.current
    dragState.current = {
      kind: 'brief',
      pointerId: e.pointerId,
      startClient: e.clientY,
      startValue: startHeight,
    }
    briefHeightRef.current = startHeight
    // Ensure height is locked to the measured px before any move.
    applyBriefHeight(startHeight)
    setDragging('brief')
    document.body.classList.add('toolbar-dragging')
  }, [applyBriefHeight])

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

      const next = clamp(
        state.startValue + (e.clientY - state.startClient),
        BRIEF_HEIGHT_MIN,
        toolbarHeightMaxPx(),
      )
      briefHeightRef.current = next
      applyBriefHeight(next)
    },
    [applyLeftWidth, applyBriefHeight],
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
    setBriefNode,
    leftPercent,
    briefHeight,
    dragging,
    onSplitPointerDown,
    onBriefPointerDown,
    onResizerPointerMove,
    onResizerPointerUp,
  }
}
