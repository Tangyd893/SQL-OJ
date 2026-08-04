const TAB_PREFIX = 'sql-oj.tab:'
const RESULT_PREFIX = 'sql-oj.result:'

export type ProblemTab = 'desc' | 'result' | 'history' | 'solution'

export function tabKey(problemId: string) {
  return `${TAB_PREFIX}${problemId}`
}

export function resultKey(problemId: string) {
  return `${RESULT_PREFIX}${problemId}`
}

export function loadTab(problemId: string): ProblemTab | null {
  const raw = sessionStorage.getItem(tabKey(problemId))
  if (
    raw === 'desc' ||
    raw === 'result' ||
    raw === 'history' ||
    raw === 'solution'
  ) {
    return raw
  }
  if (raw === 'schema') {
    return 'desc'
  }
  return null
}

export function saveTab(problemId: string, tab: ProblemTab) {
  sessionStorage.setItem(tabKey(problemId), tab)
}

export function loadResult<T>(problemId: string): T | null {
  try {
    const raw = sessionStorage.getItem(resultKey(problemId))
    if (!raw) return null
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

export function saveResult(problemId: string, result: unknown) {
  sessionStorage.setItem(resultKey(problemId), JSON.stringify(result))
}

export function clearResult(problemId: string) {
  sessionStorage.removeItem(resultKey(problemId))
}
