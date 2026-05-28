import json
from sqlalchemy.orm import Session
from app.models.log import ConversationLog
from app.database.mysql import SessionLocal

def log_conversation(
    session_id: str,
    user_query: str,
    answer: str,
    route: str,
    source_type: str,
    used_tools: list,
    evidence_summary: str
) -> bool:
    """持久化存储对话日志"""
    db: Session = SessionLocal()
    try:
        tools_str = json.dumps(used_tools, ensure_ascii=False) if used_tools else "[]"
        log_entry = ConversationLog(
            session_id=session_id,
            user_query=user_query,
            answer=answer,
            route=route,
            source_type=source_type,
            used_tools=tools_str,
            evidence_summary=evidence_summary
        )
        db.add(log_entry)
        db.commit()
        return True
    except Exception as e:
        print(f"Failed to log conversation: {e}")
        db.rollback()
        return False
    finally:
        db.close()
