from sqlalchemy import String, Boolean, JSON, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.database import Base
import uuid


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255))
    business_type: Mapped[str] = mapped_column(String(100), default="general")
    phone_number: Mapped[str | None] = mapped_column(String(20), unique=True)  # Vapi number
    vapi_assistant_id: Mapped[str | None] = mapped_column(String(255))

    # Voice config
    voice_id: Mapped[str] = mapped_column(String(255), default="EXAVITQu4vr4xnSDxMaL")
    assistant_name: Mapped[str] = mapped_column(String(100), default="Happi")
    language: Mapped[str] = mapped_column(String(10), default="fr-FR")

    # Behavior config
    greeting_message: Mapped[str] = mapped_column(Text, default="Bonjour, comment puis-je vous aider ?")
    system_prompt: Mapped[str | None] = mapped_column(Text)
    business_hours: Mapped[dict] = mapped_column(JSON, default=lambda: {
        "monday": {"open": "09:00", "close": "18:00", "enabled": True},
        "tuesday": {"open": "09:00", "close": "18:00", "enabled": True},
        "wednesday": {"open": "09:00", "close": "18:00", "enabled": True},
        "thursday": {"open": "09:00", "close": "18:00", "enabled": True},
        "friday": {"open": "09:00", "close": "18:00", "enabled": True},
        "saturday": {"open": "10:00", "close": "13:00", "enabled": False},
        "sunday": {"open": "", "close": "", "enabled": False},
    })
    after_hours_message: Mapped[str] = mapped_column(Text, default="Nous sommes actuellement fermés. Je prends votre message et vous rappellerons.")
    off_hours_behavior: Mapped[str] = mapped_column(String(50), default="take_message")  # take_message | voicemail | transfer

    # Routing
    transfer_numbers: Mapped[dict] = mapped_column(JSON, default=lambda: {})  # {"sales": "+33...", "support": "+33..."}
    escalation_keywords: Mapped[list] = mapped_column(JSON, default=lambda: ["urgent", "emergency", "directeur", "manager"])
    vip_numbers: Mapped[list] = mapped_column(JSON, default=lambda: [])

    # Calendar
    calcom_api_key: Mapped[str | None] = mapped_column(String(255))
    calcom_event_type_id: Mapped[int | None] = mapped_column()
    calendar_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Notifications
    notification_email: Mapped[str | None] = mapped_column(String(255))
    notification_sms: Mapped[str | None] = mapped_column(String(20))
    send_transcript_email: Mapped[bool] = mapped_column(Boolean, default=True)
    send_transcript_sms: Mapped[bool] = mapped_column(Boolean, default=True)

    # CRM
    crm_webhook_url: Mapped[str | None] = mapped_column(String(500))
    crm_headers: Mapped[dict] = mapped_column(JSON, default=lambda: {})

    # Features
    features: Mapped[dict] = mapped_column(JSON, default=lambda: {
        "sentiment_analysis": True,
        "call_recording": True,
        "post_call_survey": False,
        "multilingual": True,
        "order_taking": False,
        "outbound_followup": False,
    })

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
