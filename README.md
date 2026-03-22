# Happi Secretary

AI vocal secretary system — answers calls 24/7, books appointments, handles support, transcribes and notifies.

## Stack
- **Backend**: FastAPI + PostgreSQL + SQLAlchemy async
- **AI**: Claude (Anthropic) — conversation + post-call analysis
- **Telephony**: Vapi.ai — inbound/outbound calls, sub-500ms latency
- **Voice**: ElevenLabs TTS + Deepgram STT
- **Calendar**: Cal.com API — live booking during call
- **Notifications**: Resend (email) + Twilio (SMS)
- **Dashboard**: Next.js 14 + Tailwind CSS

## Quick start

```bash
# 1. Clone and configure
cp .env.example .env
# Fill in your API keys in .env

# 2. Start everything
docker-compose up --build

# Backend:   http://localhost:8000
# Dashboard: http://localhost:3000
# API docs:  http://localhost:8000/docs
```

## Call flow

```
Caller → Vapi.ai → POST /api/vapi/webhook (assistant-request)
                 → Claude builds response with client KB + rules
                 → ElevenLabs voices the reply
                 → [book_appointment] → Cal.com API
                 → [transfer_call]   → Vapi transfer
                 → [take_message]    → Email + SMS instantly
         End of call → POST /api/vapi/webhook (end-of-call-report)
                     → Claude analyzes: summary + sentiment + intent
                     → Email transcript + SMS summary sent
                     → CRM webhook fired
```

## Features
- Inbound call answering 24/7 with custom greeting
- Appointment scheduling during call (Cal.com sync)
- FAQ answering from configurable knowledge base (PDF, URL, text)
- Intelligent call routing with human summary
- Message taking + instant email/SMS transcription
- Level-1 customer support with auto-escalation
- Order taking
- Sentiment detection (positive / negative / urgent)
- VIP caller recognition
- Post-call AI analysis (summary, intent, outcome)
- Analytics dashboard
- CRM webhook push (HubSpot, Pipedrive, Zapier, Make, etc.)
- Multi-language auto-detect (FR/EN/ES)
- Call recording (RGPD compliant)

## Project structure
```
Happi-Secretary/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/          # REST routes
│   │   ├── services/     # Claude, Vapi, Cal.com, notifications, CRM
│   │   └── models/       # SQLAlchemy models
│   ├── requirements.txt
│   └── Dockerfile
├── dashboard/            # Next.js admin panel
│   └── app/
│       ├── page.tsx          # Dashboard KPIs
│       ├── calls/            # Call history + detail
│       ├── clients/          # Client config
│       ├── knowledge/        # Knowledge base
│       └── analytics/        # Charts
├── docker-compose.yml
└── .env.example
```
