"""
Vapi.ai webhook handler.
Vapi sends events here during a call:
  - assistant-request  → we tell Vapi which assistant config to use
  - function-call      → AI wants to call a tool (book appointment, transfer, etc.)
  - end-of-call-report → call finished, contains full transcript + recording
  - status-update      → call progress events
"""
import hashlib
import hmac
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.database import get_db
from app.models.client import Client
from app.models.call import CallLog
from app.services.claude_service import ClaudeService
from app.services.calcom_service import CalcomService
from app.services.notification_service import NotificationService
from app.services.crm_service import CrmService

router = APIRouter()
logger = logging.getLogger(__name__)


def verify_vapi_signature(payload: bytes, signature: str | None) -> bool:
    if not settings.VAPI_WEBHOOK_SECRET or not signature:
        return True  # Skip verification in dev if secret not set
    expected = hmac.new(
        settings.VAPI_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def get_client_by_phone(phone_number_id: str, db: AsyncSession) -> Client | None:
    result = await db.execute(
        select(Client).where(Client.vapi_assistant_id.isnot(None), Client.is_active == True)
    )
    # For now match by vapi assistant - in production match by phone_number_id
    return result.scalars().first()


@router.post("/webhook")
async def vapi_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_vapi_signature: str | None = Header(None),
):
    body = await request.body()

    if not verify_vapi_signature(body, x_vapi_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(body)
    event_type = payload.get("message", {}).get("type")

    logger.info(f"Vapi event: {event_type}")

    handlers = {
        "assistant-request": handle_assistant_request,
        "function-call": handle_function_call,
        "end-of-call-report": handle_end_of_call,
        "status-update": handle_status_update,
        "transcript": handle_transcript_update,
    }

    handler = handlers.get(event_type)
    if handler:
        return await handler(payload, db)

    return {"received": True}


# ---------------------------------------------------------------------------
# assistant-request: Vapi asks us which assistant to use for this call
# ---------------------------------------------------------------------------
async def handle_assistant_request(payload: dict, db: AsyncSession) -> dict:
    message = payload.get("message", {})
    call = message.get("call", {})
    phone_number_id = call.get("phoneNumberId", "")
    caller_number = call.get("customer", {}).get("number", "unknown")

    # Find the client associated with this phone number
    result = await db.execute(
        select(Client).where(Client.is_active == True).limit(1)
    )
    client: Client | None = result.scalars().first()

    if not client:
        return {
            "assistant": {
                "firstMessage": "Bonjour, notre service est temporairement indisponible. Veuillez rappeler plus tard.",
                "model": {"provider": "anthropic", "model": "claude-sonnet-4-6", "messages": []},
                "voice": {"provider": "elevenlabs", "voiceId": "EXAVITQu4vr4xnSDxMaL"},
            }
        }

    # Check if VIP caller
    is_vip = caller_number in (client.vip_numbers or [])

    # Build dynamic system prompt
    claude_svc = ClaudeService()
    system_prompt = claude_svc.build_system_prompt(client, is_vip=is_vip)

    # Create call log
    call_log = CallLog(
        client_id=client.id,
        vapi_call_id=call.get("id", ""),
        caller_number=caller_number,
        is_vip=is_vip,
        started_at=datetime.utcnow(),
        status="in_progress",
    )
    db.add(call_log)
    await db.flush()

    greeting = client.greeting_message
    if is_vip:
        greeting = f"Bonjour ! Je vois que vous êtes un de nos clients privilégiés. {greeting}"

    return {
        "assistant": {
            "name": client.assistant_name,
            "firstMessage": greeting,
            "model": {
                "provider": "anthropic",
                "model": settings.CLAUDE_MODEL,
                "messages": [{"role": "system", "content": system_prompt}],
                "temperature": 0.4,
                "maxTokens": 300,
            },
            "voice": {
                "provider": "elevenlabs",
                "voiceId": client.voice_id,
                "stability": 0.5,
                "similarityBoost": 0.75,
            },
            "transcriber": {
                "provider": "deepgram",
                "model": "nova-2",
                "language": client.language,
            },
            "endCallFunctionEnabled": True,
            "recordingEnabled": client.features.get("call_recording", True),
            "functions": _build_functions(client),
        }
    }


def _build_functions(client: Client) -> list[dict]:
    """Return the list of tools the AI can call during the conversation."""
    functions = [
        {
            "name": "transfer_call",
            "description": "Transfer the call to a human agent or department. Use when the caller requests it or the situation is complex.",
            "parameters": {
                "type": "object",
                "properties": {
                    "department": {"type": "string", "description": "Department: sales, support, management, or a specific name"},
                    "reason": {"type": "string", "description": "Brief reason for the transfer"},
                },
                "required": ["department", "reason"],
            },
        },
        {
            "name": "take_message",
            "description": "Record a message for the team when no one is available. Collect caller name, phone, and message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "caller_name": {"type": "string"},
                    "callback_number": {"type": "string"},
                    "message": {"type": "string"},
                    "urgency": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
                },
                "required": ["caller_name", "message", "urgency"],
            },
        },
        {
            "name": "end_call",
            "description": "Politely end the call when the conversation is complete.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Brief summary of what was accomplished"},
                },
                "required": ["summary"],
            },
        },
    ]

    if client.calendar_enabled:
        functions.append({
            "name": "book_appointment",
            "description": "Book an appointment for the caller. Check availability first, then confirm with the caller.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                    "time": {"type": "string", "description": "Time in HH:MM format (24h)"},
                    "duration_minutes": {"type": "integer", "default": 30},
                    "attendee_name": {"type": "string"},
                    "attendee_email": {"type": "string"},
                    "attendee_phone": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["date", "time", "attendee_name", "attendee_email"],
            },
        })
        functions.append({
            "name": "check_availability",
            "description": "Check available appointment slots for a given date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                },
                "required": ["date"],
            },
        })

    if client.features.get("order_taking"):
        functions.append({
            "name": "take_order",
            "description": "Record a customer order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {"type": "array", "items": {"type": "object"}},
                    "customer_name": {"type": "string"},
                    "customer_phone": {"type": "string"},
                    "delivery_address": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["items", "customer_name", "customer_phone"],
            },
        })

    return functions


# ---------------------------------------------------------------------------
# function-call: AI is invoking a tool
# ---------------------------------------------------------------------------
async def handle_function_call(payload: dict, db: AsyncSession) -> dict:
    message = payload.get("message", {})
    func_call = message.get("functionCall", {})
    call_id = message.get("call", {}).get("id", "")
    function_name = func_call.get("name")
    parameters = func_call.get("parameters", {})

    logger.info(f"Function call: {function_name} | params: {parameters}")

    # Get call log
    result = await db.execute(select(CallLog).where(CallLog.vapi_call_id == call_id))
    call_log: CallLog | None = result.scalars().first()

    # Get client
    client: Client | None = None
    if call_log:
        result = await db.execute(select(Client).where(Client.id == call_log.client_id))
        client = result.scalars().first()

    if function_name == "book_appointment" and client:
        return await _handle_book_appointment(parameters, call_log, client, db)

    elif function_name == "check_availability" and client:
        return await _handle_check_availability(parameters, client)

    elif function_name == "transfer_call" and client:
        return await _handle_transfer(parameters, call_log, client, db)

    elif function_name == "take_message" and client:
        return await _handle_take_message(parameters, call_log, client, db)

    elif function_name == "take_order" and client:
        return await _handle_take_order(parameters, call_log, client, db)

    elif function_name == "end_call":
        return {"result": "Ending call gracefully."}

    return {"result": "Function executed."}


async def _handle_book_appointment(params: dict, call_log: CallLog | None, client: Client, db: AsyncSession) -> dict:
    calcom = CalcomService(api_key=client.calcom_api_key or settings.CALCOM_API_KEY)
    result = await calcom.book_appointment(
        event_type_id=client.calcom_event_type_id,
        date=params["date"],
        time=params["time"],
        attendee_name=params["attendee_name"],
        attendee_email=params["attendee_email"],
        attendee_phone=params.get("attendee_phone", ""),
        notes=params.get("notes", ""),
    )
    if result.get("success") and call_log:
        call_log.appointment_booked = True
        call_log.appointment_id = result.get("booking_id")
        call_log.outcome = "appointment_booked"
        await db.flush()

    return {"result": result.get("message", "Rendez-vous enregistré avec succès.")}


async def _handle_check_availability(params: dict, client: Client) -> dict:
    calcom = CalcomService(api_key=client.calcom_api_key or settings.CALCOM_API_KEY)
    slots = await calcom.get_available_slots(
        event_type_id=client.calcom_event_type_id,
        date=params["date"],
    )
    if not slots:
        return {"result": f"Aucun créneau disponible le {params['date']}."}
    slot_list = ", ".join(slots[:5])
    return {"result": f"Créneaux disponibles le {params['date']} : {slot_list}"}


async def _handle_transfer(params: dict, call_log: CallLog | None, client: Client, db: AsyncSession) -> dict:
    department = params.get("department", "general")
    transfer_numbers = client.transfer_numbers or {}
    number = transfer_numbers.get(department) or transfer_numbers.get("default")

    if call_log:
        call_log.transferred_to = department
        call_log.outcome = "transferred"
        call_log.status = "transferred"
        await db.flush()

    if not number:
        return {"result": f"Je suis désolé, le transfert vers {department} n'est pas disponible. Je prends un message."}

    return {
        "result": f"Je vous transfère maintenant vers {department}. Un instant s'il vous plaît.",
        "transferCall": {"number": number},
    }


async def _handle_take_message(params: dict, call_log: CallLog | None, client: Client, db: AsyncSession) -> dict:
    if call_log:
        call_log.outcome = "message_taken"
        await db.flush()

    # Send notification immediately
    notif = NotificationService()
    msg_body = (
        f"Nouveau message de {params.get('caller_name', 'Inconnu')}\n"
        f"Tel: {params.get('callback_number', 'Non fourni')}\n"
        f"Urgence: {params.get('urgency', 'normal')}\n"
        f"Message: {params.get('message', '')}"
    )
    if client.notification_email and client.send_transcript_email:
        await notif.send_email(
            to=client.notification_email,
            subject=f"[{client.assistant_name}] Nouveau message - Urgence: {params.get('urgency', 'normal')}",
            body=msg_body,
        )
    if client.notification_sms and client.send_transcript_sms:
        await notif.send_sms(to=client.notification_sms, body=msg_body[:160])

    return {"result": "Message bien enregistré. Votre équipe vous rappellera dans les meilleurs délais."}


async def _handle_take_order(params: dict, call_log: CallLog | None, client: Client, db: AsyncSession) -> dict:
    if call_log:
        call_log.order_data = params
        call_log.outcome = "order_taken"
        await db.flush()

    # Fire CRM webhook
    if client.crm_webhook_url:
        crm = CrmService()
        await crm.push_event(
            webhook_url=client.crm_webhook_url,
            headers=client.crm_headers,
            event_type="order_created",
            data=params,
        )
    return {"result": "Commande enregistrée avec succès. Vous recevrez une confirmation."}


# ---------------------------------------------------------------------------
# end-of-call-report: call is done — save transcript, notify, push CRM
# ---------------------------------------------------------------------------
async def handle_end_of_call(payload: dict, db: AsyncSession) -> dict:
    message = payload.get("message", {})
    call_data = message.get("call", {})
    call_id = call_data.get("id", "")
    transcript = message.get("transcript", "")
    recording_url = message.get("recordingUrl")
    duration = message.get("durationSeconds", 0)
    messages_raw = message.get("messages", [])

    result = await db.execute(select(CallLog).where(CallLog.vapi_call_id == call_id))
    call_log: CallLog | None = result.scalars().first()
    if not call_log:
        return {"received": True}

    result = await db.execute(select(Client).where(Client.id == call_log.client_id))
    client: Client | None = result.scalars().first()
    if not client:
        return {"received": True}

    # Update call log
    call_log.transcript = transcript
    call_log.messages = messages_raw
    call_log.duration_seconds = duration
    call_log.ended_at = datetime.utcnow()
    call_log.status = call_log.status if call_log.status != "in_progress" else "completed"
    call_log.recording_url = recording_url
    await db.flush()

    # AI analysis (summary + sentiment + intent)
    claude = ClaudeService()
    analysis = await claude.analyze_call(transcript)
    call_log.summary = analysis.get("summary")
    call_log.sentiment = analysis.get("sentiment")
    call_log.sentiment_score = analysis.get("sentiment_score")
    call_log.intent = analysis.get("intent")
    if not call_log.outcome:
        call_log.outcome = analysis.get("outcome", "completed")
    await db.flush()

    # Send transcript by email + SMS
    notif = NotificationService()
    if client.send_transcript_email and client.notification_email and not call_log.email_sent:
        await notif.send_call_transcript_email(client=client, call_log=call_log)
        call_log.email_sent = True

    if client.send_transcript_sms and client.notification_sms and not call_log.sms_sent:
        await notif.send_call_summary_sms(client=client, call_log=call_log)
        call_log.sms_sent = True

    # Push to CRM
    if client.crm_webhook_url:
        crm = CrmService()
        await crm.push_call_completed(client=client, call_log=call_log)

    await db.flush()
    return {"received": True}


# ---------------------------------------------------------------------------
# status-update: track call state
# ---------------------------------------------------------------------------
async def handle_status_update(payload: dict, db: AsyncSession) -> dict:
    message = payload.get("message", {})
    call_id = message.get("call", {}).get("id", "")
    status = message.get("status")

    if status in ("ended", "failed"):
        result = await db.execute(select(CallLog).where(CallLog.vapi_call_id == call_id))
        call_log = result.scalars().first()
        if call_log and call_log.status == "in_progress":
            call_log.status = "missed" if status == "failed" else "completed"
            await db.flush()

    return {"received": True}


async def handle_transcript_update(payload: dict, db: AsyncSession) -> dict:
    # Real-time transcript updates — we store in end-of-call instead
    return {"received": True}
