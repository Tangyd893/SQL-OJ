import { NavLink, useLocation } from 'react-router-dom'
import { useCallback, useEffect, useState } from 'react'
import {
  getProblemsNavPath,
  isProblemsNavActive,
} from '../lib/navigation'
import {
  loadLayoutPrefs,
  saveLayoutPrefs,
  type LayoutPrefs,
} from '../lib/layoutPrefs'
import { useSidebarResize } from '../hooks/useSidebarResize'

function IconProblems() {
  return (
    <svg className="sidebar-icon" viewBox="0 0 24 24" aria-hidden>
      <path
        fill="currentColor"
        d="M4 6h16v2H4V6zm0 5h16v2H4v-2zm0 5h10v2H4v-2z"
      />
    </svg>
  )
}

function IconStats() {
  return (
    <svg className="sidebar-icon" viewBox="0 0 24 24" aria-hidden>
      <path
        fill="currentColor"
        d="M5 19V9h3v10H5zm5.5 0V5h3v14h-3zM16 19v-7h3v7h-3z"
      />
    </svg>
  )
}

function IconSettings() {
  return (
    <svg className="sidebar-icon" viewBox="0 0 24 24" aria-hidden>
      <path
        fill="currentColor"
        d="M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8zm8.94 5a7.96 7.96 0 0 1 .06.87 7.96 7.96 0 0 1-.06.87l2.03 1.58a.5.5 0 0 1 .12.64l-1.92 3.32a.5.5 0 0 1-.6.22l-2.39-.96a7.2 7.2 0 0 1-1.5.87l-.36 2.54a.5.5 0 0 1-.5.43h-3.84a.5.5 0 0 1-.5-.43l-.36-2.54a7.2 7.2 0 0 1-1.5-.87l-2.39.96a.5.5 0 0 1-.6-.22L2.85 17a.5.5 0 0 1 .12-.64l2.03-1.58A7.96 7.96 0 0 1 4.94 13c0-.29.02-.58.06-.87L2.97 10.5a.5.5 0 0 1-.12-.64l1.92-3.32a.5.5 0 0 1 .6-.22l2.39.96c.46-.35.96-.65 1.5-.87l.36-2.54a.5.5 0 0 1 .5-.43h3.84a.5.5 0 0 1 .5.43l.36 2.54c.54.22 1.04.52 1.5.87l2.39-.96a.5.5 0 0 1 .6.22l1.92 3.32a.5.5 0 0 1-.12.64l-2.03 1.58c.04.29.06.58.06.87z"
      />
    </svg>
  )
}

function IconExpand() {
  return (
    <svg className="sidebar-icon" viewBox="0 0 24 24" aria-hidden>
      <path fill="currentColor" d="M3 6h18v2H3V6zm0 5h18v2H3v-2zm0 5h18v2H3v-2z" />
    </svg>
  )
}

function IconCollapse() {
  return (
    <svg className="sidebar-icon" viewBox="0 0 24 24" aria-hidden>
      <path fill="currentColor" d="M11 4h2v16h-2V4zM4 4h5v16H4V4zm11 0h5v16h-5V4z" />
    </svg>
  )
}

const NAV_ITEMS = [
  { kind: 'problems' as const, label: '题目列表', icon: IconProblems },
  { to: '/stats', label: '练习统计', icon: IconStats },
  { to: '/settings', label: '设置', icon: IconSettings },
]

export function Sidebar() {
  const location = useLocation()
  const [prefs, setPrefs] = useState<LayoutPrefs>(() => loadLayoutPrefs())
  const [problemsPath, setProblemsPath] = useState(getProblemsNavPath)
  const { effectiveWidth, dragging, onResizeStart } = useSidebarResize(
    prefs.sidebarCollapsed,
  )

  useEffect(() => {
    const sync = () => setPrefs(loadLayoutPrefs())
    window.addEventListener('sqloj:layout-changed', sync)
    return () => window.removeEventListener('sqloj:layout-changed', sync)
  }, [])

  useEffect(() => {
    setProblemsPath(getProblemsNavPath())
  }, [location.pathname])

  const toggleCollapsed = useCallback(() => {
    const next = { ...loadLayoutPrefs(), sidebarCollapsed: !prefs.sidebarCollapsed }
    saveLayoutPrefs(next)
    setPrefs(next)
  }, [prefs.sidebarCollapsed])

  const linkClass = (active: boolean) =>
    `sidebar-link${active ? ' active' : ''}${prefs.sidebarCollapsed ? ' collapsed' : ''}`

  return (
    <>
      <nav
        className={`sidebar${prefs.sidebarCollapsed ? ' is-collapsed' : ''}`}
        style={{ width: effectiveWidth }}
        data-fg-surface
        data-fg-chrome
      >
        <button
          type="button"
          className={`sidebar-toggle${prefs.sidebarCollapsed ? ' collapsed' : ''}`}
          onClick={toggleCollapsed}
          title={prefs.sidebarCollapsed ? '展开侧栏' : '收起侧栏'}
          aria-label={prefs.sidebarCollapsed ? '展开侧栏' : '收起侧栏'}
        >
          {prefs.sidebarCollapsed ? <IconExpand /> : <IconCollapse />}
          {!prefs.sidebarCollapsed && <span>收起侧栏</span>}
        </button>

        {NAV_ITEMS.map((item) => {
          if (item.kind === 'problems') {
            const active = isProblemsNavActive(location.pathname)
            return (
              <NavLink
                key="problems"
                to={problemsPath}
                className={linkClass(active)}
                title="题目列表"
                onClick={() => setProblemsPath(getProblemsNavPath())}
              >
                <item.icon />
                {!prefs.sidebarCollapsed && <span>{item.label}</span>}
              </NavLink>
            )
          }
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => linkClass(isActive)}
              title={item.label}
            >
              <item.icon />
              {!prefs.sidebarCollapsed && <span>{item.label}</span>}
            </NavLink>
          )
        })}
      </nav>
      {!prefs.sidebarCollapsed && (
        <div
          className={`sidebar-resizer${dragging ? ' dragging' : ''}`}
          role="separator"
          aria-orientation="vertical"
          onMouseDown={onResizeStart}
        />
      )}
    </>
  )
}
