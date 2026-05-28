from langchain_openai import ChatOpenAI
from app.core.config import settings

def get_llm():
    """获取集成 DashScope 阿里云百炼的深度思考大模型 (qwen3.7-max)"""
    llm = ChatOpenAI(
        api_key=settings.DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen3.7-max",
        streaming=True,
        model_kwargs={"extra_body": {"enable_thinking": True}}
    )
    return llm
