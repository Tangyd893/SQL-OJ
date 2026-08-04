import { useCallback, useEffect, useMemo, useState } from 'react'
import { getPracticeStats } from '../api'
import { EmptyState } from '../components/EmptyState'
import {
  buildBuckets,
  heatmapCells,
  periodSummary,
} from '../lib/statsBuckets'
import type { PracticeStats, StatsPeriod } from '../types'

const PERIODS: { key: StatsPeriod; label: string }[] = [
  { key: 'day', label: '日' },
  { key: 'week', label: '周' },
  { key: 'month', label: '月' },
]

function pct(n: number, total: number): string {
  if (total <= 0) return '0%'
  return `${Math.round((n / total) * 1000) / 10}%`
}

function ProgressRing({ value, total }: { value: number; total: number }) {
  const ratio = total > 0 ? Math.min(value / total, 1) : 0
  const r = 42
  const c = 2 * Math.PI * r
  const offset = c * (1 - ratio)
  return (
    <div className="stats-ring" aria-hidden>
      <svg viewBox="0 0 100 100">
        <circle className="stats-ring-track" cx="50" cy="50" r={r} />
        <circle
          className="stats-ring-fill"
          cx="50"
          cy="50"
          r={r}
          strokeDasharray={c}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="stats-ring-label">
        <strong>{value}</strong>
        <span>/ {total}</span>
      </div>
    </div>
  )
}

function BarChart({
  buckets,
  totalProblems,
}: {
  buckets: ReturnType<typeof buildBuckets>
  totalProblems: number
}) {
  const maxPasses = Math.max(1, ...buckets.map((b) => b.newPasses))
  return (
    <div className="stats-chart">
      <div className="stats-chart-bars">
        {buckets.map((b) => (
          <div key={b.key} className="stats-bar-col" title={`${b.label}: 新通过 ${b.newPasses}`}>
            <div className="stats-bar-stack">
              <div
                className="stats-bar stats-bar-passes"
                style={{ height: `${(b.newPasses / maxPasses) * 100}%` }}
              />
            </div>
            <span className="stats-bar-label">{b.label}</span>
            <span className="stats-bar-ratio">
              {b.cumulativePassed}/{totalProblems}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ActivityHeatmap({ daily }: { daily: ReturnType<typeof heatmapCells> }) {
  const max = Math.max(1, ...daily.map((d) => d.submissions + d.newPasses * 2))
  const level = (d: (typeof daily)[0]) => {
    const score = d.submissions + d.newPasses * 2
    if (score <= 0) return 0
    if (score >= max * 0.75) return 4
    if (score >= max * 0.5) return 3
    if (score >= max * 0.25) return 2
    return 1
  }
  const weeks: (typeof daily)[] = []
  for (let i = 0; i < daily.length; i += 7) {
    weeks.push(daily.slice(i, i + 7))
  }
  return (
    <div className="stats-heatmap">
      {weeks.map((week, wi) => (
        <div key={wi} className="stats-heatmap-week">
          {week.map((d) => (
            <div
              key={d.date}
              className={`stats-heatmap-cell lv-${level(d)}`}
              title={`${d.date}\n提交 ${d.submissions} · 新通过 ${d.newPasses}`}
            />
          ))}
        </div>
      ))}
    </div>
  )
}

export function StatsPage() {
  const [stats, setStats] = useState<PracticeStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [period, setPeriod] = useState<StatsPeriod>('day')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setStats(await getPracticeStats())
    } catch (e) {
      setError(String(e))
      setStats(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
    const onSettings = () => void load()
    window.addEventListener('sqloj:settings-changed', onSettings)
    return () => window.removeEventListener('sqloj:settings-changed', onSettings)
  }, [load])

  const buckets = useMemo(
    () =>
      stats
        ? buildBuckets(stats.daily, period, stats.passedProblems)
        : [],
    [stats, period],
  )

  const summary = useMemo(
    () =>
      stats
        ? periodSummary(buckets, stats.totalProblems)
        : { newPasses: 0, submissions: 0, passed: 0, total: 0 },
    [stats, buckets],
  )

  const heatmap = useMemo(
    () => (stats ? heatmapCells(stats.daily) : []),
    [stats],
  )

  return (
    <div className="page stats-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">练习统计</h1>
          <div className="page-subtitle">通过进度与练习活跃度</div>
        </div>
        <button type="button" className="btn" onClick={() => void load()}>
          刷新
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <EmptyState title="加载中…" />
      ) : !stats ? (
        <EmptyState title="暂无统计数据" />
      ) : stats.totalProblems === 0 ? (
        <EmptyState
          icon="📊"
          title="尚未加载题库"
          hint="请先在设置中关联题库目录。"
          action={{ label: '去设置', to: '/settings' }}
        />
      ) : (
        <>
          <div className="stats-overview">
            <div className="stats-overview-ring card">
              <ProgressRing
                value={stats.passedProblems}
                total={stats.totalProblems}
              />
              <div className="stats-overview-caption">
                <div className="stats-overview-title">已通过</div>
                <div className="stats-overview-pct">
                  {pct(stats.passedProblems, stats.totalProblems)}
                </div>
              </div>
            </div>
            <div className="stats-kpi-grid">
              <div className="stats-kpi card">
                <span className="stats-kpi-value">{stats.passedProblems}</span>
                <span className="stats-kpi-label">累计通过</span>
              </div>
              <div className="stats-kpi card">
                <span className="stats-kpi-value">{stats.totalProblems}</span>
                <span className="stats-kpi-label">题库总数</span>
              </div>
              <div className="stats-kpi card">
                <span className="stats-kpi-value">{stats.totalSubmissions}</span>
                <span className="stats-kpi-label">总提交</span>
              </div>
              <div className="stats-kpi card">
                <span className="stats-kpi-value">
                  {stats.totalSubmissions > 0
                    ? pct(stats.acceptedSubmissions, stats.totalSubmissions)
                    : '—'}
                </span>
                <span className="stats-kpi-label">提交通过率</span>
              </div>
            </div>
          </div>

          <div className="card stats-panel">
            <div className="stats-panel-head">
              <div>
                <h2 className="stats-panel-title">练习趋势</h2>
                <p className="stats-panel-desc">
                  本{period === 'day' ? '月' : period === 'week' ? '季' : '年'}新通过{' '}
                  <strong>{summary.newPasses}</strong> 题 · 提交{' '}
                  <strong>{summary.submissions}</strong> 次 · 进度{' '}
                  <strong>
                    {summary.passed}/{summary.total}
                  </strong>
                </p>
              </div>
              <div className="filter-chips">
                {PERIODS.map(({ key, label }) => (
                  <button
                    key={key}
                    type="button"
                    className={`theme-chip${period === key ? ' active' : ''}`}
                    onClick={() => setPeriod(key)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            {buckets.length === 0 ? (
              <EmptyState
                title="该时段暂无练习记录"
                hint="提交题目后，统计会出现在这里。"
              />
            ) : (
              <BarChart buckets={buckets} totalProblems={stats.totalProblems} />
            )}
          </div>

          <div className="card stats-panel">
            <div className="stats-panel-head">
              <div>
                <h2 className="stats-panel-title">活跃日历</h2>
                <p className="stats-panel-desc">近 26 周提交与通过热力图</p>
              </div>
            </div>
            <ActivityHeatmap daily={heatmap} />
            <div className="stats-heatmap-legend">
              <span>少</span>
              <span className="stats-heatmap-cell lv-0" />
              <span className="stats-heatmap-cell lv-1" />
              <span className="stats-heatmap-cell lv-2" />
              <span className="stats-heatmap-cell lv-3" />
              <span className="stats-heatmap-cell lv-4" />
              <span>多</span>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
