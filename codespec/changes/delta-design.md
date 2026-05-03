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
