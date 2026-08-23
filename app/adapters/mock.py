import uuid

from sqlmodel import Session

from app.adapters.base import PublishResult
from app.models import MockPost, Platform


class MockPublisher:
    def __init__(self, platform: Platform, session: Session):
        self.platform = platform
        self.session = session
        self.name = f"mock_{platform.value}"

    def publish(self, content: str, idempotency_key: str) -> PublishResult:
        record = MockPost(
            platform=self.platform,
            content=content,
            idempotency_key=idempotency_key,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)

        external_id = f"{self.platform.value}-{uuid.uuid4().hex[:12]}"
        return PublishResult(
            success=True,
            external_id=external_id,
            message_url=f"https://mock.local/{self.platform.value}/{record.id}",
            error=None,
        )


class MockXPublisher(MockPublisher):
    def __init__(self, session: Session):
        super().__init__(Platform.X, session)


class MockLinkedInPublisher(MockPublisher):
    def __init__(self, session: Session):
        super().__init__(Platform.LINKEDIN, session)