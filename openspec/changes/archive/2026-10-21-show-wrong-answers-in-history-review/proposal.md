# Proposal

## Why

当前微信小程序的历史复盘详情虽然保存了完整题目与作答记录，但没有把本次答错的题目集中呈现，用户需要逐条比对才能定位需要复习的内容。增加独立的错题复盘视图，可以让用户在完成闯关后直接看到题干、自己的答案、正确答案和解析，形成更明确的复习闭环。

## What Changes

- 在微信小程序历史复盘详情中增加“本次错题”列表，仅展示当前这次闯关的错题。
- 每道错题展示题干、用户答案、正确答案和题目解析；选项答案同时展示选项标识与选项文本，避免只显示字母造成歧义。
- 当本次闯关没有错题时，在该区域展示明确的“本次没有错题”空状态。
- 错题列表复用历史详情接口已经返回的 `questions` 与 `answer_records`，通过 `question_id` 关联题目，通过 `is_correct` 筛选错题。
- 不新增数据库字段、不调整答题记录或报告的数据结构，也不新增后端接口。
- 本次仅调整微信小程序历史复盘页；H5 用户系统、登录、档案和历史入口均不在范围内。
- 答完题后的即时 `pages/report` 页面不在本次范围，本次仅覆盖从闯关历史进入的 `pages/history-detail` 历史复盘页。

## Capabilities

### New Capabilities

- `quiz-history-review`: 定义微信小程序历史复盘页集中展示本次错题及其题干、用户答案、正确答案、解析和空状态的行为。

### Modified Capabilities

- 无。

## Impact

- 前端：`miniapp/src/pages/history-detail/index.tsx`、`miniapp/src/pages/history-detail/index.scss`。
- 后端：复用现有 `GET /api/v1/user/quizzes/{quiz_id}` 返回结构，预期无需修改接口实现；实施时补充接口契约回归验证，防止题干、解析或作答判定字段缺失。
- 数据：继续使用 `quiz_sessions.questions_json`、`answer_records.records_json` 和 `reports.report_json`，无数据库迁移。
- 平台边界：微信小程序可访问；H5 不新增用户系统能力，也不展示该历史复盘功能。
