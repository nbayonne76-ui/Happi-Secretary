"""
Mock service — simulates ALL external APIs locally with zero cost.
Used when API keys are not set. Switches automatically to real APIs when keys are present.

Simulates:
  - Claude (conversation AI)
  - ElevenLabs (TTS — returns text)
  - Deepgram (STT — accepts text directly)
  - Cal.com (calendar — in-memory slots)
  - Twilio (SMS — logs to console)
  - Resend (email — logs to console)
  - Vapi (telephony — HTTP simulation)
"""
import logging
import random
from datetime import datetime, timedelta

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Smart conversation engine — no API key needed
# ---------------------------------------------------------------------------
class MockConversationEngine:
    """
    Rule-based conversation engine that simulates an AI secretary.
    Detects intent from caller text and returns appropriate responses.
    """

    INTENTS = {
        "appointment": ["rendez-vous", "rdv", "réserver", "disponible", "appointment", "book", "schedule", "créneau"],
        "cancel":      ["annuler", "annulation", "cancel", "supprimer"],
        "hours":       ["horaire", "heure", "ouvert", "fermé", "hours", "open", "schedule"],
        "price":       ["prix", "tarif", "coût", "combien", "price", "cost", "rate"],
        "address":     ["adresse", "où", "situé", "location", "address", "where"],
        "transfer":    ["directeur", "responsable", "manager", "parler à", "transfer", "speak to"],
        "complaint":   ["problème", "plainte", "mécontent", "complaint", "issue", "problem"],
        "order":       ["commander", "commande", "order"],
        "emergency":   ["urgent", "urgence", "emergency", "immédiat"],
        "goodbye":     ["au revoir", "merci", "bye", "goodbye", "bonne journée", "ciao"],
    }

    RESPONSES = {
        "appointment": [
            "Bien sûr, je peux vous aider à prendre un rendez-vous. Quelle date vous conviendrait ?",
            "Parfait. Avez-vous une préférence pour la date et l'heure ?",
            "Je vérifie les disponibilités. Seriez-vous disponible en début ou fin de semaine ?",
        ],
        "cancel": [
            "Je comprends. Pouvez-vous me donner votre nom et la date de votre rendez-vous pour que je l'annule ?",
            "Pas de problème. Je vais annuler votre rendez-vous. Quel est votre nom ?",
        ],
        "hours": [
            "Nous sommes ouverts du lundi au vendredi de 9h à 18h, et le samedi de 10h à 13h.",
            "Nos horaires : lundi–vendredi 9h–18h, samedi 10h–13h. Fermés le dimanche.",
        ],
        "price": [
            "Pour les informations tarifaires, je vais prendre vos coordonnées et un responsable vous rappellera dans les plus brefs délais.",
            "Les tarifs varient selon la prestation. Puis-je avoir votre email pour vous envoyer notre grille tarifaire ?",
        ],
        "address": [
            "Vous trouverez nos coordonnées sur notre site internet. Souhaitez-vous que je vous envoie l'adresse par SMS ?",
        ],
        "transfer": [
            "Je vous mets en relation avec un responsable. Un instant s'il vous plaît.",
            "Je transfère votre appel. Pouvez-vous me préciser l'objet de votre demande pour que je puisse faire un résumé ?",
        ],
        "complaint": [
            "Je suis désolé d'apprendre cela. Je comprends votre frustration. Pouvez-vous me décrire le problème en détail ?",
            "Je vous présente nos excuses. Je vais transmettre votre réclamation en urgence à notre équipe.",
        ],
        "order": [
            "Je prends votre commande. Que souhaitez-vous commander ?",
            "Bien sûr. Pouvez-vous me donner les détails de votre commande ?",
        ],
        "emergency": [
            "Je comprends l'urgence. Je vous transfère immédiatement vers notre équipe disponible.",
            "Urgent noté. Un responsable va vous prendre en charge dans les secondes qui suivent.",
        ],
        "goodbye": [
            "Merci pour votre appel. Bonne journée !",
            "De rien, n'hésitez pas à rappeler si besoin. Au revoir !",
            "Avec plaisir. Bonne journée à vous !",
        ],
        "default": [
            "Bien sûr, je note votre demande. Pouvez-vous me donner plus de détails ?",
            "Je comprends. Laissez-moi vous aider. Pouvez-vous préciser votre demande ?",
            "Absolument. Puis-je avoir votre nom et numéro de téléphone pour le suivi ?",
            "Je prends bonne note. Y a-t-il autre chose que je puisse faire pour vous ?",
        ],
    }

    SLOT_CONFIRMATIONS = [
        "Parfait ! J'ai des créneaux disponibles le {date} à 9h00, 10h30 et 14h00. Lequel vous convient ?",
        "Je vois de la disponibilité le {date}. Je vous propose 10h00 ou 15h30. Quelle heure préférez-vous ?",
    ]

    BOOKING_CONFIRMATIONS = [
        "Excellent ! Votre rendez-vous est confirmé le {date} à {time}. Vous recevrez une confirmation par email.",
        "Parfait, je vous inscris le {date} à {time}. Pouvez-vous me confirmer votre email pour l'invitation ?",
    ]

    def __init__(self, client_name: str = "notre entreprise", assistant_name: str = "Happi"):
        self.client_name = client_name
        self.assistant_name = assistant_name
        self.conversation_state = {}  # call_id -> state

    def get_greeting(self, is_vip: bool = False) -> str:
        if is_vip:
            return f"Bonjour ! Bienvenue chez {self.client_name}, je suis {self.assistant_name} votre assistante. Je vois que vous êtes un de nos clients privilégiés. Comment puis-je vous aider aujourd'hui ?"
        return f"Bonjour, vous êtes bien chez {self.client_name}, je suis {self.assistant_name} votre assistante IA. Comment puis-je vous aider ?"

    def detect_intent(self, text: str) -> str:
        text_lower = text.lower()
        for intent, keywords in self.INTENTS.items():
            if any(kw in text_lower for kw in keywords):
                return intent
        return "default"

    def get_response(self, call_id: str, caller_text: str, turn: int = 1) -> dict:
        """Returns response dict with: text, intent, action, action_data"""
        intent = self.detect_intent(caller_text)
        state = self.conversation_state.get(call_id, {})

        # Special flow: appointment booking
        if intent == "appointment":
            if not state.get("asked_date"):
                self.conversation_state[call_id] = {**state, "asked_date": True, "intent": "appointment"}
                return {
                    "text": random.choice(self.RESPONSES["appointment"]),
                    "intent": "appointment",
                    "action": None,
                }
            elif not state.get("date_confirmed"):
                # Simulate date confirmed
                tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
                self.conversation_state[call_id] = {**state, "date_confirmed": True, "date": tomorrow}
                return {
                    "text": random.choice(self.SLOT_CONFIRMATIONS).format(date=tomorrow),
                    "intent": "appointment",
                    "action": "show_slots",
                    "action_data": {"date": tomorrow, "slots": ["09:00", "10:30", "14:00"]},
                }
            else:
                # Book the appointment
                date = state.get("date", datetime.now().strftime("%d/%m/%Y"))
                time = "10:00"
                self.conversation_state[call_id] = {**state, "booked": True}
                return {
                    "text": random.choice(self.BOOKING_CONFIRMATIONS).format(date=date, time=time),
                    "intent": "appointment",
                    "action": "book_appointment",
                    "action_data": {"date": date, "time": time, "confirmed": True},
                }

        # Transfer flow
        if intent == "transfer" or intent == "emergency":
            return {
                "text": random.choice(self.RESPONSES[intent]),
                "intent": intent,
                "action": "transfer",
                "action_data": {"department": "management", "urgency": intent == "emergency"},
            }

        # Goodbye
        if intent == "goodbye":
            return {
                "text": random.choice(self.RESPONSES["goodbye"]),
                "intent": "goodbye",
                "action": "end_call",
                "action_data": {},
            }

        response_list = self.RESPONSES.get(intent, self.RESPONSES["default"])
        return {
            "text": random.choice(response_list),
            "intent": intent,
            "action": None,
            "action_data": {},
        }

    def generate_summary(self, messages: list[dict]) -> dict:
        """Generate a call summary from conversation history."""
        intents_found = set()
        for msg in messages:
            if msg.get("role") == "user":
                intent = self.detect_intent(msg.get("content", ""))
                intents_found.add(intent)

        primary_intent = next(iter(intents_found - {"default", "goodbye"}), "info")

        intent_summaries = {
            "appointment": "Le client a pris un rendez-vous. La demande a été traitée avec succès.",
            "cancel": "Le client a demandé l'annulation d'un rendez-vous.",
            "complaint": "Le client a exprimé une réclamation. Le dossier a été transmis à l'équipe.",
            "transfer": "L'appel a été transféré à un responsable suite à la demande du client.",
            "order": "Une commande a été enregistrée et confirmée au client.",
            "price": "Le client a demandé des informations tarifaires. Un suivi par email prévu.",
            "emergency": "Appel urgent — transfert immédiat effectué vers l'équipe disponible.",
            "info": "Le client a demandé des informations générales. Demande traitée.",
        }

        sentiment_map = {
            "complaint": "negative",
            "emergency": "urgent",
            "appointment": "positive",
            "order": "positive",
        }

        return {
            "summary": intent_summaries.get(primary_intent, "Appel traité avec succès."),
            "intent": primary_intent,
            "sentiment": sentiment_map.get(primary_intent, "neutral"),
            "sentiment_score": 0.7,
            "outcome": "resolved" if primary_intent not in ["transfer", "emergency"] else "transferred",
        }


# ---------------------------------------------------------------------------
# Mock notification — logs instead of sending
# ---------------------------------------------------------------------------
class MockNotificationService:
    async def send_email(self, to: str, subject: str, body: str, **kwargs) -> bool:
        logger.info(f"[MOCK EMAIL] To: {to} | Subject: {subject}")
        logger.info(f"[MOCK EMAIL] Body: {body[:200]}")
        return True

    async def send_sms(self, to: str, body: str) -> bool:
        logger.info(f"[MOCK SMS] To: {to} | {body[:160]}")
        return True

    async def send_call_transcript_email(self, client, call_log) -> bool:
        logger.info(f"[MOCK EMAIL] Transcript to {client.notification_email} for call {call_log.id}")
        return True

    async def send_call_summary_sms(self, client, call_log) -> bool:
        logger.info(f"[MOCK SMS] Summary to {client.notification_sms} for call {call_log.id}")
        return True


# ---------------------------------------------------------------------------
# Mock Cal.com — in-memory calendar
# ---------------------------------------------------------------------------
class MockCalcomService:
    async def get_available_slots(self, **kwargs) -> list[str]:
        return ["09:00", "09:30", "10:00", "11:00", "14:00", "14:30", "15:00", "16:00"]

    async def book_appointment(self, date: str, time: str, attendee_name: str, **kwargs) -> dict:
        return {
            "success": True,
            "booking_id": f"MOCK-{random.randint(1000, 9999)}",
            "message": f"Rendez-vous confirmé le {date} à {time} pour {attendee_name}. (Mode démo)",
        }


# ---------------------------------------------------------------------------
# Service factory — returns mock or real based on env
# ---------------------------------------------------------------------------
def get_notification_service():
    if settings.RESEND_API_KEY and settings.RESEND_API_KEY != "":
        from app.services.notification_service import NotificationService
        return NotificationService()
    return MockNotificationService()


def get_calcom_service(api_key: str | None = None):
    key = api_key or settings.CALCOM_API_KEY
    if key and key != "":
        from app.services.calcom_service import CalcomService
        return CalcomService(api_key=key)
    return MockCalcomService()


def is_mock_mode() -> bool:
    """Returns True if running without real API keys (demo/dev mode)."""
    return not bool(settings.ANTHROPIC_API_KEY and settings.ANTHROPIC_API_KEY not in ("", "sk-ant-..."))
