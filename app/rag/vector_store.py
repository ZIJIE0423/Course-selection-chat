import os
import hashlib
import math
import re

from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.embeddings import Embeddings
from app.core.config import settings


class LocalHashEmbeddings(Embeddings):
    """Dependency-free deterministic embeddings for synthetic M1 evaluation.

    This is not a replacement for a production semantic embedding model. It
    permits reproducible offline indexing and makes the provider choice
    explicit via ``EMBEDDING_PROVIDER=local_hash``.
    """

    dimensions = 384

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        normalized = re.sub(r"\s+", "", text.lower())
        features = [normalized[i : i + 2] for i in range(max(0, len(normalized) - 1))]
        features.extend(re.findall(r"[a-z0-9]+", text.lower()))
        for feature in features or [normalized]:
            bucket = int.from_bytes(hashlib.sha256(feature.encode("utf-8")).digest()[:4], "big")
            vector[bucket % self.dimensions] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def get_embeddings():
    """获取文本嵌入模型"""
    if settings.EMBEDDING_PROVIDER.strip().lower() == "local_hash":
        return LocalHashEmbeddings()
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
