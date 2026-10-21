# Tasks

## 1. 配置与依赖

- [x] 1.1 在 `Settings` 增加 `TAVILY_API_KEY`、`KNOWLEDGE_AGENT_ENABLED`、`TAVILY_DEFAULT_MAX_RESULTS`、`KNOWLEDGE_AGENT_MAX_TOOL_CALLS`、`TAVILY_TOOL_TIMEOUT_SECONDS` 和 `KNOWLEDGE_AGENT_TIMEOUT_SECONDS`，同步根目录 `.env.example`；用配置测试验证默认值、范围校验及关闭/缺少 Key 时可正常启动。
- [x] 1.2 在 `backend/requirements.txt` 增加 `langchain-tavily` 及所需 LangChain Agent 依赖；安装后验证 `create_agent`、`TavilySearch` 和 `TavilyExtract` 可导入。
- [x] 1.3 使用当前 DeepSeek 配置验证 Agent Tool Calling 与现有结构化题目生成可共存；通过隔离 Fake 工具测试验证模型可选择并调用工具。

## 2. 知识获取 Agent 与工具

- [x] 2.1 新增知识获取 Agent Prompt 和服务，使用 LangChain Agent + Tool Calling 接入 `TavilySearch`、`TavilyExtract`；通过 Fake 模型/工具测试确认 Agent 可返回知识摘要或明确的无有效摘要结果。
- [x] 2.2 为 `TavilySearch` 提供受限的 Agent 工具参数入口，使 Agent 可动态选择 `search_depth`、`max_results` 和 `time_range`；测试默认结果数为 5、结果数范围不超过 1–10、非法参数被拒绝。
- [x] 2.3 为 `TavilyExtract` 加入 URL 校验，覆盖普通出题输入 URL 和 Agent 选择的 URL；测试私网地址、带凭据地址及非法 URL 均不会传给工具。
- [x] 2.4 实现单次 Tavily 调用超时、Agent 总超时、最大工具调用次数及安全日志；使用可控 Fake 工具验证每项预算生效、超限停止调用且日志不含密钥和网页正文。
- [x] 2.5 限制整理后的联网上下文不超过 12,000 字，并验证过短上下文不生成有效摘要。

## 3. 普通出题链路、Prompt 与回退

- [x] 3.1 在 `QuizService.generate()` 接入知识获取 Agent，将完整普通出题输入统一交给 Agent；通过测试确认关键词、直接输入网页 URL、网址与问题混合输入均走此链路，而不切换到来源导入接口。
- [x] 3.2 校验 Agent 知识摘要：摘要不超过 1,200 字，包含 3 至 8 个关键点且每项不超过 80 字；测试空结果、越界结果和内容过滤失败均视为无效。
- [x] 3.3 改造 `QUIZ_PROMPT`，将用户学习主题与 Agent 摘要作为分离且明确标记为不可信的参考资料传入；通过 Prompt 测试确认摘要可用、注入指令不会被当作系统指令执行。
- [x] 3.4 实现关闭功能、缺少 Key、Agent/工具异常、超时、空结果或摘要无效时使用原始用户输入回退；测试确认原有题目响应结构、模型重试和持久化的 `user_input` 保持不变。
- [x] 3.5 验证 `generate_from_source()` 完全不调用知识获取 Agent；使用 Fake Agent 覆盖网页、文档和视频导入生成。

## 4. 文档与集成验收

- [x] 4.1 更新 README，说明可选 API Key、功能开关、默认结果数和调用限制；解释关键词、普通出题入口直接输入 URL、混合输入均由 Agent 判断工具，以及失败自动回退和导入材料不触发 Agent；核对配置名称与实现一致。
- [x] 4.2 运行 `pytest -q`，验证既有 API、导入材料、用户系统、报告和新增知识 Agent 测试全部通过。
- [x] 4.3 配置测试用 Tavily Key 后分别对关键词、直接输入 URL 和混合输入执行冒烟，确认 Agent 动态工具选择与摘要注入；移除 Key 或关闭功能后再次验证纯模型出题可用。

## Workflow follow-up

- 在实现与验收完成后，按项目评审要求执行 OpenSpec archive。
