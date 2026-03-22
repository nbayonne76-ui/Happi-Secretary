from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Happi-Secretary"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://happi:happi@db:5432/happi_secretary"

    # Vapi.ai
    VAPI_API_KEY: str = ""
    VAPI_PHONE_NUMBER_ID: str = ""
    VAPI_WEBHOOK_SECRET: str = ""

    # Anthropic (Claude)
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-6"

    # ElevenLabs
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_DEFAULT_VOICE_ID: str = "EXAVITQu4vr4xnSDxMaL"  # Sarah - natural French

    # Deepgram
    DEEPGRAM_API_KEY: str = ""

    # Cal.com
    CALCOM_API_KEY: str = ""
    CALCOM_API_URL: str = "https://api.cal.com/v2"

    # Notifications
    RESEND_API_KEY: str = ""
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    # Frontend
    DASHBOARD_URL: str = "http://localhost:3000"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
