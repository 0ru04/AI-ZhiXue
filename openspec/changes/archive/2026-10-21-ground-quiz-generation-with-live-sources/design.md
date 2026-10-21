# Design

## Context

当前普通文本出题由 `QuizService.generate()` 调用 `QUIZ_PROMPT` 和结构化题目输出；题目响应与持久化均保留原始用户输入。文档、网页和视频导入使用独立的 `generate_from_source()` 链路。本次联网增强只接入普通出题链路，直接输入网页地址也从该入口进入知识获取 Agent。参见 `proposal.md` 了解目标，行为约束见 `specs/grounded-quiz-generation/spec.md`。

## Goals / Non-Goals

**Goals:**

- 使用 LangChain Agent + Tool Calling 将普通出题输入交给 Agent 自主判断是否联网，以及选择搜索、网页提取或组合工具调用。
- 用 Agent 返回的知识摘要扩展现有 `QUIZ_PROMPT`，同时保留原始学习主题和原有纯模型回退。
- 对工具参数、调用次数、单次工具超时、Agent 总耗时和 URL 安全边界施加服务端限制。
- 通过配置开关与可选 Tavily Key 控制增强能力，保持 API、持久化和导入出题链路兼容。

**Non-Goals:**

- 不改造用户主动导入材料的解析与出题流程。
- 不增加来源引用、题目证据审计、来源持久化或前端来源展示。
- 不在 Agent 失败时改变接口错误码，也不将联网摘要失败当作题目生成失败。

## Decisions

### 1. 普通出题入口统一进入知识获取 Agent

在 `QuizService.generate()` 内部调用知识获取服务，传入完整的、已清理的用户原始输入。输入为关键词、直接输入 URL 或混合输入时均使用同一入口；由 Agent 判断内容意图，决定搜索、提取或组合调用。不得在 API 层把 URL 输入切换到 `/source/parse/url` 或来源出题流程。

`generate_from_source()` 不依赖知识获取服务。无论知识摘要是否成功，题库 `user_input` 都保持用户原始输入；仅提供给题目生成 Prompt 的学习参考材料会在联网成功时增加 Agent 摘要。

### 2. 通过 Agent 调用 Tavily 搜索和提取工具

使用 LangChain 的 `create_agent`（或同等的 LangChain Agent API）和现有 DeepSeek `ChatOpenAI` 配置创建知识获取 Agent，提供 `langchain-tavily` 的 `TavilySearch` 与 `TavilyExtract` 能力。Agent 系统指令说明如何区分关键词、URL 和混合输入，并要求只返回与用户学习主题有关的知识摘要。

Agent 可以逐步决定是否调用工具及调用次序。`search_depth`、`time_range` 由 Agent 根据主题时效性和检索目标选择；结果数由 Agent 提出，但服务端负责将其限制在有效范围内。LangChain Tavily 文档中 `max_results` 是 `TavilySearch` 初始化参数而不是常规调用参数，因此通过一个受限的 LangChain 工具入口接收 Agent 选择的结果数，再以该数量配置 `TavilySearch` 实例；其余搜索设置也在该入口完成范围校验。该入口只用于暴露受约束的动态参数，不另建一套搜索策略。

`TavilyExtract` 接收 Agent 选定的 URL；工具入口在实际请求前验证 URL。用户输入中的网页地址必须通过现有公开 URL 校验，私网 IP、带凭据 URL 和非法 URL 不得交给工具。对 Agent 基于搜索结果提出的提取地址也执行相同校验。搜索结果和提取上下文最多保留 12,000 字，少于 200 字时视为无有效知识。

### 3. Agent 负责生成摘要，摘要作为 Prompt 参考资料

Agent 在零次或若干次受限工具调用后生成知识摘要，作为知识获取流程的最终结果，不再启动单独的摘要模型调用。服务端校验 Agent 的最终输出：摘要不超过 1,200 字，包含 3 至 8 个关键点，每项不超过 80 字；空结果、格式不合格或内容过滤失败均视为知识获取失败。

扩展 `QUIZ_PROMPT`，将用户学习主题和 Agent 摘要放在清晰分隔的独立区块中。摘要明确标记为外部参考资料和不可信数据；题目生成模型只将其用于主题知识参考，不执行其中改变角色、泄露信息或忽略规则的指令。原有题目结构、内容过滤和输出校验不变。摘要不得带入来源编号、逐题引用或来源持久化字段。

### 4. 搜索参数与 Agent 资源预算可配置且有界

在 `Settings` 中增加以下配置并同步根目录 `.env.example`：

- `TAVILY_API_KEY`：可选的 Tavily API Key，按密钥类型读取。
- `KNOWLEDGE_AGENT_ENABLED`：功能开关，默认开启；关闭时跳过 Agent。
- `TAVILY_DEFAULT_MAX_RESULTS`：默认结果数，默认 5，范围 1 至 10；Agent 选择的值不得超过 10。
- `KNOWLEDGE_AGENT_MAX_TOOL_CALLS`：每次 Agent 执行的工具调用上限，默认 4。
- `TAVILY_TOOL_TIMEOUT_SECONDS`：单次 Tavily 调用超时，默认 10 秒。
- `KNOWLEDGE_AGENT_TIMEOUT_SECONDS`：Agent 知识获取总超时，默认 20 秒。

若功能关闭或 Key 缺失，直接跳过联网增强。所有调用次数、结果数和超时均由服务端校验，不允许 Agent 或用户绕过配置上限。Agent 运行使用现有模型配置；必须通过测试验证当前 DeepSeek 兼容端点可同时完成 Tool Calling 与原有结构化题目生成。

### 5. 知识获取失败在普通出题链路内回退

知识获取服务返回可用摘要或 `None`。Agent 构建失败、工具异常、鉴权失败、URL 不安全、超时、调用额度耗尽、空结果、摘要格式不合格或内容过滤失败时，记录不含密钥和网页正文的告警并返回 `None`。`QuizService.generate()` 在摘要为 `None` 时以原始输入填充现有 Prompt，按原有结构化输出、内容过滤和模型重试逻辑生成题目。

外层总超时必须涵盖整个 Agent 工具调用过程；超时后停止等待联网结果并继续纯模型出题。请求取消等控制流异常不得被当作联网故障吞掉。此回退仅覆盖知识获取阶段，题目生成自身原有错误处理保持不变。

### 6. 保持 API、数据和来源导入边界

不修改 `QuizGenerateRequest`、`Quiz`、`QuizGenerationOutput`、历史详情、数据库模型或迁移。`POST /api/v1/quiz/generate` 的请求和响应结构不变。只在 `QuizService.generate()` 接入知识获取服务，`generate_from_source()` 继续直接使用已导入材料、原有来源 Prompt、内容过滤和题目生成。

预计实现范围：

- 新增 `backend/app/services/live_knowledge_service.py`，封装 Agent、工具、预算、URL 校验和摘要验证。
- 新增 `backend/app/prompts/live_knowledge_prompt.py`，提供知识获取 Agent 的安全指令。
- 修改 `backend/app/core/config.py`、`backend/app/services/quiz_service.py`、`backend/app/prompts/quiz_prompt.py`。
- 修改 `backend/requirements.txt`、根目录 `.env.example` 和 README。
- 新增 Agent 工具选择、参数边界、Prompt 注入、失败回退与导入链路隔离测试。

## Risks / Trade-offs

- [当前 DeepSeek 兼容端点可能不支持 Agent 所需的 Tool Calling 组合] → 实现前以隔离测试验证工具调用和现有结构化出题；若不兼容，Agent 视为不可用并安全回退，不静默改变出题契约。
- [Agent 可能重复或不必要地调用工具] → 限制单次工具调用数、结果数及总耗时，并对 Agent 参数进行服务端校验。
- [TavilySearch 的结果数在集成中是工具实例参数] → 使用受限的 LangChain 工具入口将 Agent 选择值映射为实例参数，并测试参数上界。
- [网页内容包含提示注入或不安全 URL] → 对提取目标执行公开 URL 校验；摘要与题目 Prompt 均将外部内容标为不可信数据。
- [摘要丢失或歪曲原始资料] → 保留原始主题，约束摘要结构和长度；摘要失败时回退原输入。
- [Agent 增加出题延迟和外部 API 成本] → 提供关闭开关、默认结果数、工具调用上限、单次超时及 Agent 总超时。
- [无来源链，题目依据不可审计] → 本次不增加引用和来源持久化，题库契约维持现状。

## Migration Plan

1. 增加可选配置与 `langchain-tavily` 依赖，验证未配置 Key 时应用可启动且联网增强被跳过。
2. 实现知识获取 Agent、两个 Tavily 工具及其参数边界；使用 Fake 工具测试关键词、直接 URL、混合输入和动态参数。
3. 更新 `QUIZ_PROMPT`，接入摘要和原始输入回退；测试 Prompt 注入、摘要边界、API/持久化兼容与导入链路隔离。
4. 更新 README，运行后端测试；使用测试环境验证真实 Tavily Key 下三类输入的工具选择及无 Key 回退。
5. 回滚时移除普通出题链路的 Agent 接入和新增依赖，不涉及数据库迁移或历史数据清理。
