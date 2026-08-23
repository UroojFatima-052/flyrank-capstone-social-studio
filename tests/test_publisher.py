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
    Variant,
    VariantStatus,
)
from app.services import publisher as publisher_service
from app.services.publisher import build_idempotency_key, publish_slot


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


def make_slot(session: Session, platform: Platform = Platform.X) -> ScheduleSlot:
    post = Post(title="Test", content="Body.", source_url="https://example.com/idempotency")
    session.add(post)
    session.commit()
    session.refresh(post)

    campaign = Campaign(post_id=post.id, name=f"Campaign for {platform.value}")
    session.add(campaign)
    session.commit()
    session.refresh(campaign)

    variant = Variant(
        campaign_id=campaign.id,
        post_id=post.id,
        platform=platform,
        content=VALID_X,
        status=VariantStatus.APPROVED,
    )
    session.add(variant)
    session.commit()
    session.refresh(variant)

    slot = ScheduleSlot(
        variant_id=variant.id,
        scheduled_for=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    session.add(slot)
    session.commit()
    session.refresh(slot)
    return slot


def test_idempotency_key_is_stable():
    assert build_idempotency_key(7, 3) == build_idempotency_key(7, 3)
    assert build_idempotency_key(7, 3) != build_idempotency_key(7, 4)


def test_publish_succeeds_and_records_an_attempt(session):
    slot = make_slot(session)
    attempt = publish_slot(session, slot)
    assert attempt.status == AttemptStatus.SUCCESS
    assert attempt.external_id is not None
    assert attempt.message_url is not None


def test_publishing_twice_creates_one_attempt(session):
    slot = make_slot(session)
    first = publish_slot(session, slot)
    second = publish_slot(session, slot)

    assert first.id == second.id
    assert first.external_id == second.external_id

    attempts = session.exec(select(PublishAttempt)).all()
    assert len(attempts) == 1


def test_publishing_twice_reaches_the_adapter_once(session):
    slot = make_slot(session)
    publish_slot(session, slot)
    publish_slot(session, slot)
    publish_slot(session, slot)

    posts = session.exec(select(MockPost)).all()
    assert len(posts) == 1


def test_successful_publish_marks_variant_published(session):
    slot = make_slot(session)
    attempt = publish_slot(session, slot)
    variant = session.get(Variant, attempt.variant_id)
    assert variant.status == VariantStatus.PUBLISHED


def test_adapter_swap_changes_the_destination(session, monkeypatch):
    from app.adapters import registry

    monkeypatch.setattr(registry.settings, "discord_adapter", "mock_x")
    slot = make_slot(session, platform=Platform.DISCORD)
    attempt = publish_slot(session, slot)

    assert attempt.status == AttemptStatus.SUCCESS
    assert attempt.external_id.startswith("x-")

    posts = session.exec(select(MockPost)).all()
    assert len(posts) == 1