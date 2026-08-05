import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

type Axis = 'x' | 'y'

/**
 * Pointer-driven 1D resize: DOM updates while dragging, commit on release.
 * Avoids per-frame React re-renders (keeps Monaco / heavy trees smooth).
 */
export function usePointerSize({
  initial,
  min,
  max,
  axis,
  bodyClass,
  onCommit,
}: {
  initial: number
  min: number
  max: number
  axis: Axis
  bodyClass: string
  onCommit: (value: number) => void
}) {
  const [value, setValue] = useState(initial)
  const [dragging, setDragging] = useState(false)
  const valueRef = useRef(value)
  valueRef.current = value
  const targetRef = useRef<HTMLElement | null>(null)
  const dragRef = useRef<{
    pointerId: number
    startClient: number
    startValue: number
  } | null>(null)

  const applySize = useCallback(
    (next: number) => {
      const el = targetRef.current
      if (!el) return
      if (axis === 'x') el.style.width = `${next}px`
      else el.style.minHeight = `${next}px`
    },
    [axis],
  )

  const setTargetNode = useCallback(
    (node: HTMLElement | null) => {
      targetRef.current = node
      if (node) applySize(valueRef.current)
    },
    [applySize],
  )

  useEffect(() => {
    if (dragging) return
    applySize(value)
  }, [value, dragging, applySize])

  // After setDragging re-render, React may re-apply the committed style prop;
  // restore the live drag value so the handle does not jump on press.
  useLayoutEffect(() => {
    if (!dragging) return
    applySize(valueRef.current)
  }, [dragging, applySize])

  const onPointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (e.button !== 0) return
      e.preventDefault()
      e.currentTarget.setPointerCapture(e.pointerId)
      // Prefer live box size so press never jumps to a stale preference.
      const live =
        axis === 'x'
          ? targetRef.current?.getBoundingClientRect().width
          : targetRef.current?.getBoundingClientRect().height
      const startValue = live && live > 0 ? live : valueRef.current
      dragRef.current = {
        pointerId: e.pointerId,
        startClient: axis === 'x' ? e.clientX : e.clientY,
        startValue,
      }
      valueRef.current = startValue
      setDragging(true)
      document.body.classList.add(bodyClass)
    },
    [axis, bodyClass],
  )

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      const state = dragRef.current
      if (!state || state.pointerId !== e.pointerId) return
      const client = axis === 'x' ? e.clientX : e.clientY
      const next = clamp(state.startValue + (client - state.startClient), min, max)
      valueRef.current = next
      applySize(next)
    },
    [axis, applySize, max, min],
  )

  const endDrag = useCallback(() => {
    if (!dragRef.current) return
    dragRef.current = null
    setDragging(false)
    document.body.classList.remove(bodyClass)
    const next = Math.round(clamp(valueRef.current, min, max))
    valueRef.current = next
    setValue(next)
    applySize(next)
    onCommit(next)
  }, [applySize, bodyClass, max, min, onCommit])

  const onPointerUp = useCallback(
    (e: React.PointerEvent) => {
      const state = dragRef.current
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

  const syncFromExternal = useCallback(
    (next: number) => {
      const clamped = clamp(Math.round(next), min, max)
      valueRef.current = clamped
      setValue(clamped)
      applySize(clamped)
    },
    [applySize, max, min],
  )

  return {
    value,
    dragging,
    setTargetNode,
    syncFromExternal,
    onPointerDown,
    onPointerMove,
    onPointerUp,
  }
}
