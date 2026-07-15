import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
    # 开箱即用的本地默认值；生产环境可通过同一变量切换到 MySQL。
    MYSQL_URL = os.getenv("MYSQL_URL", "sqlite:///./course_db.sqlite")
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_data")
    CRAWL_NOTICE_URLS = [u.strip() for u in os.getenv("CRAWL_NOTICE_URLS", "").split(",") if u.strip()]
    CRAWL_FORUM_URLS = [u.strip() for u in os.getenv("CRAWL_FORUM_URLS", "").split(",") if u.strip()]
    
settings = Settings()
