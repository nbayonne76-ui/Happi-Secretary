from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.models.database import init_db
from app.api import vapi_webhook, calls, clients, knowledge, analytics, simulator, demo


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vapi_webhook.router, prefix="/api/vapi", tags=["vapi"])
app.include_router(calls.router, prefix="/api/calls", tags=["calls"])
app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(simulator.router, prefix="/api/simulator", tags=["simulator"])
app.include_router(demo.router, prefix="/api/demo", tags=["demo"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}
