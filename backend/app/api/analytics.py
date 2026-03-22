"""Analytics — dashboard stats per client."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from app.models.database import get_db
from app.models.call import CallLog

router = APIRouter()


@router.get("/stats")
async def get_stats(
    client_id: str | None = Query(None),
    days: int = Query(30),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timedelta
    since = datetime.utcnow() - timedelta(days=days)

    q = select(
        func.count(CallLog.id).label("total_calls"),
        func.avg(CallLog.duration_seconds).label("avg_duration"),
        func.sum(case((CallLog.appointment_booked == True, 1), else_=0)).label("appointments_booked"),
        func.sum(case((CallLog.status == "transferred", 1), else_=0)).label("calls_transferred"),
        func.sum(case((CallLog.outcome == "message_taken", 1), else_=0)).label("messages_taken"),
        func.sum(case((CallLog.status == "missed", 1), else_=0)).label("missed_calls"),
        func.sum(case((CallLog.sentiment == "positive", 1), else_=0)).label("positive"),
        func.sum(case((CallLog.sentiment == "negative", 1), else_=0)).label("negative"),
        func.sum(case((CallLog.sentiment == "urgent", 1), else_=0)).label("urgent"),
    ).where(CallLog.started_at >= since)

    if client_id:
        q = q.where(CallLog.client_id == client_id)

    result = await db.execute(q)
    row = result.first()

    total = row.total_calls or 0
    resolved = total - (row.calls_transferred or 0) - (row.missed_calls or 0)
    resolution_rate = round((resolved / total * 100) if total > 0 else 0, 1)

    return {
        "period_days": days,
        "total_calls": total,
        "avg_duration_seconds": round(row.avg_duration or 0),
        "resolution_rate": resolution_rate,
        "appointments_booked": row.appointments_booked or 0,
        "calls_transferred": row.calls_transferred or 0,
        "messages_taken": row.messages_taken or 0,
        "missed_calls": row.missed_calls or 0,
        "sentiment": {
            "positive": row.positive or 0,
            "negative": row.negative or 0,
            "urgent": row.urgent or 0,
            "neutral": total - (row.positive or 0) - (row.negative or 0) - (row.urgent or 0),
        },
    }


@router.get("/calls-by-day")
async def calls_by_day(
    client_id: str | None = Query(None),
    days: int = Query(30),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timedelta
    since = datetime.utcnow() - timedelta(days=days)

    q = select(
        func.date(CallLog.started_at).label("day"),
        func.count(CallLog.id).label("count"),
    ).where(CallLog.started_at >= since).group_by(func.date(CallLog.started_at)).order_by("day")

    if client_id:
        q = q.where(CallLog.client_id == client_id)

    result = await db.execute(q)
    return [{"day": str(r.day), "count": r.count} for r in result]


@router.get("/intents")
async def intent_breakdown(
    client_id: str | None = Query(None),
    days: int = Query(30),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timedelta
    since = datetime.utcnow() - timedelta(days=days)

    q = select(
        CallLog.intent,
        func.count(CallLog.id).label("count"),
    ).where(CallLog.started_at >= since).group_by(CallLog.intent)

    if client_id:
        q = q.where(CallLog.client_id == client_id)

    result = await db.execute(q)
    return [{"intent": r.intent or "other", "count": r.count} for r in result]
