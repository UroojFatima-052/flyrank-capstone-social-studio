from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./social_studio.db"
    discord_webhook_url: str = ""
    gemini_model: str = "gemini-3.6-flash"
    gemini_api_key: str = ""
    discord_adapter: str = "discord"
    x_adapter: str = "mock_x"
    linkedin_adapter: str = "mock_linkedin"
    scheduler_interval_seconds: int = 30
    scheduler_enabled: bool = True


settings = Settings()