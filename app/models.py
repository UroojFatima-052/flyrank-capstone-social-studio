from datetime import datetime, timezone
from enum import Enum
from sqlmodel import Field, SQLModel, UniqueConstraint


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"


class Platform(str, Enum):
    DISCORD = "discord"
    X = "x"
    LINKEDIN = "linkedin"


class VariantStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


class SlotStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"
    CANCELLED = "cancelled"


class AttemptStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Post(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    content: str
    source_url: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow)


class Campaign(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("post_id", "name", name="uq_campaign_post_name"),)
    
    id: int | None = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="post.id", index=True)
    name: str
    status: CampaignStatus = Field(default=CampaignStatus.DRAFT)
    created_at: datetime = Field(default_factory=utcnow)


class Variant(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.id", index=True)
    post_id: int = Field(foreign_key="post.id", index=True)
    platform: Platform
    content: str
    status: VariantStatus = Field(default=VariantStatus.DRAFT, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ScheduleSlot(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    variant_id: int = Field(foreign_key="variant.id", index=True)
    scheduled_for: datetime = Field(index=True)
    status: SlotStatus = Field(default=SlotStatus.PENDING, index=True)
    created_at: datetime = Field(default_factory=utcnow)


class PublishAttempt(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    variant_id: int = Field(foreign_key="variant.id", index=True)
    slot_id: int = Field(foreign_key="scheduleslot.id", index=True)
    idempotency_key: str = Field(unique=True, index=True)
    status: AttemptStatus
    external_id: str | None = Field(default=None)
    message_url: str | None = Field(default=None)
    error: str | None = Field(default=None)
    attempted_at: datetime = Field(default_factory=utcnow)

class MockPost(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    platform: Platform = Field(index=True)
    content: str
    idempotency_key: str = Field(index=True)
    posted_at: datetime = Field(default_factory=utcnow)