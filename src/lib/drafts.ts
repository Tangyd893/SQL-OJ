const DRAFT_PREFIX = 'sql-oj.draft:'
const MAX_DRAFTS = 200

export function draftKey(problemId: string) {
  return `${DRAFT_PREFIX}${problemId}`
}

export function saveDraft(problemId: string, sql: string) {
  localStorage.setItem(draftKey(problemId), sql)
  pruneDrafts(problemId)
}

export function loadDraft(problemId: string): string | null {
  return localStorage.getItem(draftKey(problemId))
}

function pruneDrafts(keepProblemId: string) {
  const keepKey = draftKey(keepProblemId)
  const keys = Object.keys(localStorage).filter((k) => k.startsWith(DRAFT_PREFIX))
  if (keys.length <= MAX_DRAFTS) return
  const removable = keys.filter((k) => k !== keepKey).sort()
  const extra = keys.length - MAX_DRAFTS
  for (let i = 0; i < extra && i < removable.length; i++) {
    localStorage.removeItem(removable[i])
  }
}
