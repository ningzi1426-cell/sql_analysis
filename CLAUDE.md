# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用命令

```bash
# 环境准备
uv sync                                # 安装依赖

# 测试
uv run pytest                          # 运行全部测试
uv run pytest -v                       # 详细输出
uv run pytest tests/test_parser.py     # 单个测试文件
uv run pytest -k "test_688"            # 按关键字筛选测试
uv run pytest --cov=sql_analysis --cov-report=term-missing  # 覆盖率报告

# Git
git status && git diff                 # 查看变更
git add -A && git commit -m "..."      # 提交
git push origin master                 # 推送到 GitHub
```

## 架构

```
sql_analysis/          # 单条 SQL 解析库
    models.py          # dataclass + Enum 数据模型，to_dict() 序列化，无业务逻辑
    cleaner.py         # FR-005: 在解析前清洗 &XXX / :XXX 占位符（tokenizer 方案，非正则）
    parser.py          # FR-001~004: AST 提取 + FR-006: 组装，唯一公共入口 parse_sql()
    __init__.py         # 导出: parse_sql + ColumnRef, TableRef, JoinRef, HierarchyNode 等
tests/
    conftest.py         # sql_688, sql_union 等真实 SQL fixtures
    test_cleaner.py     # 9 个测试
    test_parser.py      # 29 个测试
examples/               # 真实业务 SQL 样本
codespec/               # SDD 规范文件，权限最高，优先阅读
```

## parse_sql() 处理流程

```
SQL 输入 → clean_sql() 清洗占位符 → parse_one(oracle) → AST
  → _extract_tables()      → 表引用 [TableRef]
  → _extract_columns()     → 字段引用 [ColumnRef]
  → _extract_joins()       → 关联关系 [JoinRef]
  → _extract_hierarchy()   → 层次树 HierarchyNode
  → 组装 {tables, columns, joins, hierarchy, error}
```

- 返回 dict，错误时所有数据字段为 null，error 字段含错误信息
- 虚拟表 `dual` / `sys.dual` 自动过滤
- CTE 引用自动填充 `nested_tables`
- 函数内嵌字段会被提取（如 `sum(t.amount)` → `name='amount' source_table='t'`）
- ON 复合条件自动拆分为独立条件列表，括号内条件也会拆解

## 技术要点

- **Python 3.12+**, 包/环境管理用 **uv**
- 依赖: `sqlglot>=25.0.0`，Oracle dialect，所有解析基于 AST 遍历
- 内部用 dataclass 保证类型安全，`to_dict()` 输出 plain dict（可 json.dumps）
- 内部函数以下划线前缀标记（如 `_table_name`），不可直接调用
- 表引用类型枚举: BASE_TABLE | DERIVED_TABLE | CTE | VIRTUAL_TABLE
- JOIN 类型枚举: INNER_JOIN | LEFT_JOIN | RIGHT_JOIN | FULL_JOIN | CROSS_JOIN | IMPLICIT_JOIN

---

## SDD Workflow

This project uses Spec Driven Development.

### Project Knowledge (read before writing any code)

- `codespec/specs/spec.md` — Requirements and acceptance criteria
- `codespec/specs/design.md` — Architecture and design decisions
- `codespec/specs/tasks.md` — Current work breakdown
- `codespec/guidelines/` — Coding standards, rules, and test requirements

### Change Flow (use for any new feature or modification)

Use `/sdd change` to start a structured change. Do not write code before specs are updated.

Current change status: `codespec/changes/.status`

### Review

Use `/sdd review` to run compliance checks. Add project-specific reviewers in `codespec/reviewers/`.
