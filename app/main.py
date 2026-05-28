from fastapi import FastAPI
from app.api import chat, admin
from app.database.mysql import engine, Base
import app.models.course
import app.models.log
import app.models.crawled

# 初始化数据库表
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Warning: Database connection failed during initialization: {e}")

app = FastAPI(
    title="选课系统智能问答 API",
    description="基于 LangGraph 和 Qwen3.7-max 的选课系统智能问答服务",
    version="1.0.0"
)

# 注册路由
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])

@app.get("/")
def root():
    return {"message": "选课系统智能问答 API 正在运行"}
