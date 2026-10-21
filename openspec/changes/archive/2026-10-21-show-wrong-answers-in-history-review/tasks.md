# Tasks

## 1. 锁定现有接口契约

- [x] 1.1 在 `backend/tests/test_user_system.py` 的历史详情断言中补充检查：题目项包含 `stem`、`options`、`answer`、`explanation`，作答记录包含 `selected_answers` 和服务端计算的 `is_correct`；运行 `..\.venv\Scripts\python -m pytest -q tests/test_user_system.py` 验证通过。
- [x] 1.2 确认后端历史详情接口和持久化实现无需改动，并记录响应仍为现有 `QuizHistoryDetail` 结构；用上述接口测试验证没有新增字段或数据库迁移。

## 2. 实现错题数据派生与展示

- [x] 2.1 在 `miniapp/src/pages/history-detail/index.tsx` 中复用 `questions` 与 `answer_records`，按 `question_id` 建立映射并筛选 `is_correct` 为 `false` 的记录；运行 `npm run typecheck` 验证类型检查通过。
- [x] 2.2 在历史复盘详情中新增“本次错题”区域并渲染题干、用户答案、正确答案和解析，多选项按题目选项顺序显示“标识. 文本”；构建后人工核对单题、多选题和答案为空时的回退展示。
- [x] 2.3 当错题集合为空时渲染明确的“本次没有错题”空状态，并保留现有“答题记录”区域；分别用存在错题和全部答对的详情数据核对页面行为。

## 3. 补齐微信小程序样式

- [x] 3.1 在 `miniapp/src/pages/history-detail/index.scss` 中为错题序号、答案行、正确答案、解析和空状态增加局部样式，复用现有面板与颜色体系；在微信开发者工具中检查长题干、长解析和多项答案不会溢出或遮挡相邻内容。
- [x] 3.2 运行 `npm run build:weapp` 验证微信小程序构建成功，并确认历史复盘页仍只在微信小程序页面配置中注册。

## 4. 集成验收

- [x] 4.1 运行 `..\.venv\Scripts\python -m pytest -q` 验证后端测试全部通过，确认报告、评分、持久化和历史详情行为未回归。
- [x] 4.2 在微信开发者工具中分别验收“有错题”和“无错题”两条历史记录，核对本次错题数量、题干、用户答案、正确答案、解析及空状态均符合规格。
- [x] 4.3 运行 `npm run typecheck`、`npm run build:weapp` 和 `npm run build:h5`，确认前端构建通过且 H5 未新增历史复盘入口。

## Workflow follow-up

- 方案评审通过后，另行启动 OpenSpec apply 流程实施，不在本次提案阶段修改业务代码。
