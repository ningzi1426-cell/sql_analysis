# Agent Rules

Rules governing how AI agents should behave in this project.

## General
- Always read spec.md and design.md before writing any code
- Follow the change flow (proposal → delta → merge → implement → review)
- Do not implement features not described in spec.md without updating the spec first

## Communication
- Pause at each node and wait for explicit user approval before proceeding
- Report clearly when something in the spec is ambiguous or conflicting

## File Handling
- Do not delete files in codespec/ — append to delta files, archive before modifying specs

## Version Control

一个 SDD change 对应一个 git 分支，master 始终可交付。

### 分支命名

```
change/<短名称>
```

如 `change/sql-clustering`，与 `proposal.md` 标题对应。

### 提交流程

每个节点通过用户确认后立即提交，不在节点之间攒代码：

| 节点 | 提交内容 | commit message 示例 |
|------|---------|---------------------|
| Node 1 | proposal.md | `Node 1: proposal — 相似度聚类功能` |
| Node 2 | delta-*.md + archives/ | `Node 2: delta & archive` |
| Node 3 | spec.md / design.md / tasks.md 更新 | `Node 3: merge delta into specs` |
| Node 4 | 实现代码（每个 TASK 一个 commit） | `Node 4: TASK-004 表引用提取` |
| Node 5 | 审查通过的代码 | `Node 5: review passed` |

### 合并规则

- 只有 Node 5 审查通过后才 merge 回 master
- merge 后删除 feature 分支
- master 历史即完整变更日志

### 当前分支例外

项目初始化阶段（无代码 → 首次实现）允许直接在 master 提交。后续新 change 严格走分支流程。
