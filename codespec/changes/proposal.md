[PROCESSED: 2026-05-12]

# Proposal: spec compliance fixes

## 需求描述

修复当前实现与 `codespec/specs/spec.md` 不一致的解析行为，并补齐对应测试，确保现有代码真正满足 FR-002、FR-003、FR-004、FR-006 的验收场景。

本次修复聚焦以下偏差：

- FR-002：`SELECT * FROM users` 中 `*` 应记录源表 `users`。
- FR-002：派生表外层字段（如 `SELECT id FROM (...) t`）应标记来源为派生表别名 `t`，不穿透到内部物理表。
- FR-003：`WHERE` 条件中的隐式关联关系应返回 `IMPLICIT_JOIN`，而不是 `INNER_JOIN`。
- FR-003：链式 JOIN 的每条关系应使用正确的相邻左/右表，而不是始终把左表设为 FROM 根表。
- FR-004：含 CTE 的层次结构应包含 CTE 定义节点。
- FR-006：补充预定义 JSON Schema，并验证 `parse_sql()` 输出可通过 schema 校验。

不在本次范围内的内容：

- 不扩展 SQL 相似度/聚类功能。
- 不重构整体解析架构。
- 不修改 GUI 行为，除非测试证明现有修复影响 GUI 入口。

## 影响范围

- **spec.md**：不新增需求，仅在必要时澄清 FR-006 的 JSON Schema 存放与校验方式。
- **design.md**：补充实现决策，说明字段来源推断、JOIN 左表推导、CTE hierarchy、JSON Schema 的处理策略。
- **tasks.md**：新增本次修复任务。
- **sql_analysis/parser.py**：修复字段来源、JOIN 提取、CTE 层次结构、输出 schema 相关逻辑。
- **sql_analysis/models.py**：如 schema 校验需要，保持数据模型字段不变；避免不必要修改。
- **tests/test_parser.py**：收紧 FR-002/003/004/006 的断言，覆盖本次偏差。
- **pyproject.toml**：如采用 `jsonschema` 做测试校验，则加入测试依赖；否则使用轻量本地 schema 校验，避免新增依赖。

## 验收标准

- `SELECT * FROM users` 的 STAR 字段输出中 `star_table == "users"`。
- `SELECT id, name FROM (SELECT id, name FROM users) t` 的外层字段 `source_table == "t"`。
- `SELECT * FROM t1, t2 WHERE t1.id = t2.t1_id(+)` 从 `WHERE` 条件识别隐式关联，返回 `IMPLICIT_JOIN`，左表 `t1`，右表 `t2`。
- `SELECT * FROM a JOIN b ON a.x=b.x JOIN c ON b.y=c.y` 返回两条 JOIN，第二条左表为 `b`，右表为 `c`。
- `WITH cte AS (...) SELECT * FROM cte` 的 hierarchy 包含 `CTE_DEF` 节点，并保留主查询结构。
- `parse_sql()` 的成功与失败输出均可通过预定义 JSON Schema 校验。
- 新增/调整的测试能失败复现上述问题，并在修复后通过。
- `uv run pytest --cov=sql_analysis --cov-report=term-missing` 通过，覆盖率不低于 80%。
