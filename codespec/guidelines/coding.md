# Coding Guidelines

## 技术栈

- **语言**: Python 3.12+
- **虚拟环境管理**: [uv](https://docs.astral.sh/uv/)
- **SQL 解析**: [sqlglot](https://github.com/tobymao/sqlglot) 作为解析 SQL AST 的主要途径

### 环境初始化

```bash
uv venv
uv sync
```

## Naming Conventions
- Variables and functions: snake_case
- Classes: PascalCase
- Constants: UPPER_SNAKE_CASE
- Files: snake_case

## Code Style
- Maximum line length: 100 characters
- Use type annotations on all public functions and methods
- No commented-out code in commits

## Comments (Google Docstring Format)
- Document the "why", not the "what"
- Public functions/classes 使用 Google 风格 docstring：

```python
def parse_sql(query: str) -> dict:
    """解析单条 SQL 并返回结构化的表、字段、关联关系等信息。

    Args:
        query: 待解析的 SQL 字符串。

    Returns:
        包含 tables、columns、joins、hierarchy 等字段的字典。

    Raises:
        ParseError: SQL 语法无法解析时抛出。
    """
    ...
```

## Error Handling
- Always handle errors explicitly — no silent failures
- Log errors with context (not just the exception message)
