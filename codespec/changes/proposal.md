[PROCESSED: 2026-05-10]

# Proposal: cleaner 别名规范化

## 需求描述
为 cleaner 增加别名规范化功能，确保 SQL 中所有表引用都有独一无二的别名。目的是让后续分析流程能从别名唯一还原到具体的 schema 和表名（即别名到 `schema.table` 的映射是 1:1 的）。

至少处理以下场景：
1. **原 SQL 中表没有别名** — 自动生成别名
2. **原 SQL 中表别名出现重复** — 去重，为重复别名生成唯一变体

该功能作为 `clean_sql()` 之后、`parse_one()` 之前的独立处理步骤，集成到 `parse_sql()` 调用链中。

## 影响范围
- **spec.md** — 新增 FR-008：别名规范化
- **design.md** — 新增 Decision：别名生成策略与 AST 改写方案
- **tasks.md** — 新增 2 个实现任务（实现 + 测试）
- **sql_analysis/cleaner.py** — 新增 `normalize_aliases()` 函数
- **sql_analysis/parser.py** — `parse_sql()` 调用链中插入 `normalize_aliases()`
- **tests/test_cleaner.py** — 新增别名规范化相关测试用例

## 验收标准
- 无别名的表自动获得别名（以表名自身为别名）
- 别名重复的表自动获得唯一别名（追加数字后缀）
- 同一张物理表多次引用时，各自别名保持唯一
- `normalize_aliases()` 输出的 SQL 可被 sqlglot 正常解析
- 现有 38 个测试不受影响，全部通过
- 新增测试覆盖：无别名、别名重复、混合场景、CTE、子查询
