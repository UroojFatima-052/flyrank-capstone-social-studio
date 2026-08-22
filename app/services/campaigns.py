from sqlmodel import Session, select

from app.models import Campaign, Platform, Post, Variant, VariantStatus
from app.schemas import CampaignCreate
from app.services.ai_generator import generate_with_ai
from app.services.validator import validate_variant


def create_campaign(session: Session, data: CampaignCreate) -> Campaign | str:
    post = session.get(Post, data.post_id)
    if post is None:
        return "Post not found."

    existing = session.exec(
        select(Campaign)
        .where(Campaign.post_id == data.post_id)
        .where(Campaign.name == data.name)
    ).first()
    if existing is not None:
        return (
            f"A campaign named '{data.name}' already exists for this post "
            f"(id {existing.id}). Use a different name if you want a second "
            f"campaign for the same post."
        )

    campaign = Campaign(post_id=data.post_id, name=data.name)
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return campaign


def list_campaigns(session: Session) -> list[Campaign]:
    return list(session.exec(select(Campaign)).all())


def get_campaign(session: Session, campaign_id: int) -> Campaign | None:
    return session.get(Campaign, campaign_id)


def get_campaign_variants(session: Session, campaign_id: int) -> list[Variant]:
    statement = select(Variant).where(Variant.campaign_id == campaign_id)
    return list(session.exec(statement).all())


def generate_variants(
    session: Session, campaign_id: int
) -> tuple[list[Variant], list[str], dict[str, list[str]]] | None:
    campaign = session.get(Campaign, campaign_id)
    if campaign is None:
        return None

    post = session.get(Post, campaign.post_id)
    if post is None:
        return None

    existing = get_campaign_variants(session, campaign_id)
    already_have = {v.platform for v in existing}

    created: list[Variant] = []
    skipped: list[str] = []
    failed: dict[str, list[str]] = {}

    for platform in Platform:
        if platform in already_have:
            skipped.append(platform.value)
            continue

        text, source = generate_with_ai(post, platform)
        result = validate_variant(text, platform)

        if not result.valid:
            failed[platform.value] = result.errors
            continue

        variant = Variant(
            campaign_id=campaign.id,
            post_id=post.id,
            platform=platform,
            content=text,
            status=VariantStatus.DRAFT,
        )
        session.add(variant)
        created.append(variant)

    session.commit()
    for variant in created:
        session.refresh(variant)

    return created, skipped, failed