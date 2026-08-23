from sqlmodel import Session

from app.adapters.base import SocialPublisher
from app.adapters.discord import DiscordPublisher
from app.adapters.mock import MockLinkedInPublisher, MockXPublisher
from app.config import settings
from app.models import Platform


class UnknownAdapter(Exception):
    pass


def _build(adapter_name: str, session: Session) -> SocialPublisher:
    if adapter_name == "discord":
        return DiscordPublisher()
    if adapter_name == "mock_x":
        return MockXPublisher(session)
    if adapter_name == "mock_linkedin":
        return MockLinkedInPublisher(session)
    raise UnknownAdapter(f"No adapter named '{adapter_name}'.")


def adapter_name_for(platform: Platform) -> str:
    mapping = {
        Platform.DISCORD: settings.discord_adapter,
        Platform.X: settings.x_adapter,
        Platform.LINKEDIN: settings.linkedin_adapter,
    }
    return mapping[platform]


def get_publisher(platform: Platform, session: Session) -> SocialPublisher:
    return _build(adapter_name_for(platform), session)