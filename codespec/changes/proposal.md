[PROCESSED: 2026-05-10]

# Proposal: Column 别名传播修复

## 需求描述
修复 `normalize_aliases()` 的缺陷：当表别名被重命名（如重复别名 `u` → `u_2`）时，ON/WHERE 子句中所有**可确定归属**的 Column 节点应同步更新，使字段引用能唯一关联到对应的表。

采用比较表达式右式约定启发式：比较运算符（`=`、`<`、`>` 等）右侧的 Column 归属被重命名的表。覆盖显式 JOIN ON 和隐式关联 WHERE 两种场景。

当前行为 vs 期望：
```sql
-- 场景1（显式 JOIN ON）:
-- 输入:  SELECT u.id, u.name FROM users u JOIN orders u ON u.id = u.uid
-- 输出:  SELECT u.id, u.name FROM users u JOIN orders u_2 ON u.id = u_2.uid

-- 场景2（隐式关联 WHERE）:
-- 输入:  SELECT * FROM t1 u, t2 u WHERE u.a = u.b
-- 输出:  SELECT * FROM t1 u, t2 u_2 WHERE u.a = u_2.b
```

## 影响范围
- **spec.md** — 修改 FR-008 Scenario 2，新增 Column 同步验收条件
- **design.md** — 新增 Decision 11：Column 传播启发式策略
- **tasks.md** — 新增 TASK-014、TASK-015
- **sql_analysis/cleaner.py** — 新增 3 个辅助函数 + 2 处调用点
- **tests/test_cleaner.py** — 新增 Column 传播相关测试

## 验收标准
- ON/WHERE/HAVING 中比较运算符右侧的 Column 随表别名同步更新（覆盖 parser 所有输出子句）
- SELECT 列表中单独的 Column 引用保持不变（无 schema 无法确定归属）
- 左侧 Column 不变
- 括号包裹的条件正确处理
- AND/OR 复合条件递归处理
- CROSS JOIN（无 ON）不报错
- 现有 50 个测试全部通过
- 新增测试覆盖：ON、WHERE、HAVING 隐式关联、复合条件、括号、子查询别名、表达式多列
