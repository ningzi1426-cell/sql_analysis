"""FR-005: 清洗 SQL 中的参数和变量占位符。"""

from __future__ import annotations

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

    return " ".join(result_parts)


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
