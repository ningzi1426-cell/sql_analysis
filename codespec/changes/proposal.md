[PROCESSED: 2026-05-03]

# Proposal: 增加 GUI 直接执行入口

## 需求描述
为 cleaner.py 和 parser.py 增加 `if __name__ == '__main__'` 块，使用户可以直接通过 `python sql_analysis/cleaner.py` 或 `python sql_analysis/parser.py` 启动 GUI 界面运行模块。GUI 使用 easygui 实现，无需浏览器或复杂框架。

交互流程：
1. 弹出文件选择对话框，让用户选择单个待处理的 SQL 文件
2. 弹出确认对话框，询问是否将结果输出到本地文件（默认保存到 SQL 文件所在目录）
3. cleaner.py 将清洗后的 SQL 输出；parser.py 将结构化 JSON 输出

## 影响范围
- spec.md（新增 FR-007：GUI 直接执行入口）
- design.md（新增 easygui 依赖说明、`__main__` 块设计）
- tasks.md（新增 2 个实现任务）
- pyproject.toml（新增 easygui 依赖）
- sql_analysis/cleaner.py（新增 `__main__` 块）
- sql_analysis/parser.py（新增 `__main__` 块）

## 验收标准
- `uv run python sql_analysis/cleaner.py` 启动 GUI，选择 SQL 文件后可清洗并输出
- `uv run python sql_analysis/parser.py` 启动 GUI，选择 SQL 文件后可解析并输出 JSON
- `uv run python -m sql_analysis.cleaner` 效果同上
- `uv run python -m sql_analysis.parser` 效果同上
- 输出文件默认保存在输入 SQL 文件所在目录
- 现有 38 个测试不受影响，全部通过
- easygui 作为可选依赖或核心依赖加入 pyproject.toml

## 变更边界
仅涉及 GUI 启动入口。不修改 cleaner.py 和 parser.py 的现有函数逻辑，不引入 Web 框架。
