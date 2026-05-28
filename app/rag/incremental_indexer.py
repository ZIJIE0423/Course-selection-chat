from datetime import datetime
from langchain_core.documents import Document
from app.database.mysql import SessionLocal
from app.models.crawled import CrawledDocument
from app.rag.text_splitter import split_documents
from app.rag.vector_store import add_documents_to_store


def index_single_document(doc_id: int) -> bool:
    db = SessionLocal()
    try:
        doc = db.query(CrawledDocument).filter(CrawledDocument.id == doc_id).first()
        if not doc or doc.status != "approved":
            return False

        raw_docs = [(doc.content, {
            "file_name": doc.title or doc.source_url,
            "source_type": doc.source_type or "",
            "source_tier": doc.source_tier or "",
            "is_official": doc.source_type == "official_notice",
            "source_url": doc.source_url,
            "crawled_at": doc.crawled_at.isoformat() if doc.crawled_at else "",
            "course_name": "",
            "teacher_name": "",
            "course_code": "",
        })]
        chunks = split_documents(raw_docs)

        if chunks:
            add_documents_to_store(chunks)

        doc.status = "indexed"
        db.commit()
        return True
    except Exception as e:
        print(f"[incremental_indexer] 索引文档 {doc_id} 失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def index_approved_documents() -> dict:
    db = SessionLocal()
    try:
        approved = db.query(CrawledDocument).filter(
            CrawledDocument.status == "approved"
        ).all()
        doc_ids = [d.id for d in approved]
    finally:
        db.close()

    success = 0
    failed = 0
    for doc_id in doc_ids:
        if index_single_document(doc_id):
            success += 1
        else:
            failed += 1

    return {"total": len(doc_ids), "success": success, "failed": failed}
