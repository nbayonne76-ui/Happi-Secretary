"""
Notification service — sends email transcripts and SMS summaries after calls.
Uses: Resend (email) + Twilio (SMS)
"""
import logging

import httpx
from twilio.rest import Client as TwilioClient

from app.config import settings

logger = logging.getLogger(__name__)

SENTIMENT_EMOJI = {
    "positive": "😊",
    "neutral": "📋",
    "negative": "⚠️",
    "urgent": "🚨",
}

INTENT_LABEL = {
    "appointment": "Prise de rendez-vous",
    "support": "Support client",
    "order": "Commande",
    "info": "Demande d'information",
    "complaint": "Réclamation",
    "other": "Autre",
}


class NotificationService:
    def __init__(self):
        self._twilio: TwilioClient | None = None
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            self._twilio = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    # ------------------------------------------------------------------
    # Email via Resend
    # ------------------------------------------------------------------
    async def send_email(self, to: str, subject: str, body: str, html: str | None = None) -> bool:
        if not settings.RESEND_API_KEY:
            logger.warning("RESEND_API_KEY not set — skipping email")
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": "Happi Secretary <noreply@happi-secretary.com>",
                        "to": [to],
                        "subject": subject,
                        "text": body,
                        "html": html or body.replace("\n", "<br>"),
                    },
                )
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False

    async def send_call_transcript_email(self, client, call_log) -> bool:
        sentiment_icon = SENTIMENT_EMOJI.get(call_log.sentiment or "neutral", "📋")
        intent_label = INTENT_LABEL.get(call_log.intent or "other", "Appel")
        duration_min = (call_log.duration_seconds or 0) // 60
        duration_sec = (call_log.duration_seconds or 0) % 60

        subject = (
            f"[{client.assistant_name}] {sentiment_icon} {intent_label} "
            f"— {call_log.caller_number or 'Numéro inconnu'}"
        )

        html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
  <div style="background: #6C63FF; padding: 20px; border-radius: 8px 8px 0 0;">
    <h1 style="color: white; margin: 0; font-size: 20px;">{client.assistant_name} — Rapport d'appel</h1>
  </div>
  <div style="background: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; border: 1px solid #e0e0e0;">

    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
      <tr><td style="padding: 6px 0; color: #666; width: 40%;">📞 Numéro</td><td><strong>{call_log.caller_number or 'Inconnu'}</strong>{"&nbsp; ⭐ VIP" if call_log.is_vip else ""}</td></tr>
      <tr><td style="padding: 6px 0; color: #666;">⏱ Durée</td><td><strong>{duration_min}min {duration_sec}s</strong></td></tr>
      <tr><td style="padding: 6px 0; color: #666;">🎯 Intention</td><td><strong>{intent_label}</strong></td></tr>
      <tr><td style="padding: 6px 0; color: #666;">😊 Sentiment</td><td><strong>{sentiment_icon} {call_log.sentiment or 'neutral'}</strong></td></tr>
      <tr><td style="padding: 6px 0; color: #666;">✅ Résultat</td><td><strong>{call_log.outcome or 'completed'}</strong></td></tr>
    </table>

    <div style="background: white; border-left: 4px solid #6C63FF; padding: 12px; margin-bottom: 20px; border-radius: 0 4px 4px 0;">
      <strong>Résumé IA</strong><br>
      {call_log.summary or 'Aucun résumé disponible.'}
    </div>

    {"<div style='background: #fff3cd; border: 1px solid #ffc107; padding: 10px; border-radius: 4px; margin-bottom: 20px;'><strong>📅 Rendez-vous réservé</strong> — ID: " + str(call_log.appointment_id or '') + "</div>" if call_log.appointment_booked else ""}

    <details>
      <summary style="cursor: pointer; font-weight: bold; margin-bottom: 10px;">📝 Transcription complète</summary>
      <div style="background: white; padding: 12px; border-radius: 4px; font-size: 13px; white-space: pre-wrap; border: 1px solid #e0e0e0; max-height: 300px; overflow-y: auto;">
{call_log.transcript or 'Aucune transcription disponible.'}
      </div>
    </details>

    {"<p><a href='" + str(call_log.recording_url) + "' style='color: #6C63FF;'>🎵 Écouter l'enregistrement</a></p>" if call_log.recording_url else ""}

    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
    <p style="font-size: 12px; color: #999;">Happi Secretary — Votre secrétariat IA 24h/24</p>
  </div>
</body>
</html>
"""
        return await self.send_email(to=client.notification_email, subject=subject, html=html, body=call_log.summary or "")

    # ------------------------------------------------------------------
    # SMS via Twilio
    # ------------------------------------------------------------------
    async def send_sms(self, to: str, body: str) -> bool:
        if not self._twilio or not settings.TWILIO_FROM_NUMBER:
            logger.warning("Twilio not configured — skipping SMS")
            return False
        try:
            self._twilio.messages.create(
                to=to,
                from_=settings.TWILIO_FROM_NUMBER,
                body=body[:1600],
            )
            return True
        except Exception as e:
            logger.error(f"SMS send failed: {e}")
            return False

    async def send_call_summary_sms(self, client, call_log) -> bool:
        intent_label = INTENT_LABEL.get(call_log.intent or "other", "Appel")
        body = (
            f"[{client.assistant_name}] Appel de {call_log.caller_number or 'inconnu'}\n"
            f"Motif: {intent_label}\n"
            f"Résultat: {call_log.outcome or 'completed'}\n"
            f"{(call_log.summary or '')[:100]}"
        )
        return await self.send_sms(to=client.notification_sms, body=body)
