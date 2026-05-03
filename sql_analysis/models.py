"""SQL 解析结果的数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TableType(Enum):
    """表引用类型。"""

    BASE_TABLE = "BASE_TABLE"
    DERIVED_TABLE = "DERIVED_TABLE"
    CTE = "CTE"
    VIRTUAL_TABLE = "VIRTUAL_TABLE"


class JoinType(Enum):
    """JOIN 类型。"""

    INNER_JOIN = "INNER_JOIN"
    LEFT_JOIN = "LEFT_JOIN"
    RIGHT_JOIN = "RIGHT_JOIN"
    FULL_JOIN = "FULL_JOIN"
    CROSS_JOIN = "CROSS_JOIN"
    IMPLICIT_JOIN = "IMPLICIT_JOIN"


class ColumnRefType(Enum):
    """字段引用类型。"""

    COLUMN = "COLUMN"
    STAR = "STAR"


@dataclass
class TableRef:
    """表引用。"""

    name: str
    schema: str | None = None
    alias: str | None = None
    table_type: TableType = TableType.BASE_TABLE
    nested_tables: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "schema": self.schema,
            "alias": self.alias,
            "table_type": self.table_type.value,
            "nested_tables": self.nested_tables,
        }


@dataclass
class ColumnRef:
    """字段引用。"""

    name: str
    source_table: str | None = None
    position: int = -1
    ref_type: ColumnRefType = ColumnRefType.COLUMN
    star_table: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "source_table": self.source_table,
            "position": self.position,
            "ref_type": self.ref_type.value,
            "star_table": self.star_table,
        }


@dataclass
class JoinRef:
    """JOIN 关联关系。"""

    left_table: str
    right_table: str
    left_alias: str | None = None
    right_alias: str | None = None
    join_type: JoinType = JoinType.INNER_JOIN
    condition: str | None = None
    conditions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "left_table": self.left_table,
            "left_alias": self.left_alias,
            "right_table": self.right_table,
            "right_alias": self.right_alias,
            "join_type": self.join_type.value,
            "condition": self.condition,
            "conditions": self.conditions,
        }


@dataclass
class HierarchyNode:
    """查询层次结构节点。"""

    node_type: str
    name: str | None = None
    depth: int = 0
    children: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "node_type": self.node_type,
            "name": self.name,
            "depth": self.depth,
            "children": self.children,
        }
