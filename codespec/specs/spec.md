# Project Specification

<!-- This is the full requirements document. Fill it in before starting any development. -->

## Project Overview
这个项目是针对SQL做批量分析的工具，它预期主要实现两部分功能：
1、拆解单个SQL，识别并结构化其中的表、字段、关联关系等关键要素。
2、对一群SQL通过某种算法识别它们的相似度，并进行聚类分组。

## Functional Requirements

<!-- ============================================ -->
<!--  第一部分：单条 SQL 解析                        -->
<!-- ============================================ -->

### FR-001: 提取 SQL 中的表引用

The system shall extract all table references from a SQL statement,
including the schema prefix when present, and distinguishing between
base tables, derived tables (subqueries), CTEs, and views.

#### Scenario: 简单单表查询
- **GIVEN** 输入 SQL 为 `SELECT id, name FROM users WHERE status = 1`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回 1 条表引用记录：表名 `users`，schema 为空，类型为 BASE_TABLE，无别名

#### Scenario: 带 schema 前缀的表名
- **GIVEN** 输入 SQL 为 `SELECT id FROM dwrdim.dwr_dim_user_d WHERE status = 1`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回的表引用中：schema 为 `dwrdim`，表名 `dwr_dim_user_d`，类型 BASE_TABLE

#### Scenario: 同一张物理表被多次引用
- **GIVEN** 输入 SQL 为 `SELECT pr.prod_code, pr2.prod_code FROM dwrdim.dwr_dim_product_d pr LEFT JOIN dwrdim.dwr_dim_product_d pr2 ON pr.parent_key = pr2.prod_key`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回 2 条表引用记录：
  - 表名 `dwr_dim_product_d`，schema `dwrdim`，别名 `pr`
  - 表名 `dwr_dim_product_d`，schema `dwrdim`，别名 `pr2`
  两者物理表相同但通过别名区分

#### Scenario: 带别名的多表 JOIN
- **GIVEN** 输入 SQL 为 `SELECT a.id, b.name FROM orders a JOIN customers b ON a.cid = b.id`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回 2 条表引用记录：
  - 表名 `orders`，schema 为空，类型 BASE_TABLE，别名 `a`
  - 表名 `customers`，schema 为空，类型 BASE_TABLE，别名 `b`

#### Scenario: 包含子查询作为派生表
- **GIVEN** 输入 SQL 为 `SELECT a.id, b.total FROM users a JOIN (SELECT user_id, sum(amount) AS total FROM orders GROUP BY user_id) b ON a.id = b.user_id`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回的表引用中：
  - 包含 `users`（schema 为空，BASE_TABLE，别名 `a`）
  - 包含一个类型为 DERIVED_TABLE 的条目（别名 `b`），其内部包含 `orders`（schema 为空，BASE_TABLE）

#### Scenario: 包含 CTE 的查询
- **GIVEN** 输入 SQL 为 `WITH active AS (SELECT id, name FROM users WHERE status = 1) SELECT * FROM active`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回 `active`（类型 CTE，引用自 `users`），且 `users` 为 BASE_TABLE，schema 均为空

#### Scenario: 无 FROM 子句的查询
- **GIVEN** 输入 SQL 为 `SELECT 1 AS id`（无 FROM 子句，部分数据库合法）
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 别为虚拟表（类型 VIRTUAL_TABLE），不纳入表引用分析结果中

#### Scenario: 虚拟表无需分析
- **GIVEN** 输入 SQL 为 `SELECT 1 AS id FROM dual`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** `dual` 被识别为虚拟表（类型 VIRTUAL_TABLE），不纳入表引用分析结果中

#### Scenario: 解析失败时的处理
- **GIVEN** 输入为语法不完整的 SQL，如 `SELECT a FROM`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回解析错误，错误信息中包含失败原因，不返回部分结果

---

### FR-002: 提取 SQL 中的字段引用

When a SQL statement is parsed, the system shall extract all column references,
including their source table or alias qualification.

#### Scenario: 不带表限定符的字段
- **GIVEN** 输入 SQL 为 `SELECT id, name, status FROM users`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回 3 条字段引用记录，每条包含字段名及其在 SELECT 中的位置索引；无法推断源表时，源表字段标记为 UNKNOWN

#### Scenario: 带表限定符的字段
- **GIVEN** 输入 SQL 为 `SELECT a.id, a.name, b.total FROM users a JOIN orders b ON a.id = b.user_id`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回的字段引用中：
  - `a.id` → 字段名 `id`，源表别名 `a`，可关联至 `users`
  - `a.name` → 字段名 `name`，源表别名 `a`
  - `b.total` → 字段名 `total`，源表别名 `b`，可关联至 `orders`

#### Scenario: 跨子查询边界的字段
- **GIVEN** 输入 SQL 为 `SELECT id, name FROM (SELECT id, name FROM users) t`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 外层 SELECT 的 `id`、`name` 来源标记为别名 `t`（派生表），不穿透到 `users`

#### Scenario: 使用通配符 `*` 的查询
- **GIVEN** 输入 SQL 为 `SELECT * FROM users`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** `*` 被记录为特殊字段引用，类型为 STAR，源表为 `users`

---

### FR-003: 识别 SQL 中的表关联关系

The system shall identify all JOIN relationships within a SQL statement,
including join type, participating tables, and join conditions.

#### Scenario: 单条 INNER JOIN
- **GIVEN** 输入 SQL 为 `SELECT * FROM orders a JOIN customers b ON a.cid = b.id`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回 1 条关联关系：
  - 左表：`orders`（别名 `a`），右表：`customers`（别名 `b`）
  - JOIN 类型：INNER_JOIN
  - 连接条件：`a.cid = b.id`

#### Scenario: LEFT JOIN 与复合条件
- **GIVEN** 输入 SQL 为 `SELECT * FROM users u LEFT JOIN orders o ON u.id = o.user_id AND o.status = 1`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回的关联关系中：
  - JOIN 类型：LEFT_JOIN
  - 连接条件虽然包含 2 个条件表达式：`u.id = o.user_id` 和 `o.status = 1`，但仅关注 `u.id = o.user_id` 类的表间关联关系

#### Scenario: ON 子句被括号包围
- **GIVEN** 输入 SQL 为 `SELECT * FROM orders o LEFT JOIN products p ON (o.prod_key = p.prod_key AND p.scd_active_ind = 1)`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 正确解析括号内的连接条件，返回 JOIN 类型 LEFT_JOIN，连接条件包含 `o.prod_key = p.prod_key`，`p.scd_active_ind = 1` 作为附加过滤条件

#### Scenario: 无显式连接条件的 CROSS JOIN
- **GIVEN** 输入 SQL 为 `SELECT * FROM t1 CROSS JOIN t2`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回 1 条关联关系：JOIN 类型 CROSS_JOIN，连接条件为空

#### Scenario: 嵌套 JOIN 的关联顺序
- **GIVEN** 输入 SQL 为 `SELECT * FROM a JOIN b ON a.x=b.x JOIN c ON b.y=c.y`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回 2 条关联关系，顺序与 SQL 中 JOIN 出现的顺序一致

#### Scenario: 隐式连接（FROM 子句中逗号分隔的多表）
- **GIVEN** 输入 SQL 为 `SELECT * FROM t1, t2 WHERE t1.id = t2.t1_id(+)`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回 1 条关联关系：
  - 类型 IMPLICIT_JOIN，左表 `t1`，右表 `t2`
  - 出现 `(+)` Oracle数据库关联标识时，表示左关联，其前面的字段是右表字段

---

### FR-004: 识别 SQL 的层次结构

While parsing a SQL statement, the system shall recognize the hierarchical
structure formed by subqueries and CTEs, recording nesting relationships.

#### Scenario: 查询无嵌套
- **GIVEN** 输入 SQL 为 `SELECT id FROM users`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回的层次结构中只有 1 层根查询节点，类型为 SELECT，无子节点

#### Scenario: 含子查询的嵌套查询
- **GIVEN** 输入 SQL 为 `SELECT id FROM (SELECT id, name FROM users) t`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回的层次结构中根节点为外层 SELECT，其子节点为内层 SELECT（派生表 `t`），嵌套深度为 2

#### Scenario: 含 CTE 的查询
- **GIVEN** 输入 SQL 为 `WITH cte AS (SELECT id FROM users WHERE status=1) SELECT * FROM cte`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回的结构包含 1 个 CTE 定义节点 `cte`（内部为 SELECT），以及 1 个主查询节点引用该 CTE

#### Scenario: 多层嵌套子查询
- **GIVEN** 输入 SQL 为 `SELECT * FROM (SELECT id FROM (SELECT id FROM users) t1) t2`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回的嵌套深度为 3，父子关系与 SQL 中的嵌套顺序一致

#### Scenario: 包含 UNION 的查询
- **GIVEN** 输入 SQL 为 `SELECT a.id FROM user1 a UNION ALL SELECT b.id FROM user1 b`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回的结构中将 UNION 的两个分支作为并列节点：
  - 分支 1 包含表引用 `user1`（别名 `a`）
  - 分支 2 包含表引用 `user1`（别名 `b`）
  - 最终汇总表引用时，`user1` 共出现 2 次

---

### FR-005: 清洗 SQL 中的参数和变量占位符

Before parsing a SQL statement, the system shall identify all the parameter and variable placeholders,
and then clean it to avoid interfering with the analysis.

#### Scenario: 参数的识别与清洗
- **GIVEN** 输入 SQL 为 `SELECT * FROM users WHERE status = 1 AND &AAA`
- **WHEN** 调用解析器前
- **THEN** 将符合 `&XXX` 格式的参数内容统一替换为 `(1 = 1)`

#### Scenario: 变量的识别与清洗
- **GIVEN** 输入 SQL 为 `SELECT id, name, :BBB FROM users WHERE status = 1 AND id = :CCC`
- **WHEN** 调用解析器前
- **THEN** 将符合 `:XXX` 格式的变量内容统一替换为 `(1 = 1)`

---

### FR-006: 输出结构化解析结果

When parsing is complete, the system shall produce a structured representation
in a machine-readable format containing all identified elements.

#### Scenario: 常规查询的结构化输出
- **GIVEN** 输入 SQL 为 `SELECT a.id, b.name FROM users a JOIN orders b ON a.id = b.uid WHERE a.status = 1`
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回的 JSON 结构中包含：
  - `tables`: 表引用列表（FR-001 的输出）
  - `columns`: 字段引用列表（FR-002 的输出）
  - `joins`: 关联关系列表（FR-003 的输出）
  - `hierarchy`: 查询层次结构（FR-004 的输出）
  各部分的字段定义与对应 FR 一致

#### Scenario: 解析失败时的输出
- **GIVEN** 输入为无法解析的 SQL
- **WHEN** 调用解析器对该语句进行分析
- **THEN** 返回结构包含 `error` 字段，`tables`、`columns` 等字段为 `null`

#### Scenario: 输出格式验证
- **GIVEN** 任意合法输入 SQL
- **WHEN** 解析器完成分析
- **THEN** 输出结果可通过预定义的 JSON Schema 校验

<!-- EARS patterns (pick one per requirement):
  Ubiquitous:    The system shall [action].
  Event-driven:  When [event], the system shall [action].
  State-driven:  While [state], the system shall [action].
  Unwanted:      If [condition], then the system shall [action].
  Optional:      Where [feature enabled], the system shall [action].

  Rules:
  - Each requirement MUST have at least one Scenario
  - Each Scenario MUST use GIVEN/WHEN/THEN
  - Keep requirements atomic — one behavior per FR
  - Add more Scenarios for edge cases and error conditions
-->

<!-- Add more requirements following the same pattern -->

### FR-007: GUI 直接执行入口

The system shall provide a direct GUI entry point for cleaner.py and parser.py,
allowing users to launch the modules via `python sql_analysis/cleaner.py` or
`python sql_analysis/parser.py` (or `python -m` equivalents).

#### Scenario: cleaner.py GUI 启动与清洗输出
- **GIVEN** 用户通过 `python sql_analysis/cleaner.py` 或 `python -m sql_analysis.cleaner` 启动模块
- **WHEN** 模块运行时弹出 easygui 文件选择对话框
- **THEN** 用户可选择单个 SQL 文件，随后弹出确认对话框询问是否输出结果到本地文件；确认后清洗结果保存至 SQL 文件所在目录，文件名为 `<原文件名>_cleaned.sql`

#### Scenario: parser.py GUI 启动与解析输出
- **GIVEN** 用户通过 `python sql_analysis/parser.py` 或 `python -m sql_analysis.parser` 启动模块
- **WHEN** 模块运行时弹出 easygui 文件选择对话框
- **THEN** 用户可选择单个 SQL 文件，随后弹出确认对话框询问是否输出结果到本地文件；确认后 JSON 解析结果保存至 SQL 文件所在目录，文件名为 `<原文件名>_parsed.json`

#### Scenario: 用户取消文件选择
- **GIVEN** 用户通过任一模块启动 GUI
- **WHEN** 用户在文件选择对话框中取消操作
- **THEN** 程序安静退出，不输出任何文件，不抛出异常

#### Scenario: 用户选择不输出到文件
- **GIVEN** 用户在确认对话框中选择了"否"
- **WHEN** 程序完成处理
- **THEN** 结果不保存到文件，程序正常退出

---

### FR-008: 别名规范化

When SQL 语句被清洗后、解析前, the system shall normalize table aliases to ensure every table reference has a unique alias, enabling unambiguous mapping from alias back to schema and table name.

#### Scenario: 无别名的表自动获得别名
- **GIVEN** 输入 SQL 为 `SELECT id FROM users`
- **WHEN** 调用别名规范化
- **THEN** `users` 获得别名 `users`，输出 SQL 中 `FROM users` 变为 `FROM users AS users`

#### Scenario: 别名重复的表自动去重
- **GIVEN** 输入 SQL 为 `SELECT * FROM users u JOIN orders u ON u.id = u.uid`
- **WHEN** 调用别名规范化
- **THEN** 第二个别名 `u` 被重命名为 `u_2`（或等价唯一后缀），字段引用中的别名同步更新

#### Scenario: 同一张物理表多次引用时别名保持唯一
- **GIVEN** 输入 SQL 为 `SELECT pr.prod_code, pr2.prod_code FROM dwrdim.dwr_dim_product_d pr LEFT JOIN dwrdim.dwr_dim_product_d pr2 ON pr.parent_key = pr2.prod_key`
- **WHEN** 调用别名规范化
- **THEN** 两个表引用的别名 `pr` 和 `pr2` 均保持原样不冲突，无需修改

#### Scenario: 包含子查询的表别名处理
- **GIVEN** 输入 SQL 为 `SELECT a.id, b.total FROM users a JOIN (SELECT user_id FROM orders) b ON a.id = b.user_id`
- **WHEN** 调用别名规范化
- **THEN** 派生表别名 `b` 不变，`users` 别名 `a` 不变

#### Scenario: 包含 CTE 的表别名处理
- **GIVEN** 输入 SQL 为 `WITH active AS (SELECT id FROM users) SELECT * FROM active`
- **WHEN** 调用别名规范化
- **THEN** CTE 名称 `active` 在引用处作为别名保留，CTE 内部 `users` 无别名时自动获得别名 `users`

#### Scenario: 混合场景（部分有别名、部分无别名、部分重复）
- **GIVEN** 输入 SQL 为 `SELECT * FROM users a JOIN orders a JOIN products ON a.id = products.id`
- **WHEN** 调用别名规范化
- **THEN** `users` 保留别名 `a`，`orders` 的重复别名 `a` 被重命名为 `a_2`，`products` 获得别名 `products`

#### Scenario: 规范化后 SQL 仍可正常解析
- **GIVEN** 任意合法输入 SQL
- **WHEN** 别名规范化完成后
- **THEN** 输出 SQL 可被 sqlglot 正常解析，且后续 `parse_sql()` 流程不受影响

## Non-Functional Requirements
<!-- Performance, security, scalability, availability requirements -->

## Out of Scope
<!-- Explicitly list what this project will NOT do -->
