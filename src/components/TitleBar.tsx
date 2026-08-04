import {
  windowClose,
  windowMinimize,
  windowToggleMaximize,
} from '../api'

export function TitleBar() {
  return (
    <header className="titlebar" data-tauri-drag-region data-fg-surface data-fg-chrome>
      <div className="titlebar-brand" data-tauri-drag-region>
        <img className="titlebar-logo" src="/icon.svg" alt="" aria-hidden />
        <div className="titlebar-title">SQL OJ</div>
      </div>
      <div className="titlebar-controls">
        <button
          type="button"
          className="titlebar-btn"
          aria-label="最小化"
          onClick={() => void windowMinimize()}
        >
          ─
        </button>
        <button
          type="button"
          className="titlebar-btn"
          aria-label="最大化"
          onClick={() => void windowToggleMaximize()}
        >
          □
        </button>
        <button
          type="button"
          className="titlebar-btn close"
          aria-label="关闭"
          onClick={() => void windowClose()}
        >
          ✕
        </button>
      </div>
    </header>
  )
}
