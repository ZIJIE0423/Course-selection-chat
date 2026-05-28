import os
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from app.core.config import settings

def get_embeddings():
    """获取文本嵌入模型"""
    return DashScopeEmbeddings(
        dashscope_api_key=settings.DASHSCOPE_API_KEY,
        model="text-embedding-v3"
    )

def get_vector_store():
    """获取 Chroma 向量数据库实例"""
    embeddings = get_embeddings()
    # 确保目录存在
    os.makedirs(settings.CHROMA_DB_PATH, exist_ok=True)
    
    vector_store = Chroma(
        collection_name="course_knowledge",
        embedding_function=embeddings,
        persist_directory=settings.CHROMA_DB_PATH
    )
    return vector_store

def add_documents_to_store(docs):
    """向向量数据库添加文档"""
    vector_store = get_vector_store()
    vector_store.add_documents(docs)

def clear_vector_store():
    """清空向量数据库"""
    import shutil
    if os.path.exists(settings.CHROMA_DB_PATH):
        shutil.rmtree(settings.CHROMA_DB_PATH)
