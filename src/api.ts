import { invoke } from '@tauri-apps/api/core'
import type {
  AppSettings,
  BankInspectResult,
  BankStatus,
  JudgeResult,
  ListProblemsResult,
  PracticeStats,
  ProblemDetail,
  SubmissionRecord,
} from './types'

export async function getSettings(): Promise<AppSettings> {
  return invoke('get_settings')
}

export async function setProblemBankPath(path: string): Promise<void> {
  return invoke('set_problem_bank_path', { path })
}

export async function pickProblemBankFolder(): Promise<string | null> {
  return invoke('pick_problem_bank_folder')
}

export async function inspectProblemBank(path: string): Promise<BankInspectResult> {
  return invoke('inspect_problem_bank', { path })
}

export async function getBankStatus(): Promise<BankStatus> {
  return invoke('get_bank_status')
}

export async function listProblems(): Promise<ListProblemsResult> {
  return invoke('list_problems')
}

export async function getProblem(id: string): Promise<ProblemDetail> {
  return invoke('get_problem', { id })
}

export async function submitSolution(
  problemId: string,
  sql: string,
): Promise<JudgeResult> {
  return invoke('submit_solution', { problemId, sql })
}

export async function previewSolution(
  problemId: string,
  sql: string,
): Promise<JudgeResult> {
  return invoke('preview_solution', { problemId, sql })
}

export async function cancelJudge(): Promise<void> {
  return invoke('cancel_judge')
}

export async function getSubmissions(
  problemId?: string,
): Promise<SubmissionRecord[]> {
  return invoke('get_submissions', { problemId: problemId ?? null })
}

export async function getPracticeStats(): Promise<PracticeStats> {
  return invoke('get_practice_stats')
}

export async function reloadBank(): Promise<ListProblemsResult> {
  return invoke('reload_bank')
}

export async function windowMinimize(): Promise<void> {
  return invoke('window_minimize')
}

export async function windowToggleMaximize(): Promise<void> {
  return invoke('window_toggle_maximize')
}

export async function windowClose(): Promise<void> {
  return invoke('window_close')
}
