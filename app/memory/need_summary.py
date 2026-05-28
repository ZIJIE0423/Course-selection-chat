import json
from sqlalchemy.orm import Session
from app.models.log import StudentNeedSummary
from app.database.mysql import SessionLocal
from app.memory.conversation_logger import log_conversation
from app.memory.preference_extractor import extract_preferences

def process_and_save_needs(
    session_id: str,
    user_query: str,
    answer: str,
    route: str,
    source_type: str,
    used_tools: list,
    evidence_summary: str
) -> bool:
    """整合操作：先记录对话，再提取需求并沉淀入库"""
    
    # 1. 记录对话
    log_saved = log_conversation(
        session_id, user_query, answer, route, source_type, used_tools, evidence_summary
    )
    
    # 2. 提取需求 (异步或者在后台任务中调用会更好，但此处按流程同步执行或交给调用方后台)
    prefs = extract_preferences(user_query, answer)
    
    if not prefs:
        return False
        
    # 3. 需求沉淀入库
    db: Session = SessionLocal()
    try:
        need_entry = StudentNeedSummary(
            session_id=session_id,
            course_name=prefs.get("course_name", ""),
            teacher_name=prefs.get("teacher_name", ""),
            preference_tags=json.dumps(prefs.get("preference_tags", []), ensure_ascii=False),
            concern_tags=json.dumps(prefs.get("concern_tags", []), ensure_ascii=False),
            time_preference=prefs.get("time_preference", ""),
            difficulty_preference=prefs.get("difficulty_preference", ""),
            assessment_preference=prefs.get("assessment_preference", ""),
            extracted_summary=prefs.get("extracted_summary", ""),
            is_anonymized=True
        )
        db.add(need_entry)
        db.commit()
        return True
    except Exception as e:
        print(f"Failed to save student need summary: {e}")
        db.rollback()
        return False
    finally:
        db.close()
