from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models import Campaign, Platform, Post, SlotStatus, Variant, VariantStatus
from app.services import schedule as schedule_service
from app.services.variants import VariantError


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


@pytest.fixture
def variant(session):
    post = Post(title="Test", content="Body.", source_url="https://example.com/idempotency")
    session.add(post)
    session.commit()
    session.refresh(post)

    campaign = Campaign(post_id=post.id, name="Test campaign")
    session.add(campaign)
    session.commit()
    session.refresh(campaign)

    variant = Variant(
        campaign_id=campaign.id,
        post_id=post.id,
        platform=Platform.X,
        content=VALID_X,
    )
    session.add(variant)
    session.commit()
    session.refresh(variant)
    return variant


def future() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=1)


def past() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=1)


def test_cannot_schedule_a_draft_variant(session, variant):
    result = schedule_service.schedule_variant(session, variant, future())
    assert isinstance(result, VariantError)
    assert "approved" in result.reason


def test_cannot_schedule_a_rejected_variant(session, variant):
    variant.status = VariantStatus.REJECTED
    session.add(variant)
    session.commit()
    result = schedule_service.schedule_variant(session, variant, future())
    assert isinstance(result, VariantError)


def test_approved_variant_can_be_scheduled(session, variant):
    variant.status = VariantStatus.APPROVED
    session.add(variant)
    session.commit()
    slot = schedule_service.schedule_variant(session, variant, future())
    assert slot.variant_id == variant.id
    assert slot.status == SlotStatus.PENDING


def test_cannot_schedule_in_the_past(session, variant):
    variant.status = VariantStatus.APPROVED
    session.add(variant)
    session.commit()
    result = schedule_service.schedule_variant(session, variant, past())
    assert isinstance(result, VariantError)
    assert "future" in result.reason


def test_cannot_double_schedule_the_same_variant(session, variant):
    variant.status = VariantStatus.APPROVED
    session.add(variant)
    session.commit()
    schedule_service.schedule_variant(session, variant, future())
    result = schedule_service.schedule_variant(session, variant, future())
    assert isinstance(result, VariantError)
    assert "pending slot" in result.reason


def test_cancelling_frees_the_variant_for_rescheduling(session, variant):
    variant.status = VariantStatus.APPROVED
    session.add(variant)
    session.commit()
    slot = schedule_service.schedule_variant(session, variant, future())
    schedule_service.cancel_slot(session, slot.id)
    second = schedule_service.schedule_variant(session, variant, future())
    assert second.status == SlotStatus.PENDING
    assert second.id != slot.id