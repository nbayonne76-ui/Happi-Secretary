"""
Vapi management service.
Handles: creating/updating assistants, provisioning phone numbers, outbound calls.
"""
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)
VAPI_BASE = "https://api.vapi.ai"


class VapiService:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {settings.VAPI_API_KEY}",
            "Content-Type": "application/json",
        }

    async def create_assistant(self, client) -> str | None:
        """Create a Vapi assistant for a client. Returns assistant ID."""
        payload = {
            "name": f"{client.assistant_name} — {client.name}",
            "model": {
                "provider": "anthropic",
                "model": settings.CLAUDE_MODEL,
                "temperature": 0.4,
                "maxTokens": 300,
                "messages": [],  # System prompt injected via webhook assistant-request
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
            "serverUrl": f"{settings.DASHBOARD_URL.replace('3000', '8000')}/api/vapi/webhook",
            "endCallFunctionEnabled": True,
            "recordingEnabled": client.features.get("call_recording", True),
        }
        try:
            async with httpx.AsyncClient(timeout=15) as http:
                resp = await http.post(f"{VAPI_BASE}/assistant", headers=self.headers, json=payload)
                resp.raise_for_status()
                return resp.json().get("id")
        except Exception as e:
            logger.error(f"Vapi create_assistant failed: {e}")
            return None

    async def update_assistant(self, assistant_id: str, client) -> bool:
        payload = {
            "name": f"{client.assistant_name} — {client.name}",
            "voice": {"provider": "elevenlabs", "voiceId": client.voice_id},
        }
        try:
            async with httpx.AsyncClient(timeout=15) as http:
                resp = await http.patch(
                    f"{VAPI_BASE}/assistant/{assistant_id}",
                    headers=self.headers,
                    json=payload,
                )
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Vapi update_assistant failed: {e}")
            return False

    async def list_phone_numbers(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=10) as http:
                resp = await http.get(f"{VAPI_BASE}/phone-number", headers=self.headers)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"Vapi list_phone_numbers failed: {e}")
            return []

    async def make_outbound_call(
        self,
        to_number: str,
        assistant_id: str,
        first_message: str = "Bonjour, je vous contacte suite à votre appel manqué.",
    ) -> dict | None:
        """Initiate an outbound follow-up call."""
        try:
            async with httpx.AsyncClient(timeout=15) as http:
                resp = await http.post(
                    f"{VAPI_BASE}/call/phone",
                    headers=self.headers,
                    json={
                        "assistantId": assistant_id,
                        "customer": {"number": to_number},
                        "assistantOverrides": {
                            "firstMessage": first_message,
                        },
                    },
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"Vapi outbound call failed: {e}")
            return None
