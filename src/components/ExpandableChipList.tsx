import { useEffect, useRef, useState, type ReactNode } from 'react'

type ExpandLevel = 0 | 1 | 2

export function ExpandableChipList({ children }: { children: ReactNode }) {
  const innerRef = useRef<HTMLDivElement>(null)
  const [level, setLevel] = useState<ExpandLevel>(0)
  const [overflows, setOverflows] = useState(false)

  useEffect(() => {
    const el = innerRef.current
    if (!el) return

    const check = () => {
      const oneLine = 30
      setOverflows(el.scrollHeight > oneLine + 2)
    }

    check()
    const ro = new ResizeObserver(check)
    ro.observe(el)
    return () => ro.disconnect()
  }, [children])

  const atMax = level >= 2
  const showToggle = overflows && !atMax

  return (
    <div className={`expandable-chips level-${level}`}>
      <div ref={innerRef} className="expandable-chips-inner">
        {children}
      </div>
      {showToggle && (
        <button
          type="button"
          className="expandable-chips-toggle"
          aria-label="展开更多考点"
          onClick={() => setLevel((l) => (l < 2 ? ((l + 1) as ExpandLevel) : l))}
        >
          ▼
        </button>
      )}
      {overflows && atMax && (
        <button
          type="button"
          className="expandable-chips-toggle"
          aria-label="收起考点"
          onClick={() => setLevel(0)}
        >
          ▲
        </button>
      )}
    </div>
  )
}
