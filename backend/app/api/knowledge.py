"""Knowledge base CRUD — manual FAQ, URL ingestion, PDF upload."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import get_db
from app.models.knowledge import KnowledgeEntry
from app.services.knowledge_service import KnowledgeService

router = APIRouter()
svc = KnowledgeService()


class FAQCreate(BaseModel):
    client_id: str
    question: str
    answer: str


class ManualCreate(BaseModel):
    client_id: str
    title: str
    content: str


class URLIngest(BaseModel):
    client_id: str
    url: str


@router.get("/{client_id}")
async def list_knowledge(client_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(KnowledgeEntry)
        .where(KnowledgeEntry.client_id == client_id)
        .order_by(KnowledgeEntry.created_at.desc())
    )
    entries = result.scalars().all()
    return [_serialize(e) for e in entries]


@router.post("/faq", status_code=201)
async def add_faq(data: FAQCreate, db: AsyncSession = Depends(get_db)):
    entry = await svc.add_manual_faq(
        client_id=data.client_id,
        question=data.question,
        answer=data.answer,
        db=db,
    )
    return _serialize(entry)


@router.post("/manual", status_code=201)
async def add_manual(data: ManualCreate, db: AsyncSession = Depends(get_db)):
    entry = KnowledgeEntry(
        client_id=data.client_id,
        title=data.title,
        content=data.content,
        source_type="manual",
    )
    db.add(entry)
    await db.flush()
    return _serialize(entry)


@router.post("/url", status_code=201)
async def ingest_url(data: URLIngest, db: AsyncSession = Depends(get_db)):
    try:
        entry = await svc.ingest_url(client_id=data.client_id, url=data.url, db=db)
        return _serialize(entry)
    except Exception as e:
        raise HTTPException(500, f"URL ingestion failed: {str(e)}")


@router.post("/pdf", status_code=201)
async def ingest_pdf(
    client_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")
    pdf_bytes = await file.read()
    try:
        entry = await svc.ingest_pdf(
            client_id=client_id,
            filename=file.filename,
            pdf_bytes=pdf_bytes,
            db=db,
        )
        return _serialize(entry)
    except Exception as e:
        raise HTTPException(500, f"PDF ingestion failed: {str(e)}")


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(entry_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id))
    entry = result.scalars().first()
    if not entry:
        raise HTTPException(404, "Entry not found")
    entry.is_active = False
    await db.flush()


def _serialize(e: KnowledgeEntry) -> dict:
    return {
        "id": e.id,
        "client_id": e.client_id,
        "title": e.title,
        "content": e.content[:300] + "..." if len(e.content) > 300 else e.content,
        "source_type": e.source_type,
        "source_url": e.source_url,
        "is_active": e.is_active,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }
