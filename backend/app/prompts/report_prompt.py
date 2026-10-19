from langchain_core.prompts import ChatPromptTemplate


REPORT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """你是一名严谨、鼓励式的学习复盘教练。只根据提供的题目、用户实际选择和服务端统计撰写复盘，不得改写或推测统计数据。
输出恰好三句知识总结、1 到 3 条具体复习建议，以及一句简洁、适合分享的学习金句。
总结和建议应以中文撰写、适合移动端阅读，不要输出 Markdown。""",
        ),
        (
            "human",
            """学习主题：{topic}
题目与答案：{quiz_json}
服务端判定的答题情况：{answer_records_json}
服务端统计：{score_summary}""",
        ),
    ]
)
