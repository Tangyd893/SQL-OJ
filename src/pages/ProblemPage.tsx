import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import type { editor } from 'monaco-editor'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  cancelJudge,
  getProblem,
  getSubmissions,
  listProblems,
  previewSolution,
  submitSolution,
} from '../api'
import { ResultTable } from '../components/ResultTable'
import { EmptyState } from '../components/EmptyState'
import { ProblemNeighborList } from '../components/ProblemNeighborList'
import { useDisplaySettings } from '../hooks/useDisplaySettings'
import { useProblemSplit } from '../hooks/useProblemSplit'
import { loadDraft, saveDraft } from '../lib/drafts'
import { preferProblemList, setLastProblem } from '../lib/navigation'
import { getNextProblemId } from '../lib/problemNeighbors'
import {
  loadResult,
  loadTab,
  saveResult,
  saveTab,
  type ProblemTab,
} from '../lib/problemSession'
import { registerShortcutHandler } from '../lib/shortcutHandlers'
import {
  chordToMonacoKeybinding,
  formatChord,
  getShortcutChord,
} from '../lib/shortcuts'
import { registerMonacoThemes } from '../lib/monacoThemes'
import { useMonacoTheme } from '../lib/useMonacoTheme'
import type { CaseResult, JudgeResult, ProblemDetail, ProblemSummary, SubmissionRecord } from '../types'

const PROBLEM_TABS: ProblemTab[] = ['desc', 'solution', 'result', 'history']

export function ProblemPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const editorTheme = useMonacoTheme()
  const display = useDisplaySettings()
  const {
    splitRef,
    setLeftPaneNode,
    setToolbarNode,
    toolbarContentRef,
    leftPercent,
    toolbarHeight,
    dragging,
    onSplitPointerDown,
    onToolbarPointerDown,
    onResizerPointerMove,
    onResizerPointerUp,
  } = useProblemSplit()
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null)
  const editorActionsRef = useRef<{ dispose: () => void }[]>([])
  const [problem, setProblem] = useState<ProblemDetail | null>(null)
  const [sql, setSql] = useState('SELECT ')
  const [tab, setTab] = useState<ProblemTab>('desc')
  const [result, setResult] = useState<JudgeResult | null>(null)
  const [history, setHistory] = useState<SubmissionRecord[]>([])
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  const [allProblems, setAllProblems] = useState<ProblemSummary[]>([])
  const busy = submitting || previewing

  const refreshProblemList = useCallback(async () => {
    try {
      const { problems } = await listProblems()
      setAllProblems(problems)
    } catch {
      setAllProblems([])
    }
  }, [])

  const loadHistory = useCallback(async () => {
    if (!id) return
    try {
      const records = await getSubmissions(id)
      setHistory(records)
    } catch {
      setHistory([])
    }
  }, [id])

  useEffect(() => {
    void refreshProblemList()
  }, [refreshProblemList])

  useEffect(() => {
    void getProblem(id)
      .then(setProblem)
      .catch((e) => setError(String(e)))
    void loadHistory()
  }, [id, loadHistory])

  useEffect(() => {
    if (id) setLastProblem(id)
  }, [id])

  useEffect(() => {
    setSql(loadDraft(id) ?? 'SELECT ')
    setResult(loadResult<JudgeResult>(id))
    setTab(loadTab(id) ?? 'desc')
    setError(null)
  }, [id])

  useEffect(() => {
    if (id) saveDraft(id, sql)
  }, [id, sql])

  useEffect(() => {
    if (id) saveTab(id, tab)
  }, [id, tab])

  useEffect(() => {
    if (id && result) saveResult(id, result)
  }, [id, result])

  useEffect(() => {
    editorRef.current?.updateOptions({ fontSize: display.editorFontSize })
  }, [display.editorFontSize])

  const applyJudge = useCallback(
    (judge: JudgeResult, preview: boolean) => {
      setResult(judge)
      if (judge.message === '已取消') {
        setError('判题已取消')
        return
      }
      setTab('result')
      if (!preview) {
        void loadHistory()
        void refreshProblemList()
      }
    },
    [loadHistory, refreshProblemList],
  )

  const onSubmit = useCallback(async () => {
    if (!sql.trim()) {
      setError('SQL 不能为空')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      applyJudge(await submitSolution(id, sql), false)
    } catch (e) {
      setError(String(e))
    } finally {
      setSubmitting(false)
    }
  }, [id, sql, applyJudge])

  const onPreview = useCallback(async () => {
    if (!sql.trim()) {
      setError('SQL 不能为空')
      return
    }
    setPreviewing(true)
    setError(null)
    try {
      applyJudge(await previewSolution(id, sql), true)
    } catch (e) {
      setError(String(e))
    } finally {
      setPreviewing(false)
    }
  }, [id, sql, applyJudge])

  const syncEditorShortcutActions = useCallback(
    (ed: editor.IStandaloneCodeEditor) => {
      editorActionsRef.current.forEach((d) => d.dispose())
      editorActionsRef.current = []

      const submitBinding = chordToMonacoKeybinding(getShortcutChord('submit'))
      const previewBinding = chordToMonacoKeybinding(getShortcutChord('preview'))

      if (submitBinding) {
        const d = ed.addAction({
          id: 'submit-solution',
          label: '提交判题',
          keybindings: [submitBinding],
          run: () => {
            if (!busy) void onSubmit()
          },
        })
        if (d) editorActionsRef.current.push(d)
      }

      if (previewBinding) {
        const d = ed.addAction({
          id: 'preview-solution',
          label: '试运行',
          keybindings: [previewBinding],
          run: () => {
            if (!busy) void onPreview()
          },
        })
        if (d) editorActionsRef.current.push(d)
      }
    },
    [busy, onPreview, onSubmit],
  )

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return
      const idx = Number(e.key) - 1
      if (idx >= 0 && idx < PROBLEM_TABS.length && e.key >= '1' && e.key <= '9') {
        e.preventDefault()
        setTab(PROBLEM_TABS[idx]!)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    registerShortcutHandler('submit', () => {
      if (!busy) void onSubmit()
    })
    registerShortcutHandler('preview', () => {
      if (!busy) void onPreview()
    })
    return () => {
      registerShortcutHandler('submit', null)
      registerShortcutHandler('preview', null)
    }
  }, [onSubmit, onPreview, busy])

  useEffect(() => {
    const onShortcutsChanged = () => {
      if (editorRef.current) syncEditorShortcutActions(editorRef.current)
    }
    window.addEventListener('sqloj:shortcuts-changed', onShortcutsChanged)
    return () =>
      window.removeEventListener('sqloj:shortcuts-changed', onShortcutsChanged)
  }, [syncEditorShortcutActions])

  const submitHint = formatChord(getShortcutChord('submit'))
  const previewHint = formatChord(getShortcutChord('preview'))
  const nextProblemId = getNextProblemId(allProblems, id)

  const onNextProblem = () => {
    if (!nextProblemId) return
    setLastProblem(nextProblemId)
    navigate(`/problems/${nextProblemId}`)
  }

  const onEditorMount = (ed: editor.IStandaloneCodeEditor) => {
    editorRef.current = ed
    ed.updateOptions({ fontSize: display.editorFontSize })
    syncEditorShortcutActions(ed)
  }

  if (error && !problem) {
    return (
      <div className="page">
        <div className="alert alert-error">{error}</div>
        <Link to="/problems">返回列表</Link>
      </div>
    )
  }

  if (!problem) {
    return (
      <div className="page">
        <EmptyState title="加载题目…" />
      </div>
    )
  }

  return (
    <div className="problem-layout">
      <header className="problem-toolbar" ref={setToolbarNode}>
        <div className="problem-toolbar-content" ref={toolbarContentRef}>
          <div className="problem-toolbar-main">
            <Link
              to="/problems"
              className="problem-back"
              onClick={() => preferProblemList()}
            >
              ← 题目列表
            </Link>
            <h1 className="problem-title">
              {problem.id} · {problem.title}
            </h1>
            <div className="problem-meta">
              {problem.caseCount} 个测试点 · {submitHint} 提交 · {previewHint} 试运行 · Alt+1~4
              切换侧栏
            </div>
          </div>
          <div className="problem-toolbar-actions">
            <ProblemNeighborList problems={allProblems} currentId={id} />
            <button
              type="button"
              className="btn"
              disabled={!nextProblemId || busy}
              title={nextProblemId ? undefined : '已是最后一题'}
              onClick={onNextProblem}
            >
              下一题
            </button>
            {busy && (
              <button type="button" className="btn" onClick={() => void cancelJudge()}>
                取消
              </button>
            )}
            <button type="button" className="btn" disabled={busy} onClick={() => void onPreview()}>
              {previewing ? '试运行中…' : '试运行'}
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={busy}
              onClick={() => void onSubmit()}
            >
              {submitting ? '判题中…' : '提交'}
            </button>
          </div>
        </div>
      </header>

      <div
        className={`problem-toolbar-resizer${dragging === 'toolbar' ? ' dragging' : ''}`}
        role="separator"
        aria-orientation="horizontal"
        aria-label="调整顶部工具栏高度"
        aria-valuenow={toolbarHeight}
        onPointerDown={onToolbarPointerDown}
        onPointerMove={onResizerPointerMove}
        onPointerUp={onResizerPointerUp}
        onPointerCancel={onResizerPointerUp}
      />

      {error && <div className="alert alert-error problem-alert">{error}</div>}

      <div className="problem-split" ref={splitRef}>
        <aside
          className="problem-pane-left"
          ref={setLeftPaneNode}
          style={{ width: `${leftPercent}%` }}
        >
          <div className="tabs">
              {(
              [
                ['desc', '题目描述'],
                ['solution', '题解'],
                ['result', '判题结果'],
                ['history', `历史 (${history.length})`],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                className={`tab${tab === key ? ' active' : ''}`}
                onClick={() => setTab(key)}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="problem-pane-scroll">
            <div className={`tab-panel${tab === 'desc' ? '' : ' hidden'}`}>
              <div className="markdown-body">
                {problem.description ? (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {problem.description}
                  </ReactMarkdown>
                ) : (
                  '（无描述）'
                )}
              </div>
              {problem.expectedColumns.length > 0 && (
                <div className="expected-result-block">
                  <ResultTable
                    title="预期结果"
                    columns={problem.expectedColumns}
                    rows={problem.expectedRows}
                  />
                </div>
              )}
            </div>
            <div className={`tab-panel${tab === 'solution' ? '' : ' hidden'}`}>
              {problem.solutionExplanation?.trim() && (
                <div className="markdown-body solution-explanation">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {problem.solutionExplanation}
                  </ReactMarkdown>
                </div>
              )}
              {problem.solutionSql?.trim() ? (
                <>
                  <div className="solution-toolbar">
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={() => setSql(problem.solutionSql!.trim())}
                    >
                      填入编辑器
                    </button>
                  </div>
                  <pre className="markdown-body solution-sql">{problem.solutionSql}</pre>
                </>
              ) : !problem.solutionExplanation?.trim() ? (
                <EmptyState title="本题暂无题解" hint="可参考题目描述自行练习。" />
              ) : null}
            </div>
            <div className={`tab-panel${tab === 'result' ? '' : ' hidden'}`}>
              {!result ? (
                <EmptyState title="尚无判题结果" hint="提交或试运行后将在此显示。" />
              ) : (
                <>
                  <div
                    className={`result-banner ${result.accepted ? 'accepted' : 'rejected'}`}
                  >
                    {result.message} · {result.durationMs} ms
                  </div>
                  <div className="case-list">
                    {result.cases.map((c) => (
                      <CaseResultView key={c.caseId} c={c} />
                    ))}
                  </div>
                </>
              )}
            </div>
            <div className={`tab-panel${tab === 'history' ? '' : ' hidden'}`}>
              {history.length === 0 ? (
                <EmptyState title="暂无提交记录" />
              ) : (
                <div className="history-list">
                  {history.map((h) => (
                    <div key={h.id} className={`history-item ${h.accepted ? 'pass' : 'fail'}`}>
                      <div className="history-meta">
                        <span>{h.accepted ? 'AC' : 'WA'}</span>
                        <span>{h.message}</span>
                        <span>{new Date(h.createdAt).toLocaleString()}</span>
                      </div>
                      <pre className="history-sql">{h.sql}</pre>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </aside>

        <div
          className={`problem-split-resizer${dragging === 'split' ? ' dragging' : ''}`}
          role="separator"
          aria-orientation="vertical"
          aria-label="调整题目描述与编辑器宽度"
          aria-valuenow={Math.round(leftPercent)}
          aria-valuemin={20}
          aria-valuemax={70}
          onPointerDown={onSplitPointerDown}
          onPointerMove={onResizerPointerMove}
          onPointerUp={onResizerPointerUp}
          onPointerCancel={onResizerPointerUp}
        />

        <section className="problem-pane-right">
          <Editor
            height="100%"
            defaultLanguage="sql"
            value={sql}
            onChange={(v) => setSql(v ?? '')}
            onMount={onEditorMount}
            beforeMount={registerMonacoThemes}
            theme={editorTheme}
            options={{
              minimap: { enabled: false },
              fontSize: display.editorFontSize,
              scrollBeyondLastLine: false,
              automaticLayout: true,
            }}
          />
        </section>
      </div>
    </div>
  )
}

function CaseResultView({ c }: { c: CaseResult }) {
  const hasExpected = c.expectedColumns != null && c.expectedRows != null
  const hasActual = c.actualColumns != null && c.actualRows != null

  return (
    <div className={`case-item ${c.passed ? 'pass' : 'fail'}`}>
      <div>
        测试点 {c.caseId}: {c.message}
      </div>
      {(hasExpected || hasActual) && (
        <div className="case-diff">
          {hasExpected && (
            <ResultTable
              title="期望结果"
              columns={c.expectedColumns!}
              rows={c.expectedRows!}
            />
          )}
          {hasActual && (
            <ResultTable
              title="你的结果"
              columns={c.actualColumns!}
              rows={c.actualRows!}
            />
          )}
        </div>
      )}
    </div>
  )
}
