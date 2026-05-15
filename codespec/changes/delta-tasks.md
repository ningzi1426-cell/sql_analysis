# tasks.md 变更日志

<!-- This file is append-only. Each change adds a new ## section. Do not edit or delete existing sections. -->

## 2026-05-02 单条 SQL 解析功能

### 变更摘要
新增单条 SQL 解析功能的 9 项工作任务拆解，从项目脚手架到完整测试套件，按依赖关系排序。

### 对 tasks.md 的变更
- **新建文件**：`codespec/specs/tasks.md`
- **TASK-001 项目脚手架**：建立 pyproject.toml、模块骨架、uv 环境和空测试运行。
- **TASK-002 数据模型 models.py**：定义全部 dataclass 和 Enum，含 to_dict() 序列化。
- **TASK-003 参数/变量清洗 cleaner.py（FR-005）**：处理 `&XXX`/`:XXX` 替换，跳过字符串和注释。
- **TASK-004 表引用提取 parser.py part 1（FR-001）**：基表/派生表/CTE/虚拟表识别与剔除。
- **TASK-005 字段引用提取 parser.py part 2（FR-002）**：限定符、位置索引、子查询边界、星号。
- **TASK-006 关联关系识别 parser.py part 3（FR-003）**：JOIN 类型、条件、隐式连接、Oracle (+)。
- **TASK-007 层次结构识别 parser.py part 4（FR-004）**：嵌套树、CTE_DEF、UNION 分支、深度统计。
- **TASK-008 parse_sql() 编排与 JSON 输出 parser.py part 5（FR-006）**：串联流程、异常处理、JSON 组装。
- **TASK-009 完整测试套件**：覆盖全部 spec 场景 + 示例文件，覆盖率 >= 80%。

## 2026-05-03 增加 GUI 直接执行入口

### 变更摘要
新增 2 项实现任务（TASK-010、TASK-011）：为 cleaner.py 和 parser.py 分别添加 `__main__` GUI 入口块，使用 easygui 实现文件选择和处理输出。

### 对 tasks.md 的变更
- **TASK-010: cleaner.py GUI 入口（FR-007）**
  - Context: 在 cleaner.py 末尾添加 `if __name__ == '__main__'` 块，使用 easygui 实现文件选择和清洗输出
  - Acceptance:
    - `uv run python sql_analysis/cleaner.py` 启动 GUI，选择 SQL 文件后可清洗并输出
    - `uv run python -m sql_analysis.cleaner` 效果同上
    - 输出文件默认保存在输入 SQL 文件所在目录
    - easygui 加入 pyproject.toml 依赖
- **TASK-011: parser.py GUI 入口（FR-007）**
  - Context: 在 parser.py 末尾添加 `if __name__ == '__main__'` 块，使用 easygui 实现文件选择、解析和 JSON 输出
  - Acceptance:
    - `uv run python sql_analysis/parser.py` 启动 GUI，选择 SQL 文件后可解析并输出 JSON
    - `uv run python -m sql_analysis.parser` 效果同上
    - 输出文件默认保存在输入 SQL 文件所在目录
    - 现有 38 个测试不受影响，全部通过

## 2026-05-10 cleaner 别名规范化

### 变更摘要
新增 2 项实现任务（TASK-012、TASK-013）：为 cleaner.py 新增 `normalize_aliases()` 函数，集成到 `parse_sql()` 调用链，并编写完整测试覆盖。

### 对 tasks.md 的变更
- **TASK-012: 实现 `normalize_aliases()` 函数（FR-008）**
  - Context: 在 `cleaner.py` 中新增 `normalize_aliases(sql: str) -> str`，遍历 AST 中所有表引用，为无别名表生成别名、为重复别名追加数字后缀。需处理基表（exp.Table）、派生表（exp.Subquery）、CTE 引用。别名生成策略：无别名时用表名自身；重复时追加 `_2`、`_3` 数字后缀。需同步更新 `parse_sql()` 调用链（在 `clean_sql()` 之后、`parse_one()` 之前插入）。
  - Acceptance:
    - 无别名表自动获得别名（表名自身）
    - 重复别名追加数字后缀
    - 同一物理表多次引用但别名不冲突时不做修改
    - 输出 SQL 可被 sqlglot 解析
    - `parse_sql()` 调用链中插入 `normalize_aliases()`，现有 38 个测试全部通过

- **TASK-013: 测试别名规范化（FR-008）**
  - Context: 在 `test_cleaner.py` 中新增测试类，覆盖 spec.md FR-008 全部 7 个 Scenario
  - Acceptance:
    - 覆盖：无别名表、别名重复、同表不同别名不冲突、CTE、子查询、混合场景、输出可解析
    - 所有新测试通过
    - 覆盖率 >= 80%

## 2026-05-10 Column 别名传播修复

### 变更摘要
新增 2 项实现任务（TASK-014、TASK-015）：修复 `normalize_aliases()` 中表别名重命名后 Column 引用未同步更新的缺陷，并编写完整测试覆盖。

### 对 tasks.md 的变更
- **TASK-014: 实现 Column 别名传播（FR-008 修复）**
  - Context: 在 `cleaner.py` 中新增 `_propagate_column_alias()`、`_propagate_in_condition()`、`_update_columns_in_subtree()` 三个内部函数。修改 `normalize_aliases()` 在 `exp.Table` 和 `exp.Subquery` 的重复别名分支中各加一行调用。`_propagate_column_alias` 从节点向上找所属 SELECT，遍历其 WHERE、HAVING、所有 JOIN 的 ON 子句，对比较表达式右侧 Column 同步更新。覆盖 parser 所需的所有子句。
  - Acceptance:
    - ON/WHERE/HAVING 中比较运算符右侧 Column 随表别名同步更新
    - 左侧 Column 不变、SELECT 列表中单独 Column 不变（无法确定归属）
    - 括号、AND/OR 复合条件递归处理
    - CROSS JOIN 不报错
    - 现有 50 个测试全部通过

- **TASK-015: 测试 Column 别名传播**
  - Context: 在 `test_cleaner.py` 的 `TestNormalizeAliases` 类中新增 Column 传播相关测试
  - Acceptance:
    - 覆盖：ON 右侧更新、WHERE 隐式关联更新、HAVING 条件更新、复合条件、括号、子查询别名、表达式多列更新、CROSS JOIN 跳过、无冲突不变
    - 所有新测试通过
    - 覆盖率 >= 80%

## 2026-05-12 spec compliance fixes

### 变更摘要
新增 4 项任务，修复现有 parser 与 spec 的偏差，并补齐精确测试。

### 对 tasks.md 的变更
- **TASK-016: 修复 FR-002 字段来源推断**
  - Context: 修改 `parser.py` 的字段提取逻辑，为当前 SELECT 构建 FROM 源上下文；支持 `SELECT * FROM users` 的 `star_table`，以及 `SELECT id FROM (...) t` 外层字段来源为 `t`。
  - Acceptance:
    - STAR 字段记录 `star_table == "users"`。
    - 派生表外层未限定字段记录 `source_table == "t"`。
    - 多表或无法消歧时仍返回 `UNKNOWN`。
- **TASK-017: 修复 FR-003 JOIN 关系识别**
  - Context: 修改 `parser.py` 的 JOIN 提取逻辑，显式链式 JOIN 从 ON 条件推导实际左表；WHERE 隐式关联从 WHERE 比较表达式识别表间关系并返回 `IMPLICIT_JOIN`。
  - Acceptance:
    - `a JOIN b ... JOIN c ON b.y=c.y` 的第二条 JOIN 左表为 `b`，右表为 `c`。
    - `WHERE t1.id = t2.t1_id(+)` 识别为 `IMPLICIT_JOIN`，左表 `t1`，右表 `t2`。
    - CROSS JOIN 不受影响。
- **TASK-018: 修复 FR-004 CTE hierarchy**
  - Context: 修改 hierarchy 构建逻辑，使 CTE 定义以 `CTE_DEF` 节点出现在层次结构中，同时保留主查询节点。
  - Acceptance:
    - `WITH cte AS (...) SELECT * FROM cte` 的 hierarchy 包含 `CTE_DEF`。
    - 原有无嵌套、子查询、UNION hierarchy 测试继续通过。
- **TASK-019: 补齐 FR-006 JSON Schema 验证测试**
  - Context: 在测试中定义 parse result JSON Schema，覆盖成功输出与错误输出。
  - Acceptance:
    - 成功输出通过 schema 校验。
    - 解析失败输出通过 schema 校验。
    - `uv run pytest --cov=sql_analysis --cov-report=term-missing` 通过，覆盖率不低于 80%。

## 2026-05-13 implicit join splitting

### 变更摘要
新增 2 项任务，先收紧隐式 JOIN 测试，再修复 parser 的 WHERE 条件拆分逻辑。

### 对 tasks.md 的变更
- **TASK-020: 补充多条件隐式 JOIN 测试**
  - Context: 在 `tests/test_parser.py` 中新增/收紧 FR-003 测试，覆盖多表 WHERE 条件和 `examples/230278.sql` 代表场景。
  - Acceptance:
    - 多条件 WHERE 只为表间比较生成 `IMPLICIT_JOIN`。
    - `230278.sql` 输出包含 `ht -> lt`、`lt -> s2`、`lt -> s2`、`ht -> gl`。
    - 每条 JOIN 的 `condition`/`conditions` 不再是完整 WHERE。
- **TASK-021: 修复 WHERE 隐式 JOIN 拆分实现**
  - Context: 修改 `sql_analysis/parser.py` 的隐式 JOIN 提取逻辑，递归拆分 WHERE 中的 AND 条件，并为每条表间比较生成独立 `JoinRef`。
  - Acceptance:
    - TASK-020 新增测试通过。
    - 现有显式 INNER/LEFT/CROSS JOIN 测试不回归。
    - `uv run pytest --cov=sql_analysis --cov-report=term-missing` 通过，覆盖率不低于 80%。

### 2026-05-13 补充：Oracle (+) 测试任务要求
- **TASK-020 验收补充**：测试必须包含带 Oracle `(+)` 的 WHERE 隐式 JOIN 条件，覆盖单条件和多条件混合场景。
- **TASK-021 验收补充**：实现必须在带 `(+)` 的 Column 上仍能正确提取左右表并生成独立 `IMPLICIT_JOIN`。

### 2026-05-13 修正：JoinRef 输出字段任务要求
- **TASK-020 验收修正**：隐式 JOIN 测试不再期望 `join_type == "IMPLICIT_JOIN"`，而应断言 `is_implicit == True`，普通 WHERE 表间条件对应 `join_type == "INNER_JOIN"`，带 `(+)` 的条件对应 `join_type == "LEFT_JOIN"`。
- **TASK-021 实现修正**：更新 `JoinRef` 数据模型与 parser 输出，新增 `is_implicit` 字段，并停止输出 `IMPLICIT_JOIN` 类型。

## 2026-05-15 cte union table expansion

### 变更摘要
新增 2 项任务，先补充 UNION CTE 回归测试，再修复 parser 中 CTE 定义体只接受 `Select` 的限制。

### 对 tasks.md 的变更
- **TASK-022: 补充 UNION CTE 表引用和层次结构测试**
  - Context: 在 `tests/test_parser.py` 中新增覆盖 `examples/243791.sql` 或等价精简 SQL 的测试，验证 `final AS (... UNION ALL ...)` 能被识别为 CTE。
  - Acceptance:
    - `final` 的 `table_type == "CTE"`，不是 `BASE_TABLE`。
    - `final.nested_tables` 包含 UNION 分支中的 `rev_data` 引用。
    - `hierarchy.children` 包含名为 `final` 的 `CTE_DEF`。
    - `final` 的 CTE_DEF 子树包含 `UNION` 节点和两个 SELECT 分支。

- **TASK-023: 修复 UNION CTE 定义收集与展开实现**
  - Context: 修改 `sql_analysis/parser.py`，让 CTE 定义收集、CTE nested_tables 填充和 hierarchy 构建支持 `exp.Select | exp.Union`。必要时新增统一表提取辅助函数，避免在多个调用点重复类型分支。
  - Acceptance:
    - TASK-022 新增测试通过。
    - `examples/243791.sql` 的 `tables` 输出能展开 `final -> rev_data`，并保留 `rev_data` 对底层物理表的展开能力。
    - 现有 CTE、UNION、JOIN、隐式 JOIN 测试不回归。
    - `uv run pytest --cov=sql_analysis --cov-report=term-missing` 通过，覆盖率不低于 80%。
