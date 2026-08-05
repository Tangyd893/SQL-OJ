# Problem Layout & Icons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pin 考点「全部」to first row; add resizable problem toolbar height; make L/R split drag follow the pointer; sync Tauri bundle icons with `public/icon.svg`.

**Architecture:** Extend `layoutPrefs` + rewrite `useProblemSplit` for DOM-only drag with pointer capture; add toolbar bottom resizer; CSS flex-start for filter chips; regenerate `src-tauri/icons` via `tauri icon`.

**Tech Stack:** React 18, TypeScript, Vite, Tauri 2, CSS.

## Global Constraints

- Keep left-right problem split (no vertical stack layout).
- Persist via `sql-oj.layout` / `layoutPrefs.ts`.
- Split range 20–70%, default 40%; toolbar height max `min(280px, 40vh)`.
- Icon source of truth: `public/icon.svg`.

---

### Task 1: Pin 考点「全部」

**Files:** `src/styles/global.css`

- [ ] Change `.filter-tags-row` and `.expandable-chips` from `align-items: flex-end` to `flex-start`.

### Task 2: Layout prefs

**Files:** `src/lib/layoutPrefs.ts`

- [ ] `SPLIT_MIN=20`, `SPLIT_MAX=70`.
- [ ] Add `problemToolbarHeight: number` (0 = natural content height).
- [ ] Load/save/clamp helpers for toolbar height.

### Task 3: Pointer-drag split + toolbar height

**Files:** `src/hooks/useProblemSplit.ts`, `src/pages/ProblemPage.tsx`, `src/styles/global.css`

- [ ] DOM-only drag during move; commit on pointerup.
- [ ] `setPointerCapture` + body drag classes; editor `pointer-events: none` while dragging.
- [ ] Toolbar bottom resizer; measure content min height; clamp max.
- [ ] Wire refs/handlers in `ProblemPage`.

### Task 4: Icons

**Files:** `scripts/generate-icon.ps1`, `src-tauri/icons/*`

- [ ] Regenerate icons from `public/icon.svg` via `tauri icon`.
- [ ] Update generate script to call that flow.
- [ ] Commit icon assets referenced by `tauri.conf.json`.
