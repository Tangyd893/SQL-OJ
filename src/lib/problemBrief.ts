/** Split ## 目标 / ## 提示 out of problem description markdown. */

export interface ProblemBriefParts {
  /** Body left for the 题目描述 tab (目标/提示 removed). */
  body: string
  /** Markdown under ## 目标 (or legacy ## 任务). */
  goals: string | null
  /** Markdown under ## 提示. */
  hints: string | null
}

const GOAL_TITLES = new Set(['目标', '任务'])
const HINT_TITLES = new Set(['提示'])

function parseHeading(line: string): string | null {
  const m = /^(#{1,6})\s+(.+?)\s*$/.exec(line)
  if (!m || m[1].length !== 2) return null
  return m[2].trim()
}

/**
 * Extract ## 目标 / ## 任务 / ## 提示 sections. Remaining markdown is `body`.
 */
export function splitProblemBrief(description: string): ProblemBriefParts {
  const text = description.replace(/\r\n/g, '\n')
  if (!text.trim()) {
    return { body: '', goals: null, hints: null }
  }

  const lines = text.split('\n')
  const bodyLines: string[] = []
  let goalsLines: string[] | null = null
  let hintsLines: string[] | null = null
  let current: 'body' | 'goals' | 'hints' = 'body'

  for (const line of lines) {
    const heading = parseHeading(line)
    if (heading !== null) {
      if (GOAL_TITLES.has(heading)) {
        current = 'goals'
        if (!goalsLines) goalsLines = []
        continue
      }
      if (HINT_TITLES.has(heading)) {
        current = 'hints'
        if (!hintsLines) hintsLines = []
        continue
      }
      // Other ## headings belong in the description body.
      current = 'body'
      bodyLines.push(line)
      continue
    }

    if (current === 'goals') {
      goalsLines!.push(line)
    } else if (current === 'hints') {
      hintsLines!.push(line)
    } else {
      bodyLines.push(line)
    }
  }

  const trimBlock = (lines: string[] | null): string | null => {
    if (!lines) return null
    const s = lines.join('\n').trim()
    return s ? s : null
  }

  return {
    body: bodyLines.join('\n').trim(),
    goals: trimBlock(goalsLines),
    hints: trimBlock(hintsLines),
  }
}
