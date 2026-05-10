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
  - Context: 在 `cleaner.py` 中新增 `_propagate_column_alias()`、`_propagate_in_condition()`、`_update_columns_in_subtree()` 三个内部函数。修改 `normalize_aliases()` 在 `exp.Table` 和 `exp.Subquery` 的重复别名分支中各加一行调用。处理 ON 子句（显式 JOIN）和 WHERE 子句（隐式关联）中所有比较表达式。比较运算符包括 EQ/NEQ/GT/LT/GTE/LTE/Is/NullSafeEQ。递归处理 AND/OR、解包括号。
  - Acceptance:
    - ON 条件中比较运算符右侧 Column 随表别名同步更新
    - WHERE 隐式关联条件中比较运算符右侧 Column 同步更新
    - 左侧 Column 不变、SELECT 中 Column 不变（无法确定归属）
    - 括号、AND/OR 复合条件递归处理
    - CROSS JOIN 不报错
    - 现有 50 个测试全部通过

- **TASK-015: 测试 Column 别名传播**
  - Context: 在 `test_cleaner.py` 的 `TestNormalizeAliases` 类中新增 Column 传播相关测试
  - Acceptance:
    - 覆盖：ON 右侧更新、WHERE 隐式关联更新、复合条件、括号、子查询别名、表达式多列更新、CROSS JOIN 跳过、无冲突不变
    - 所有新测试通过
    - 覆盖率 >= 80%
