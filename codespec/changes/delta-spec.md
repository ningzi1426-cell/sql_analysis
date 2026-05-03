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
