from app.crawler.playwright_client import fetch_page
from app.crawler.crawler_cleaner import clean_to_document
from app.core.config import settings

DEFAULT_FORUM_URLS = [
    "https://example.edu/forum",
]

async def crawl_forum_reviews() -> list[dict]:
    urls = settings.CRAWL_FORUM_URLS or DEFAULT_FORUM_URLS
    results = []
    for url in urls:
        html = await fetch_page(url)
        if html is None:
            continue
        doc = clean_to_document(
            raw_html=html,
            source_url=url,
            source_type="student_review",
            source_tier="tier_3_student_review",
        )
        if doc["content"]:
            results.append(doc)
    return results
