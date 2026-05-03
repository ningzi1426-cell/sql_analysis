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
