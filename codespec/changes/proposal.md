[PROCESSED: 2026-05-02]
# Proposal: 单条 SQL 解析功能

## 需求描述
实现 SQL 批量分析工具的第一部分：解析单条 SQL，识别并结构化输出其中的表、字段、关联关系和层次结构。

具体包括：
- FR-001：提取表引用（含 schema、别名、类型）
- FR-002：提取字段引用（含限定符、位置索引、跨子查询边界）
- FR-003：识别 JOIN 关联关系（含隐式连接、Oracle (+) 语法）
- FR-004：识别层次结构（子查询嵌套、CTE、UNION 分支）
- FR-005：清洗参数和变量占位符（`&XXX`、`:XXX`）
- FR-006：输出结构化 JSON，含错误处理

技术栈：Python 3.12+ / uv / sqlglot

## 影响范围
- spec（已完成需求编写）
- design（已完成架构设计）
- tasks（已完成任务拆解）

## 验收标准
- `uv run pytest` 全绿，覆盖率 >= 80%
- 所有 spec 场景（FR-001 ~ FR-006 共 24 个 Scenario）有对应测试
- `examples/688.sql` 和 `examples/union.sql` 作为输入可产生正确的结构化 JSON
- `uv run python -c "from sql_analysis import parse_sql"` 正常导入

## 变更边界
单一关注点：单条 SQL 的结构化解析。第二部分（相似度聚类）不在本次变更范围内。
