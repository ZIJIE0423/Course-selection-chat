from app.crawler.playwright_client import fetch_page
from app.crawler.crawler_cleaner import clean_to_document
from app.core.config import settings

DEFAULT_NOTICE_URLS = [
    "https://jwgl.ouc.edu.cn/",
]

async def crawl_official_notices() -> list[dict]:
    urls = settings.CRAWL_NOTICE_URLS or DEFAULT_NOTICE_URLS
    results = []
    for url in urls:
        html = await fetch_page(url)
        if html is None:
            continue
        doc = clean_to_document(
            raw_html=html,
            source_url=url,
            source_type="official_notice",
            source_tier="tier_2_official_document",
        )
        if doc["content"]:
            results.append(doc)
    return results
