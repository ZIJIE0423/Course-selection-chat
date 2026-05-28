from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.database.mysql import Base

class ConversationLog(Base):
    __tablename__ = "conversation_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True, nullable=False)
    user_query = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    route = Column(String(50), nullable=True)
    source_type = Column(String(100), nullable=True)
    used_tools = Column(String(255), nullable=True) # JSON 序列化列表
    evidence_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

class StudentNeedSummary(Base):
    __tablename__ = "student_need_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True, nullable=False)
    course_name = Column(String(255), nullable=True)
    teacher_name = Column(String(255), nullable=True)
    preference_tags = Column(Text, nullable=True) # JSON 序列化列表
    concern_tags = Column(Text, nullable=True)    # JSON 序列化列表
    time_preference = Column(String(255), nullable=True)
    difficulty_preference = Column(String(255), nullable=True)
    assessment_preference = Column(String(255), nullable=True)
    extracted_summary = Column(Text, nullable=True)
    is_anonymized = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
