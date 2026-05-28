import chromadb
from app.core.config import settings

def get_chroma_client():
    """获取本地 ChromaDB 客户端"""
    client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
    return client
