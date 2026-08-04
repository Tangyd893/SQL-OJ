import { useEffect, useRef, useState, type MutableRefObject, type RefObject } from 'react'
import type { ProblemSummary } from '../types'
import {
  difficultyClass,
  normalizeDifficulty,
  tagBadgeClass,
  type DifficultyFilter,
} from '../lib/problemFilters'

const ROW_HEIGHT = 44
const OVERSCAN = 6
const VIRTUAL_THRESHOLD = 60

export function VirtualProblemTable({
  problems,
  selectedIndex,
  tagFilter,
  scrollRootRef,
  rowRefs,
  onSelectIndex,
  onNavigate,
  onToggleDifficulty,
  onToggleTag,
}: {
  problems: ProblemSummary[]
  selectedIndex: number
  tagFilter: string | null
  scrollRootRef: RefObject<HTMLElement | null>
  rowRefs: MutableRefObject<(HTMLTableRowElement | null)[]>
  onSelectIndex: (index: number) => void
  onNavigate: (id: string) => void
  onToggleDifficulty: (d: DifficultyFilter) => void
  onToggleTag: (tag: string) => void
}) {
  const tableRef = useRef<HTMLTableElement>(null)
  const [range, setRange] = useState({ start: 0, end: problems.length })
  const useVirtual = problems.length >= VIRTUAL_THRESHOLD

  useEffect(() => {
    if (!useVirtual) {
      setRange({ start: 0, end: problems.length })
      return
    }

    const root = scrollRootRef.current
    const table = tableRef.current
    if (!root || !table) return

    const update = () => {
      const tableTop = table.offsetTop
      const relativeScroll = root.scrollTop - tableTop
      const viewport = root.clientHeight
      const start = Math.max(0, Math.floor(relativeScroll / ROW_HEIGHT) - OVERSCAN)
      const visibleCount = Math.ceil(viewport / ROW_HEIGHT) + OVERSCAN * 2
      const end = Math.min(problems.length, start + visibleCount)
      setRange((prev) =>
        prev.start === start && prev.end === end ? prev : { start, end },
      )
    }

    update()
    root.addEventListener('scroll', update, { passive: true })
    window.addEventListener('resize', update)
    return () => {
      root.removeEventListener('scroll', update)
      window.removeEventListener('resize', update)
    }
  }, [problems.length, scrollRootRef, useVirtual])

  useEffect(() => {
    rowRefs.current[selectedIndex]?.scrollIntoView({ block: 'nearest' })
  }, [selectedIndex, rowRefs])

  const topSpacer = useVirtual ? range.start * ROW_HEIGHT : 0
  const bottomSpacer = useVirtual ? (problems.length - range.end) * ROW_HEIGHT : 0
  const visible = useVirtual ? problems.slice(range.start, range.end) : problems

  return (
    <table className="problem-table" ref={tableRef}>
      <thead>
        <tr>
          <th>状态</th>
          <th>编号</th>
          <th>标题</th>
          <th>难度</th>
          <th>标签</th>
        </tr>
      </thead>
      <tbody>
        {topSpacer > 0 && (
          <tr aria-hidden className="virtual-spacer">
            <td colSpan={5} style={{ height: topSpacer, padding: 0, border: 'none' }} />
          </tr>
        )}
        {visible.map((p, offset) => {
          const index = useVirtual ? range.start + offset : offset
          const tagTitle = p.tags.length > 0 ? p.tags.join(' · ') : undefined
          return (
            <tr
              key={p.id}
              ref={(el) => {
                rowRefs.current[index] = el
              }}
              className={`problem-row${index === selectedIndex ? ' selected' : ''}`}
              onClick={() => onNavigate(p.id)}
              onMouseEnter={() => onSelectIndex(index)}
            >
              <td>
                {p.accepted ? (
                  <span className="badge badge-easy">AC</span>
                ) : (
                  <span className="badge badge-muted">—</span>
                )}
              </td>
              <td>{p.id}</td>
              <td>
                <span className="problem-link">{p.title}</span>
              </td>
              <td>
                <button
                  type="button"
                  className={`badge badge-clickable ${difficultyClass(p.difficulty)}`}
                  onClick={(e) => {
                    e.stopPropagation()
                    onToggleDifficulty(normalizeDifficulty(p.difficulty))
                  }}
                >
                  {p.difficulty || 'medium'}
                </button>
              </td>
              <td className="tag-cell" title={tagTitle}>
                <div className="tag-list tag-list-inline">
                  {p.tags.length === 0 ? (
                    '—'
                  ) : (
                    p.tags.map((tag) => (
                      <button
                        key={tag}
                        type="button"
                        className={`badge badge-clickable ${tagBadgeClass(tag)}${tagFilter === tag ? ' active' : ''}`}
                        onClick={(e) => {
                          e.stopPropagation()
                          onToggleTag(tag)
                        }}
                      >
                        {tag}
                      </button>
                    ))
                  )}
                </div>
              </td>
            </tr>
          )
        })}
        {bottomSpacer > 0 && (
          <tr aria-hidden className="virtual-spacer">
            <td colSpan={5} style={{ height: bottomSpacer, padding: 0, border: 'none' }} />
          </tr>
        )}
      </tbody>
    </table>
  )
}
