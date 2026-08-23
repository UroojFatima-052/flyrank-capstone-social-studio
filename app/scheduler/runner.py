import logging

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database import engine
from app.scheduler.worker import recover_interrupted_attempts, run_due_publishes
from sqlmodel import Session

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(
    jobstores={"default": SQLAlchemyJobStore(engine=engine)},
    timezone="UTC",
)

PUBLISH_JOB_ID = "publish-due-slots"


def start_scheduler() -> None:
    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled by config")
        return

    with Session(engine) as session:
        recovered = recover_interrupted_attempts(session)
        if recovered:
            logger.warning("Recovered %s interrupted attempt(s) on startup", recovered)

    scheduler.add_job(
        run_due_publishes,
        trigger="interval",
        seconds=settings.scheduler_interval_seconds,
        id=PUBLISH_JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started, checking every %s seconds",
        settings.scheduler_interval_seconds,
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")