"""FR-005: 清洗 SQL 中的参数和变量占位符；FR-008: 别名规范化。"""

from __future__ import annotations

from sqlglot import exp, parse_one
from sqlglot.errors import ErrorLevel
from sqlglot.tokens import TokenType, Tokenizer


def clean_sql(sql: str) -> str:
    """将 SQL 中的 `&XXX` 和 `:XXX` 占位符替换为 `(1 = 1)`，避免干扰解析。

    Args:
        sql: 原始 SQL 字符串。

    Returns:
        清洗后的 SQL 字符串。
    """
    tokens = list(Tokenizer().tokenize(sql))
    result_parts: list[str] = []
    skip_next = False

    for i, token in enumerate(tokens):
        if skip_next:
            skip_next = False
            continue

        if token.token_type == TokenType.AMP:
            # &XXX 或 & XXX — 消费 & 和下一个标识符
            if i + 1 < len(tokens) and tokens[i + 1].token_type == TokenType.VAR:
                skip_next = True
            result_parts.append("(1 = 1)")
        elif token.token_type == TokenType.COLON:
            # :XXX — 消费 : 和下一个标识符
            if i + 1 < len(tokens) and tokens[i + 1].token_type == TokenType.VAR:
                skip_next = True
                result_parts.append("(1 = 1)")
            else:
                result_parts.append(token.text)
        elif token.token_type == TokenType.STRING:
            # 保留字符串引号：token.text 不含引号，需重新包裹
            result_parts.append(f"'{token.text}'")
        else:
            result_parts.append(token.text)

    return " ".join(result_parts).replace("( + )", "(+)")


def normalize_aliases(sql: str) -> str:
    """确保 SQL 中所有表引用都有独一无二的别名。

    无别名的表自动以表名作为别名；别名重复的表追加数字后缀去重。
    基于 AST 遍历和修改，避免误改字符串/注释中的内容。

    Args:
        sql: 待规范化的 SQL 字符串。

    Returns:
        别名规范化后的 SQL 字符串。
    """
    try:
        ast = parse_one(sql, read="oracle", error_level=ErrorLevel.RAISE)
    except Exception:
        return sql

    seen: dict[str, int] = {}

    for node in ast.walk():
        if isinstance(node, exp.Table):
            old_alias = node.alias
            if old_alias:
                if old_alias in seen:
                    seen[old_alias] += 1
                    new_alias = f"{old_alias}_{seen[old_alias]}"
                    node.set(
                        "alias",
                        exp.TableAlias(this=exp.to_identifier(new_alias)),
                    )
                    _propagate_column_alias(node, old_alias, new_alias)
                else:
                    seen[old_alias] = 1
            else:
                name = _table_name_str(node)
                if name in seen:
                    seen[name] += 1
                    alias_name = f"{name}_{seen[name]}"
                else:
                    seen[name] = 1
                    alias_name = name
                node.set(
                    "alias",
                    exp.TableAlias(this=exp.to_identifier(alias_name)),
                )
        elif isinstance(node, exp.Subquery):
            old_alias = node.alias
            if old_alias:
                if old_alias in seen:
                    seen[old_alias] += 1
                    new_alias = f"{old_alias}_{seen[old_alias]}"
                    node.set(
                        "alias",
                        exp.TableAlias(this=exp.to_identifier(new_alias)),
                    )
                    _propagate_column_alias(node, old_alias, new_alias)
                else:
                    seen[old_alias] = 1

    return ast.sql(dialect="oracle")


def _table_name_str(node: exp.Table) -> str:
    """获取 Table 节点的表名（字符串形式）。"""
    name = node.name
    return name if isinstance(name, str) else str(name)


def _propagate_column_alias(
    node: exp.Table | exp.Subquery,
    old_alias: str,
    new_alias: str,
) -> None:
    """将别名重命名传播到相关子句中的 Column 引用。

    对 JOIN ON：仅传播到当前节点所属 JOIN 的 ON 子句。
    对 WHERE/HAVING：传播到所属 SELECT 的 WHERE/HAVING 子句。

    Args:
        node: 别名被重命名的 Table 或 Subquery 节点。
        old_alias: 原始别名。
        new_alias: 新别名。
    """
    select = node.find_ancestor(exp.Select)
    if select is None:
        return

    # 仅处理当前节点所属 JOIN 的 ON 子句
    join = node.find_ancestor(exp.Join)
    if join is not None:
        on_expr = join.args.get("on")
        if on_expr is not None:
            _propagate_in_condition(on_expr, old_alias, new_alias)

    # WHERE 子句
    where = select.args.get("where")
    if where is not None:
        _propagate_in_condition(where.this, old_alias, new_alias)

    # HAVING 子句
    having = select.args.get("having")
    if having is not None:
        _propagate_in_condition(having.this, old_alias, new_alias)


def _propagate_in_condition(
    expr: exp.Expression,
    old_alias: str,
    new_alias: str,
) -> None:
    """递归遍历条件表达式，对比较运算符右侧 Column 进行别名更新。

    Args:
        expr: 条件表达式节点。
        old_alias: 要匹配的旧别名。
        new_alias: 替换后的新别名。
    """
    if isinstance(expr, (exp.And, exp.Or)):
        _propagate_in_condition(expr.this, old_alias, new_alias)
        _propagate_in_condition(expr.expression, old_alias, new_alias)
    elif isinstance(expr, exp.Paren):
        _propagate_in_condition(expr.this, old_alias, new_alias)
    elif isinstance(
        expr,
        (exp.EQ, exp.NEQ, exp.GT, exp.LT, exp.GTE, exp.LTE, exp.Is, exp.NullSafeEQ),
    ):
        _update_columns_in_subtree(expr.expression, old_alias, new_alias)


def _update_columns_in_subtree(
    expr: exp.Expression,
    old_alias: str,
    new_alias: str,
) -> None:
    """更新子树中所有匹配旧别名的 Column 节点。

    Args:
        expr: 表达式子树根节点。
        old_alias: 要匹配的旧别名。
        new_alias: 替换后的新别名。
    """
    for col in expr.find_all(exp.Column):
        t = col.args.get("table")
        if t is not None:
            t_str = t if isinstance(t, str) else str(t)
            if t_str == old_alias:
                col.set("table", exp.to_identifier(new_alias))


if __name__ == "__main__":
    import sys
    from pathlib import Path

    import easygui

    filepath = easygui.fileopenbox(
        title="选择要清洗的 SQL 文件",
        filetypes=[["*.sql", "SQL files"]],
    )
    if filepath is None:
        sys.exit(0)

    with open(filepath, encoding="utf-8") as f:
        sql = f.read()
    cleaned = clean_sql(sql)

    save = easygui.ynbox(
        title="输出结果",
        msg="是否将清洗结果输出到本地文件？",
    )
    if save:
        input_path = Path(filepath)
        output_path = input_path.parent / f"{input_path.stem}_cleaned.sql"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(cleaned)
        easygui.msgbox(
            msg=f"清洗完成，结果已保存至：\n{output_path}",
            title="完成",
        )
    else:
        easygui.msgbox(
            msg=f"清洗完成。\n\n清洗后的 SQL：\n{cleaned[:2000]}",
            title="完成",
        )
