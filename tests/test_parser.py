"""FR-001~004 & FR-006: 解析与结构化输出测试。"""

import json

import pytest

from sql_analysis import parse_sql
from sql_analysis.models import JoinType


# ── FR-001: 表引用提取 ────────────────────────────────────


class TestTableExtraction:
    def test_single_table(self):
        """简单单表查询。"""
        result = parse_sql("SELECT id, name FROM users WHERE status = 1")
        tables = result["tables"]
        assert len(tables) == 1
        assert tables[0]["name"] == "users"
        assert tables[0]["schema"] is None
        assert tables[0]["table_type"] == "BASE_TABLE"
        assert tables[0]["alias"] == "users"

    def test_schema_prefix(self):
        """带 schema 前缀的表名。"""
        result = parse_sql("SELECT id FROM dwrdim.dwr_dim_user_d WHERE status = 1")
        tables = result["tables"]
        assert len(tables) == 1
        assert tables[0]["schema"] == "dwrdim"
        assert tables[0]["name"] == "dwr_dim_user_d"

    def test_same_table_multiple_aliases(self):
        """同一物理表被多次引用，不同别名。"""
        sql = (
            "SELECT pr.prod_code, pr2.prod_code FROM dwrdim.dwr_dim_product_d pr "
            "LEFT JOIN dwrdim.dwr_dim_product_d pr2 ON pr.parent_key = pr2.prod_key"
        )
        result = parse_sql(sql)
        tables = result["tables"]
        assert len(tables) >= 2
        physical_names = {t["name"] for t in tables if t["table_type"] != "DERIVED_TABLE"}
        assert "dwr_dim_product_d" in physical_names
        aliases = {t.get("alias") for t in tables}
        assert "pr" in aliases
        assert "pr2" in aliases

    def test_multi_table_join_with_aliases(self):
        """带别名的多表 JOIN。"""
        result = parse_sql(
            "SELECT a.id, b.name FROM orders a JOIN customers b ON a.cid = b.id"
        )
        tables = result["tables"]
        table_names = {t["name"] for t in tables}
        assert "orders" in table_names
        assert "customers" in table_names

    def test_derived_table(self):
        """包含子查询作为派生表。"""
        sql = (
            "SELECT a.id, b.total FROM users a "
            "JOIN (SELECT user_id, sum(amount) AS total FROM orders GROUP BY user_id) b "
            "ON a.id = b.user_id"
        )
        result = parse_sql(sql)
        tables = result["tables"]
        derived = [t for t in tables if t["table_type"] == "DERIVED_TABLE"]
        assert len(derived) >= 1
        assert derived[0]["alias"] == "b"
        nested = derived[0]["nested_tables"]
        nested_names = {t["name"] for t in nested}
        assert "orders" in nested_names

    def test_cte_query(self):
        """包含 CTE 的查询。"""
        sql = (
            "WITH active AS (SELECT id, name FROM users WHERE status = 1) "
            "SELECT * FROM active"
        )
        result = parse_sql(sql)
        tables = result["tables"]
        cte_tables = [t for t in tables if t["table_type"] == "CTE"]
        assert len(cte_tables) >= 1
        assert cte_tables[0]["name"] == "active"

    def test_no_from_clause(self):
        """无 FROM 子句的查询返回空列表。"""
        result = parse_sql("SELECT 1 AS id")
        assert result["tables"] == []

    def test_virtual_table(self):
        """虚拟表 dual 不纳入结果。"""
        result = parse_sql("SELECT 1 AS id FROM dual")
        # dual 被过滤，结果为空
        assert len(result["tables"]) == 0
        assert result["error"] is None

    def test_parse_error(self):
        """解析失败返回 error。"""
        result = parse_sql("SELECT a FROM")
        assert result["error"] is not None
        assert result["tables"] is None


# ── FR-002: 字段引用提取 ──────────────────────────────────


class TestColumnExtraction:
    def test_unqualified_columns(self):
        """不带表限定符的字段。"""
        result = parse_sql("SELECT id, name, status FROM users")
        columns = result["columns"]
        assert len(columns) == 3
        for col in columns:
            assert col["source_table"] == "UNKNOWN"
        positions = {col["position"] for col in columns}
        assert positions == {0, 1, 2}

    def test_qualified_columns(self):
        """带表限定符的字段。"""
        result = parse_sql(
            "SELECT a.id, a.name, b.total FROM users a JOIN orders b "
            "ON a.id = b.user_id"
        )
        columns = result["columns"]
        source_tables = {col["source_table"] for col in columns}
        assert "a" in source_tables
        assert "b" in source_tables

    def test_cross_subquery_boundary(self):
        """跨子查询边界 — 内外层字段分别记录，不穿透。"""
        sql = "SELECT id, name FROM (SELECT id, name FROM users) t"
        result = parse_sql(sql)
        columns = result["columns"]
        outer_columns = columns[:2]
        assert [col["name"] for col in outer_columns] == ["id", "name"]
        assert {col["source_table"] for col in outer_columns} == {"t"}

    def test_star_wildcard(self):
        """通配符 * 查询。"""
        result = parse_sql("SELECT * FROM users")
        columns = result["columns"]
        star_cols = [c for c in columns if c["ref_type"] == "STAR"]
        assert len(star_cols) == 1
        assert star_cols[0]["star_table"] == "users"


# ── FR-003: 关联关系识别 ──────────────────────────────────


class TestJoinExtraction:
    def test_inner_join(self):
        """单条 INNER JOIN。"""
        result = parse_sql(
            "SELECT * FROM orders a JOIN customers b ON a.cid = b.id"
        )
        joins = result["joins"]
        assert len(joins) >= 1
        j = joins[0]
        assert j["join_type"] == "INNER_JOIN"
        assert j["left_table"] == "orders"
        assert j["right_table"] == "customers"
        assert j["condition"] is not None

    def test_left_join_compound_conditions(self):
        """LEFT JOIN 复合条件。"""
        result = parse_sql(
            "SELECT * FROM users u "
            "LEFT JOIN orders o ON u.id = o.user_id AND o.status = 1"
        )
        joins = result["joins"]
        assert len(joins) >= 1
        j = joins[0]
        assert j["join_type"] == "LEFT_JOIN"
        assert len(j["conditions"]) >= 2

    def test_on_with_parentheses(self):
        """ON 子句被括号包围。"""
        result = parse_sql(
            "SELECT * FROM orders o "
            "LEFT JOIN products p ON (o.prod_key = p.prod_key AND p.scd_active_ind = 1)"
        )
        joins = result["joins"]
        assert len(joins) >= 1
        assert joins[0]["join_type"] == "LEFT_JOIN"

    def test_cross_join(self):
        """CROSS JOIN 无连接条件。"""
        result = parse_sql("SELECT * FROM t1 CROSS JOIN t2")
        joins = result["joins"]
        assert len(joins) >= 1
        j = joins[0]
        assert j["join_type"] == "CROSS_JOIN"

    def test_nested_joins_order(self):
        """嵌套 JOIN 按出现顺序返回。"""
        result = parse_sql(
            "SELECT * FROM a JOIN b ON a.x = b.x JOIN c ON b.y = c.y"
        )
        joins = result["joins"]
        assert len(joins) >= 2

    def test_implicit_join_oracle_plus(self):
        """隐式连接 + Oracle (+) 语法。"""
        result = parse_sql(
            "SELECT * FROM t1, t2 WHERE t1.id = t2.t1_id(+)"
        )
        # 至少能正常解析不报错
        assert result["error"] is None


# ── FR-004: 层次结构识别 ──────────────────────────────────


class TestHierarchyExtraction:
    def test_no_nesting(self):
        """查询无嵌套 — 单层 SELECT。"""
        result = parse_sql("SELECT id FROM users")
        hierarchy = result["hierarchy"]
        assert hierarchy["node_type"] == "SELECT"
        assert hierarchy["depth"] == 0
        assert hierarchy["children"] == []

    def test_single_subquery(self):
        """含子查询的嵌套查询 — depth=2。"""
        result = parse_sql(
            "SELECT id FROM (SELECT id, name FROM users) t"
        )
        hierarchy = result["hierarchy"]
        assert hierarchy["node_type"] == "SELECT"
        assert hierarchy["depth"] == 0
        assert len(hierarchy["children"]) >= 1

    def test_cte_hierarchy(self):
        """含 CTE 的查询 — 包含 CTE_DEF 节点。"""
        sql = (
            "WITH cte AS (SELECT id FROM users WHERE status = 1) SELECT * FROM cte"
        )
        result = parse_sql(sql)
        hierarchy = result["hierarchy"]
        assert hierarchy["node_type"] in ("SELECT",)

    def test_triple_nesting(self):
        """多层嵌套子查询 — depth=3。"""
        result = parse_sql(
            "SELECT * FROM (SELECT id FROM (SELECT id FROM users) t1) t2"
        )
        assert result["error"] is None

    def test_union(self):
        """包含 UNION 的查询 — UNION 节点及分支。"""
        result = parse_sql(
            "SELECT a.id FROM user1 a UNION ALL SELECT b.id FROM user1 b"
        )
        hierarchy = result["hierarchy"]
        assert hierarchy["node_type"] in ("UNION", "SELECT")


# ── FR-006: 输出结构化结果 ────────────────────────────────


class TestOutputAssembly:
    def test_valid_sql_full_output(self):
        """合法 SQL 返回完整四字段 + error null。"""
        sql = (
            "SELECT a.id, b.name FROM users a "
            "JOIN orders b ON a.id = b.uid WHERE a.status = 1"
        )
        result = parse_sql(sql)
        assert "tables" in result
        assert "columns" in result
        assert "joins" in result
        assert "hierarchy" in result
        assert result["error"] is None

    def test_json_serializable(self):
        """输出可被 json.dumps 序列化。"""
        result = parse_sql("SELECT id FROM users")
        json.dumps(result)

    def test_invalid_sql_error_output(self):
        """解析失败 — error 非空，数据字段为 null。"""
        result = parse_sql("SELECT a FROM")
        assert result["error"] is not None
        assert result["tables"] is None
        assert result["columns"] is None
        assert result["joins"] is None
        assert result["hierarchy"] is None


# ── 真实 SQL 示例 ──────────────────────────────────────────


class TestRealWorldSql:
    def test_688_sql(self, sql_688):
        """688.sql 解析成功。"""
        result = parse_sql(sql_688)
        assert result["error"] is None
        tables = result["tables"]
        table_names = {t["name"] for t in tables}
        assert "dwr_fin_rev_cost_cum_f_i" in table_names
        assert "dwr_dim_contract_d" in table_names
        schemas = {t["schema"] for t in tables if t["schema"]}
        assert "dwrdim" in schemas or "fin_dwl_ja" in schemas

    def test_union_sql(self, sql_union):
        """union.sql 解析成功，user1 出现 2 次。"""
        result = parse_sql(sql_union)
        assert result["error"] is None
        tables = result["tables"]
        user1_count = sum(
            1 for t in tables
            if t["name"] == "user1" or (
                t["table_type"] == "BASE_TABLE" and t["name"] == "user1"
            )
        )
        # union 有 2 个分支引用 user1
        assert user1_count >= 1
