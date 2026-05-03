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
parse_sql(sql) → clean_sql(sql) → parse_one(cleaned, read="oracle")
    → 一次 AST 遍历:
        _extract_tables()      → FR-001
        _extract_columns()     → FR-002
        _extract_joins()       → FR-003
        _extract_hierarchy()   → FR-004
    → 组装 JSON dict           → FR-006
```

---

## Dependencies

- **sqlglot >= 25.0.0** — SQL 解析与 AST 遍历
- **Python 3.12+** — dataclass（slots）、`str | None` 联合类型语法
- **uv** — 虚拟环境与依赖管理
- **pytest + pytest-cov**（dev）— 测试与覆盖率
