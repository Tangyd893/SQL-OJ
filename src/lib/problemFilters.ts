import type { ProblemSummary } from '../types'

export type StatusFilter = 'all' | 'accepted' | 'pending'
export type DifficultyFilter = 'all' | 'easy' | 'medium' | 'hard'

export function normalizeDifficulty(raw: string): 'easy' | 'medium' | 'hard' {
  const key = raw.trim().toLowerCase()
  if (key === 'easy') return 'easy'
  if (key === 'hard') return 'hard'
  return 'medium'
}

export function difficultyClass(d: string): string {
  const key = normalizeDifficulty(d)
  if (key === 'easy') return 'badge-easy'
  if (key === 'hard') return 'badge-hard'
  return 'badge-medium'
}

export function tagBadgeClass(tag: string): string {
  let hash = 0
  for (let i = 0; i < tag.length; i++) {
    hash = (hash + tag.charCodeAt(i)) % 6
  }
  return `badge-tag badge-tag-${hash}`
}

export function collectTags(problems: ProblemSummary[]): string[] {
  const set = new Set<string>()
  for (const p of problems) {
    for (const t of p.tags) {
      const trimmed = t.trim()
      if (trimmed) set.add(trimmed)
    }
  }
  return [...set].sort((a, b) => a.localeCompare(b, 'zh-CN'))
}

export interface ProblemFilters {
  query: string
  status: StatusFilter
  difficulty: DifficultyFilter
  tag: string | null
}

export function filterProblems(
  problems: ProblemSummary[],
  filters: ProblemFilters,
): ProblemSummary[] {
  const q = filters.query.trim().toLowerCase()
  return problems.filter((p) => {
    if (filters.status === 'accepted' && !p.accepted) return false
    if (filters.status === 'pending' && p.accepted) return false
    if (
      filters.difficulty !== 'all' &&
      normalizeDifficulty(p.difficulty) !== filters.difficulty
    ) {
      return false
    }
    if (filters.tag && !p.tags.includes(filters.tag)) return false
    if (!q) return true
    return (
      p.id.toLowerCase().includes(q) ||
      p.title.toLowerCase().includes(q) ||
      p.tags.some((t) => t.toLowerCase().includes(q))
    )
  })
}

export function countByDifficulty(problems: ProblemSummary[]) {
  const counts = { all: problems.length, easy: 0, medium: 0, hard: 0 }
  for (const p of problems) {
    counts[normalizeDifficulty(p.difficulty)]++
  }
  return counts
}

export function countByTag(problems: ProblemSummary[], tag: string): number {
  return problems.filter((p) => p.tags.includes(tag)).length
}
