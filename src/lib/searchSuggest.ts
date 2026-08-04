import type { ProblemSummary } from '../types'
import type { SubmissionRecord } from '../types'

export function buildSearchTermsFromStrings(values: Iterable<string>): string[] {
  const set = new Set<string>()
  for (const raw of values) {
    const v = raw.trim()
    if (v) set.add(v)
  }
  return [...set].sort((a, b) => a.localeCompare(b, 'zh-CN'))
}

export function suggestTerms(query: string, terms: string[], limit = 10): string[] {
  const q = query.trim()
  if (!q) return []
  const lower = q.toLowerCase()
  return terms
    .filter((t) => {
      const tl = t.toLowerCase()
      return tl.includes(lower) && tl !== lower
    })
    .slice(0, limit)
}

export function buildProblemSearchTerms(problems: ProblemSummary[]): string[] {
  const values: string[] = []
  for (const p of problems) {
    values.push(p.id, p.title, ...p.tags)
  }
  return buildSearchTermsFromStrings(values)
}

export function buildSubmissionSearchTerms(records: SubmissionRecord[]): string[] {
  const values: string[] = []
  for (const r of records) {
    values.push(r.problemId)
    if (r.message.trim()) values.push(r.message.trim())
  }
  return buildSearchTermsFromStrings(values)
}
