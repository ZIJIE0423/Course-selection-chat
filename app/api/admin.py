from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime
import json
from app.database.mysql import get_db
from app.models.log import StudentNeedSummary, ConversationLog
from app.models.crawled import CrawledDocument
from app.rag.incremental_indexer import index_single_document

router = APIRouter()

# TODO: 预留后续认证与权限管控的扩展空间
# def verify_admin(token: str = Depends(oauth2_scheme)): ...


@router.get("/needs/recent")
def get_recent_needs(limit: int = 50, db: Session = Depends(get_db)):
    needs = db.query(StudentNeedSummary).order_by(desc(StudentNeedSummary.created_at)).limit(limit).all()
    return {"data": needs}


@router.get("/needs/tags")
def get_needs_tags(db: Session = Depends(get_db)):
    needs = db.query(StudentNeedSummary).all()
    preference_counts = {}
    concern_counts = {}
    for need in needs:
        try:
            if need.preference_tags:
                tags = json.loads(need.preference_tags)
                for t in tags:
                    preference_counts[t] = preference_counts.get(t, 0) + 1
            if need.concern_tags:
                tags = json.loads(need.concern_tags)
                for t in tags:
                    concern_counts[t] = concern_counts.get(t, 0) + 1
        except Exception:
            pass
    return {"preferences": preference_counts, "concerns": concern_counts}


@router.get("/conversations/recent")
def get_recent_conversations(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(ConversationLog).order_by(desc(ConversationLog.created_at)).limit(limit).all()
    return {"data": logs}


@router.get("/crawled/pending")
def get_crawled_pending(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = "pending",
    db: Session = Depends(get_db),
):
    docs = (
        db.query(CrawledDocument)
        .filter(CrawledDocument.status == status)
        .order_by(desc(CrawledDocument.crawled_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": db.query(CrawledDocument).filter(CrawledDocument.status == status).count(),
        "data": [
            {
                "id": d.id,
                "title": d.title,
                "content_preview": d.content[:200] if d.content else "",
                "source_url": d.source_url,
                "source_type": d.source_type,
                "source_tier": d.source_tier,
                "hash_id": d.hash_id,
                "status": d.status,
                "crawled_at": d.crawled_at.isoformat() if d.crawled_at else None,
                "reviewed_at": d.reviewed_at.isoformat() if d.reviewed_at else None,
            }
            for d in docs
        ],
    }


@router.post("/crawled/{doc_id}/approve")
def approve_crawled_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(CrawledDocument).filter(CrawledDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status not in ("pending", "rejected"):
        raise HTTPException(status_code=400, detail=f"Cannot approve document with status '{doc.status}'")
    doc.status = "approved"
    doc.reviewed_at = datetime.now()
    db.commit()
    return {"message": "Document approved", "id": doc_id, "status": doc.status}


@router.post("/crawled/{doc_id}/reject")
def reject_crawled_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(CrawledDocument).filter(CrawledDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.status = "rejected"
    doc.reviewed_at = datetime.now()
    db.commit()
    return {"message": "Document rejected", "id": doc_id, "status": doc.status}


@router.post("/crawled/{doc_id}/index")
def index_crawled_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(CrawledDocument).filter(CrawledDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "approved":
        raise HTTPException(status_code=400, detail=f"Document must be 'approved' to index, current status: '{doc.status}'")

    success = index_single_document(doc_id)
    if success:
        return {"message": "Document indexed into ChromaDB", "id": doc_id, "status": "indexed"}
    else:
        raise HTTPException(status_code=500, detail="Failed to index document into ChromaDB")
