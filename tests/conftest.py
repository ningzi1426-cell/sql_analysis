"""pytest 共享 fixtures。"""

from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture
def sql_688():
    """688.sql — 真实业务 SQL 示例。"""
    return (EXAMPLES_DIR / "688.sql").read_text(encoding="utf-8")


@pytest.fixture
def sql_union():
    """union.sql — UNION 查询示例。"""
    return (EXAMPLES_DIR / "union.sql").read_text(encoding="utf-8")
