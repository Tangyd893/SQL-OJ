import type { ShortcutId } from './shortcuts'

type Handler = () => void

const handlers: Partial<Record<ShortcutId, Handler>> = {}

export function registerShortcutHandler(id: ShortcutId, handler: Handler | null): void {
  if (handler) {
    handlers[id] = handler
  } else {
    delete handlers[id]
  }
}

export function invokeShortcut(id: ShortcutId): boolean {
  const handler = handlers[id]
  if (!handler) return false
  handler()
  return true
}
