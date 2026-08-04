import { Link } from 'react-router-dom'
import type { ReactNode } from 'react'

export function EmptyState({
  icon,
  title,
  hint,
  action,
}: {
  icon?: ReactNode
  title: string
  hint?: string
  action?: { label: string; to?: string; onClick?: () => void }
}) {
  return (
    <div className="empty-state">
      {icon && <div className="empty-state-icon">{icon}</div>}
      <div className="empty-state-title">{title}</div>
      {hint && <p className="empty-state-hint">{hint}</p>}
      {action &&
        (action.to ? (
          <Link to={action.to} className="btn btn-sm empty-state-action">
            {action.label}
          </Link>
        ) : (
          <button
            type="button"
            className="btn btn-sm empty-state-action"
            onClick={action.onClick}
          >
            {action.label}
          </button>
        ))}
    </div>
  )
}
