import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models import Campaign, Platform, Post, Variant, VariantStatus
from app.services import variants as variant_service
from app.services.transitions import can_transition
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
    post = Post(title="Test post", content="Body text.", source_url="https://example.com/idempotency")
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


def test_new_variant_is_draft(variant):
    assert variant.status == VariantStatus.DRAFT


def test_approve_moves_to_approved(session, variant):
    result = variant_service.approve(session, variant)
    assert result.status == VariantStatus.APPROVED


def test_cannot_approve_twice(session, variant):
    variant_service.approve(session, variant)
    result = variant_service.approve(session, variant)
    assert isinstance(result, VariantError)


def test_cannot_approve_a_rejected_variant(session, variant):
    variant_service.reject(session, variant)
    result = variant_service.approve(session, variant)
    assert isinstance(result, VariantError)
    assert "rejected" in result.reason


def test_edit_resets_to_draft(session, variant):
    variant_service.approve(session, variant)
    new_text = (
        "Reworked how the scheduler handles retries after a timeout. "
        "Read more at https://example.com/idempotency #backend"
    )
    result = variant_service.edit_content(session, variant, new_text)
    assert result.status == VariantStatus.DRAFT
    assert result.content == new_text


def test_edit_rejects_invalid_content(session, variant):
    result = variant_service.edit_content(session, variant, "too short")
    assert isinstance(result, VariantError)
    assert result.details


def test_published_variant_cannot_be_edited(session, variant):
    variant.status = VariantStatus.PUBLISHED
    session.add(variant)
    session.commit()
    result = variant_service.edit_content(session, variant, VALID_X)
    assert isinstance(result, VariantError)


def test_published_is_terminal():
    for target in VariantStatus:
        assert not can_transition(VariantStatus.PUBLISHED, target)