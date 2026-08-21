from datetime import datetime

from pydantic import BaseModel, Field, model_validator


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