import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from app.crawler.official_notice_crawler import crawl_official_notices
from app.crawler.forum_review_crawler import crawl_forum_reviews
from app.database.mysql import SessionLocal
from app.models.crawled import CrawledDocument


async def run_weekly_crawl():
    print("=== 开始每周定时采集 ===\n")

    all_docs = []
    try:
        notices = await crawl_official_notices()
        all_docs.extend(notices)
        print(f"  官方公告采集: {len(notices)} 条")
    except Exception as e:
        print(f"  官方公告采集失败: {e}")

    try:
        reviews = await crawl_forum_reviews()
        all_docs.extend(reviews)
        print(f"  论坛评价采集: {len(reviews)} 条")
    except Exception as e:
        print(f"  论坛评价采集失败: {e}")

    total = len(all_docs)
    new_count = 0
    skip_count = 0
    fail_count = 0

    db = SessionLocal()
    try:
        for doc in all_docs:
            try:
                existing = db.query(CrawledDocument).filter(
                    CrawledDocument.hash_id == doc["hash_id"]
                ).first()
                if existing:
                    skip_count += 1
                    continue

                new_doc = CrawledDocument(
                    title=doc["title"],
                    content=doc["content"],
                    source_url=doc["source_url"],
                    source_type=doc["source_type"],
                    source_tier=doc["source_tier"],
                    hash_id=doc["hash_id"],
                    status="pending",
                )
                db.add(new_doc)
                new_count += 1
            except Exception as e:
                print(f"  写入失败 [{doc.get('source_url', '?')}]: {e}")
                db.rollback()
                fail_count += 1

        db.commit()
    finally:
        db.close()

    print(f"\n=== 采集统计 ===")
    print(f"  采集总数: {total}")
    print(f"  新增入库: {new_count}")
    print(f"  跳过(重复): {skip_count}")
    print(f"  失败: {fail_count}")
    print(f"================\n")


if __name__ == "__main__":
    asyncio.run(run_weekly_crawl())
