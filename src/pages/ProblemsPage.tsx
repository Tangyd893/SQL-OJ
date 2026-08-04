import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getBankStatus, listProblems, reloadBank } from '../api'
import { BankImportPanel } from '../components/BankImportPanel'
import { ExpandableChipList } from '../components/ExpandableChipList'
import { EmptyState } from '../components/EmptyState'
import { SearchBox } from '../components/SearchBox'
import { VirtualProblemTable } from '../components/VirtualProblemTable'
import { buildProblemSearchTerms } from '../lib/searchSuggest'
import type { BankStatus, ProblemSummary } from '../types'
import {
  loadProblemsScrollTop,
  readFiltersFromSearch,
  saveProblemsScrollTop,
  useProblemListUrlSync,
} from '../lib/problemListUrl'
import {
  collectTags,
  countByDifficulty,
  countByTag,
  filterProblems,
  type DifficultyFilter,
  type StatusFilter,
} from '../lib/problemFilters'

function isTextInputFocused(): boolean {
  const el = document.activeElement
  return (
    el instanceof HTMLInputElement ||
    el instanceof HTMLTextAreaElement ||
    (el instanceof HTMLElement && el.isContentEditable)
  )
}

function needsBankSetup(
  bankStatus: BankStatus | null,
  problems: ProblemSummary[],
  listError: string | null,
): boolean {
  if (!bankStatus) return true
  if (!bankStatus.linked || !bankStatus.pathExists) return true
  if (problems.length > 0) return false
  if (bankStatus.problemCount === 0) return true
  if (listError) return true
  return Boolean(bankStatus.error)
}

export function ProblemsPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const pageRef = useRef<HTMLDivElement>(null)
  const [problems, setProblems] = useState<ProblemSummary[]>([])
  const [warnings, setWarnings] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [bankStatus, setBankStatus] = useState<BankStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [query, setQuery] = useState(
    () => readFiltersFromSearch(searchParams).query,
  )
  const [statusFilter, setStatusFilter] = useState<StatusFilter>(
    () => readFiltersFromSearch(searchParams).status,
  )
  const [difficultyFilter, setDifficultyFilter] = useState<DifficultyFilter>(
    () => readFiltersFromSearch(searchParams).difficulty,
  )
  const [tagFilter, setTagFilter] = useState<string | null>(
    () => readFiltersFromSearch(searchParams).tag,
  )
  const [selectedIndex, setSelectedIndex] = useState(0)
  const rowRefs = useRef<(HTMLTableRowElement | null)[]>([])

  const filters = useMemo(
    () => ({
      query,
      status: statusFilter,
      difficulty: difficultyFilter,
      tag: tagFilter,
    }),
    [query, statusFilter, difficultyFilter, tagFilter],
  )

  useProblemListUrlSync(filters)

  const applyList = (result: { problems: ProblemSummary[]; warnings: string[] }) => {
    setProblems(result.problems)
    setWarnings(result.warnings)
  }

  const refreshBankStatus = useCallback(async () => {
    setBankStatus(await getBankStatus())
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      applyList(await listProblems())
    } catch (e) {
      setError(String(e))
      setProblems([])
      setWarnings([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refreshBankStatus()
    void load()
    const onSettings = () => {
      void refreshBankStatus()
      void load()
    }
    window.addEventListener('sqloj:settings-changed', onSettings)
    return () => window.removeEventListener('sqloj:settings-changed', onSettings)
  }, [load, refreshBankStatus])

  useEffect(() => {
    if (loading) return
    const el = pageRef.current
    if (!el) return
    el.scrollTop = loadProblemsScrollTop()
  }, [loading])

  useEffect(() => {
    const el = pageRef.current
    if (!el) return
    const onScroll = () => saveProblemsScrollTop(el.scrollTop)
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [])

  const allTags = useMemo(() => collectTags(problems), [problems])
  const difficultyCounts = useMemo(() => countByDifficulty(problems), [problems])
  const searchTerms = useMemo(() => buildProblemSearchTerms(problems), [problems])

  const filtered = useMemo(
    () =>
      filterProblems(problems, {
        query,
        status: statusFilter,
        difficulty: difficultyFilter,
        tag: tagFilter,
      }),
    [problems, query, statusFilter, difficultyFilter, tagFilter],
  )

  useEffect(() => {
    setSelectedIndex(0)
  }, [filtered])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (filtered.length === 0 || isTextInputFocused()) return
      if (e.ctrlKey || e.metaKey || e.altKey) return

      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1))
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((i) => Math.max(i - 1, 0))
        return
      }
      if (e.key === 'Home') {
        e.preventDefault()
        setSelectedIndex(0)
        return
      }
      if (e.key === 'End') {
        e.preventDefault()
        setSelectedIndex(filtered.length - 1)
        return
      }
      if (e.key === 'Enter') {
        const p = filtered[selectedIndex]
        if (p) {
          e.preventDefault()
          navigate(`/problems/${p.id}`)
        }
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [filtered, selectedIndex, navigate])

  const onRefresh = async () => {
    setRefreshing(true)
    setError(null)
    try {
      applyList(await reloadBank())
      await refreshBankStatus()
    } catch (e) {
      setError(String(e))
    } finally {
      setRefreshing(false)
    }
  }

  const onBankLinked = () => {
    void refreshBankStatus()
    void load()
  }

  const toggleDifficulty = (d: DifficultyFilter) => {
    setDifficultyFilter((current) => (current === d ? 'all' : d))
  }

  const toggleTag = (tag: string) => {
    setTagFilter((current) => (current === tag ? null : tag))
  }

  const clearFilters = () => {
    setStatusFilter('all')
    setDifficultyFilter('all')
    setTagFilter(null)
    setQuery('')
  }

  const acceptedCount = problems.filter((p) => p.accepted).length
  const showBankSetup = !loading && needsBankSetup(bankStatus, problems, error)
  const bankReady = bankStatus?.linked && bankStatus.pathExists && bankStatus.problemCount > 0
  const hasActiveFilters =
    statusFilter !== 'all' ||
    difficultyFilter !== 'all' ||
    tagFilter !== null ||
    query.trim() !== ''

  return (
    <div className="page" ref={pageRef}>
      <div className="page-header">
        <div>
          <h1 className="page-title">题目列表</h1>
          {problems.length > 0 && (
            <div className="page-subtitle">
              已通过 {acceptedCount} / {problems.length}
              {filtered.length > 0 && ' · ↑↓ 选择 · Enter 打开'}
            </div>
          )}
        </div>
        <button
          type="button"
          className="btn"
          disabled={refreshing || !bankReady}
          onClick={() => void onRefresh()}
        >
          {refreshing ? '刷新中…' : '刷新题库'}
        </button>
      </div>

      {error && !showBankSetup && <div className="alert alert-error">{error}</div>}

      {warnings.length > 0 && !showBankSetup && (
        <div className="alert alert-warn">
          {warnings.length} 个题目加载失败：
          <ul className="warn-list">
            {warnings.slice(0, 5).map((w) => (
              <li key={w}>{w}</li>
            ))}
            {warnings.length > 5 && <li>…另有 {warnings.length - 5} 条</li>}
          </ul>
        </div>
      )}

      {loading ? (
        <EmptyState title="加载中…" />
      ) : showBankSetup ? (
        <div className="card bank-setup-card">
          <BankImportPanel variant="setup" onLinked={onBankLinked} />
        </div>
      ) : (
        <>
          {problems.length > 0 && (
            <>
              <div className="search-bar">
                <SearchBox terms={searchTerms} value={query} onChange={setQuery} placeholder="搜索编号、标题或标签…" />
              </div>

              <div className="filter-group">
                <span className="filter-group-label">状态</span>
                <div className="filter-chips">
                  {(
                    [
                      ['all', '全部'],
                      ['accepted', '已通过'],
                      ['pending', '未通过'],
                    ] as const
                  ).map(([key, label]) => (
                    <button
                      key={key}
                      type="button"
                      className={`theme-chip${statusFilter === key ? ' active' : ''}`}
                      onClick={() => setStatusFilter(key)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="filter-group">
                <span className="filter-group-label">难度</span>
                <div className="filter-chips">
                  {(
                    [
                      ['all', '全部', difficultyCounts.all],
                      ['easy', 'Easy', difficultyCounts.easy],
                      ['medium', 'Medium', difficultyCounts.medium],
                      ['hard', 'Hard', difficultyCounts.hard],
                    ] as const
                  ).map(([key, label, count]) => (
                    <button
                      key={key}
                      type="button"
                      className={`theme-chip${difficultyFilter === key ? ' active' : ''}`}
                      onClick={() => setDifficultyFilter(key)}
                    >
                      {label} ({count})
                    </button>
                  ))}
                </div>
              </div>

              {allTags.length > 0 && (
                <div className="filter-group">
                  <span className="filter-group-label">考点</span>
                  <div className="filter-tags-row">
                    <button
                      type="button"
                      className={`theme-chip tag-chip-all${tagFilter === null ? ' active' : ''}`}
                      onClick={() => setTagFilter(null)}
                    >
                      全部
                    </button>
                    <ExpandableChipList>
                      {allTags.map((tag) => (
                        <button
                          key={tag}
                          type="button"
                          className={`theme-chip tag-chip${tagFilter === tag ? ' active' : ''}`}
                          onClick={() => toggleTag(tag)}
                        >
                          {tag} ({countByTag(problems, tag)})
                        </button>
                      ))}
                    </ExpandableChipList>
                  </div>
                </div>
              )}

              {hasActiveFilters && filtered.length === 0 && (
                <EmptyState
                  title="没有匹配的题目"
                  action={{ label: '清除筛选', onClick: clearFilters }}
                />
              )}
            </>
          )}

          {problems.length === 0 ? (
            <EmptyState
              icon="📂"
              title="题库为空"
              hint="请检查外部题库目录，或在设置中重新关联题库。"
              action={{ label: '前往设置', to: '/settings?section=bank' }}
            />
          ) : filtered.length === 0 && hasActiveFilters ? null : filtered.length === 0 ? (
            <EmptyState title="没有匹配的题目" />
          ) : (
            <div className="card">
              <VirtualProblemTable
                problems={filtered}
                selectedIndex={selectedIndex}
                tagFilter={tagFilter}
                scrollRootRef={pageRef}
                rowRefs={rowRefs}
                onSelectIndex={setSelectedIndex}
                onNavigate={(pid) => navigate(`/problems/${pid}`)}
                onToggleDifficulty={toggleDifficulty}
                onToggleTag={toggleTag}
              />
            </div>
          )}
        </>
      )}
    </div>
  )
}
