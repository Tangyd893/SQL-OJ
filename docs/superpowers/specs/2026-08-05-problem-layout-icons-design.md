# 做题页布局、考点筛选钉位与应用图标

日期：2026-08-05

## 目标

1. 题目列表「考点」筛选中，「全部」按钮在列表展开时始终保持在首行第一位，不随展开下移。
2. 做题页保持左右分栏；工具栏底部可竖向拖拽拉高/压矮，以便把编辑器首行下移到更舒适的平视高度；左右宽度比例可调，且拖拽跟手。
3. exe / 任务栏 / 窗口图标与应用内新图标（`public/icon.svg`）一致。

## 非目标

- 不改为上下分栏布局。
- 不改考点筛选语义（「全部」仍为清除筛选，非多选全选）。
- 不在本次自动替用户完成安装包分发；图标生效依赖重新打包/安装。

## 1. 考点「全部」钉位

### 现状

`.filter-tags-row` 与 `.expandable-chips` 使用 `align-items: flex-end`。展开增高时，「全部」在交叉轴贴底，视觉上随列表下沉。

### 方案

- `.filter-tags-row`、`.expandable-chips`：`align-items: flex-start`。
- 「全部」保持为 `.filter-tags-row` 的第一个子元素，并保留 `flex-shrink: 0`。
- 展开/收起逻辑与 `ExpandableChipList` 行为不变。

## 2. 做题页布局

### 结构

```
problem-toolbar              # 内容顶对齐；可通过 min-height 拉高
  toolbar 内容…
problem-toolbar-resizer      # 新增横条，cursor: row-resize
problem-alert?               # 不变
problem-split
  左：题目描述 (width %)
  竖向 resizer
  右：编辑器
```

### 高度（工具栏）

| 项 | 值 |
|---|---|
| 偏好字段 | `problemToolbarHeight`（px） |
| 默认 | 内容自然高度（不强制加高；可用 `0` 或未设置表示自动） |
| 下限 | 内容自然高度（测量 toolbar 内容高度） |
| 上限 | `min(280px, 40vh)` |
| 对齐 | 内容贴顶；多余高度为工具栏底部空白 |

松手后写入 `sql-oj.layout`（与现有 `layoutPrefs` 一致）。

### 宽度（左右分栏）

| 项 | 旧值 | 新值 |
|---|---|---|
| 最小左栏 | 25% | 20% |
| 最大左栏 | 55% | 70% |
| 默认 | 40% | 40%（不变） |

加载旧偏好时 clamp 到新范围。

### 拖拽跟手感

现状问题：每次 `mousemove` 调用 `setState` 触发整页重渲染（含 Monaco），且 `Math.round` 按整百分比步进，导致不跟手、顿挫。

统一策略（左右与上下）：

1. **拖拽中只改 DOM**（左栏 `style.width` / 工具栏 `style.minHeight`），不触发 React 重渲染。
2. **松手再 commit** 到 React state + `localStorage`。
3. 使用 **Pointer Events** + `setPointerCapture`，减少丢事件。
4. 拖拽中 `body` class：禁用文本选择；编辑器区域 `pointer-events: none`，避免 Monaco 抢指针。
5. 拖拽过程用浮点计算位置，避免每帧整百分比取整造成一格一格跳。
6. 上下/左右共用同一套拖拽模式（可抽小工具或扩展现有 hook）。

视觉：横/竖 resizer hover 与 dragging 高亮与现有竖条一致（accent 色）。

## 3. 应用图标

### 现状

- 应用内顶栏 / favicon：`public/icon.svg`（新图标）。
- 打包图标：`src-tauri/tauri.conf.json` 指向 `src-tauri/icons/*`，但仓库中栅格/ICO 资源缺失或过时；`scripts/generate-icon.ps1` 生成的是旧蓝底 “SQL” 字图。

### 方案

1. 以 `public/icon.svg` 为唯一视觉源。
2. 用 `tauri icon`（或等价流程）生成完整 `src-tauri/icons/` 并**纳入版本库**（含 conf 中列出的 png/ico/icns）。
3. 更新 `scripts/generate-icon.ps1`：改为基于 SVG 调用生成流程，删除旧 Drawing “SQL” 逻辑。
4. 应用内继续引用 `/icon.svg`。

### 生效说明

- 开发：生成 icons 后 `tauri dev` 可验证窗口图标。
- 发布：需重新 `tauri build` 并安装/替换 exe 后，任务栏与 exe 图标才会更新。

## 4. 涉及文件（预期）

| 区域 | 文件 |
|---|---|
| 考点 CSS | `src/styles/global.css` |
| 布局偏好 | `src/lib/layoutPrefs.ts` |
| 分栏 hook | `src/hooks/useProblemSplit.ts`（及可能的工具栏高度逻辑） |
| 做题页 | `src/pages/ProblemPage.tsx` |
| 样式 | `src/styles/global.css`（toolbar resizer、拖拽 class） |
| 图标脚本 | `scripts/generate-icon.ps1` |
| 打包图标 | `src-tauri/icons/*` |

## 5. 验收

- [ ] 考点列表从收起到完全展开，「全部」始终在首行左侧第一位，不垂直移动。
- [ ] 做题页可拖工具栏底边拉高/压矮；松手后刷新仍保持；编辑器区域整体随之下移/上移。
- [ ] 左右分栏可在约 20–70% 内拖动；拖拽过程跟手，无明显步进或编辑器卡顿。
- [ ] `src-tauri/icons` 中的 ico/png 与 `public/icon.svg` 视觉一致；重新打包后 exe/任务栏为新图标。
