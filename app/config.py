from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./social_studio.db"
    discord_webhook_url: str = ""
    gemini_api_key: str = ""


settings = Settings()