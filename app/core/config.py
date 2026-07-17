import os
from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
    # 模型供应商保持可配置；LLM_PROVIDER=none 时仅使用确定性解析与检索。
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "none")
    MODEL_NAME = os.getenv("MODEL_NAME", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
    LLM_API_KEY_ENV = os.getenv("LLM_API_KEY_ENV", "")
    ENABLE_REASONING = _as_bool(os.getenv("ENABLE_REASONING"), False)
    # 开箱即用的本地默认值；生产环境可通过同一变量切换到 MySQL。
    MYSQL_URL = os.getenv("MYSQL_URL", "sqlite:///./course_db.sqlite")
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_data")
    INTEGRATION_TOKEN = os.getenv("INTEGRATION_TOKEN", "")
    MAX_HISTORY_UPLOAD_MB = int(os.getenv("MAX_HISTORY_UPLOAD_MB", "10"))
    HISTORY_OCR_ENDPOINT = os.getenv("HISTORY_OCR_ENDPOINT", "")
    HISTORY_OCR_API_KEY = os.getenv("HISTORY_OCR_API_KEY", "")
    FEATURE_COURSE_PLANNING = _as_bool(os.getenv("FEATURE_COURSE_PLANNING"), True)
    FEATURE_ACADEMIC_HISTORY = _as_bool(os.getenv("FEATURE_ACADEMIC_HISTORY"), True)
    FEATURE_SCHEDULE_CONFLICT = _as_bool(os.getenv("FEATURE_SCHEDULE_CONFLICT"), False)
    FEATURE_COURSE_FEEDBACK = _as_bool(os.getenv("FEATURE_COURSE_FEEDBACK"), False)
    FEATURE_STUDENT_REVIEW_RAG = _as_bool(os.getenv("FEATURE_STUDENT_REVIEW_RAG"), False)
    CRAWL_NOTICE_URLS = [u.strip() for u in os.getenv("CRAWL_NOTICE_URLS", "").split(",") if u.strip()]
    CRAWL_FORUM_URLS = [u.strip() for u in os.getenv("CRAWL_FORUM_URLS", "").split(",") if u.strip()]
    
settings = Settings()
