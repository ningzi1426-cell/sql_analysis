# Task Breakdown

## Completed Tasks

- [x] **TASK-001**: 项目脚手架 — 完成于 2026-05-02
- [x] **TASK-002**: 数据模型 `models.py` — 完成于 2026-05-02
- [x] **TASK-003**: 参数/变量清洗 `cleaner.py`（FR-005） — 完成于 2026-05-02
- [x] **TASK-004**: 表引用提取 `parser.py` part 1（FR-001） — 完成于 2026-05-02
- [x] **TASK-005**: 字段引用提取 `parser.py` part 2（FR-002） — 完成于 2026-05-02
- [x] **TASK-006**: 关联关系识别 `parser.py` part 3（FR-003） — 完成于 2026-05-02
- [x] **TASK-007**: 层次结构识别 `parser.py` part 4（FR-004） — 完成于 2026-05-02
- [x] **TASK-008**: `parse_sql()` 编排与 JSON 输出（FR-006） — 完成于 2026-05-02
- [x] **TASK-009**: 完整测试套件 — 完成于 2026-05-02（38/38 通过, 91% 覆盖率）

## GUI 入口（FR-007）

- [x] **TASK-010**: cleaner.py GUI 入口（FR-007） — 完成于 2026-05-03
  - Context: 在 cleaner.py 末尾添加 `if __name__ == '__main__'` 块，使用 easygui 实现文件选择和清洗输出
  - Acceptance:
    - `uv run python sql_analysis/cleaner.py` 启动 GUI，选择 SQL 文件后可清洗并输出
    - `uv run python -m sql_analysis.cleaner` 效果同上
    - 输出文件默认保存在输入 SQL 文件所在目录，文件名为 `<原文件名>_cleaned.sql`
    - easygui 加入 pyproject.toml 依赖
- [x] **TASK-011**: parser.py GUI 入口（FR-007） — 完成于 2026-05-03
  - Context: 在 parser.py 末尾添加 `if __name__ == '__main__'` 块，使用 easygui 实现文件选择、解析和 JSON 输出
  - Acceptance:
    - `uv run python sql_analysis/parser.py` 启动 GUI，选择 SQL 文件后可解析并输出 JSON
    - `uv run python -m sql_analysis.parser` 效果同上
    - 输出文件默认保存在输入 SQL 文件所在目录，文件名为 `<原文件名>_parsed.json`
    - 现有 38 个测试不受影响，全部通过
