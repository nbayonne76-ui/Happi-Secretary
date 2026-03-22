from sqlalchemy import String, Boolean, JSON, Text, DateTime, Float, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.database import Base
import uuid


class CallLog(Base):
    __tablename__ = "call_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id: Mapped[str] = mapped_column(String, ForeignKey("clients.id"))
    vapi_call_id: Mapped[str] = mapped_column(String(255), unique=True)

    # Caller info
    caller_number: Mapped[str | None] = mapped_column(String(20))
    caller_name: Mapped[str | None] = mapped_column(String(255))  # From VIP list or CRM
    is_vip: Mapped[bool] = mapped_column(Boolean, default=False)

    # Call metadata
    started_at: Mapped[DateTime | None] = mapped_column(DateTime)
    ended_at: Mapped[DateTime | None] = mapped_column(DateTime)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="in_progress")  # in_progress | completed | transferred | missed

    # AI analysis
    intent: Mapped[str | None] = mapped_column(String(255))  # appointment | support | order | info | other
    sentiment: Mapped[str | None] = mapped_column(String(50))  # positive | neutral | negative | urgent
    sentiment_score: Mapped[float | None] = mapped_column(Float)
    summary: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(String(100))  # resolved | transferred | message_taken | appointment_booked

    # Transcript
    transcript: Mapped[str | None] = mapped_column(Text)
    messages: Mapped[list] = mapped_column(JSON, default=lambda: [])  # [{role, content, timestamp}]

    # Actions taken
    appointment_booked: Mapped[bool] = mapped_column(Boolean, default=False)
    appointment_id: Mapped[str | None] = mapped_column(String(255))
    transferred_to: Mapped[str | None] = mapped_column(String(50))
    order_data: Mapped[dict | None] = mapped_column(JSON)

    # Notifications
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    sms_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    # Recording
    recording_url: Mapped[str | None] = mapped_column(String(500))

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
