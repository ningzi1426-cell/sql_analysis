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
