"""
Claude conversation service.
Handles:
  - Building system prompts per client config + knowledge base
  - Post-call analysis (summary, sentiment, intent)
"""
import logging
from datetime import datetime

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

INTENT_LABELS = ["appointment", "support", "order", "info", "complaint", "other"]
SENTIMENT_LABELS = ["positive", "neutral", "negative", "urgent"]


class ClaudeService:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    def build_system_prompt(self, client, is_vip: bool = False, knowledge_chunks: list[str] | None = None) -> str:
        now = datetime.now()
        weekday = now.strftime("%A").lower()
        current_time = now.strftime("%H:%M")
        current_date = now.strftime("%d/%m/%Y")

        business_hours = client.business_hours or {}
        today_hours = business_hours.get(weekday, {})
        is_open = today_hours.get("enabled", False)
        open_time = today_hours.get("open", "09:00")
        close_time = today_hours.get("close", "18:00")

        # Determine if currently within business hours
        if is_open and open_time and close_time:
            in_hours = open_time <= current_time <= close_time
        else:
            in_hours = False

        vip_note = "\n⭐ This caller is a VIP client. Greet them by name if known, prioritize their request, and offer premium service." if is_vip else ""

        knowledge_section = ""
        if knowledge_chunks:
            knowledge_text = "\n\n".join(knowledge_chunks[:10])
            knowledge_section = f"\n\n## Knowledge Base\nUse the following information to answer questions:\n{knowledge_text}"

        transfer_section = ""
        if client.transfer_numbers:
            depts = ", ".join(client.transfer_numbers.keys())
            transfer_section = f"\n\nAvailable transfer departments: {depts}"

        hours_section = ""
        if is_open:
            hours_section = f"\n\nBusiness hours today: {open_time} - {close_time}. Currently {'open' if in_hours else 'closed'}."
        else:
            hours_section = "\n\nThe business is closed today."

        escalation_keywords = client.escalation_keywords or ["urgent", "emergency"]
        escalation_str = ", ".join(escalation_keywords)

        calendar_section = ""
        if client.calendar_enabled:
            calendar_section = "\n\nYou can book appointments during this conversation using the book_appointment and check_availability functions."

        system_prompt = f"""You are {client.assistant_name}, an intelligent AI secretary for {client.name}.

## Core Behavior
- Respond in the caller's language (auto-detect: French/English/Spanish)
- Be warm, professional, and concise — phone calls should be efficient
- Never say you're an AI unless directly asked. Simply say you are the secretary
- Never put callers on hold unnecessarily
- Always confirm important information (names, dates, phone numbers) by repeating them back
- Current date: {current_date} | Current time: {current_time}{vip_note}

## Business Context
{client.system_prompt or f"You handle inbound calls for {client.name} ({client.business_type} business)."}
{hours_section}
{transfer_section}
{calendar_section}

## Escalation Rules
- If the caller uses keywords like {escalation_str}, treat as high priority and offer immediate transfer or callback
- If you cannot resolve the request after 2-3 exchanges, offer to transfer or take a message
- For complex technical issues, always transfer to a specialist

## Available Actions (Functions)
1. **check_availability** — Check free appointment slots for a date
2. **book_appointment** — Book an appointment during the call
3. **transfer_call** — Transfer to a department with a summary
4. **take_message** — Record caller name, number, message, and urgency
5. **take_order** — Record a customer order (if applicable)
6. **end_call** — End the call politely after resolving the request

## Communication Guidelines
- Keep responses under 50 words for simple confirmations
- Use natural spoken language, avoid lists or bullet points (this is a phone call)
- Spell out numbers: say "nine o'clock" not "9:00"
- When booking, always confirm: date, time, name, and contact details
- After handling the request, ask if there is anything else before ending the call
{knowledge_section}

## After-Hours Behavior
{"You are currently operating after hours. " + client.after_hours_message if not in_hours else "You are currently operating during business hours."}
"""
        return system_prompt.strip()

    async def analyze_call(self, transcript: str) -> dict:
        """Post-call: extract summary, sentiment, intent, outcome."""
        if not transcript or len(transcript) < 20:
            return {
                "summary": "Appel trop court pour analyse.",
                "sentiment": "neutral",
                "sentiment_score": 0.5,
                "intent": "other",
                "outcome": "completed",
            }

        prompt = f"""Analyze this phone call transcript and respond with a JSON object only, no markdown:

Transcript:
{transcript[:3000]}

Return exactly this JSON structure:
{{
  "summary": "2-3 sentence summary of the call in French",
  "sentiment": "positive|neutral|negative|urgent",
  "sentiment_score": 0.0-1.0,
  "intent": "appointment|support|order|info|complaint|other",
  "outcome": "resolved|transferred|message_taken|appointment_booked|order_taken|unresolved",
  "next_action": "brief description of what needs to happen next, in French"
}}"""

        try:
            response = await self.client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )
            import json
            text = response.content[0].text.strip()
            # Strip markdown code blocks if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except Exception as e:
            logger.error(f"Claude analysis failed: {e}")
            return {
                "summary": "Analyse non disponible.",
                "sentiment": "neutral",
                "sentiment_score": 0.5,
                "intent": "other",
                "outcome": "completed",
            }
