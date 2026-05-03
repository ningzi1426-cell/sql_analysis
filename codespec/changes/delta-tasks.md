# tasks.md 变更日志

<!-- This file is append-only. Each change adds a new ## section. Do not edit or delete existing sections. -->

## 2026-05-02 单条 SQL 解析功能

### 变更摘要
新增单条 SQL 解析功能的 9 项工作任务拆解，从项目脚手架到完整测试套件，按依赖关系排序。

### 对 tasks.md 的变更
- **新建文件**：`codespec/specs/tasks.md`
- **TASK-001 项目脚手架**：建立 pyproject.toml、模块骨架、uv 环境和空测试运行。
- **TASK-002 数据模型 models.py**：定义全部 dataclass 和 Enum，含 to_dict() 序列化。
- **TASK-003 参数/变量清洗 cleaner.py（FR-005）**：处理 `&XXX`/`:XXX` 替换，跳过字符串和注释。
- **TASK-004 表引用提取 parser.py part 1（FR-001）**：基表/派生表/CTE/虚拟表识别与剔除。
- **TASK-005 字段引用提取 parser.py part 2（FR-002）**：限定符、位置索引、子查询边界、星号。
- **TASK-006 关联关系识别 parser.py part 3（FR-003）**：JOIN 类型、条件、隐式连接、Oracle (+)。
- **TASK-007 层次结构识别 parser.py part 4（FR-004）**：嵌套树、CTE_DEF、UNION 分支、深度统计。
- **TASK-008 parse_sql() 编排与 JSON 输出 parser.py part 5（FR-006）**：串联流程、异常处理、JSON 组装。
- **TASK-009 完整测试套件**：覆盖全部 spec 场景 + 示例文件，覆盖率 >= 80%。
