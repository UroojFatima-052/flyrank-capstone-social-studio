from dataclasses import dataclass
from typing import Protocol


@dataclass
class PublishResult:
    success: bool
    external_id: str | None = None
    message_url: str | None = None
    error: str | None = None


class SocialPublisher(Protocol):
    name: str

    def publish(self, content: str, idempotency_key: str) -> PublishResult:
        ...