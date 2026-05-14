[PROCESSED: 2026-05-13]

# Proposal: implicit join splitting

## 需求描述

修复 FR-003 中隐式 JOIN 识别的细粒度拆分问题。当前 parser 能识别 `WHERE` 中存在隐式关联，但在多表、多条件场景下会把完整 WHERE 条件复制到多条 JOIN 上，并且左表可能固定成 FROM 的第一个表，导致关系不准确。同时，`join_type` 不应再输出 `IMPLICIT_JOIN`；连接类型应归类为 `INNER_JOIN`、`LEFT_JOIN` 等语义类型，是否来自 WHERE 隐式 JOIN 由独立字段承载。

典型问题来自 `examples/230278.sql`：

```sql
FROM ht, lt, (...) s2, gl
WHERE
    ht.ae_header_id = lt.ae_header_id
    AND lt.ae_header_id = s2.ae_header_id
    AND lt.ae_line_num = s2.ae_line_num
    AND ht.je_transfer_status_code <> 'NT'
    AND ht.ledger_short_name = gl.ledger_short_name
```

期望输出应按表间比较条件拆分隐式 JOIN：

- `ht` -> `lt`，条件 `ht.ae_header_id = lt.ae_header_id`
- `lt` -> `s2`，条件 `lt.ae_header_id = s2.ae_header_id`
- `lt` -> `s2`，条件 `lt.ae_line_num = s2.ae_line_num`
- `ht` -> `gl`，条件 `ht.ledger_short_name = gl.ledger_short_name`

非表间过滤条件（如 `ht.je_transfer_status_code <> 'NT'`）不生成 JOIN。

不在本次范围内：

- 不做 GROUP BY/SELECT 中未知别名的语义校验，例如 `ss2t.sr1`。
- 不重构显式 JOIN 的整体提取逻辑，除非为避免回归需要小幅调整共用辅助函数。
- 不修改数据模型字段结构。

## 影响范围

- **spec.md**：澄清 FR-003 的 WHERE 隐式连接场景，要求按表间比较条件拆分多条 `IMPLICIT_JOIN`，过滤条件不生成 JOIN。
- **design.md**：补充隐式 JOIN 拆分策略：递归拆分 WHERE 的 AND 条件，只为左右两侧均有不同表限定符的比较表达式生成关系；新增 `is_implicit` 字段承载隐式来源。
- **tasks.md**：新增本次修复任务。
- **sql_analysis/models.py**：更新 `JoinRef` 输出结构，新增 `is_implicit` 字段。
- **sql_analysis/parser.py**：修复 `_extract_joins()` / 相关辅助函数的隐式 JOIN 提取逻辑，并停止输出 `join_type = IMPLICIT_JOIN`。
- **tests/test_parser.py**：新增或收紧多表 WHERE 隐式 JOIN 测试，覆盖 `230278.sql` 代表场景。

## 验收标准

- `WHERE a.id = b.a_id AND b.id = c.b_id AND a.status <> 'X'` 返回 2 条隐式 JOIN，`is_implicit == true`，`join_type == INNER_JOIN`，不为 `a.status <> 'X'` 生成 JOIN。
- `examples/230278.sql` 至少返回以下隐式关系：`ht -> lt`、`lt -> s2`（两条条件）、`ht -> gl`。
- 带 Oracle `(+)` 的条件（如 `t1.id = t2.t1_id(+)`）返回 `is_implicit == true`，左表 `t1`，右表 `t2`，`join_type == LEFT_JOIN`。
- 每条隐式 JOIN 的 `condition` 为对应的单条表间比较条件，而不是完整 WHERE 条件。
- 每条隐式 JOIN 的 `conditions` 只包含该条条件。
- 现有显式 INNER/LEFT/CROSS JOIN 测试不回归。
- `uv run pytest --cov=sql_analysis --cov-report=term-missing` 通过，覆盖率不低于 80%。
