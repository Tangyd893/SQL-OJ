import type { ProblemSummary } from '../types'

export function findProblemIndex(problems: ProblemSummary[], id: string): number {
  return problems.findIndex((p) => p.id === id)
}

export function getNextProblemId(
  problems: ProblemSummary[],
  id: string,
): string | null {
  const idx = findProblemIndex(problems, id)
  if (idx < 0 || idx >= problems.length - 1) return null
  return problems[idx + 1]!.id
}

export function getNeighborWindow(
  problems: ProblemSummary[],
  id: string,
  radius = 10,
): { index: number; seq: number; item: ProblemSummary }[] {
  const index = findProblemIndex(problems, id)
  if (index < 0) return []

  const start = Math.max(0, index - radius)
  const end = Math.min(problems.length, index + radius + 1)
  return problems.slice(start, end).map((item, offset) => ({
    index: start + offset,
    seq: start + offset + 1,
    item,
  }))
}
