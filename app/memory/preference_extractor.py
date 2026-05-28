import json
from langchain_core.messages import SystemMessage, HumanMessage
from app.agent.llm import get_llm

PROMPT_TEMPLATE = """
你是一个学生选课需求提取助手。你的任务是从以下学生和智能体的对话中，提取出学生的核心选课需求和关注点。

【脱敏要求】
严格执行数据脱敏规则，禁止在输出中包含姓名、学号、手机号等任何用户敏感个人信息。只保留课程名、教师名以及抽象需求。

【提取字段要求】
请输出一个合法的 JSON 对象，包含以下字段：
- course_name: (string) 关注的课程名称，如未提及为空字符串
- teacher_name: (string) 关注的教师姓名，如未提及为空字符串
- preference_tags: (list of string) 偏好标签，例如 ["AI方向", "项目实践"] 等
- concern_tags: (list of string) 关注点标签，例如 ["作业量", "给分宽松度", "考试难度", "教师风格", "课程冲突", "毕业要求"] 等
- time_preference: (string) 时间偏好，如 "希望早上没课"
- difficulty_preference: (string) 难度偏好，如 "希望不硬核"
- assessment_preference: (string) 考核方式偏好，如 "无期末考试"、"论文考核"
- extracted_summary: (string) 对该生选课需求的简短一句话摘要

对话记录：
用户：{user_query}
系统：{answer}

请只返回 JSON 对象，不要包含其他文本。
"""

def extract_preferences(user_query: str, answer: str) -> dict:
    """利用大模型提取学生选课需求"""
    try:
        llm = get_llm()
        prompt = PROMPT_TEMPLATE.format(user_query=user_query, answer=answer)
        
        messages = [
            HumanMessage(content=prompt)
        ]
        
        # 为了稳定输出 JSON，如果不直接支持 with_structured_output，可以通过约束解析
        response = llm.invoke(messages)
        content = response.content
        
        # 清理可能存在的 Markdown 代码块标记
        content = content.replace("```json", "").replace("```", "").strip()
        
        return json.loads(content)
    except Exception as e:
        print(f"Failed to extract preferences: {e}")
        return {}
