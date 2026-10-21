# quiz-history-review Specification

## Purpose

定义微信小程序历史复盘页如何从一次已完成的闯关记录中集中展示错题，帮助用户快速回顾错误答案、正确答案与解析。该能力不改变现有答题记录和报告的数据结构。

## Requirements

### Requirement: 历史复盘页展示本次错题

微信小程序历史复盘详情加载成功后，系统 SHALL 展示一个“本次错题”区域，其中仅包含当前 `quiz_id` 对应闯关的答错题目。

#### Scenario: 本次闯关存在错题

- **WHEN** 用户打开一条包含答错记录的历史复盘详情
- **THEN** 页面显示“本次错题”区域，并按原有答题顺序列出本次所有答错题目

#### Scenario: 本次闯关存在多道错题

- **WHEN** 当前闯关的 `answer_records` 中有多于一道记录的 `is_correct` 为 `false`
- **THEN** “本次错题”区域展示全部这些错题，且不混入本次答对的题目

### Requirement: 错题展示完整复盘信息

每道错题 SHALL 展示题干、用户答案、正确答案和解析；答案包含多个选项时 MUST 全部展示，并使用选项标识与选项文本表示。

#### Scenario: 展示单选题错题

- **WHEN** 一道单选题的 `is_correct` 为 `false`
- **THEN** 该错题显示题干、用户选择的选项标识与文本、正确的选项标识与文本以及 `explanation` 解析

#### Scenario: 展示多选题错题

- **WHEN** 一道多选题的 `is_correct` 为 `false` 且用户选择或正确答案包含多个选项
- **THEN** 该错题按选项顺序展示全部用户答案和全部正确答案，并显示解析

#### Scenario: 用户未留下有效选项

- **WHEN** 错题记录没有可展示的用户选项
- **THEN** 用户答案位置显示“未作答”，正确答案和解析仍正常展示

### Requirement: 无错题时展示明确空状态

当本次闯关的全部作答记录均为正确时，系统 SHALL 在“本次错题”区域展示明确的空状态，不得只隐藏该区域。

#### Scenario: 本次闯关全部答对

- **WHEN** 用户打开一条所有 `answer_records.is_correct` 均为 `true` 的历史复盘详情
- **THEN** 页面显示“本次没有错题”或语义等价的明确提示

### Requirement: 复用现有历史详情数据契约

错题复盘 SHALL 使用现有历史详情接口返回的 `questions` 与 `answer_records` 关联生成，MUST NOT 新增数据库字段、报告字段或专用错题接口。

#### Scenario: 使用现有接口打开历史复盘

- **WHEN** 小程序调用 `GET /api/v1/user/quizzes/{quiz_id}` 并成功获得题目、作答记录和报告
- **THEN** 页面无需额外请求即可生成“本次错题”区域

#### Scenario: 接口保持现有响应结构

- **WHEN** 后端返回现有 `QuizHistoryDetail` 结构
- **THEN** 题目中的 `stem`、`options`、`answer`、`explanation` 以及作答记录中的 `selected_answers`、`is_correct` 足以完成错题展示

### Requirement: 保持 H5 用户系统不变

本次错题复盘能力 SHALL 仅在微信小程序历史复盘页提供，MUST NOT 为 H5 启用用户历史、登录或错题复盘入口。

#### Scenario: 在 H5 打开应用

- **WHEN** 应用以 H5 环境运行
- **THEN** 不出现本次新增的微信小程序历史错题复盘能力，现有 H5 匿名学习流程保持不变
