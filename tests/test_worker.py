from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import (
    AttemptStatus,
    Campaign,
    MockPost,
    Platform,
    Post,
    PublishAttempt,
    ScheduleSlot,
    SlotStatus,
    Variant,
    VariantStatus,
)
from app.scheduler.worker import find_due_slots, recover_interrupted_attempts
from app.services.publisher import publish_slot


VALID_X = (
    "Rebuilt the retry logic this week and learned a lot about constraints. "
    "Read more at https://example.com/idempotency #backend"
)


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def make_slot(session: Session, scheduled_for: datetime) -> ScheduleSlot:
    post = Post(title="T", content="B.", source_url="https://example.com/idempotency")
    session.add(post)
    session.commit()
    session.refresh(post)

    campaign = Campaign(post_id=post.id, name=f"Campaign {scheduled_for.isoformat()}")
    session.add(campaign)
    session.commit()
    session.refresh(campaign)

    variant = Variant(
        campaign_id=campaign.id,
        post_id=post.id,
        platform=Platform.X,
        content=VALID_X,
        status=VariantStatus.APPROVED,
    )
    session.add(variant)
    session.commit()
    session.refresh(variant)

    slot = ScheduleSlot(variant_id=variant.id, scheduled_for=scheduled_for)
    session.add(slot)
    session.commit()
    session.refresh(slot)
    return slot


def past() -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=5)


def future() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=2)


def test_due_slots_include_past_pending_slots(session):
    slot = make_slot(session, past())
    due = find_due_slots(session)
    assert [s.id for s in due] == [slot.id]


def test_due_slots_exclude_future_slots(session):
    make_slot(session, future())
    assert find_due_slots(session) == []


def test_due_slots_exclude_cancelled_slots(session):
    slot = make_slot(session, past())
    slot.status = SlotStatus.CANCELLED
    session.add(slot)
    session.commit()
    assert find_due_slots(session) == []


def test_published_slot_is_no_longer_due(session):
    slot = make_slot(session, past())
    publish_slot(session, slot)
    assert find_due_slots(session) == []


def test_recovery_marks_interrupted_attempts_failed(session):
    slot = make_slot(session, past())
    attempt = PublishAttempt(
        variant_id=slot.variant_id,
        slot_id=slot.id,
        idempotency_key=f"variant-{slot.variant_id}-slot-{slot.id}",
        status=AttemptStatus.IN_PROGRESS,
    )
    session.add(attempt)
    session.commit()

    recovered = recover_interrupted_attempts(session)
    session.refresh(attempt)

    assert recovered == 1
    assert attempt.status == AttemptStatus.FAILED
    assert "interrupted" in attempt.error or "stopped" in attempt.error


def test_recovery_does_nothing_when_no_attempts_are_stuck(session):
    make_slot(session, past())
    assert recover_interrupted_attempts(session) == 0


def test_interrupted_slot_is_never_republished(session):
    slot = make_slot(session, past())

    attempt = PublishAttempt(
        variant_id=slot.variant_id,
        slot_id=slot.id,
        idempotency_key=f"variant-{slot.variant_id}-slot-{slot.id}",
        status=AttemptStatus.IN_PROGRESS,
    )
    session.add(attempt)
    session.commit()

    recover_interrupted_attempts(session)
    publish_slot(session, slot)

    posts = session.exec(select(MockPost)).all()
    assert len(posts) == 0

    attempts = session.exec(select(PublishAttempt)).all()
    assert len(attempts) == 1