# spec.md 变更日志

<!-- This file is append-only. Each change adds a new ## section. Do not edit or delete existing sections. -->

## 2026-05-02 单条 SQL 解析功能

### 变更摘要
新增 SQL 批量分析工具第一部分（单条 SQL 解析）的完整需求规格，覆盖 6 个功能需求（FR-001 ~ FR-006）共 24 个验收场景。

### 对 spec.md 的变更
- **新建文件**：`codespec/specs/spec.md`
- **项目概述**：定义项目为 SQL 批量分析工具，包含单条 SQL 解析和相似度聚类两部分功能。
- **FR-001 提取表引用**：7 个 Scenario，覆盖简单单表、schema 前缀、同表多别名、派生表、CTE、无 FROM 子句、虚拟表过滤、解析失败处理。
- **FR-002 提取字段引用**：4 个 Scenario，覆盖非限定字段、限定字段、跨子查询边界、通配符 *。
- **FR-003 识别 JOIN 关联关系**：6 个 Scenario，覆盖 INNER JOIN、LEFT JOIN 复合条件、ON 括号、CROSS JOIN、嵌套 JOIN 顺序、隐式连接 + Oracle (+) 语法。
- **FR-004 识别层次结构**：5 个 Scenario，覆盖无嵌套、单层子查询、CTE、三层嵌套、UNION 并列分支。
- **FR-005 清洗参数和变量占位符**：2 个 Scenario，覆盖 &XXX 参数和 :XXX 变量的识别与替换。
- **FR-006 输出结构化 JSON**：3 个 Scenario，覆盖常规查询输出、解析失败输出、JSON Schema 校验。

## 2026-05-03 增加 GUI 直接执行入口

### 变更摘要
新增 FR-007：GUI 直接执行入口，允许用户通过 `python sql_analysis/cleaner.py` 或 `python sql_analysis/parser.py` 启动 easygui 图形界面，选择 SQL 文件进行处理，无需浏览器或复杂框架。

### 对 spec.md 的变更
- **新增 FR-007: GUI 直接执行入口**：用户可直接运行 cleaner.py 或 parser.py 启动图形界面。
- **入口支持**：`python sql_analysis/cleaner.py`、`python sql_analysis/parser.py`、`python -m sql_analysis.cleaner`、`python -m sql_analysis.parser` 四种方式均可用。
- **交互流程**：弹出 easygui 文件选择对话框让用户选择 SQL 文件 → 弹出确认对话框询问是否将结果输出到本地文件 → cleaner.py 输出清洗后的 SQL 文件，parser.py 输出结构化 JSON 文件。
- **输出位置**：输出文件默认保存在输入 SQL 文件所在目录。
- **新增依赖**：easygui 作为可选依赖加入 pyproject.toml。
- **变更边界**：仅涉及 GUI 启动入口，不修改现有函数逻辑，不引入 Web 框架。

## 2026-05-10 cleaner 别名规范化

### 变更摘要
新增 FR-008：别名规范化。在解析前对 SQL 进行预处理，确保所有表引用都有独一无二的别名，使后续分析流程能从别名唯一还原到 schema 和表名。

### 对 spec.md 的变更
- **新增 FR-008: 别名规范化**：When SQL 语句被清洗后、解析前, the system shall normalize table aliases to ensure every table reference has a unique alias.
  - **Scenario: 无别名的表自动获得别名** — GIVEN SQL 为 `SELECT id FROM users` / WHEN 调用别名规范化 / THEN `users` 获得别名 `users`，输出 SQL 中 `FROM users` 变为 `FROM users AS users`
  - **Scenario: 别名重复的表自动去重** — GIVEN SQL 为 `SELECT * FROM users u JOIN orders u ON u.id = u.uid` / WHEN 调用别名规范化 / THEN 第二个别名 `u` 被重命名为 `u_2`（或等价唯一后缀），字段引用中的别名同步更新
  - **Scenario: 同一张物理表多次引用时别名保持唯一** — GIVEN SQL 为 `SELECT pr.prod_code, pr2.prod_code FROM dwrdim.dwr_dim_product_d pr LEFT JOIN dwrdim.dwr_dim_product_d pr2 ON pr.parent_key = pr2.prod_key` / WHEN 调用别名规范化 / THEN 两个表引用的别名 `pr` 和 `pr2` 均保持原样不冲突，无需修改
  - **Scenario: 包含子查询的表别名处理** — GIVEN SQL 为 `SELECT a.id, b.total FROM users a JOIN (SELECT user_id FROM orders) b ON a.id = b.user_id` / WHEN 调用别名规范化 / THEN 派生表别名 `b` 不变，`users` 别名 `a` 不变
  - **Scenario: 包含 CTE 的表别名处理** — GIVEN SQL 为 `WITH active AS (SELECT id FROM users) SELECT * FROM active` / WHEN 调用别名规范化 / THEN CTE 名称 `active` 在引用处作为别名保留，CTE 内部 `users` 无别名时自动获得别名 `users`
  - **Scenario: 混合场景（部分有别名、部分无别名、部分重复）** — GIVEN SQL 为 `SELECT * FROM users a JOIN orders a JOIN products ON a.id = products.id` / WHEN 调用别名规范化 / THEN `users` 保留别名 `a`，`orders` 的重复别名 `a` 被重命名为 `a_2`，`products` 获得别名 `products`
  - **Scenario: 规范化后 SQL 仍可正常解析** — GIVEN 任意合法输入 SQL / WHEN 别名规范化完成后 / THEN 输出 SQL 可被 sqlglot 正常解析，且后续 `parse_sql()` 流程不受影响

## 2026-05-10 Column 别名传播修复

### 变更摘要
修复 FR-008 中 `normalize_aliases()` 的缺陷：当表别名被重命名时，同步更新 ON / WHERE 子句中所有**可确定归属**的 Column 的 `table` 属性。采用比较表达式右式约定启发式（比较运算符右侧 Column 归属被重命名的表）。覆盖场景：显式 JOIN ON、隐式关联 WHERE、复合条件、括号、表达式子树。

### 对 spec.md 的变更
- **修改 FR-008 Scenario: 别名重复的表自动去重**：THEN 子句增强为「第二个别名 `u` 被重命名为 `u_2`，且所有比较表达式中引用该表的字段前缀同步更新为 `u_2`」
- **新增 Scenario: ON 条件中字段引用同步更新** — GIVEN `SELECT u.id FROM users u JOIN orders u ON u.id = u.uid` / WHEN 调用别名规范化 / THEN `u.uid` → `u_2.uid`，`u.id`（左侧）不变
- **新增 Scenario: WHERE 隐式关联中字段引用同步更新** — GIVEN `SELECT * FROM t1 u, t2 u WHERE u.a = u.b` / WHEN 调用别名规范化 / THEN `u.b` → `u_2.b`，`u.a` 不变
- **新增 Scenario: 复合条件和括号正确处理** — GIVEN ON/WHERE 含 AND/OR/括号 / WHEN 调用别名规范化 / THEN 递归处理所有比较表达式
