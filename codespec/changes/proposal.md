# [PROCESSED: 2026-05-15]

# Proposal: cte union table expansion

## 需求描述

修复 CTE 定义体为 `UNION` / `UNION ALL` 时，解析结果中 `tables`
和 `hierarchy` 展开不完整的问题。

当前 parser 只把 CTE 定义体为 `SELECT` 的节点收集到 `cte_defs`。
当 SQL 包含如下结构时：

```sql
WITH final AS (
    SELECT ... FROM rev_data r
    UNION ALL
    SELECT ... FROM rev_data r
)
SELECT ... FROM final f
```

`final` 在 sqlglot AST 中是 `exp.Union`，因此没有被识别为 CTE
定义。后续表引用提取会把 `final` 误判为 `BASE_TABLE`，且
`nested_tables` 为空；层次结构中也缺少 `final` 的 `CTE_DEF` 节点。

本次变更只修复 CTE 定义体为 `SELECT` 或 `UNION` 时的统一收集和展开。
不做字段血缘、别名语义校验、UNION 去重策略或其他解析能力扩展。

## 影响范围

- **spec.md**：补充 FR-001 / FR-004 对 UNION CTE 的表引用和层次结构要求。
- **design.md**：补充 CTE 定义收集和展开应支持 `Select | Union` 的设计决策。
- **tasks.md**：新增本次修复任务。
- **sql_analysis/parser.py**：修复 CTE 定义收集、CTE nested_tables 展开、CTE hierarchy 构建中只接受 `Select` 的限制。
- **tests/test_parser.py**：新增覆盖 `examples/243791.sql` 代表场景的回归测试。

## 验收标准

- `examples/243791.sql` 解析结果中，`final` 被识别为 `CTE` 而不是 `BASE_TABLE`。
- `final` 的 `nested_tables` 能展开其 UNION 分支中的 `rev_data` 引用。
- `rev_data` 的 CTE 展开仍能包含其底层物理表，如 `ogg_hah_je_batch_8863_vi`、`ogg_hah_je_header_8863_vi`、`ogg_hah_je_line_8863_vi`、`ogg_gsc_ledgers_t_8863`、`dwr_dim_product_d` 和 `ebg_contract`。
- `hierarchy` 中包含 `final` 的 `CTE_DEF` 节点，且该节点子树体现 UNION 的两个分支。
- 现有 CTE、UNION、JOIN、隐式 JOIN 测试不回归。
- `uv run pytest --cov=sql_analysis --cov-report=term-missing` 通过，覆盖率不低于 80%。
