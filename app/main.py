from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.api import academic_history, catalog, chat, admin, integrations, planning, student, system
from app.core.config import settings
from app.database.mysql import engine, Base
import app.models.course
import app.models.log
import app.models.crawled
import app.models.planning

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
app.include_router(integrations.router, prefix="/api/v1/integrations", tags=["Integrations"])
app.include_router(system.router, prefix="/api/v1", tags=["System"])
app.include_router(student.router, prefix="/api/v1/student", tags=["Student Profile"])
app.include_router(catalog.router, prefix="/api/v1/catalog", tags=["Course Catalog"])
if settings.FEATURE_ACADEMIC_HISTORY:
    app.include_router(
        academic_history.router,
        prefix="/api/v1/academic-history",
        tags=["Academic History"],
    )
if settings.FEATURE_COURSE_PLANNING:
    app.include_router(planning.router, prefix="/api/v1/planning", tags=["Course Planning"])

# 高保真前端原型与 API 同源部署，避免本地联调时的跨域问题。
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/prototype", StaticFiles(directory=frontend_dir, html=True), name="prototype")

@app.get("/")
def root():
    if frontend_dir.exists():
        return RedirectResponse(url="/prototype/")
    return {"message": "选课系统智能问答 API 正在运行"}
