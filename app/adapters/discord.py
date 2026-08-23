import logging

import httpx

from app.adapters.base import PublishResult
from app.config import settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 10


class DiscordPublisher:
    name = "discord"

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or settings.discord_webhook_url

    def publish(self, content: str, idempotency_key: str) -> PublishResult:
        if not self.webhook_url:
            return PublishResult(
                success=False, error="No Discord webhook URL configured."
            )

        try:
            response = httpx.post(
                self.webhook_url,
                params={"wait": "true"},
                json={"content": content},
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("Discord returned %s", exc.response.status_code)
            return PublishResult(
                success=False,
                error=f"Discord returned {exc.response.status_code}.",
            )
        except httpx.RequestError as exc:
            logger.warning("Could not reach Discord: %s", exc)
            return PublishResult(success=False, error=f"Could not reach Discord: {exc}")

        try:
            payload = response.json()
            message_id = payload["id"]
            channel_id = payload["channel_id"]
        except (ValueError, KeyError) as exc:
            logger.warning("Unexpected Discord response: %s", exc)
            return PublishResult(
                success=False, error="Discord response did not include a message id."
            )

        return PublishResult(
            success=True,
            external_id=message_id,
            message_url=f"https://discord.com/channels/@me/{channel_id}/{message_id}",
        )