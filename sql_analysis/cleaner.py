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
        else:
            result_parts.append(token.text)

    return " ".join(result_parts)
