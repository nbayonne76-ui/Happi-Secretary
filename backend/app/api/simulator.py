"""
Call Simulator API — simulates inbound calls without any external service.
Used for development, demos, and testing workflows.

Endpoints:
  POST /api/simulator/call/start       → start a simulated call
  POST /api/simulator/call/{id}/message → send a caller message, get AI response
  POST /api/simulator/call/{id}/end    → end the call, generate summary
  GET  /api/simulator/call/{id}        → get current call state
"""
import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import get_db
from app.models.client import Client
from app.models.call import CallLog
from app.services.mock_service import MockConversationEngine, get_notification_service, get_calcom_service, is_mock_mode

router = APIRouter()

# In-memory engines per active call (resets on restart — fine for demo)
_engines: dict[str, MockConversationEngine] = {}
_turn_counters: dict[str, int] = {}


class StartCallBody(BaseModel):
    client_id: str
    caller_number: str = "+33600000000"
    caller_name: str | None = None
    is_vip: bool = False


class MessageBody(BaseModel):
    text: str


@router.post("/call/start")
async def start_call(body: StartCallBody, db: AsyncSession = Depends(get_db)):
    """Start a simulated inbound call."""
    result = await db.execute(select(Client).where(Client.id == body.client_id, Client.is_active == True))
    client: Client | None = result.scalars().first()
    if not client:
        raise HTTPException(404, "Client not found")

    # Create call log
    call_log = CallLog(
        client_id=client.id,
        vapi_call_id=f"sim-{random.randint(100000, 999999)}",
        caller_number=body.caller_number,
        caller_name=body.caller_name,
        is_vip=body.is_vip,
        started_at=datetime.utcnow(),
        status="in_progress",
    )
    db.add(call_log)
    await db.flush()

    # Init conversation engine
    engine = MockConversationEngine(
        client_name=client.name,
        assistant_name=client.assistant_name,
    )
    _engines[call_log.id] = engine
    _turn_counters[call_log.id] = 0

    greeting = engine.get_greeting(is_vip=body.is_vip)

    # Add greeting to messages
    call_log.messages = [{"role": "assistant", "content": greeting, "timestamp": datetime.utcnow().isoformat()}]
    await db.flush()

    return {
        "call_id": call_log.id,
        "vapi_call_id": call_log.vapi_call_id,
        "assistant_name": client.assistant_name,
        "greeting": greeting,
        "mode": "mock" if is_mock_mode() else "live",
        "client": {"id": client.id, "name": client.name},
    }


@router.post("/call/{call_id}/message")
async def send_message(call_id: str, body: MessageBody, db: AsyncSession = Depends(get_db)):
    """Send a caller message and receive the AI secretary response."""
    result = await db.execute(select(CallLog).where(CallLog.id == call_id))
    call_log: CallLog | None = result.scalars().first()
    if not call_log:
        raise HTTPException(404, "Call not found")
    if call_log.status != "in_progress":
        raise HTTPException(400, "Call is not in progress")

    # Get or recreate engine
    engine = _engines.get(call_id)
    if not engine:
        result2 = await db.execute(select(Client).where(Client.id == call_log.client_id))
        client = result2.scalars().first()
        engine = MockConversationEngine(
            client_name=client.name if client else "l'entreprise",
            assistant_name=client.assistant_name if client else "Happi",
        )
        _engines[call_id] = engine

    turn = _turn_counters.get(call_id, 0) + 1
    _turn_counters[call_id] = turn

    # Get AI response
    response = engine.get_response(
        call_id=call_id,
        caller_text=body.text,
        turn=turn,
    )

    # Update messages in call log
    messages = list(call_log.messages or [])
    messages.append({"role": "user",      "content": body.text,          "timestamp": datetime.utcnow().isoformat()})
    messages.append({"role": "assistant", "content": response["text"],   "timestamp": datetime.utcnow().isoformat()})
    call_log.messages = messages
    await db.flush()

    # Handle actions
    action_result = None
    if response.get("action") == "book_appointment":
        action_data = response.get("action_data", {})
        calcom = get_calcom_service()
        booking = await calcom.book_appointment(
            date=action_data.get("date", ""),
            time=action_data.get("time", "10:00"),
            attendee_name=call_log.caller_name or call_log.caller_number or "Client",
            attendee_email="demo@example.com",
        )
        call_log.appointment_booked = True
        call_log.appointment_id = booking.get("booking_id")
        action_result = booking
        await db.flush()

    elif response.get("action") == "transfer":
        call_log.transferred_to = response.get("action_data", {}).get("department", "management")
        action_result = {"transferred_to": call_log.transferred_to}
        await db.flush()

    return {
        "call_id": call_id,
        "turn": turn,
        "caller_text": body.text,
        "response": response["text"],
        "intent": response.get("intent"),
        "action": response.get("action"),
        "action_data": response.get("action_data"),
        "action_result": action_result,
        "should_end": response.get("action") == "end_call",
    }


@router.post("/call/{call_id}/end")
async def end_call(call_id: str, db: AsyncSession = Depends(get_db)):
    """End the simulated call and generate summary + send notifications."""
    result = await db.execute(select(CallLog).where(CallLog.id == call_id))
    call_log: CallLog | None = result.scalars().first()
    if not call_log:
        raise HTTPException(404, "Call not found")

    result2 = await db.execute(select(Client).where(Client.id == call_log.client_id))
    client: Client | None = result2.scalars().first()

    # Generate full transcript
    messages = call_log.messages or []
    transcript_lines = []
    for msg in messages:
        role_label = "Assistant" if msg["role"] == "assistant" else "Client"
        transcript_lines.append(f"{role_label}: {msg['content']}")
    transcript = "\n".join(transcript_lines)

    # Generate summary using mock engine
    engine = _engines.get(call_id, MockConversationEngine())
    analysis = engine.generate_summary(messages)

    # Calculate duration
    duration = int((datetime.utcnow() - call_log.started_at).total_seconds()) if call_log.started_at else 30

    # Update call log
    call_log.transcript = transcript
    call_log.ended_at = datetime.utcnow()
    call_log.duration_seconds = duration
    call_log.status = "transferred" if call_log.transferred_to else "completed"
    call_log.summary = analysis["summary"]
    call_log.intent = analysis["intent"]
    call_log.sentiment = analysis["sentiment"]
    call_log.sentiment_score = analysis["sentiment_score"]
    call_log.outcome = call_log.outcome or analysis["outcome"]
    await db.flush()

    # Send notifications (mock or real)
    if client:
        notif = get_notification_service()
        if client.notification_email and client.send_transcript_email:
            await notif.send_call_transcript_email(client=client, call_log=call_log)
            call_log.email_sent = True
        if client.notification_sms and client.send_transcript_sms:
            await notif.send_call_summary_sms(client=client, call_log=call_log)
            call_log.sms_sent = True
        await db.flush()

    # Cleanup
    _engines.pop(call_id, None)
    _turn_counters.pop(call_id, None)

    return {
        "call_id": call_id,
        "duration_seconds": duration,
        "transcript": transcript,
        "summary": analysis["summary"],
        "intent": analysis["intent"],
        "sentiment": analysis["sentiment"],
        "outcome": call_log.outcome,
        "appointment_booked": call_log.appointment_booked,
        "transferred_to": call_log.transferred_to,
        "messages": messages,
    }


@router.get("/call/{call_id}")
async def get_call_state(call_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CallLog).where(CallLog.id == call_id))
    call_log = result.scalars().first()
    if not call_log:
        raise HTTPException(404, "Call not found")
    return {
        "call_id": call_id,
        "status": call_log.status,
        "messages": call_log.messages,
        "appointment_booked": call_log.appointment_booked,
        "transferred_to": call_log.transferred_to,
        "duration_seconds": call_log.duration_seconds,
    }
