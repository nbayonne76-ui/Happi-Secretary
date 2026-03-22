"""
Cal.com v2 API integration.
Handles: slot availability checks + booking during live calls.
"""
import logging
from datetime import datetime, timedelta

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class CalcomService:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.CALCOM_API_KEY
        self.base_url = settings.CALCOM_API_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "cal-api-version": "2024-09-04",
        }

    async def get_available_slots(self, event_type_id: int | None, date: str) -> list[str]:
        """Return list of available time slots (HH:MM) for a given date."""
        if not event_type_id or not self.api_key:
            return self._mock_slots(date)

        try:
            # Cal.com v2 slots endpoint
            start = f"{date}T00:00:00Z"
            end_dt = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            end = f"{end_dt}T00:00:00Z"

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.base_url}/slots/available",
                    headers=self.headers,
                    params={
                        "eventTypeId": event_type_id,
                        "startTime": start,
                        "endTime": end,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                slots = data.get("data", {}).get("slots", {}).get(date, [])
                return [s.get("time", "")[-8:-3] for s in slots if s.get("time")]
        except Exception as e:
            logger.error(f"Cal.com get_slots error: {e}")
            return self._mock_slots(date)

    async def book_appointment(
        self,
        event_type_id: int | None,
        date: str,
        time: str,
        attendee_name: str,
        attendee_email: str,
        attendee_phone: str = "",
        notes: str = "",
    ) -> dict:
        """Book an appointment and return success + booking ID."""
        if not event_type_id or not self.api_key:
            return self._mock_booking(date, time, attendee_name)

        try:
            start_time = f"{date}T{time}:00Z"
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.base_url}/bookings",
                    headers=self.headers,
                    json={
                        "eventTypeId": event_type_id,
                        "start": start_time,
                        "attendee": {
                            "name": attendee_name,
                            "email": attendee_email,
                            "phoneNumber": attendee_phone,
                            "timeZone": "Europe/Paris",
                            "language": "fr",
                        },
                        "metadata": {"notes": notes, "source": "happi-secretary"},
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                booking = data.get("data", {})
                return {
                    "success": True,
                    "booking_id": str(booking.get("id", "")),
                    "message": f"Rendez-vous confirmé le {date} à {time} pour {attendee_name}.",
                }
        except Exception as e:
            logger.error(f"Cal.com booking error: {e}")
            return {
                "success": False,
                "message": "Je n'ai pas pu confirmer le rendez-vous. Votre demande a été enregistrée et nous vous confirmerons par email.",
            }

    async def cancel_appointment(self, booking_id: str, reason: str = "") -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.delete(
                    f"{self.base_url}/bookings/{booking_id}",
                    headers=self.headers,
                    json={"cancellationReason": reason},
                )
                return resp.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Cal.com cancel error: {e}")
            return False

    def _mock_slots(self, date: str) -> list[str]:
        """Return mock slots for dev/testing when no Cal.com key is set."""
        return ["09:00", "09:30", "10:00", "11:00", "14:00", "14:30", "15:00", "16:00"]

    def _mock_booking(self, date: str, time: str, name: str) -> dict:
        return {
            "success": True,
            "booking_id": "mock-booking-001",
            "message": f"Rendez-vous confirmé le {date} à {time} pour {name}. (Mode test)",
        }
