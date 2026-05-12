"""FR-001~004: SQL 解析与信息提取，FR-006: JSON 输出编排。"""

from __future__ import annotations

import sys
from pathlib import Path

# 支持 python sql_analysis/parser.py 直接执行
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlglot import exp, parse_one
from sqlglot.errors import ErrorLevel

from sql_analysis.cleaner import clean_sql, normalize_aliases
from sql_analysis.models import (
    ColumnRef,
    ColumnRefType,
    HierarchyNode,
    JoinRef,
    JoinType,
    TableRef,
    TableType,
)

VIRTUAL_TABLES = {"dual", "sys.dual"}

# ── 工具函数 ──────────────────────────────────────────────


def _table_name(node: exp.Table) -> str:
    return node.name if isinstance(node.name, str) else str(node.name)


def _schema_name(node: exp.Table) -> str | None:
    db = node.args.get("db")
    if db is None:
        return None
    return db if isinstance(db, str) else str(db)


def _alias_of(node: exp.Table | exp.Subquery) -> str | None:
    """提取表或子查询的别名，无别名返回 None。"""
    a = node.args.get("alias")
    if a is None:
        return None
    return a.name if hasattr(a, "name") else str(a)


def _col_name(col: exp.Column) -> str:
    return col.name if isinstance(col.name, str) else str(col.name)


def _col_table(col: exp.Column) -> str | None:
    t = col.args.get("table")
    if t is None:
        return None
    return t if isinstance(t, str) else str(t)


def _join_kind_to_enum(kind: str | None) -> JoinType:
    """将 sqlglot 的 join kind 字符串映射到 JoinType 枚举。"""
    if kind is None:
        return JoinType.INNER_JOIN
    kind_upper = kind.upper()
    mapping = {
        "INNER": JoinType.INNER_JOIN,
        "LEFT": JoinType.LEFT_JOIN,
        "RIGHT": JoinType.RIGHT_JOIN,
        "FULL": JoinType.FULL_JOIN,
        "CROSS": JoinType.CROSS_JOIN,
        "IMPLICIT": JoinType.IMPLICIT_JOIN,
    }
    return mapping.get(kind_upper, JoinType.INNER_JOIN)


def _source_info(node: exp.Expression | None) -> tuple[str, str | None]:
    if isinstance(node, exp.Table):
        return _table_name(node), _alias_of(node)
    if isinstance(node, exp.Subquery):
        return "", _alias_of(node)
    return "", None


def _table_lookup(select: exp.Select) -> dict[str, tuple[str, str | None]]:
    lookup: dict[str, tuple[str, str | None]] = {}
    from_expr = select.args.get("from_")
    if from_expr is not None:
        source = from_expr.this if isinstance(from_expr, exp.From) else from_expr
        name, alias = _source_info(source)
        if alias:
            lookup[alias] = (name, alias)
        if name:
            lookup[name] = (name, alias)

    for join_node in select.args.get("joins") or []:
        name, alias = _source_info(join_node.this)
        if alias:
            lookup[alias] = (name, alias)
        if name:
            lookup[name] = (name, alias)

    return lookup


def _first_column_table(expr: exp.Expression | None) -> str | None:
    if expr is None:
        return None
    if isinstance(expr, exp.Column):
        return _col_table(expr)
    column = next(expr.find_all(exp.Column), None)
    return _col_table(column) if column is not None else None


def _comparison_tables(expr: exp.Expression) -> tuple[str | None, str | None] | None:
    if isinstance(expr, exp.Paren):
        return _comparison_tables(expr.this)
    if isinstance(expr, (exp.And, exp.Or)):
        return _comparison_tables(expr.this) or _comparison_tables(expr.expression)
    if isinstance(expr, (exp.EQ, exp.NEQ, exp.GT, exp.LT, exp.GTE, exp.LTE, exp.Is)):
        left_table = _first_column_table(expr.this)
        right_table = _first_column_table(expr.expression)
        if left_table and right_table and left_table != right_table:
            return left_table, right_table
    return None


def _where_join_tables(
    select: exp.Select,
    right_alias: str | None,
) -> tuple[str | None, str | None] | None:
    where = select.args.get("where")
    if where is None:
        return None

    tables = _comparison_tables(where.this)
    if tables is None:
        return None

    left_table, right_table = tables
    if right_alias is None or right_alias == right_table:
        return left_table, right_table
    if right_alias == left_table:
        return right_table, left_table
    return None


# ── FR-001: 表引用提取 ────────────────────────────────────


def _extract_tables_from_select(
    select: exp.Select,
    cte_names: set[str],
    top_level: bool = True,
) -> list[dict]:
    tables: list[dict] = []

    for table in select.find_all(exp.Table):
        if top_level and (
            table.find_ancestor(exp.Subquery)
            or table.find_ancestor(exp.CTE)
        ):
            continue

        name = _table_name(table)
        if name.lower() in VIRTUAL_TABLES:
            continue

        t = TableRef(
            name=name,
            schema=_schema_name(table),
            alias=_alias_of(table),
            table_type=(
                TableType.CTE
                if name.lower() in cte_names
                else TableType.BASE_TABLE
            ),
        )
        tables.append(t.to_dict())

    if top_level:
        for subquery in select.find_all(exp.Subquery):
            inner = subquery.this
            if isinstance(inner, exp.Select):
                nested = _extract_tables_from_select(
                    inner, cte_names, top_level=False
                )
                t = TableRef(
                    name="",
                    alias=_alias_of(subquery),
                    table_type=TableType.DERIVED_TABLE,
                    nested_tables=nested,
                )
                tables.append(t.to_dict())

    return tables


def _extract_tables_from_union(
    union: exp.Union, cte_names: set[str]
) -> list[dict]:
    all_tables: list[dict] = []

    for branch in (union.this, union.expression):
        if isinstance(branch, exp.Select):
            all_tables.extend(_extract_tables_from_select(branch, cte_names))
        elif isinstance(branch, exp.Union):
            all_tables.extend(_extract_tables_from_union(branch, cte_names))

    return all_tables


# ── FR-002: 字段引用提取 ──────────────────────────────────


def _single_from_source(select: exp.Select) -> tuple[str, str] | None:
    """返回当前 SELECT 唯一 FROM 源的类型和别名。"""
    if select.args.get("joins"):
        return None

    from_expr = select.args.get("from_")
    if from_expr is None:
        return None

    source = from_expr.this if isinstance(from_expr, exp.From) else from_expr
    if isinstance(source, exp.Table):
        return ("table", _alias_of(source) or _table_name(source))
    if isinstance(source, exp.Subquery):
        alias = _alias_of(source)
        if alias:
            return ("derived", alias)
    return None


def _extract_columns(select: exp.Select) -> list[dict]:
    """提取当前 SELECT 级别的字段引用，不穿透子查询边界。"""
    columns: list[dict] = []
    select_exprs = select.args.get("expressions")
    if not select_exprs:
        return columns

    from_source = _single_from_source(select)

    for pos, expr in enumerate(select_exprs):
        # 解包 Alias 节点
        inner = expr
        while isinstance(inner, exp.Alias):
            inner = inner.this

        if isinstance(inner, exp.Star):
            star_table = None
            inner_table = inner.args.get("table")
            if inner_table is not None:
                star_table = (
                    inner_table
                    if isinstance(inner_table, str)
                    else str(inner_table)
                )
            elif from_source is not None and from_source[0] == "table":
                star_table = from_source[1]
            columns.append(
                ColumnRef(
                    name="*",
                    star_table=star_table,
                    position=pos,
                    ref_type=ColumnRefType.STAR,
                ).to_dict()
            )
        elif isinstance(inner, exp.Column):
            source = _col_table(inner)
            if source is None and from_source is not None and from_source[0] == "derived":
                source = from_source[1]
            source = source or "UNKNOWN"
            columns.append(
                ColumnRef(
                    name=_col_name(inner),
                    source_table=source,
                    position=pos,
                    ref_type=ColumnRefType.COLUMN,
                ).to_dict()
            )
        else:
            # 从表达式中提取内嵌的列引用（如 sum(t.tc_amount) 中的 t.tc_amount）
            inner_cols = list(inner.find_all(exp.Column))
            if inner_cols:
                for col in inner_cols:
                    source = _col_table(col) or "UNKNOWN"
                    columns.append(
                        ColumnRef(
                            name=_col_name(col),
                            source_table=source,
                            position=pos,
                            ref_type=ColumnRefType.COLUMN,
                        ).to_dict()
                    )
            else:
                alias_name = ""
                outer = expr
                if isinstance(outer, exp.Alias):
                    a = outer.args.get("alias")
                    if a is not None:
                        alias_name = a if isinstance(a, str) else str(a)
                columns.append(
                    ColumnRef(
                        name=alias_name,
                        position=pos,
                        ref_type=ColumnRefType.COLUMN,
                    ).to_dict()
                )

    return columns


def _extract_columns_recursive(
    node: exp.Expression,
) -> list[dict]:
    """递归提取所有层级的字段引用（每个 SELECT 一层）。"""
    columns: list[dict] = []

    if isinstance(node, exp.Select):
        columns.extend(_extract_columns(node))

    for child in node.walk():
        if child is node:
            continue
        if isinstance(child, exp.Select):
            columns.extend(_extract_columns(child))

    return columns


# ── FR-003: 关联关系识别 ──────────────────────────────────


def _extract_joins(select: exp.Select) -> list[dict]:
    joins: list[dict] = []
    lookup = _table_lookup(select)

    # 显式 JOIN
    for join_node in select.find_all(exp.Join):
        kind = join_node.args.get("kind")
        side = join_node.args.get("side")
        on_expr = join_node.args.get("on")
        # sqlglot 对 LEFT/RIGHT/FULL JOIN 使用 side 属性，kind 为 None
        if side is not None:
            side_str = side if isinstance(side, str) else str(side)
            join_type = _join_kind_to_enum(side_str.upper())
        elif kind is not None:
            kind_str = kind if isinstance(kind, str) else str(kind)
            join_type = _join_kind_to_enum(kind_str.upper())
        elif on_expr is None:
            join_type = JoinType.IMPLICIT_JOIN
        else:
            join_type = JoinType.INNER_JOIN

        # 提取右表信息
        right_expr = join_node.this
        right_name, right_alias = _source_info(right_expr)

        left_name = ""
        left_alias = None

        condition_tables = _comparison_tables(on_expr) if on_expr is not None else None
        if condition_tables is None and join_type == JoinType.IMPLICIT_JOIN:
            condition_tables = _where_join_tables(select, right_alias or right_name)

        if condition_tables is not None:
            left_key, right_key = condition_tables
            if right_key == (right_alias or right_name):
                left_name, left_alias = lookup.get(left_key or "", (left_key or "", left_key))
            elif left_key == (right_alias or right_name):
                left_name, left_alias = lookup.get(right_key or "", (right_key or "", right_key))

        if not left_name:
            from_expr = select.args.get("from_")
            if from_expr is not None:
                from_table = from_expr.this if isinstance(from_expr, exp.From) else from_expr
                left_name, left_alias = _source_info(from_table)

        condition = None
        conditions: list[str] = []
        if on_expr is not None:
            condition = on_expr.sql(dialect="oracle")
            conditions = _split_conditions(on_expr)
        elif join_type == JoinType.IMPLICIT_JOIN and select.args.get("where") is not None:
            where_expr = select.args["where"].this
            condition = where_expr.sql(dialect="oracle")
            conditions = _split_conditions(where_expr)

        joins.append(
            JoinRef(
                left_table=left_name,
                left_alias=left_alias,
                right_table=right_name,
                right_alias=right_alias,
                join_type=join_type,
                condition=condition,
                conditions=conditions,
            ).to_dict()
        )

    # 兼容 sqlglot 未把逗号来源暴露为 Join 节点的情况。
    if not joins:
        from_expr = select.args.get("from_")
        if from_expr is not None:
            from_table = from_expr.this if isinstance(from_expr, exp.From) else from_expr
            if isinstance(from_table, exp.Table):
                tables_in_from = [from_table]
                # 检查是否有逗号分隔的额外表
                joins_list = from_table.args.get("joins")
                if joins_list:
                    for j in joins_list:
                        if isinstance(j, exp.Join) and not j.args.get("on"):
                            right_table = j.this
                            if isinstance(right_table, exp.Table):
                                tables_in_from.append(right_table)

                if len(tables_in_from) > 1:
                    for i in range(len(tables_in_from) - 1):
                        left = tables_in_from[i]
                        right = tables_in_from[i + 1]
                        joins.append(
                            JoinRef(
                                left_table=_table_name(left),
                                left_alias=_alias_of(left),
                                right_table=_table_name(right),
                                right_alias=_alias_of(right),
                                join_type=JoinType.IMPLICIT_JOIN,
                            ).to_dict()
                        )

    return joins


def _split_conditions(on_expr: exp.Expression) -> list[str]:
    """将 AND 连接的复合 ON 条件拆分为独立条件列表。"""
    if isinstance(on_expr, exp.Paren):
        return _split_conditions(on_expr.this)
    if isinstance(on_expr, exp.And):
        left_conds = _split_conditions(on_expr.this)
        right_conds = _split_conditions(on_expr.expression)
        return left_conds + right_conds
    return [on_expr.sql(dialect="oracle")]


# ── FR-004: 层次结构识别 ──────────────────────────────────


def _extract_hierarchy(
    node: exp.Expression,
    cte_defs: dict[str, exp.Select],
    depth: int = 0,
) -> dict:
    """递归构建查询层次结构树。"""
    if isinstance(node, exp.Select):
        current = HierarchyNode(
            node_type="SELECT",
            depth=depth,
        )

        # 从 FROM 提取子查询作为子节点
        from_expr = node.args.get("from_")
        if from_expr is not None:
            root = from_expr.this if isinstance(from_expr, exp.From) else from_expr
            current.children = _find_child_selects(root, cte_defs, depth + 1)

        # 从 JOIN 提取子查询
        for join_node in node.find_all(exp.Join):
            if isinstance(join_node.this, exp.Subquery):
                inner = join_node.this.this
                if isinstance(inner, exp.Select):
                    current.children.append(
                        _extract_hierarchy(inner, cte_defs, depth + 1)
                    )

        # 添加 CTE 定义
        with_expr = node.args.get("with_")
        cte_nodes = with_expr.expressions if with_expr is not None else None
        if cte_nodes:
            for cte in cte_nodes:
                inner = cte.this
                if isinstance(inner, exp.Select):
                    cte_name = cte.alias if isinstance(cte.alias, str) else str(cte.alias)
                    cte_child = HierarchyNode(
                        node_type="CTE_DEF",
                        name=cte_name,
                        depth=0,
                        children=[_extract_hierarchy(inner, cte_defs, 1)],
                    )
                    current.children.append(cte_child.to_dict())

        return current.to_dict()

    if isinstance(node, exp.Union):
        union_node = HierarchyNode(node_type="UNION", depth=depth)
        left_child = _extract_hierarchy(node.this, cte_defs, depth + 1)
        right_child = _extract_hierarchy(node.expression, cte_defs, depth + 1)
        union_node.children = [left_child, right_child]
        return union_node.to_dict()

    return HierarchyNode(node_type="UNKNOWN", depth=depth).to_dict()


def _find_child_selects(
    source: exp.Expression,
    cte_defs: dict[str, exp.Select],
    depth: int,
) -> list[dict]:
    """从 FROM 源中查找子查询并递归处理。"""
    children: list[dict] = []
    if isinstance(source, exp.Subquery):
        inner = source.this
        if isinstance(inner, (exp.Select, exp.Union)):
            children.append(_extract_hierarchy(inner, cte_defs, depth))

    # 遍历 JOIN 链
    if isinstance(source, exp.Table):
        for join_node in source.args.get("joins") or []:
            if isinstance(join_node, exp.Join) and isinstance(
                join_node.this, exp.Subquery
            ):
                inner = join_node.this.this
                if isinstance(inner, (exp.Select, exp.Union)):
                    children.append(_extract_hierarchy(inner, cte_defs, depth))

    return children


# ── 收集 CTE 定义 ─────────────────────────────────────────


def _collect_cte_defs(ast: exp.Expression) -> dict[str, exp.Select]:
    """从 AST 收集所有 CTE 名称到其定义 SELECT 的映射。"""
    cte_defs: dict[str, exp.Select] = {}
    for cte in ast.find_all(exp.CTE):
        name = cte.alias if isinstance(cte.alias, str) else str(cte.alias)
        inner = cte.this
        if isinstance(inner, exp.Select):
            cte_defs[name.lower()] = inner
    return cte_defs


# ── FR-005~006: 主解析入口 ────────────────────────────────


def parse_sql(sql: str) -> dict:
    """解析单条 SQL，返回结构化的表、字段、关联关系和层次结构信息。

    Args:
        sql: 待解析的 SQL 字符串。

    Returns:
        包含 tables、columns、joins、hierarchy、error 字段的字典。
    """
    # FR-005: 清洗参数/变量占位符
    cleaned = clean_sql(sql)

    # FR-008: 别名规范化
    normalized = normalize_aliases(cleaned)

    # 解析 SQL
    try:
        ast = parse_one(normalized, read="oracle", error_level=ErrorLevel.RAISE)
    except Exception as exc:
        return {
            "tables": None,
            "columns": None,
            "joins": None,
            "hierarchy": None,
            "error": str(exc),
        }

    # 收集 CTE 定义
    cte_defs = _collect_cte_defs(ast)
    cte_names = set(cte_defs.keys())

    # FR-001: 提取表引用
    if isinstance(ast, exp.Select):
        tables = _extract_tables_from_select(ast, cte_names)
    elif isinstance(ast, exp.Union):
        tables = _extract_tables_from_union(ast, cte_names)
    else:
        tables = []

    # 为 CTE 引用填充 nested_tables
    for t in tables:
        if t["table_type"] == "CTE" and t["name"].lower() in cte_defs:
            inner_select = cte_defs[t["name"].lower()]
            t["nested_tables"] = _extract_tables_from_select(
                inner_select, cte_names, top_level=False
            )

    # FR-002: 提取字段引用
    columns = _extract_columns_recursive(ast)

    # FR-003: 提取关联关系
    joins: list[dict] = []
    if isinstance(ast, exp.Select):
        joins = _extract_joins(ast)

    # FR-004: 提取层次结构
    hierarchy = _extract_hierarchy(ast, cte_defs)

    # FR-006: 组装输出
    return {
        "tables": tables,
        "columns": columns,
        "joins": joins,
        "hierarchy": hierarchy,
        "error": None,
    }


if __name__ == "__main__":
    import json

    import easygui

    filepath = easygui.fileopenbox(
        title="选择要解析的 SQL 文件",
        filetypes=[["*.sql", "SQL files"]],
    )
    if filepath is None:
        sys.exit(0)

    with open(filepath, encoding="utf-8") as f:
        sql = f.read()
    result = parse_sql(sql)

    save = easygui.ynbox(
        title="输出结果",
        msg="是否将解析结果输出到本地文件？",
    )
    output_json = json.dumps(result, indent=2, ensure_ascii=False)
    if save:
        input_path = Path(filepath)
        output_path = input_path.parent / f"{input_path.stem}_parsed.json"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_json)
        easygui.msgbox(
            msg=f"解析完成，结果已保存至：\n{output_path}",
            title="完成",
        )
    else:
        easygui.msgbox(
            msg=f"解析完成。\n\n解析结果：\n{output_json[:2000]}",
            title="完成",
        )
