# design.md 变更日志

<!-- This file is append-only. Each change adds a new ## section. Do not edit or delete existing sections. -->

## 2026-05-02 单条 SQL 解析功能

### 变更摘要
新增单条 SQL 解析功能的架构设计文档，确立了 sqlglot 解析引擎、模块分层、数据模型和解析流程的技术方案。

### 对 design.md 的变更
- **新建文件**：`codespec/specs/design.md`
- **架构总览**：定义 3 个核心模块（models.py 数据模型、cleaner.py 清洗、parser.py 解析编排）和测试目录结构。
- **决策 1 — sqlglot 作为解析引擎**：选用 `sqlglot.parse_one(sql, read="oracle")`，基于 AST 遍历实现所有提取逻辑。
- **决策 2 — Tokenizer 做参数清洗**：使用 sqlglot tokenizer 识别 `&XXX` 和 `:XXX` token，避免正则误匹配字符串/注释内内容。
- **决策 3 — 单次 AST 遍历 + 上下文栈**：一次递归遍历维护 SELECT 作用域和嵌套深度，避免多次 `find_all()` 无法正确维护上下文。
- **决策 4 — dataclass 内部表示 + dict JSON 输出**：内部类型安全的 dataclass，`to_dict()` 序列化，`parse_sql()` 返回 plain dict。
- **决策 5 — 虚拟表白名单**：维护 `{"dual", "sys.dual"}` 集合做 VIRTUAL_TABLE 识别和过滤。
- **数据模型**：定义 TableType/JoinType/ColumnRefType 枚举，TableRef/ColumnRef/JoinRef/HierarchyNode/ParseResult 结构体。
- **解析流程**：`parse_sql()` → `clean_sql()` → `parse_one()` → 单次 AST 遍历提取四类信息 → 组装 JSON dict。
- **依赖声明**：sqlglot >= 25.0.0、Python 3.12+、uv、pytest + pytest-cov。

## 2026-05-03 增加 GUI 直接执行入口

### 变更摘要
新增 easygui 依赖说明和 `__main__` 块设计，为 cleaner.py 和 parser.py 增加 GUI 直接执行入口，用户无需命令行即可通过图形界面选择文件并处理。

### 对 design.md 的变更
- **新增依赖 easygui**：用于文件选择对话框和确认对话框，无需浏览器或复杂框架。easygui 提供 `fileopenbox()` 和 `ynbox()` 等简单 API。
- **新增 `__main__` 块设计**：cleaner.py 和 parser.py 各自在末尾新增 `if __name__ == '__main__'` 块，不修改现有函数逻辑。
- **交互流程设计**：
  1. `easygui.fileopenbox()` 弹出文件选择对话框，过滤显示 SQL 文件
  2. `easygui.ynbox()` 弹出确认对话框，询问用户是否将结果保存到本地文件
  3. cleaner.py 读取文件内容后调用 `clean_sql()` 清洗，将清洗结果写入同目录输出文件
  4. parser.py 读取文件内容后调用 `parse_sql()` 解析，将 JSON 结果写入同目录输出文件
  5. 输出文件默认保存到输入 SQL 文件所在目录
- **架构影响**：不新增模块，仅在现有 cleaner.py 和 parser.py 末尾追加 `__main__` 块。easygui 作为核心依赖加入 pyproject.toml。

### 审查偏差记录 (2026-05-03)

**Node 5 合规审查**: 指南合规性审查 FAIL — `__main__` 块缺少显式错误处理

**偏差**: `__main__` 块中的文件读写和解析操作未包裹 try/except，不符合 coding.md "Always handle errors explicitly" 规则。

**接受理由**: `__main__` 块是面向用户的 GUI 入口，不是库代码路径。easygui 自身的异常对话框（exceptionbox）本身也在 easygui 事件循环中。当前行为（Python traceback 输出到控制台）对于通过命令行启动的用户来说是可接受的调试信息，与直接调用 `parse_sql()` 的错误暴露方式一致。后续可在使用中根据实际遇到的错误场景逐步完善错误提示。

**影响**: 无功能影响。`__main__` 块行为不变。

## 2026-05-10 cleaner 别名规范化

### 变更摘要
新增别名规范化功能，作为 `clean_sql()` 之后的独立处理步骤。使用 sqlglot AST 遍历识别所有表引用，对无别名或别名重复的表进行修正，确保别名到 `schema.table` 的映射是 1:1 的。

### 对 design.md 的变更
- **新增 Decision 8: `normalize_aliases()` 作为独立函数**
  - **Choice**: 在 `cleaner.py` 中新增 `normalize_aliases(sql: str) -> str` 函数，基于 sqlglot AST 遍历修改表别名，返回规范化后的 SQL 字符串。
  - **Rationale**: 与现有 `clean_sql()` 职责分离（清洗占位符 vs 规范化别名），各自独立可测试。`normalize_aliases()` 需要 AST 级别的信息（表名、别名、作用域），不适合 tokenizer 方案。
  - **Implications**: `cleaner.py` 新增 sqlglot `parse_one` / `exp` 相关导入；`parse_sql()` 调用链变为 `clean_sql()` → `normalize_aliases()` → `parse_one()`。

- **新增 Decision 9: 别名生成策略**
  - **Choice**: 无别名时以表名自身作为别名；别名重复时追加数字后缀 `_2`、`_3`...（第一个保留原名）。
  - **Rationale**: 表名作为别名语义清晰，便于人工阅读；数字后缀简单直接，不会与现有别名冲突。
  - **Implications**: 别名冲突检测需维护已见别名集合，按表在 SQL 中出现的顺序分配。

- **新增 Decision 10: AST 改写方式**
  - **Choice**: 遍历 `exp.Table` 和 `exp.Subquery` 节点，对需要修改别名的节点设置 `alias` 属性，通过 `ast.sql(dialect="oracle")` 输出修改后的 SQL。
  - **Rationale**: 直接修改 AST 对象比字符串替换更安全，避免误改注释/字符串中的内容。
  - **Implications**: 需注意 `exp.Subquery` 的别名设置方式可能与 `exp.Table` 不同（`Subquery.args["alias"]` 是 Identifier 对象 vs `Table` 的 `alias` 属性）。CTE 引用（`exp.CTE`）也需要作为表引用参与别名检测。

### 对 tasks.md 的变更
- **TASK-012: 实现 `normalize_aliases()` 函数（FR-008）**
  - Context: 在 `cleaner.py` 中新增 `normalize_aliases(sql: str) -> str`，遍历 AST 中所有表引用，为无别名表生成别名、为重复别名追加数字后缀。需处理基表、派生表（子查询）、CTE 引用。
  - Acceptance:
    - 无别名表自动获得别名（表名自身）
    - 重复别名追加数字后缀（首个保留原名，后续为 `_2`、`_3`...）
    - 同一物理表多次引用但别名不冲突时不做修改
    - 输出 SQL 可被 sqlglot 解析
    - `parse_sql()` 调用链中插入 `normalize_aliases()`，现有 38 个测试全部通过

- **TASK-013: 测试别名规范化（FR-008）**
  - Context: 在 `test_cleaner.py` 中新增别名规范化测试类
  - Acceptance:
    - 覆盖：无别名表、别名重复、混合场景、CTE、子查询、无冲突保持原样
    - 所有新测试通过
    - 覆盖率 >= 80%

## 2026-05-10 Column 别名传播修复

### 变更摘要
修复 `normalize_aliases()` 的表别名重命名后 Column 引用未同步更新的缺陷。新增辅助函数，在别名重命名时同步更新 ON/WHERE 子句中所有**可确定归属**的 Column 引用。

### 对 design.md 的变更
- **新增 Decision 11: Column 别名传播启发式**
  - **Choice**: 当表别名被重命名时，在查询的 ON 和 WHERE 子句中查找比较表达式（`=`、`<`、`>` 等），将右侧子树中 `table` 属性匹配旧别名的 Column 更新为新别名。基于 `左表.列 = 右表.列` 约定。
  - **Rationale**: 无 schema 信息时，比较表达式是唯一能确定 Column 归属的语法结构。此启发式覆盖显式 JOIN ON、隐式关联 WHERE、复合条件、括号包裹等场景。无法确定的 Column（如 `WHERE u.col = 1` 中的单边引用）保持原样。
  - **Implications**: CROSS JOIN（无 ON）跳过；SELECT 列表中的 Column 不更新（无法消歧义）；识别局限性在代码注释中标明。

- **新增三个内部辅助函数**：
  - `_propagate_column_alias(node, old_alias, new_alias)` — 从节点出发，找到所属的 SELECT 节点，遍历其 ON/WHERE 子句
  - `_propagate_in_condition(expr, old_alias, new_alias)` — 递归遍历条件表达式，对比较运算符的右侧子树调用更新
  - `_update_columns_in_subtree(expr, old_alias, new_alias)` — 在子树中 `find_all(exp.Column)` 并更新匹配的 `table`

- **覆盖场景**：
  - 显式 JOIN ON：`FROM t1 u JOIN t2 u ON u.a = u.b` → `u.b` → `u_2.b`
  - 隐式关联 WHERE：`FROM t1 u, t2 u WHERE u.a = u.b` → `u.b` → `u_2.b`
  - 复合条件 AND/OR 递归
  - 括号解包
  - 表达式子树：`u.a = u.b + u.c` → `u.b`, `u.c` → `u_2.b`, `u_2.c`

- **normalize_aliases() 修改**：在 `exp.Table` 和 `exp.Subquery` 的重复别名分支中，`node.set("alias", ...)` 后各加一行 `_propagate_column_alias()` 调用。

### 对 tasks.md 的变更
- **TASK-014: 实现 Column 别名传播（FR-008 修复）**
  - Context: 在 `cleaner.py` 中新增 `_propagate_column_alias()`、`_propagate_in_on_expression()`、`_update_columns_in_subtree()` 三个内部函数。修改 `normalize_aliases()` 两处调用点。处理 AND/OR、括号、比较运算符等各种表达式形态。
  - Acceptance:
    - ON 条件中比较运算符右侧 Column 随表别名同步更新
    - 左侧 Column 不变、SELECT 中 Column 不变
    - 括号、复合条件正确处理
    - CROSS JOIN 不报错
    - 现有 50 个测试全部通过

- **TASK-015: 测试 Column 别名传播**
  - Context: 在 `test_cleaner.py` 中新增 Column 传播相关测试
  - Acceptance:
    - 覆盖：ON 右侧更新、复合条件、括号、子查询别名、CROSS JOIN、无冲突不变
    - 所有新测试通过
    - 覆盖率 >= 80%
