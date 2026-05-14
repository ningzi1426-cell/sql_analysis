# Task Breakdown

## Completed Tasks

- [x] **TASK-001**: 项目脚手架 — 完成于 2026-05-02
- [x] **TASK-002**: 数据模型 `models.py` — 完成于 2026-05-02
- [x] **TASK-003**: 参数/变量清洗 `cleaner.py`（FR-005） — 完成于 2026-05-02
- [x] **TASK-004**: 表引用提取 `parser.py` part 1（FR-001） — 完成于 2026-05-02
- [x] **TASK-005**: 字段引用提取 `parser.py` part 2（FR-002） — 完成于 2026-05-02
- [x] **TASK-006**: 关联关系识别 `parser.py` part 3（FR-003） — 完成于 2026-05-02
- [x] **TASK-007**: 层次结构识别 `parser.py` part 4（FR-004） — 完成于 2026-05-02
- [x] **TASK-008**: `parse_sql()` 编排与 JSON 输出（FR-006） — 完成于 2026-05-02
- [x] **TASK-009**: 完整测试套件 — 完成于 2026-05-02（38/38 通过, 91% 覆盖率）

## GUI 入口（FR-007）

- [x] **TASK-010**: cleaner.py GUI 入口（FR-007） — 完成于 2026-05-03
  - Context: 在 cleaner.py 末尾添加 `if __name__ == '__main__'` 块，使用 easygui 实现文件选择和清洗输出
  - Acceptance:
    - `uv run python sql_analysis/cleaner.py` 启动 GUI，选择 SQL 文件后可清洗并输出
    - `uv run python -m sql_analysis.cleaner` 效果同上
    - 输出文件默认保存在输入 SQL 文件所在目录，文件名为 `<原文件名>_cleaned.sql`
    - easygui 加入 pyproject.toml 依赖
- [x] **TASK-011**: parser.py GUI 入口（FR-007） — 完成于 2026-05-03
  - Context: 在 parser.py 末尾添加 `if __name__ == '__main__'` 块，使用 easygui 实现文件选择、解析和 JSON 输出
  - Acceptance:
    - `uv run python sql_analysis/parser.py` 启动 GUI，选择 SQL 文件后可解析并输出 JSON
    - `uv run python -m sql_analysis.parser` 效果同上
    - 输出文件默认保存在输入 SQL 文件所在目录，文件名为 `<原文件名>_parsed.json`
    - 现有 38 个测试不受影响，全部通过

## 别名规范化（FR-008）

- [x] **TASK-012**: 实现 `normalize_aliases()` 函数（FR-008） — 完成于 2026-05-10
  - Context: 在 `cleaner.py` 中新增 `normalize_aliases(sql: str) -> str`，遍历 AST 中所有表引用，为无别名表生成别名、为重复别名追加数字后缀。需处理基表（exp.Table）、派生表（exp.Subquery）、CTE 引用。别名生成策略：无别名时用表名自身；重复时追加 `_2`、`_3` 数字后缀。需同步更新 `parse_sql()` 调用链（在 `clean_sql()` 之后、`parse_one()` 之前插入）。
  - Acceptance:
    - 无别名表自动获得别名（表名自身）
    - 重复别名追加数字后缀
    - 同一物理表多次引用但别名不冲突时不做修改
    - 输出 SQL 可被 sqlglot 解析
    - `parse_sql()` 调用链中插入 `normalize_aliases()`，现有 38 个测试全部通过

- [x] **TASK-013**: 测试别名规范化（FR-008） — 完成于 2026-05-10
  - Context: 在 `test_cleaner.py` 中新增测试类，覆盖 spec.md FR-008 全部 7 个 Scenario
  - Acceptance:
    - 覆盖：无别名表、别名重复、同表不同别名不冲突、CTE、子查询、混合场景、输出可解析
    - 所有新测试通过
    - 覆盖率 >= 80%

## Column 别名传播修复（FR-008）

- [x] **TASK-014**: 实现 Column 别名传播（FR-008 修复） — 完成于 2026-05-10
  - Context: 在 `cleaner.py` 中新增 `_propagate_column_alias()`、`_propagate_in_condition()`、`_update_columns_in_subtree()` 三个内部函数。修改 `normalize_aliases()` 在 `exp.Table` 和 `exp.Subquery` 的重复别名分支中各加一行调用。`_propagate_column_alias` 从节点向上找所属 JOIN 的 ON 子句 + 所属 SELECT 的 WHERE/HAVING 子句，对比较表达式右侧 Column 同步更新。
  - Acceptance:
    - ON/WHERE/HAVING 中比较运算符右侧 Column 随表别名同步更新
    - 左侧 Column 不变、SELECT 列表中单独 Column 不变
    - 括号、AND/OR 复合条件递归处理
    - CROSS JOIN 不报错
    - 现有 50 个测试全部通过

- [x] **TASK-015**: 测试 Column 别名传播 — 完成于 2026-05-10
  - Context: 在 `test_cleaner.py` 中新增 `TestColumnPropagation` 类，覆盖 11 个测试
  - Acceptance:
    - 覆盖：ON 右侧更新、WHERE 隐式关联更新、HAVING 条件更新、复合条件、括号、子查询别名、表达式多列更新、CROSS JOIN 跳过、无冲突不变
    - 所有新测试通过
    - 覆盖率 >= 80%

## Spec 合规修复（FR-002/003/004/006）

- [x] **TASK-016**: 修复 FR-002 字段来源推断
  - Context: 修改 `parser.py` 的字段提取逻辑，为当前 SELECT 构建 FROM 源上下文；支持 `SELECT * FROM users` 的 `star_table`，以及 `SELECT id FROM (...) t` 外层字段来源为 `t`。
  - Acceptance:
    - STAR 字段记录 `star_table == "users"`
    - 派生表外层未限定字段记录 `source_table == "t"`
    - 多表或无法消歧时仍返回 `UNKNOWN`

- [x] **TASK-017**: 修复 FR-003 JOIN 关系识别
  - Context: 修改 `parser.py` 的 JOIN 提取逻辑，显式链式 JOIN 从 ON 条件推导实际左表；WHERE 隐式关联从 WHERE 比较表达式识别表间关系并返回 `IMPLICIT_JOIN`。
  - Acceptance:
    - `a JOIN b ... JOIN c ON b.y=c.y` 的第二条 JOIN 左表为 `b`，右表为 `c`
    - `WHERE t1.id = t2.t1_id(+)` 识别为 `IMPLICIT_JOIN`，左表 `t1`，右表 `t2`
    - CROSS JOIN 不受影响

- [x] **TASK-018**: 修复 FR-004 CTE hierarchy
  - Context: 修改 hierarchy 构建逻辑，使 CTE 定义以 `CTE_DEF` 节点出现在层次结构中，同时保留主查询节点。
  - Acceptance:
    - `WITH cte AS (...) SELECT * FROM cte` 的 hierarchy 包含 `CTE_DEF`
    - 原有无嵌套、子查询、UNION hierarchy 测试继续通过

- [x] **TASK-019**: 补齐 FR-006 JSON Schema 验证测试
  - Context: 在测试中定义 parse result JSON Schema，覆盖成功输出与错误输出。
  - Acceptance:
    - 成功输出通过 schema 校验
    - 解析失败输出通过 schema 校验
    - `uv run pytest --cov=sql_analysis --cov-report=term-missing` 通过，覆盖率不低于 80%
