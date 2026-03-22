"""Call logs — list, filter, search, detail."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.models.database import get_db
from app.models.call import CallLog

router = APIRouter()


@router.get("/")
async def list_calls(
    client_id: str | None = Query(None),
    status: str | None = Query(None),
    intent: str | None = Query(None),
    sentiment: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    q = select(CallLog).order_by(desc(CallLog.created_at))
    if client_id:
        q = q.where(CallLog.client_id == client_id)
    if status:
        q = q.where(CallLog.status == status)
    if intent:
        q = q.where(CallLog.intent == intent)
    if sentiment:
        q = q.where(CallLog.sentiment == sentiment)
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    calls = result.scalars().all()
    return [_serialize(c) for c in calls]


@router.get("/{call_id}")
async def get_call(call_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CallLog).where(CallLog.id == call_id))
    call = result.scalars().first()
    if not call:
        from fastapi import HTTPException
        raise HTTPException(404, "Call not found")
    return _serialize(call, include_messages=True)


def _serialize(c: CallLog, include_messages: bool = False) -> dict:
    data = {
        "id": c.id,
        "client_id": c.client_id,
        "vapi_call_id": c.vapi_call_id,
        "caller_number": c.caller_number,
        "caller_name": c.caller_name,
        "is_vip": c.is_vip,
        "started_at": c.started_at.isoformat() if c.started_at else None,
        "ended_at": c.ended_at.isoformat() if c.ended_at else None,
        "duration_seconds": c.duration_seconds,
        "status": c.status,
        "intent": c.intent,
        "sentiment": c.sentiment,
        "sentiment_score": c.sentiment_score,
        "summary": c.summary,
        "outcome": c.outcome,
        "appointment_booked": c.appointment_booked,
        "appointment_id": c.appointment_id,
        "transferred_to": c.transferred_to,
        "order_data": c.order_data,
        "transcript": c.transcript,
        "email_sent": c.email_sent,
        "sms_sent": c.sms_sent,
        "recording_url": c.recording_url,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
    if include_messages:
        data["messages"] = c.messages
    return data
