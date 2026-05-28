from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database.mysql import Base

class CrawledDocument(Base):
    __tablename__ = "crawled_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    source_url = Column(String(512), index=True, nullable=False)
    source_type = Column(String(50), nullable=True)
    source_tier = Column(String(50), nullable=True)
    hash_id = Column(String(64), unique=True, index=True, nullable=False)
    status = Column(String(20), default="pending", index=True)  # pending, approved, rejected, indexed
    crawled_at = Column(DateTime, default=func.now())
    reviewed_at = Column(DateTime, nullable=True)
