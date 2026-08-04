import type { DailyActivity, StatsBucket, StatsPeriod } from '../types'

function parseDate(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

function formatDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function isoWeekKey(d: Date): string {
  const copy = new Date(d.getTime())
  copy.setHours(0, 0, 0, 0)
  copy.setDate(copy.getDate() + 3 - ((copy.getDay() + 6) % 7))
  const week1 = new Date(copy.getFullYear(), 0, 4)
  const week =
    1 +
    Math.round(
      ((copy.getTime() - week1.getTime()) / 86400000 -
        3 +
        ((week1.getDay() + 6) % 7)) /
        7,
    )
  return `${copy.getFullYear()}-W${String(week).padStart(2, '0')}`
}

function monthKey(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function bucketLabel(key: string, period: StatsPeriod): string {
  if (period === 'month') {
    const [y, m] = key.split('-')
    return `${y}年${Number(m)}月`
  }
  if (period === 'week') {
    const [y, w] = key.split('-W')
    return `${y} 第${Number(w)}周`
  }
  const d = parseDate(key)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function fillDailyRange(daily: DailyActivity[], count: number): DailyActivity[] {
  const map = new Map(daily.map((d) => [d.date, d]))
  const end = new Date()
  end.setHours(0, 0, 0, 0)
  const out: DailyActivity[] = []
  for (let i = count - 1; i >= 0; i--) {
    const d = new Date(end)
    d.setDate(d.getDate() - i)
    const key = formatDate(d)
    const row = map.get(key)
    out.push(
      row ?? { date: key, submissions: 0, newPasses: 0 },
    )
  }
  return out
}

export function buildBuckets(
  daily: DailyActivity[],
  period: StatsPeriod,
  passedTotal: number,
): StatsBucket[] {
  const rangeDays = period === 'day' ? 30 : period === 'week' ? 84 : 365
  const filled = fillDailyRange(daily, rangeDays)

  const grouped = new Map<string, { newPasses: number; submissions: number }>()
  for (const row of filled) {
    const d = parseDate(row.date)
    const key =
      period === 'day'
        ? row.date
        : period === 'week'
          ? isoWeekKey(d)
          : monthKey(d)
    const prev = grouped.get(key) ?? { newPasses: 0, submissions: 0 }
    grouped.set(key, {
      newPasses: prev.newPasses + row.newPasses,
      submissions: prev.submissions + row.submissions,
    })
  }

  const keys = [...grouped.keys()].sort()
  let cumulativeBefore = passedTotal
  for (const row of filled) {
    cumulativeBefore -= row.newPasses
  }
  cumulativeBefore = Math.max(0, cumulativeBefore)

  let running = cumulativeBefore
  return keys.map((key) => {
    const g = grouped.get(key)!
    running += g.newPasses
    return {
      key,
      label: bucketLabel(key, period),
      newPasses: g.newPasses,
      submissions: g.submissions,
      cumulativePassed: running,
    }
  })
}

export function periodSummary(
  buckets: StatsBucket[],
  totalProblems: number,
): { newPasses: number; submissions: number; passed: number; total: number } {
  const newPasses = buckets.reduce((s, b) => s + b.newPasses, 0)
  const submissions = buckets.reduce((s, b) => s + b.submissions, 0)
  const passed = buckets.length ? buckets[buckets.length - 1].cumulativePassed : 0
  return { newPasses, submissions, passed, total: totalProblems }
}

export function heatmapCells(daily: DailyActivity[], weeks = 26): DailyActivity[] {
  return fillDailyRange(daily, weeks * 7)
}
