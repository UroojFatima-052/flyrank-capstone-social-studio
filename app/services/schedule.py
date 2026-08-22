from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models import ScheduleSlot, SlotStatus, Variant, VariantStatus
from app.services.variants import VariantError


def schedule_variant(
    session: Session, variant: Variant, scheduled_for: datetime
) -> ScheduleSlot | VariantError:
    if variant.status != VariantStatus.APPROVED:
        return VariantError(
            reason=(
                f"Only approved variants can be scheduled. "
                f"This one is {variant.status.value}."
            )
        )

    if scheduled_for.tzinfo is None:
        scheduled_for = scheduled_for.replace(tzinfo=timezone.utc)

    if scheduled_for <= datetime.now(timezone.utc):
        return VariantError(reason="Scheduled time must be in the future.")

    existing = session.exec(
        select(ScheduleSlot)
        .where(ScheduleSlot.variant_id == variant.id)
        .where(ScheduleSlot.status == SlotStatus.PENDING)
    ).first()
    if existing is not None:
        return VariantError(
            reason=f"This variant already has a pending slot (id {existing.id})."
        )

    slot = ScheduleSlot(variant_id=variant.id, scheduled_for=scheduled_for)
    session.add(slot)
    session.commit()
    session.refresh(slot)
    return slot


def list_slots(session: Session) -> list[ScheduleSlot]:
    statement = select(ScheduleSlot).order_by(ScheduleSlot.scheduled_for)
    return list(session.exec(statement).all())


def cancel_slot(session: Session, slot_id: int) -> ScheduleSlot | None:
    slot = session.get(ScheduleSlot, slot_id)
    if slot is None:
        return None
    slot.status = SlotStatus.CANCELLED
    session.add(slot)
    session.commit()
    session.refresh(slot)
    return slot