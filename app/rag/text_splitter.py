import uuid
import time
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

def split_documents(docs):
    """
    对长文档进行切分
    每个 chunk 约 500-800 字符，保留一定 overlap
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100,
        length_function=len,
        is_separator_regex=False,
    )
    
    split_docs = []
    
    for content, metadata in docs:
        chunks = text_splitter.split_text(content)
        for i, chunk in enumerate(chunks):
            # 复制基础 metadata 并追加 chunk 相关元数据
            chunk_meta = metadata.copy()
            chunk_meta["doc_id"] = str(uuid.uuid4())
            chunk_meta["created_at"] = int(time.time())
            chunk_meta["chunk_index"] = i
            
            # TODO: 如果有明确格式，可在这里尝试提取 course_name, teacher_name 等
            # 这里先设为默认值
            chunk_meta["course_name"] = ""
            chunk_meta["teacher_name"] = ""
            chunk_meta["course_code"] = ""
            
            # 将字典中为空或不支持的类型转为空字符串，以适应 ChromaDB 元数据要求
            for k, v in chunk_meta.items():
                if v is None:
                    chunk_meta[k] = ""
            
            doc = Document(page_content=chunk, metadata=chunk_meta)
            split_docs.append(doc)
            
    return split_docs
