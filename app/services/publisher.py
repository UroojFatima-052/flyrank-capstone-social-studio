import logging

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.adapters.base import PublishResult
from app.adapters.registry import get_publisher
from app.models import (
    AttemptStatus,
    PublishAttempt,
    ScheduleSlot,
    SlotStatus,
    Variant,
    VariantStatus,
    utcnow,
)

logger = logging.getLogger(__name__)


def build_idempotency_key(variant_id: int, slot_id: int) -> str:
    return f"variant-{variant_id}-slot-{slot_id}"


def publish_slot(session: Session, slot: ScheduleSlot) -> PublishAttempt:
    variant = session.get(Variant, slot.variant_id)
    key = build_idempotency_key(variant.id, slot.id)

    existing = session.exec(
        select(PublishAttempt).where(PublishAttempt.idempotency_key == key)
    ).first()
    if existing is not None:
        logger.info("Publish already recorded for key %s, skipping", key)
        if slot.status == SlotStatus.PENDING:
            slot.status = SlotStatus.DONE
            session.add(slot)
            session.commit()
        return existing

    attempt = PublishAttempt(
        variant_id=variant.id,
        slot_id=slot.id,
        idempotency_key=key,
        status=AttemptStatus.IN_PROGRESS,
    )
    session.add(attempt)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        logger.info("Lost the race for key %s, another worker owns it", key)
        return session.exec(
            select(PublishAttempt).where(PublishAttempt.idempotency_key == key)
        ).first()

    session.refresh(attempt)

    publisher = get_publisher(variant.platform, session)
    result = publisher.publish(variant.content, key)

    attempt.status = AttemptStatus.SUCCESS if result.success else AttemptStatus.FAILED
    attempt.external_id = result.external_id
    attempt.message_url = result.message_url
    attempt.error = result.error
    attempt.attempted_at = utcnow()
    session.add(attempt)

    if result.success:
        variant.status = VariantStatus.PUBLISHED
        variant.updated_at = utcnow()
        slot.status = SlotStatus.DONE
        session.add(variant)
        session.add(slot)

    session.commit()
    session.refresh(attempt)
    return attempt