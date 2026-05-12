# Technical Design

## Architecture Overview

```
sql_analysis/
    __init__.py          # 公开 API： parse_sql() + 关键类型
    models.py            # 数据模型（dataclass + Enum），无业务逻辑
    cleaner.py           # FR-005：参数/变量占位符清洗
    parser.py            # FR-001~004 提取逻辑 + FR-006 JSON 组装

tests/
    __init__.py
    conftest.py          # 共享 fixtures（688.sql, union.sql 等）
    test_cleaner.py      # FR-005 测试
    test_parser.py       # FR-001~004 & FR-006 测试
```

`cleaner.py` 和 `parser.py` 各自独立，`parser.py` 的 `parse_sql()` 编排调用流程：
先清洗 → 再解析 → 一次 AST 遍历提取四类信息 → 组装 JSON。

`models.py` 定义所有结构体，被其他模块引用，本身无业务逻辑。

---

## Key Design Decisions

### Decision 1: sqlglot 作为解析引擎
**Choice**: `sqlglot.parse_one(sql, read="oracle")`
**Rationale**: sqlglot 提供完整的 AST 遍历 API（`find_all(exp.Table)`、`find_all(exp.Column)`、`find_all(exp.Join)` 等），原生支持 Oracle `(+)` 语法、`dual` 虚拟表、无 FROM 子句的 SQL。无需自行实现 SQL 解析器。
**Implications**: 所有提取逻辑基于 AST 遍历，不写 SQL 字符串解析代码。

### Decision 2: Tokenizer 做参数清洗，不用正则
**Choice**: `clean_sql()` 使用 sqlglot 的 tokenizer 分词后识别 `&XXX` 和 `:XXX` token
**Rationale**: 正则无法区分字符串字面量内的 `:var` 和真正的绑定变量。Tokenizer 已标记 token 类型，可安全跳过字符串和注释中的内容。
**Implications**: cleaner 依赖 sqlglot tokenizer，无额外运行时成本。

### Decision 3: 多次独立 `find_all()` 遍历
**Choice**: 四个提取器各自独立遍历 AST，通过不同机制维护作用域：
- 表提取：`find_all(exp.Table)` + `find_ancestor()` 过滤 + `top_level` 参数控制子查询穿透
- 字段提取：`node.walk()` 找所有 SELECT，每个 SELECT 独立提取，天然不穿透
- JOIN 提取：`find_all(exp.Join)`，仅对顶层 SELECT 调用
- 层次结构：自己递归遍历，`depth` 参数传递嵌套深度
**Rationale**: 实践中 `find_all()` + 祖先过滤／递归参数能正确维护作用域和深度上下文。多次独立遍历比单次遍历更简单，每个提取器职责清晰互不干扰。
**Implications**: 代码结构简单，修改一个提取器不影响其他提取器。性能差异对常规 SQL 可忽略。

### Decision 4: dataclass 内部表示 + dict JSON 输出
**Choice**: 内部使用 dataclass（类型安全、IDE 补全），`to_dict()` 序列化为 dict，`parse_sql()` 返回 plain dict
**Rationale**: 开发时有类型检查，对外 API 简单，不引入 Pydantic 等额外依赖。
**Implications**: 每个 dataclass 需维护 `to_dict()` 方法。

### Decision 5: 虚拟表白名单
**Choice**: 维护 `{"dual", "sys.dual"}` 集合，匹配的表标记为 VIRTUAL_TABLE 并排除
**Rationale**: 虚拟表是有限集合，白名单简单直接。
**Implications**: 新增虚拟表需编辑此集合。

---

## Data Model

```
TableType: BASE_TABLE | DERIVED_TABLE | CTE | VIRTUAL_TABLE
JoinType:  INNER_JOIN | LEFT_JOIN | RIGHT_JOIN | FULL_JOIN | CROSS_JOIN | IMPLICIT_JOIN
ColumnRefType: COLUMN | STAR

TableRef:      name, schema?, alias?, table_type, nested_tables[]
ColumnRef:     name, source_table?, position, ref_type, star_table?
JoinRef:       left_table, left_alias?, right_table, right_alias?, join_type, condition?, conditions[]
HierarchyNode: node_type, name?, depth, children[]

ParseResult: tables[], columns[], joins[], hierarchy{}, error?
```

---

## Parse Flow

```
parse_sql(sql) → clean_sql(sql) → normalize_aliases(cleaned) → parse_one(normalized, read="oracle")
    → 一次 AST 遍历:
        _extract_tables()      → FR-001
        _extract_columns()     → FR-002
        _extract_joins()       → FR-003
        _extract_hierarchy()   → FR-004
    → 组装 JSON dict           → FR-006
```

---

### Decision 6: easygui 做 GUI 入口，不引入 Web 框架
**Choice**: 使用 easygui 提供文件选择对话框和确认对话框，在 cleaner.py 和 parser.py 末尾追加 `if __name__ == '__main__'` 块
**Rationale**: easygui 是纯 Python 的轻量 GUI 库，无需浏览器、无 Web 服务、无复杂框架依赖。`fileopenbox()` 选择文件、`ynbox()` 确认输出，API 简单直接。`__main__` 块仅在使用 `python xxx.py` 时触发，不改变模块被 import 时的行为。
**Implications**: 新增 easygui 依赖；`__main__` 块代码不参与单元测试（仅 GUI 触发），不影响现有 38 个测试。

### Decision 7: 输出文件与输入文件同目录
**Choice**: 输出文件默认保存在输入 SQL 文件所在目录，无需用户额外指定路径
**Rationale**: 简化交互流程，减少用户操作步骤（少一个路径选择框）。用户只需确认是否输出，不需要选择输出位置。
**Implications**: 输出文件名规范为 `<原文件名>_cleaned.sql`（cleaner）和 `<原文件名>_parsed.json`（parser）。

### Decision 8: `normalize_aliases()` 作为独立函数
**Choice**: 在 `cleaner.py` 中新增 `normalize_aliases(sql: str) -> str` 函数，基于 sqlglot AST 遍历修改表别名，返回规范化后的 SQL 字符串。
**Rationale**: 与现有 `clean_sql()` 职责分离（清洗占位符 vs 规范化别名），各自独立可测试。`normalize_aliases()` 需要 AST 级别的信息（表名、别名、作用域），不适合 tokenizer 方案。
**Implications**: `cleaner.py` 新增 sqlglot `parse_one` / `exp` 相关导入；`parse_sql()` 调用链变为 `clean_sql()` → `normalize_aliases()` → `parse_one()`。

### Decision 9: 别名生成策略
**Choice**: 无别名时以表名自身作为别名；别名重复时追加数字后缀 `_2`、`_3`...（第一个保留原名）。
**Rationale**: 表名作为别名语义清晰，便于人工阅读；数字后缀简单直接，不会与现有别名冲突。
**Implications**: 别名冲突检测需维护已见别名集合，按表在 SQL 中出现的顺序分配。

### Decision 10: AST 改写方式
**Choice**: 遍历 `exp.Table` 和 `exp.Subquery` 节点，对需要修改别名的节点设置 `alias` 属性，通过 `ast.sql(dialect="oracle")` 输出修改后的 SQL。
**Rationale**: 直接修改 AST 对象比字符串替换更安全，避免误改注释/字符串中的内容。
**Implications**: 需注意 `exp.Subquery` 的别名设置方式可能与 `exp.Table` 不同。CTE 引用也需作为表引用参与别名检测。

### Decision 11: ON/WHERE/HAVING Column 别名传播启发式
**Choice**: 当表别名被重命名时，沿 AST 向上找到所属 SELECT 节点，遍历其 WHERE、HAVING 及所有 JOIN 的 ON 子句中的比较表达式（`=`、`<`、`>`、`!=`、`IS` 等）。将右侧子树中 `table` 匹配旧别名的 Column 更新为新别名。基于 `左表.列 = 右表.列` 约定。
**Rationale**: parser 从 ON、WHERE、HAVING 等子句中提取 Column 引用。比较表达式的左右结构是唯一能在无 schema 情况下确定 Column 归属的 AST 特征。右侧 Column 归属右表（被重命名的表）。
**Implications**: 新增 `_propagate_column_alias()`、`_propagate_in_condition()`、`_update_columns_in_subtree()` 三个内部函数。SELECT 列表中单独的 Column（如 `u.id`）无法消歧义，保留原样。CROSS JOIN 跳过。

### Decision 12: SELECT 作用域内的字段来源推断
**Choice**: 对当前 SELECT 构建轻量 FROM 源上下文。单一基表时，`SELECT *` 的 `star_table` 使用该表别名；单一派生表时，外层未限定字段的 `source_table` 使用派生表别名；多源或无法消歧时仍返回 `UNKNOWN`。
**Rationale**: 只实现 spec 明确要求的可判定场景，避免引入复杂血缘推断。
**Implications**: 不穿透派生表内部字段来源，保持跨子查询边界。

### Decision 13: JOIN 关系按实际 ON/WHERE 条件推导左右表
**Choice**: 显式链式 JOIN 中，右表来自当前 `exp.Join.this`；左表优先从当前 ON 条件左侧限定符推导，无法推导时退回到上一张已知表。WHERE 隐式关联从 WHERE 比较表达式中提取左右限定符，并生成 `IMPLICIT_JOIN`。
**Rationale**: sqlglot AST 中链式 JOIN 不总能通过顶层 FROM 根表表达每条关系的左表，ON/WHERE 条件是更贴近 spec 的来源。
**Implications**: CROSS JOIN 无 ON 条件时仍使用 FROM 顺序；WHERE 中非表间比较不生成隐式关联。

### Decision 14: CTE hierarchy 节点挂载在查询层次根上
**Choice**: 在构建 hierarchy 时从 AST 收集 CTE 定义，将每个 CTE 表示为 `CTE_DEF` 节点，并作为根查询的子节点之一，同时保留主查询节点本身。
**Rationale**: 满足 FR-004 对 CTE 定义节点与主查询引用的可见性要求。
**Implications**: 不改变 tables 中 CTE 的 `nested_tables` 逻辑。

### Decision 15: 预定义 JSON Schema 用于输出合同验证
**Choice**: 在测试中维护 parse result 的 JSON Schema，并覆盖成功输出和错误输出。生产 `parse_sql()` 仍返回 plain dict，不引入运行时 schema 校验依赖。
**Rationale**: FR-006 要求输出可校验，而不是每次解析必须执行校验；测试级 schema 能证明输出合同稳定，同时避免新增运行时依赖。
**Implications**: 若未来公开 schema 给外部调用方，可将测试 schema 提升为包内资源文件。

---

## Dependencies

- **sqlglot >= 25.0.0** — SQL 解析与 AST 遍历
- **easygui >= 0.98** — GUI 文件选择与确认对话框
- **Python 3.12+** — dataclass（slots）、`str | None` 联合类型语法
- **uv** — 虚拟环境与依赖管理
- **pytest + pytest-cov**（dev）— 测试与覆盖率
