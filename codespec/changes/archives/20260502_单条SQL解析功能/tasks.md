# Task Breakdown

## Active Tasks

- [ ] **TASK-001**: 项目脚手架
  - Context: 建立 Python 项目骨架，使后续任务有可运行环境
  - Acceptance:
    - `pyproject.toml` 配置 name=`sql_analysis`, python>=3.12, sqlglot>=25, pytest+pytest-cov dev dependency
    - `sql_analysis/__init__.py` 和 `tests/__init__.py`、`tests/conftest.py` 创建
    - `uv run python -c "import sql_analysis"` 成功
    - `uv run pytest` 能运行（测试数为 0）

- [ ] **TASK-002**: 数据模型 `models.py`
  - Context: 定义所有 dataclass 和 Enum，作为后续模块的数据契约
  - Acceptance:
    - TableType / JoinType / ColumnRefType 枚举
    - TableRef / ColumnRef / JoinRef / HierarchyNode dataclass
    - 每个 dataclass 有 `to_dict()` 方法，Enum 序列化为字符串值
    - 从 `sql_analysis` 可导入所有类型

- [ ] **TASK-003**: 参数/变量清洗 `cleaner.py`（FR-005）
  - Context: 解析前预处理，将 `&XXX` 和 `:XXX` 替换为 `(1 = 1)`，避免干扰解析
  - Acceptance:
    - `clean_sql("SELECT * FROM t WHERE &AAA")` → `"SELECT * FROM t WHERE (1 = 1)"`
    - `clean_sql("SELECT * FROM t WHERE :BBB")` → `"SELECT * FROM t WHERE (1 = 1)"`
    - `clean_sql("SELECT * FROM t WHERE & PERIOD_ID")` → `"SELECT * FROM t WHERE (1 = 1)"`
    - `clean_sql("SELECT ':CCC' FROM t")` → 不替换字符串内变量
    - `clean_sql("-- comment with &VAR")` → 不替换注释内参数

- [ ] **TASK-004**: 表引用提取 `parser.py` part 1（FR-001）
  - Context: 从 AST 提取所有表引用，包含 schema、别名、类型（基表/派生表/CTE/虚拟表）
  - Acceptance:
    - 简单单表 `SELECT id FROM users` → 1 条 BASE_TABLE
    - schema 前缀 `dwrdim.dwr_dim_user_d` → schema=`dwrdim`
    - 同表多别名 → 2 条记录，物理表名相同，别名不同
    - 派生表（子查询）→ DERIVED_TABLE，含嵌套表引用
    - CTE → CTE 类型，含嵌套表引用
    - 无 FROM 子句 → 空列表
    - 虚拟表 `dual` → 空列表（过滤掉）

- [ ] **TASK-005**: 字段引用提取 `parser.py` part 2（FR-002）
  - Context: 从 SELECT 列表提取所有字段引用，含位置索引和源表限定符，不穿透子查询边界
  - Acceptance:
    - 非限定列 `SELECT id, name FROM users` → source=`UNKNOWN`, position 0,1
    - 限定列 `SELECT a.id, b.name FROM ...` → source=`a`, `b`
    - 跨子查询 `SELECT id FROM (SELECT id FROM users) t` → 外层 source=`t`, 内层独立记录
    - 通配符 `SELECT * FROM users` → STAR 类型

- [ ] **TASK-006**: 关联关系识别 `parser.py` part 3（FR-003）
  - Context: 提取所有 JOIN 关系，含类型、参与表、连接条件、Oracle (+) 语法
  - Acceptance:
    - INNER JOIN → 正确左右表、条件
    - LEFT JOIN 复合条件 → 多个条件分离
    - ON 括号包裹 → 正确解析
    - CROSS JOIN → 条件为空
    - 嵌套 JOIN → 按出现顺序返回
    - 隐式连接 + Oracle `(+)` → IMPLICIT_JOIN 类型

- [ ] **TASK-007**: 层次结构识别 `parser.py` part 4（FR-004）
  - Context: 构建嵌套查询树、CTE 定义、UNION 分支，含嵌套深度和表出现次数统计
  - Acceptance:
    - 无嵌套 → 单层 SELECT, depth=0
    - 单层子查询 → depth=2, 正确父子关系
    - CTE 查询 → CTE_DEF 节点 + 主查询节点
    - 三层嵌套 → depth=3
    - UNION → UNION 根节点 + 分支子节点，表出现次数汇总

- [ ] **TASK-008**: `parse_sql()` 编排与 JSON 输出 `parser.py` part 5（FR-006）
  - Context: 串联清洗→解析→提取→组装，处理异常，输出最终 JSON
  - Acceptance:
    - 合法 SQL → 含 tables/columns/joins/hierarchy 四字段，error 为 null
    - 非法 SQL `SELECT a FROM` → error 字段含错误信息，数据字段为 null
    - 输出可被 `json.dumps()` 序列化

- [ ] **TASK-009**: 完整测试套件
  - Context: 覆盖所有 spec 场景 + 真实示例文件，确保 >= 80% 覆盖率
  - Acceptance:
    - `uv run pytest` 全绿
    - `uv run pytest --cov=sql_analysis --cov-report=term-missing` 覆盖率 >= 80%
    - `examples/688.sql` 和 `examples/union.sql` 输入验证输出正确

## Completed Tasks

<!-- Move tasks here when done, with completion date -->
