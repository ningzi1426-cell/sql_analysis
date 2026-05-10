[PROCESSED: 2026-05-10]

# Proposal: Column 别名传播修复

## 需求描述
修复 `normalize_aliases()` 的缺陷：当表别名被重命名（如重复别名 `u` → `u_2`）时，ON 子句中引用旧别名的 Column 节点也应同步更新，使字段引用能唯一关联到对应的表。

当前行为：
```sql
-- 输入: SELECT u.id, u.name FROM users u JOIN orders u ON u.id = u.uid
-- 当前输出: SELECT u.id, u.name FROM users u JOIN orders u_2 ON u.id = u.uid
-- 问题: u.uid 的 Column.table 仍为 "u"，应指向 orders(u_2) 却指向了 users(u)
```

期望行为：
```sql
-- 输出: SELECT u.id, u.name FROM users u JOIN orders u_2 ON u.id = u_2.uid
```

采用 JOIN ON 右式约定启发式：比较运算符右侧的 Column 归属右表（被重命名的表）。

## 影响范围
- **spec.md** — 修改 FR-008 Scenario 2，新增 Column 同步验收条件
- **design.md** — 新增 Decision 11：Column 传播启发式策略
- **tasks.md** — 新增 TASK-014、TASK-015
- **sql_analysis/cleaner.py** — 新增 3 个辅助函数 + 2 处调用点
- **tests/test_cleaner.py** — 新增 Column 传播相关测试

## 验收标准
- ON 条件中比较运算符右侧的 Column 引用随表别名同步更新
- SELECT/WHERE 中的 Column 保持不变（无 schema 无法消歧义）
- 括号包裹的 ON 条件正确处理
- AND/OR 复合条件递归处理
- CROSS JOIN（无 ON）不报错
- 现有 50 个测试全部通过
- 新增测试覆盖：ON 右侧更新、复合条件、括号、子查询别名
