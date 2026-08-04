import type { BankStatus } from '../types'

export function formatBankLabel(status: BankStatus): string {
  if (!status.linked || !status.path) return '未链接'
  const title = status.name ?? '外部题库'
  if (status.problemCount > 0) {
    return `${title} · ${status.problemCount} 题`
  }
  return title
}
