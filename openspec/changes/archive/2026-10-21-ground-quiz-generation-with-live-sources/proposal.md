# Proposal

## Why

大模型的训练数据存在时间上限，用户学习新概念时可能因缺少相关资料而得到领域错位或过时的题目。纯文本出题需要引入知识获取 Agent，让 AI 根据用户输入自主选择联网搜索或网页提取并将知识摘要用于出题；联网能力不可用时仍须保证原有出题链路可用。

## What Changes

- 在原有普通出题入口接入 LangChain Agent + Tool Calling。关键词、直接输入的网页 URL 和混合输入均进入同一知识获取 Agent 链路；Agent 自主判断意图并选择 Tavily 搜索、网页提取或组合调用。直接输入 URL 不改走现有来源导入链路。
- 使用 `langchain-tavily` 提供的 `TavilySearch` 和 `TavilyExtract`。Agent 可依据任务动态选择 `search_depth`、`max_results` 和 `time_range`；服务端配置默认结果数、允许范围、工具调用上限和超时，约束调用成本。
- Agent 获取并整理知识摘要后，将其作为参考资料注入出题 Prompt。摘要不超过 1,200 字，包含 3 至 8 个关键点，每项不超过 80 字；联网内容按不可信数据处理。
- 搜索开关关闭、密钥缺失、Agent 或工具调用失败、超时、空结果或摘要无效时，使用用户原始输入回退到原有纯模型出题，不新增接口错误状态。
- 新增搜索配置，包括 Tavily API Key、功能开关、默认结果数及 Agent 调用限制；密钥缺失时联网增强不可用但不影响应用启动和原有出题。
- 保持 `POST /api/v1/quiz/generate`、题库响应结构、数据库和小程序页面不变；题库仍保存用户原始输入，用户主动导入材料的现有链路也不变。

## Capabilities

### New Capabilities

- `grounded-quiz-generation`: 定义知识获取 Agent 如何依据普通出题输入选择联网工具、生成参考摘要并在联网不可用时回退到原有纯模型出题。

### Modified Capabilities

无。

## Impact

- 后端配置：增加可选 `TAVILY_API_KEY`、联网开关、默认搜索结果数、Agent 工具调用上限和超时等配置。
- 后端服务：在 `QuizService.generate()` 前增加知识获取 Agent；以 Agent 摘要扩展现有出题 Prompt，并继续复用结构化题目输出、内容过滤和原有模型重试。
- 外部依赖：增加 `langchain-tavily`，使用其 `TavilySearch` 与 `TavilyExtract`；为 Agent 可动态选择结果数提供受配置约束的工具参数入口。
- 接口与数据：不新增或修改 API 字段，不新增来源模型、数据库列、迁移或历史详情字段；题库仍保存用户原始输入。
- 前端：不修改请求参数、响应类型、加载状态或页面展示。
- 测试：覆盖关键词、直接输入 URL、混合输入下的 Agent 工具选择与参数、摘要注入出题 Prompt、配置开关与边界、超时和失败回退、URL 安全、Prompt 注入及导入材料链路不受影响。
- 不在本次范围：来源引用、答案证据审计、来源持久化、前端来源展示和对历史题库重新核验。
