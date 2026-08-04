const LAST_PROBLEM_KEY = 'sql-oj.last-problem'
const PREFER_LIST_KEY = 'sql-oj.prefer-list'

export function setLastProblem(id: string): void {
  sessionStorage.setItem(LAST_PROBLEM_KEY, id)
  sessionStorage.removeItem(PREFER_LIST_KEY)
}

export function preferProblemList(): void {
  sessionStorage.setItem(PREFER_LIST_KEY, '1')
}

export function getProblemsNavPath(): string {
  if (sessionStorage.getItem(PREFER_LIST_KEY)) {
    return '/problems'
  }
  const last = sessionStorage.getItem(LAST_PROBLEM_KEY)
  return last ? `/problems/${last}` : '/problems'
}

export function isProblemsNavActive(pathname: string): boolean {
  return pathname === '/problems' || pathname.startsWith('/problems/')
}
