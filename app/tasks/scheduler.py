import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


def _job_wrapper():
    from app.tasks.weekly_crawl import run_weekly_crawl
    asyncio.run(run_weekly_crawl())


def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _job_wrapper,
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
        id="weekly_crawl",
        name="每周日凌晨2点定时采集",
    )
    scheduler.start()
    return scheduler


def stop_scheduler(scheduler):
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
