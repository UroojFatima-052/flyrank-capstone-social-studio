import logging
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.database import engine
from app.models import AttemptStatus, PublishAttempt, ScheduleSlot, SlotStatus
from app.services.publisher import publish_slot

logger = logging.getLogger(__name__)


def find_due_slots(session: Session) -> list[ScheduleSlot]:
    now = datetime.now(timezone.utc)
    statement = (
        select(ScheduleSlot)
        .where(ScheduleSlot.status == SlotStatus.PENDING)
        .where(ScheduleSlot.scheduled_for <= now)
        .order_by(ScheduleSlot.scheduled_for)
    )
    return list(session.exec(statement).all())


def recover_interrupted_attempts(session: Session) -> int:
    statement = select(PublishAttempt).where(
        PublishAttempt.status == AttemptStatus.IN_PROGRESS
    )
    stuck = list(session.exec(statement).all())

    for attempt in stuck:
        logger.warning(
            "Attempt %s for key %s was interrupted, marking failed",
            attempt.id,
            attempt.idempotency_key,
        )
        attempt.status = AttemptStatus.FAILED
        attempt.error = "Worker stopped before this publish finished."
        session.add(attempt)

    if stuck:
        session.commit()

    return len(stuck)


def run_due_publishes() -> int:
    published = 0
    with Session(engine) as session:
        for slot in find_due_slots(session):
            logger.info("Publishing slot %s", slot.id)
            attempt = publish_slot(session, slot)
            if attempt.status == AttemptStatus.SUCCESS:
                published += 1
            else:
                logger.warning(
                    "Slot %s failed: %s", slot.id, attempt.error
                )
    return published