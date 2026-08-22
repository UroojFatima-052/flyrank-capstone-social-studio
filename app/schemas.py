from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models import CampaignStatus, Platform, VariantStatus


class PostCreate(BaseModel):
    title: str | None = Field(default=None)
    content: str | None = Field(default=None)
    source_url: str | None = Field(default=None)

    @model_validator(mode="after")
    def require_content_or_url(self):
        if not self.content and not self.source_url:
            raise ValueError("Provide either content or source_url.")
        if self.content and not self.title:
            raise ValueError("Title is required when providing content directly.")
        return self


class PostRead(BaseModel):
    id: int
    title: str
    content: str
    source_url: str | None
    created_at: datetime

class CampaignCreate(BaseModel):
    post_id: int
    name: str


class VariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    post_id: int
    platform: Platform
    content: str
    status: VariantStatus
    created_at: datetime


class CampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    post_id: int
    name: str
    status: CampaignStatus
    created_at: datetime


class CampaignDetail(CampaignRead):
    variants: list[VariantRead]


class GenerationReport(BaseModel):
    campaign_id: int
    created: list[VariantRead]
    failed: dict[str, list[str]]