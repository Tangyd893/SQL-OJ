export interface ListProblemsResult {
  problems: ProblemSummary[]
  warnings: string[]
}

export interface AppSettings {
  problemBankPath: string | null
}

export interface BankInspectResult {
  valid: boolean
  path: string
  name: string | null
  version: string | null
  problemCount: number
  warnings: string[]
  error: string | null
}

export interface BankStatus {
  linked: boolean
  path: string | null
  pathExists: boolean
  name: string | null
  version: string | null
  problemCount: number
  warnings: string[]
  error: string | null
}

export interface ProblemSummary {
  id: string
  title: string
  difficulty: string
  tags: string[]
  accepted?: boolean
}

export interface ProblemDetail {
  id: string
  title: string
  difficulty: string
  tags: string[]
  description: string
  schemaSql: string
  caseCount: number
  solutionSql?: string | null
  solutionExplanation?: string | null
  expectedColumns: string[]
  expectedRows: unknown[][]
}

export interface CaseResult {
  caseId: string
  passed: boolean
  message: string
  expectedColumns?: string[]
  expectedRows?: unknown[][]
  actualColumns?: string[]
  actualRows?: unknown[][]
}

export interface JudgeResult {
  accepted: boolean
  message: string
  cases: CaseResult[]
  durationMs: number
}

export interface SubmissionRecord {
  id: number
  problemId: string
  sql: string
  accepted: boolean
  message: string
  createdAt: string
}

export interface DailyActivity {
  date: string
  submissions: number
  newPasses: number
}

export interface PracticeStats {
  totalProblems: number
  passedProblems: number
  totalSubmissions: number
  acceptedSubmissions: number
  daily: DailyActivity[]
}

export type StatsPeriod = 'day' | 'week' | 'month'

export interface StatsBucket {
  key: string
  label: string
  newPasses: number
  submissions: number
  cumulativePassed: number
}
