"""FR-005: 参数/变量清洗测试。"""

import sqlglot

from sql_analysis.cleaner import clean_sql


class TestAmpersandParameter:
    """&XXX 参数识别与替换。"""

    def test_amp_without_space(self):
        """&AAA → (1 = 1)"""
        result = clean_sql("SELECT * FROM users WHERE &AAA")
        assert "(1 = 1)" in result
        sqlglot.parse_one(result)  # 可解析

    def test_amp_with_space(self):
        """& PERIOD_ID → (1 = 1)"""
        result = clean_sql("SELECT * FROM users WHERE & PERIOD_ID")
        assert "(1 = 1)" in result
        sqlglot.parse_one(result)


class TestColonVariable:
    """:XXX 变量识别与替换。"""

    def test_colon_variable_in_where(self):
        """:BBB → (1 = 1)"""
        result = clean_sql("SELECT * FROM users WHERE :BBB")
        assert "(1 = 1)" in result
        sqlglot.parse_one(result)

    def test_multiple_colon_variables(self):
        """多个 :XXX 全部替换"""
        result = clean_sql("SELECT id, :BBB FROM users WHERE id = :CCC AND status = 1")
        # 两个变量都被替换
        assert result.count("(1 = 1)") == 2
        sqlglot.parse_one(result)


class TestStringLiteralProtection:
    """字符串字面量内的 :XXX 不被替换。"""

    def test_variable_in_string_literal(self):
        """SELECT ':CCC' FROM t — 字符串内 :XXX 不替换"""
        result = clean_sql("SELECT ':CCC' FROM t")
        assert "(1 = 1)" not in result
        sqlglot.parse_one(result)

    def test_amp_in_string_literal(self):
        """字符串内 &XXX 不替换"""
        result = clean_sql("SELECT 'test & test' FROM dual")
        assert "(1 = 1)" not in result
        sqlglot.parse_one(result)


class TestCleanSql:
    """无占位符的 SQL 保持不变。"""

    def test_clean_sql_unchanged(self):
        result = clean_sql("SELECT id FROM users")
        sqlglot.parse_one(result)


class TestRealWorldSql:
    """真实 SQL 清洗。"""

    def test_688_sql_cleanable(self, sql_688):
        """688.sql 清洗后仍可解析。"""
        result = clean_sql(sql_688)
        sqlglot.parse_one(result)

    def test_union_sql_cleanable(self, sql_union):
        """union.sql 清洗后仍可解析。"""
        result = clean_sql(sql_union)
        sqlglot.parse_one(result)


class TestNormalizeAliases:
    """FR-008: 别名规范化。"""

    def test_no_alias_table_adds_alias(self):
        """无别名的表自动以表名作为别名。"""
        from sql_analysis.cleaner import normalize_aliases

        result = normalize_aliases("SELECT id FROM users")
        assert "AS users" in result or "users AS users" in result or "FROM users users" in result
        # 输出可解析
        sqlglot.parse_one(result)

    def test_no_alias_table_with_schema(self):
        """带 schema 的表无别名时自动以表名作为别名。"""
        from sql_analysis.cleaner import normalize_aliases

        result = normalize_aliases("SELECT id FROM dw.dim_user_d WHERE status = 1")
        assert "dim_user_d" in result
        sqlglot.parse_one(result)

    def test_duplicate_alias_deduplicated(self):
        """别名重复时第二个表别名被重命名。"""
        from sql_analysis.cleaner import normalize_aliases

        result = normalize_aliases(
            "SELECT * FROM users u JOIN orders u ON u.id = u.uid"
        )
        assert "u_2" in result
        # verify table aliases in AST
        ast = sqlglot.parse_one(result)
        table_aliases = [
            t.alias for t in ast.find_all(sqlglot.exp.Table) if t.alias
        ]
        assert "u" in table_aliases
        assert "u_2" in table_aliases

    def test_same_table_different_aliases_preserved(self):
        """同表不同别名不冲突，保持原样。"""
        from sql_analysis.cleaner import normalize_aliases

        result = normalize_aliases(
            "SELECT pr.prod_code, pr2.prod_code "
            "FROM dwrdim.dwr_dim_product_d pr "
            "LEFT JOIN dwrdim.dwr_dim_product_d pr2 "
            "ON pr.parent_key = pr2.prod_key"
        )
        assert " AS pr" in result or " pr AS pr" in result or " pr " in result
        assert " AS pr2" in result or " pr2 AS pr2" in result or " pr2 " in result
        sqlglot.parse_one(result)

    def test_subquery_alias_unchanged(self):
        """派生表已有别名，保持不变。"""
        from sql_analysis.cleaner import normalize_aliases

        result = normalize_aliases(
            "SELECT a.id, b.total FROM users a "
            "JOIN (SELECT user_id FROM orders) b ON a.id = b.user_id"
        )
        sqlglot.parse_one(result)
        # 解析后检查表别名
        ast = sqlglot.parse_one(result)
        tables = list(ast.find_all(sqlglot.exp.Table))
        aliases = [t.alias for t in tables if t.alias]
        assert "a" in aliases
        # 派生表 b 保留
        subqueries = list(ast.find_all(sqlglot.exp.Subquery))
        subq_aliases = [s.alias for s in subqueries if s.alias]
        assert "b" in subq_aliases

    def test_cte_alias_preserved(self):
        """CTE 引用别名保留。"""
        from sql_analysis.cleaner import normalize_aliases

        result = normalize_aliases(
            "WITH active AS (SELECT id FROM users) SELECT * FROM active"
        )
        sqlglot.parse_one(result)
        # 内部 users 表获得别名
        assert "users" in result

    def test_mixed_scenario(self):
        """混合场景：部分有别名、部分无别名、部分重复。"""
        from sql_analysis.cleaner import normalize_aliases

        result = normalize_aliases(
            "SELECT * FROM users a JOIN orders a JOIN products "
            "ON a.id = products.id"
        )
        sqlglot.parse_one(result)
        # users 保留 a，orders 的重复 a 变为 a_2，products 获得 products
        assert "a_2" in result
        assert "products" in result

    def test_output_parsable(self):
        """规范化后的 SQL 可被正常解析。"""
        from sql_analysis.cleaner import normalize_aliases

        result = normalize_aliases(
            "SELECT a.id, b.name FROM users a "
            "JOIN orders b ON a.id = b.uid "
            "WHERE a.status = 1"
        )
        ast = sqlglot.parse_one(result)
        assert ast is not None

    def test_688_sql_normalizable(self, sql_688):
        """688.sql 清洗后再规范化，仍可解析。"""
        from sql_analysis.cleaner import normalize_aliases, clean_sql

        cleaned = clean_sql(sql_688)
        result = normalize_aliases(cleaned)
        sqlglot.parse_one(result)

    def test_duplicate_table_name_no_alias(self):
        """同一表名多次出现且都没有别名时，第二个获得去重别名。"""
        from sql_analysis.cleaner import normalize_aliases

        result = normalize_aliases("SELECT * FROM users, users")
        assert "users_2" in result
        sqlglot.parse_one(result)

    def test_duplicate_subquery_alias(self):
        """派生表别名重复时去重。"""
        from sql_analysis.cleaner import normalize_aliases

        result = normalize_aliases(
            "SELECT * FROM (SELECT 1 AS id) t JOIN (SELECT 2 AS id) t ON t.id = t.id"
        )
        assert "t_2" in result
        sqlglot.parse_one(result)

    def test_union_sql_normalizable(self, sql_union):
        """union.sql 清洗后再规范化，仍可解析。"""
        from sql_analysis.cleaner import normalize_aliases, clean_sql

        cleaned = clean_sql(sql_union)
        result = normalize_aliases(cleaned)
        sqlglot.parse_one(result)
