# sql_analysis — SQL 批量分析工具

基于 [sqlglot](https://github.com/tobymao/sqlglot) AST 解析的单条 SQL 结构化分析库，提取表引用、字段引用、JOIN 关联关系和查询层次结构。

## 快速开始

```bash
# 环境准备
uv sync

# 解析一条 SQL
uv run python -c "
from sql_analysis import parse_sql
import json
result = parse_sql('SELECT a.id, b.name FROM users a JOIN orders b ON a.id = b.uid')
print(json.dumps(result, indent=2, ensure_ascii=False))
"
```

## 功能

- **表引用提取** — 识别所有表（含 schema、别名），区分基表、派生表、CTE、虚拟表
- **字段引用提取** — 提取 SELECT 列表中所有字段引用，含源表限定符和位置索引
- **关联关系识别** — 识别 JOIN 类型、参与表、连接条件，支持 Oracle `(+)` 语法
- **层次结构识别** — 构建子查询/CTE/UNION 的嵌套层次树
- **参数清洗** — 自动清洗 `&XXX` / `:XXX` 占位符，不影响解析

## 输出格式

```json
{
  "tables":    [{"name": "users", "schema": null, "alias": "a", "table_type": "BASE_TABLE"}],
  "columns":   [{"name": "id", "source_table": "a", "position": 0, "ref_type": "COLUMN"}],
  "joins":     [{"left_table": "users", "right_table": "orders", "join_type": "INNER_JOIN", "conditions": ["a.id = b.uid"]}],
  "hierarchy": {"node_type": "SELECT", "depth": 0, "children": []},
  "error": null
}
```

## 技术栈

- **Python 3.12+**
- **sqlglot >= 25.0.0** — Oracle dialect AST 解析
- **uv** — 包与环境管理
- **pytest + pytest-cov** — 测试与覆盖率

## 运行测试

```bash
uv run pytest                          # 全部测试（38 个）
uv run pytest -k "test_688"            # 按关键字筛选
uv run pytest --cov=sql_analysis --cov-report=term-missing  # 覆盖率
```

## 项目结构

```
sql_analysis/          # 解析库
    models.py          # 数据模型
    cleaner.py         # 参数/变量清洗
    parser.py          # AST 提取 + JSON 组装
tests/                 # 测试
examples/              # 真实 SQL 样本
codespec/              # SDD 规范文档
```

## License

MIT
