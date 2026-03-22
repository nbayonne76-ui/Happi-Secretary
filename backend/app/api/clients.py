"""Client CRUD + Vapi assistant provisioning."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any

from app.models.database import get_db
from app.models.client import Client
from app.services.vapi_service import VapiService

router = APIRouter()


class ClientCreate(BaseModel):
    name: str
    business_type: str = "general"
    assistant_name: str = "Happi"
    language: str = "fr-FR"
    greeting_message: str = "Bonjour, comment puis-je vous aider ?"
    system_prompt: str | None = None
    notification_email: str | None = None
    notification_sms: str | None = None


class ClientUpdate(BaseModel):
    name: str | None = None
    business_type: str | None = None
    assistant_name: str | None = None
    voice_id: str | None = None
    language: str | None = None
    greeting_message: str | None = None
    after_hours_message: str | None = None
    off_hours_behavior: str | None = None
    system_prompt: str | None = None
    business_hours: dict | None = None
    transfer_numbers: dict | None = None
    escalation_keywords: list[str] | None = None
    vip_numbers: list[str] | None = None
    calcom_api_key: str | None = None
    calcom_event_type_id: int | None = None
    calendar_enabled: bool | None = None
    notification_email: str | None = None
    notification_sms: str | None = None
    send_transcript_email: bool | None = None
    send_transcript_sms: bool | None = None
    crm_webhook_url: str | None = None
    crm_headers: dict | None = None
    features: dict | None = None


@router.get("/")
async def list_clients(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Client).order_by(Client.created_at.desc()))
    clients = result.scalars().all()
    return [_serialize(c) for c in clients]


@router.post("/", status_code=201)
async def create_client(data: ClientCreate, db: AsyncSession = Depends(get_db)):
    client = Client(**data.model_dump())
    db.add(client)
    await db.flush()

    # Provision Vapi assistant automatically
    vapi = VapiService()
    assistant_id = await vapi.create_assistant(client)
    if assistant_id:
        client.vapi_assistant_id = assistant_id
        await db.flush()

    return _serialize(client)


@router.get("/{client_id}")
async def get_client(client_id: str, db: AsyncSession = Depends(get_db)):
    client = await _get_or_404(client_id, db)
    return _serialize(client)


@router.patch("/{client_id}")
async def update_client(client_id: str, data: ClientUpdate, db: AsyncSession = Depends(get_db)):
    client = await _get_or_404(client_id, db)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(client, field, value)
    await db.flush()

    # Sync voice change to Vapi
    if data.voice_id and client.vapi_assistant_id:
        vapi = VapiService()
        await vapi.update_assistant(client.vapi_assistant_id, client)

    return _serialize(client)


@router.delete("/{client_id}", status_code=204)
async def delete_client(client_id: str, db: AsyncSession = Depends(get_db)):
    client = await _get_or_404(client_id, db)
    client.is_active = False
    await db.flush()


@router.post("/{client_id}/outbound-call")
async def trigger_outbound_call(
    client_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """Trigger an outbound follow-up call to a given number."""
    client = await _get_or_404(client_id, db)
    if not client.vapi_assistant_id:
        raise HTTPException(400, "Client has no Vapi assistant configured")
    vapi = VapiService()
    result = await vapi.make_outbound_call(
        to_number=body.get("to_number", ""),
        assistant_id=client.vapi_assistant_id,
        first_message=body.get("first_message", "Bonjour, je vous contacte suite à votre appel."),
    )
    if not result:
        raise HTTPException(500, "Outbound call failed")
    return result


async def _get_or_404(client_id: str, db: AsyncSession) -> Client:
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalars().first()
    if not client:
        raise HTTPException(404, "Client not found")
    return client


def _serialize(c: Client) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "business_type": c.business_type,
        "phone_number": c.phone_number,
        "vapi_assistant_id": c.vapi_assistant_id,
        "assistant_name": c.assistant_name,
        "voice_id": c.voice_id,
        "language": c.language,
        "greeting_message": c.greeting_message,
        "after_hours_message": c.after_hours_message,
        "off_hours_behavior": c.off_hours_behavior,
        "system_prompt": c.system_prompt,
        "business_hours": c.business_hours,
        "transfer_numbers": c.transfer_numbers,
        "escalation_keywords": c.escalation_keywords,
        "vip_numbers": c.vip_numbers,
        "calendar_enabled": c.calendar_enabled,
        "calcom_event_type_id": c.calcom_event_type_id,
        "notification_email": c.notification_email,
        "notification_sms": c.notification_sms,
        "send_transcript_email": c.send_transcript_email,
        "send_transcript_sms": c.send_transcript_sms,
        "crm_webhook_url": c.crm_webhook_url,
        "features": c.features,
        "is_active": c.is_active,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
