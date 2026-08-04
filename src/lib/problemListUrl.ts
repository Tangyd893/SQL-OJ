import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { DifficultyFilter, StatusFilter } from './problemFilters'

const SCROLL_KEY = 'sql-oj.problems-scroll'

export interface ProblemListFilters {
  query: string
  status: StatusFilter
  difficulty: DifficultyFilter
  tag: string | null
}

function parseStatus(value: string | null): StatusFilter {
  if (value === 'accepted' || value === 'pending') return value
  return 'all'
}

function parseDifficulty(value: string | null): DifficultyFilter {
  if (value === 'easy' || value === 'medium' || value === 'hard') return value
  return 'all'
}

export function readFiltersFromSearch(params: URLSearchParams): ProblemListFilters {
  return {
    query: params.get('q') ?? '',
    status: parseStatus(params.get('status')),
    difficulty: parseDifficulty(params.get('difficulty')),
    tag: params.get('tag'),
  }
}

export function writeFiltersToSearch(filters: ProblemListFilters): URLSearchParams {
  const params = new URLSearchParams()
  if (filters.query.trim()) params.set('q', filters.query.trim())
  if (filters.status !== 'all') params.set('status', filters.status)
  if (filters.difficulty !== 'all') params.set('difficulty', filters.difficulty)
  if (filters.tag) params.set('tag', filters.tag)
  return params
}

export function useProblemListUrlSync(filters: ProblemListFilters): void {
  const [searchParams, setSearchParams] = useSearchParams()

  useEffect(() => {
    const next = writeFiltersToSearch(filters)
    const current = writeFiltersToSearch(readFiltersFromSearch(searchParams))
    if (next.toString() === current.toString()) return
    setSearchParams(next, { replace: true })
  }, [filters, searchParams, setSearchParams])
}

export function saveProblemsScrollTop(top: number): void {
  sessionStorage.setItem(SCROLL_KEY, String(top))
}

export function loadProblemsScrollTop(): number {
  const raw = sessionStorage.getItem(SCROLL_KEY)
  if (!raw) return 0
  const n = Number(raw)
  return Number.isFinite(n) ? n : 0
}
