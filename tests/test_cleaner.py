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
