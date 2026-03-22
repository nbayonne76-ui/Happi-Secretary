"""
CRM webhook service.
Pushes call events to any CRM (HubSpot, Pipedrive, Salesforce, n8n, Make, Zapier, etc.)
via a configurable webhook URL per client.
"""
import logging

import httpx

logger = logging.getLogger(__name__)


class CrmService:
    async def push_event(
        self,
        webhook_url: str,
        headers: dict,
        event_type: str,
        data: dict,
    ) -> bool:
        payload = {"event": event_type, "data": data}
        return await self._post(webhook_url, headers, payload)

    async def push_call_completed(self, client, call_log) -> bool:
        payload = {
            "event": "call.completed",
            "source": "happi-secretary",
            "client_id": client.id,
            "client_name": client.name,
            "call": {
                "id": call_log.id,
                "vapi_call_id": call_log.vapi_call_id,
                "caller_number": call_log.caller_number,
                "caller_name": call_log.caller_name,
                "is_vip": call_log.is_vip,
                "started_at": call_log.started_at.isoformat() if call_log.started_at else None,
                "ended_at": call_log.ended_at.isoformat() if call_log.ended_at else None,
                "duration_seconds": call_log.duration_seconds,
                "status": call_log.status,
                "intent": call_log.intent,
                "sentiment": call_log.sentiment,
                "outcome": call_log.outcome,
                "summary": call_log.summary,
                "appointment_booked": call_log.appointment_booked,
                "appointment_id": call_log.appointment_id,
                "transferred_to": call_log.transferred_to,
                "order_data": call_log.order_data,
                "recording_url": call_log.recording_url,
            },
        }
        return await self._post(client.crm_webhook_url, client.crm_headers or {}, payload)

    async def _post(self, url: str, headers: dict, payload: dict) -> bool:
        try:
            merged_headers = {"Content-Type": "application/json", **headers}
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, headers=merged_headers, json=payload)
                resp.raise_for_status()
                logger.info(f"CRM webhook pushed to {url} — {resp.status_code}")
                return True
        except Exception as e:
            logger.error(f"CRM webhook failed ({url}): {e}")
            return False
