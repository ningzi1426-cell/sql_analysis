"""SQL 批量分析工具 — 单条 SQL 解析模块。"""

__version__ = "0.1.0"

from sql_analysis.cleaner import normalize_aliases
from sql_analysis.models import (
    ColumnRef,
    ColumnRefType,
    HierarchyNode,
    JoinRef,
    JoinType,
    TableRef,
    TableType,
)
from sql_analysis.parser import parse_sql

__all__ = [
    "ColumnRef",
    "ColumnRefType",
    "HierarchyNode",
    "JoinRef",
    "JoinType",
    "TableRef",
    "TableType",
    "normalize_aliases",
    "parse_sql",
]
