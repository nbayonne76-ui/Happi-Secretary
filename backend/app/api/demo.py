"""
Demo data seeder — populates the database with realistic demo data.
Clients, calls, knowledge base entries — ready to show to prospects.
"""
import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.database import get_db
from app.models.client import Client
from app.models.call import CallLog
from app.models.knowledge import KnowledgeEntry

router = APIRouter()

DEMO_CLIENTS = [
    {
        "name": "Cabinet Médical Dr. Martin",
        "business_type": "medical",
        "assistant_name": "Sophie",
        "language": "fr-FR",
        "greeting_message": "Bonjour, cabinet médical du Dr. Martin, je suis Sophie votre assistante. Comment puis-je vous aider ?",
        "system_prompt": "Tu es l'assistante du cabinet médical du Dr. Martin. Tu gères les rendez-vous, réponds aux questions sur les consultations, et orientes les urgences médicales.",
        "notification_email": "demo@cabinet-martin.fr",
        "notification_sms": "+33600000001",
        "calendar_enabled": True,
        "transfer_numbers": {"urgence": "+15550001", "docteur": "+15550002"},
        "escalation_keywords": ["urgent", "douleur", "emergency", "urgence", "saignement"],
        "features": {"sentiment_analysis": True, "call_recording": True, "multilingual": True, "outbound_followup": True},
    },
    {
        "name": "Restaurant Le Provençal",
        "business_type": "restaurant",
        "assistant_name": "Marie",
        "language": "fr-FR",
        "greeting_message": "Bonjour, restaurant Le Provençal, je suis Marie. Je peux prendre votre réservation ou répondre à vos questions.",
        "system_prompt": "Tu es l'assistante du restaurant Le Provençal, un restaurant de cuisine provençale. Tu gères les réservations, informes sur le menu et les horaires.",
        "notification_email": "demo@leprovencal.fr",
        "notification_sms": "+33600000002",
        "calendar_enabled": True,
        "transfer_numbers": {"cuisine": "+15550003", "direction": "+15550004"},
        "escalation_keywords": ["allergie", "intoxication", "plainte", "directeur"],
        "features": {"sentiment_analysis": True, "call_recording": True, "order_taking": True},
    },
    {
        "name": "Agence Immobilière Horizon",
        "business_type": "real_estate",
        "assistant_name": "Clara",
        "language": "fr-FR",
        "greeting_message": "Bonjour, agence Horizon, je suis Clara votre assistante immobilière. En quoi puis-je vous aider ?",
        "system_prompt": "Tu es l'assistante de l'agence immobilière Horizon. Tu qualifies les prospects, organises des visites, et transmets les demandes aux agents.",
        "notification_email": "demo@agence-horizon.fr",
        "notification_sms": "+33600000003",
        "calendar_enabled": True,
        "transfer_numbers": {"ventes": "+15550005", "locations": "+15550006"},
        "escalation_keywords": ["urgent", "achat cash", "investisseur", "promoteur"],
        "features": {"sentiment_analysis": True, "call_recording": True, "multilingual": True, "vip_detection": True},
    },
]

DEMO_KNOWLEDGE = {
    "Cabinet Médical Dr. Martin": [
        {"title": "Horaires du cabinet", "content": "Le cabinet est ouvert lundi, mardi, jeudi et vendredi de 9h à 12h et de 14h à 18h. Fermé mercredi et week-end. Pour les urgences, composer le 15.", "source_type": "manual"},
        {"title": "Tarifs consultations", "content": "Consultation généraliste : 25€ (secteur 1). Consultation avec dépassement : 30€. Carte vitale et mutuelle acceptées. Tiers payant possible.", "source_type": "faq"},
        {"title": "Prise de rendez-vous", "content": "Les rendez-vous se prennent par téléphone ou via Doctolib. Délai moyen : 2-3 jours. Pour les urgences, un créneau de la journée est toujours disponible.", "source_type": "faq"},
        {"title": "Spécialités", "content": "Médecine générale, suivi des maladies chroniques (diabète, hypertension), pédiatrie, gériatrie, médecine du sport. Téléconsultation disponible.", "source_type": "manual"},
    ],
    "Restaurant Le Provençal": [
        {"title": "Horaires d'ouverture", "content": "Ouvert mardi au dimanche. Déjeuner : 12h-14h30. Dîner : 19h-22h30. Fermé le lundi. Réservation recommandée le week-end.", "source_type": "manual"},
        {"title": "Menu et prix", "content": "Menu déjeuner : 18€ (entrée+plat ou plat+dessert), 24€ (entrée+plat+dessert). Carte le soir : 35-55€ par personne. Menu enfant : 12€.", "source_type": "faq"},
        {"title": "Réservations", "content": "Réservations acceptées jusqu'à la veille pour le déjeuner. Pour les groupes de plus de 8 personnes, contacter directement le restaurant. Acompte demandé pour les groupes.", "source_type": "faq"},
        {"title": "Allergènes et régimes", "content": "Menu végétarien disponible. Plats sans gluten sur demande. Informer le serveur de toute allergie. Liste des allergènes disponible sur demande.", "source_type": "manual"},
    ],
    "Agence Immobilière Horizon": [
        {"title": "Services proposés", "content": "Vente et location de biens résidentiels et commerciaux. Gestion locative. Estimation gratuite. Accompagnement complet jusqu'à la signature.", "source_type": "manual"},
        {"title": "Secteurs couverts", "content": "Nous couvrons toute l'Île-de-France avec des agences à Paris, Vincennes, Saint-Maur et Nogent-sur-Marne.", "source_type": "faq"},
        {"title": "Honoraires", "content": "Honoraires conformes à la loi Alur. Vente : 4-6% TTC du prix de vente. Location : 1 mois de loyer HC pour le locataire. Estimation et mandat exclusif gratuits.", "source_type": "faq"},
        {"title": "Processus d'achat", "content": "1. Estimation budget et recherche. 2. Visites organisées sous 48h. 3. Offre d'achat. 4. Compromis de vente. 5. Acte authentique chez le notaire. Délai moyen : 3 mois.", "source_type": "manual"},
    ],
}

CALL_SCENARIOS = [
    {"intent": "appointment", "sentiment": "positive", "outcome": "appointment_booked", "caller": "+33611223344", "summary": "Client a pris rendez-vous pour une consultation de routine. Créneau confirmé pour demain à 10h."},
    {"intent": "info",        "sentiment": "neutral",  "outcome": "resolved",           "caller": "+33622334455", "summary": "Demande d'informations sur les horaires et tarifs. Informations fournies, client satisfait."},
    {"intent": "complaint",   "sentiment": "negative", "outcome": "transferred",        "caller": "+33633445566", "summary": "Client mécontent suite à un problème de facturation. Appel transféré au responsable."},
    {"intent": "support",     "sentiment": "neutral",  "outcome": "message_taken",      "caller": "+33644556677", "summary": "Demande de rappel pour discuter d'une situation urgente. Message transmis à l'équipe."},
    {"intent": "appointment", "sentiment": "positive", "outcome": "appointment_booked", "caller": "+33655667788", "summary": "Nouveau patient souhaitant s'inscrire. Rendez-vous pris pour bilan initial."},
    {"intent": "info",        "sentiment": "positive", "outcome": "resolved",           "caller": "+33666778899", "summary": "Question sur le menu et disponibilité ce soir. Réservation proposée et acceptée."},
    {"intent": "order",       "sentiment": "positive", "outcome": "order_taken",        "caller": "+33677889900", "summary": "Commande pour livraison prise avec succès. Total : 45€, livraison 30 min."},
    {"intent": "complaint",   "sentiment": "urgent",   "outcome": "transferred",        "caller": "+33688990011", "summary": "Urgence signalée par le client. Transfert immédiat vers l'équipe de permanence."},
    {"intent": "info",        "sentiment": "neutral",  "outcome": "resolved",           "caller": "+33699001122", "summary": "Renseignements sur les biens disponibles à la vente. Visite programmée pour samedi."},
    {"intent": "appointment", "sentiment": "positive", "outcome": "appointment_booked", "caller": "+33611334455", "summary": "Visite d'appartement programmée. Client intéressé par un 3 pièces dans le 12ème."},
]


@router.post("/seed")
async def seed_demo_data(db: AsyncSession = Depends(get_db)):
    """Seed the database with demo clients, calls and knowledge base."""

    # Clear existing demo data
    await db.execute(delete(KnowledgeEntry))
    await db.execute(delete(CallLog))
    await db.execute(delete(Client))
    await db.flush()

    created_clients = []

    for client_data in DEMO_CLIENTS:
        client = Client(**client_data)
        db.add(client)
        await db.flush()
        created_clients.append(client)

        # Add knowledge entries
        for entry_data in DEMO_KNOWLEDGE.get(client.name, []):
            entry = KnowledgeEntry(client_id=client.id, **entry_data)
            db.add(entry)

        # Generate call history (last 30 days)
        for i, scenario in enumerate(CALL_SCENARIOS[:7]):
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(8, 18)
            call_time = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago)
            duration = random.randint(60, 420)

            messages = [
                {"role": "assistant", "content": client.greeting_message, "timestamp": call_time.isoformat()},
                {"role": "user", "content": _sample_caller_text(scenario["intent"]), "timestamp": (call_time + timedelta(seconds=5)).isoformat()},
                {"role": "assistant", "content": _sample_response(scenario["intent"]), "timestamp": (call_time + timedelta(seconds=12)).isoformat()},
            ]

            call = CallLog(
                client_id=client.id,
                vapi_call_id=f"demo-{client.id[:8]}-{i}",
                caller_number=scenario["caller"],
                started_at=call_time,
                ended_at=call_time + timedelta(seconds=duration),
                duration_seconds=duration,
                status="completed" if scenario["outcome"] != "transferred" else "transferred",
                intent=scenario["intent"],
                sentiment=scenario["sentiment"],
                sentiment_score=random.uniform(0.5, 0.95),
                summary=scenario["summary"],
                outcome=scenario["outcome"],
                appointment_booked=scenario["outcome"] == "appointment_booked",
                appointment_id=f"DEMO-{random.randint(100, 999)}" if scenario["outcome"] == "appointment_booked" else None,
                transferred_to="management" if scenario["outcome"] == "transferred" else None,
                transcript="\n".join([f"{'Assistant' if m['role'] == 'assistant' else 'Client'}: {m['content']}" for m in messages]),
                messages=messages,
                email_sent=True,
                sms_sent=True,
            )
            db.add(call)

    await db.flush()
    return {
        "success": True,
        "message": f"{len(created_clients)} clients créés avec données de démo.",
        "clients": [{"id": c.id, "name": c.name} for c in created_clients],
    }


@router.delete("/reset")
async def reset_demo_data(db: AsyncSession = Depends(get_db)):
    """Clear all demo data."""
    await db.execute(delete(KnowledgeEntry))
    await db.execute(delete(CallLog))
    await db.execute(delete(Client))
    await db.flush()
    return {"success": True, "message": "Toutes les données ont été supprimées."}


def _sample_caller_text(intent: str) -> str:
    texts = {
        "appointment": "Bonjour, je voudrais prendre un rendez-vous s'il vous plaît.",
        "info": "Bonjour, je voulais avoir des informations sur vos services.",
        "complaint": "Bonjour, j'ai un problème avec ma dernière facture, je suis assez mécontent.",
        "support": "Bonjour, j'aurais besoin d'aide pour une situation un peu urgente.",
        "order": "Bonjour, je voudrais passer une commande s'il vous plaît.",
    }
    return texts.get(intent, "Bonjour, j'ai une question.")


def _sample_response(intent: str) -> str:
    responses = {
        "appointment": "Bien sûr ! Avez-vous une préférence pour la date et l'heure ?",
        "info": "Je suis là pour vous aider. Quelle information recherchez-vous exactement ?",
        "complaint": "Je suis vraiment désolé d'apprendre cela. Pouvez-vous me donner plus de détails ?",
        "support": "Je comprends. Pouvez-vous me décrire la situation ?",
        "order": "Avec plaisir. Que souhaitez-vous commander ?",
    }
    return responses.get(intent, "Je vous écoute, comment puis-je vous aider ?")
