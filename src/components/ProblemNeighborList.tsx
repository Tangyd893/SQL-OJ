import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getNeighborWindow } from '../lib/problemNeighbors'
import { setLastProblem } from '../lib/navigation'
import type { ProblemSummary } from '../types'

interface Props {
  problems: ProblemSummary[]
  currentId: string
}

export function ProblemNeighborList({ problems, currentId }: Props) {
  const navigate = useNavigate()
  const wrapRef = useRef<HTMLDivElement>(null)
  const currentItemRef = useRef<HTMLButtonElement>(null)
  const [open, setOpen] = useState(false)
  const neighbors = getNeighborWindow(problems, currentId, 10)
  const currentIdx = neighbors.findIndex((n) => n.item.id === currentId)

  useEffect(() => {
    if (!open) return
    const onDocClick = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDocClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  useEffect(() => {
    setOpen(false)
  }, [currentId])

  useEffect(() => {
    if (open) {
      currentItemRef.current?.scrollIntoView({ block: 'nearest' })
    }
  }, [open, currentId])

  const go = (id: string) => {
    setLastProblem(id)
    navigate(`/problems/${id}`)
    setOpen(false)
  }

  if (problems.length === 0) return null

  return (
    <div className="problem-neighbor-wrap" ref={wrapRef}>
      <button
        type="button"
        className="btn"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        题目列表
      </button>
      {open && (
        <div className="problem-neighbor-panel" role="listbox" aria-label="邻近题目">
          <div className="problem-neighbor-panel-head">
            按题号 · 当前前后各 10 题
          </div>
          <ul className="problem-neighbor-list">
            {neighbors.map(({ seq, item }) => {
              const isCurrent = item.id === currentId
              const isAccepted = !!item.accepted
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={isCurrent}
                    ref={isCurrent ? currentItemRef : undefined}
                    className={[
                      'problem-neighbor-item',
                      isCurrent ? 'current' : '',
                      isAccepted ? 'accepted' : '',
                    ]
                      .filter(Boolean)
                      .join(' ')}
                    onClick={() => go(item.id)}
                  >
                    <span className="problem-neighbor-seq">{String(seq).padStart(3, '0')}</span>
                    <span className="problem-neighbor-title">{item.title}</span>
                    <span className="problem-neighbor-badges">
                      {isCurrent && <span className="badge badge-current">当前</span>}
                      {isAccepted && <span className="badge badge-ac">已通过</span>}
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
          {currentIdx < 0 && (
            <p className="problem-neighbor-empty">当前题目不在列表中</p>
          )}
        </div>
      )}
    </div>
  )
}
