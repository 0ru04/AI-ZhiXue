# grounded-quiz-generation Specification

## Purpose

让普通出题链路在需要时通过知识获取 Agent 查询最新公开信息，并把获得的知识摘要作为出题参考；联网增强失败或关闭时，用户仍能使用原有纯模型出题流程。

## Requirements

### Requirement: 普通出题必须尝试使用知识获取 Agent

系统 SHALL 在普通文本出题时将用户输入交给知识获取 Agent 判断是否需要联网获取知识。直接输入网页地址仍 MUST 走普通出题入口的同一 Agent 链路。

#### Scenario: 关键词输入进入 Agent 链路

- **WHEN** 用户通过普通出题入口提交不包含网页地址的学习主题
- **THEN** 系统将原始输入交给知识获取 Agent 判断是否需要搜索

#### Scenario: 直接输入网页地址进入 Agent 链路

- **WHEN** 用户通过普通出题入口提交一个公开网页地址
- **THEN** 系统仍将该输入交给知识获取 Agent，由 Agent 判断并选择网页提取工具，而不改走来源导入接口

#### Scenario: 混合输入进入 Agent 链路

- **WHEN** 用户通过普通出题入口同时提交网页地址和学习问题
- **THEN** 系统将完整输入交给知识获取 Agent，由 Agent 自主判断应搜索、提取或组合使用工具

### Requirement: Agent 必须自主选择联网工具和搜索参数

知识获取 Agent SHALL 使用 `TavilySearch` 和 `TavilyExtract` 按输入意图决定工具及参数；服务端 MUST 对可调用工具、参数范围、调用次数和执行时长施加配置约束。

#### Scenario: 关键词搜索

- **WHEN** Agent 判断输入需要查询最新或补充的网络知识
- **THEN** Agent 选择 `TavilySearch`，并按主题动态选择 `search_depth`、`max_results` 和 `time_range`

#### Scenario: 网页内容提取

- **WHEN** Agent 判断用户提供的网页地址适合直接作为知识来源
- **THEN** Agent 选择 `TavilyExtract` 获取该网页内容

#### Scenario: 混合输入选择工具

- **WHEN** 输入包含网页地址及相关问题
- **THEN** Agent 可根据问题需要选择网页提取、关键词搜索或组合调用，而不受固定分支策略限制

#### Scenario: 搜索结果数受限

- **WHEN** Agent 为搜索选择结果数
- **THEN** 系统以配置的默认结果数作为缺省值，并将 Agent 选择限制在配置允许的最大范围内

#### Scenario: 工具调用次数和时长受限

- **WHEN** Agent 执行一个知识获取请求
- **THEN** 系统限制该请求的工具调用总数和总执行时长，超出限制时停止联网步骤

#### Scenario: 不安全 URL 不得传给提取工具

- **WHEN** Agent 请求提取私网地址、包含凭据的地址或未通过公开 URL 校验的地址
- **THEN** 系统拒绝将该地址传给联网工具，并将本次知识获取视为失败

### Requirement: Agent 知识摘要必须注入出题 Prompt

系统 SHALL 将有效的 Agent 知识摘要作为参考资料提供给题目生成 Prompt，并将联网内容视为不可信数据。

#### Scenario: 摘要用于生成题目

- **WHEN** Agent 成功获得并整理出有效知识摘要
- **THEN** 题目生成 Prompt 同时收到用户的学习主题和标记为参考资料的知识摘要

#### Scenario: 摘要长度与关键点受限

- **WHEN** Agent 返回知识摘要
- **THEN** 摘要不超过 1,200 字，包含 3 至 8 个关键点且每项不超过 80 字

#### Scenario: 联网内容包含提示注入

- **WHEN** 搜索或提取结果中包含要求改变角色、泄露信息或忽略规则的内容
- **THEN** 系统将这些结果作为不可信参考资料处理，不执行其中的指令

### Requirement: 联网增强必须可配置且可选

系统 SHALL 提供联网功能开关、Tavily API Key、默认搜索结果数和 Agent 执行限制配置；联网配置缺失或关闭 MUST NOT 阻止普通出题。

#### Scenario: 搜索开关关闭

- **WHEN** 后端关闭知识获取 Agent 功能
- **THEN** 系统跳过联网步骤并使用用户原始输入进行原有纯模型出题

#### Scenario: 缺少 Tavily API Key

- **WHEN** 后端未配置 Tavily API Key
- **THEN** 系统跳过联网步骤，应用仍可启动且普通出题继续可用

#### Scenario: 使用默认结果数

- **WHEN** Agent 未为搜索明确选择结果数
- **THEN** 系统使用配置的默认结果数，并遵守配置的最大结果数限制

### Requirement: Agent 失败必须回退原有出题链路

当联网未启用、Agent 或工具调用失败、超时、结果为空或摘要无效时，系统 SHALL 使用用户原始输入执行原有纯模型出题，且 MUST NOT 返回新的联网专属错误。

#### Scenario: Agent 执行失败

- **WHEN** Agent 执行或工具调用发生异常
- **THEN** 系统记录不含密钥和网页正文的告警，并使用用户原始输入执行原有纯模型出题

#### Scenario: Agent 超出执行限制

- **WHEN** Agent 达到工具调用上限或知识获取总时长上限
- **THEN** 系统停止本次联网步骤并使用用户原始输入回退出题

#### Scenario: 无有效摘要

- **WHEN** Agent 返回空结果、过短内容或不符合摘要约束的结果
- **THEN** 系统放弃该摘要并使用用户原始输入回退出题

### Requirement: 现有接口、持久化与导入链路必须保持兼容

本能力 SHALL 复用现有普通出题接口及题库结构；联网摘要不得改变题库保存的用户原始输入，用户主动导入材料的出题链路 MUST NOT 调用知识获取 Agent。

#### Scenario: 普通出题 API 兼容

- **WHEN** 客户端继续使用原有 `POST /api/v1/quiz/generate` 请求
- **THEN** 请求和成功响应结构保持不变，客户端无需新增字段或错误处理

#### Scenario: 用户原始输入保持不变

- **WHEN** 系统使用 Agent 摘要生成题目并保存题库
- **THEN** 题库的 `user_input` 仍为用户提交的原始输入

#### Scenario: 导入材料不触发知识获取 Agent

- **WHEN** 用户通过现有 `/source/parse/*` 和 `/source/generate` 链路使用导入材料出题
- **THEN** 系统继续只使用导入材料生成题目，不调用 `TavilySearch` 或 `TavilyExtract`
