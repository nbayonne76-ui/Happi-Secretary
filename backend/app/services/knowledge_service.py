"""
Knowledge base service.
Handles: ingesting PDFs, URLs, and manual FAQ entries.
Formats content into chunks for Claude's system prompt.
"""
import logging
import re

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.knowledge import KnowledgeEntry

logger = logging.getLogger(__name__)


class KnowledgeService:
    async def get_chunks_for_client(self, client_id: str, db: AsyncSession) -> list[str]:
        """Return knowledge base entries as text chunks for injection into system prompt."""
        result = await db.execute(
            select(KnowledgeEntry)
            .where(KnowledgeEntry.client_id == client_id, KnowledgeEntry.is_active == True)
            .order_by(KnowledgeEntry.created_at)
        )
        entries = result.scalars().all()
        return [f"### {e.title}\n{e.content}" for e in entries]

    async def ingest_url(self, client_id: str, url: str, db: AsyncSession) -> KnowledgeEntry:
        """Fetch a webpage and extract text content."""
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                raw_html = resp.text

            # Basic HTML stripping
            text = re.sub(r"<script[^>]*>.*?</script>", "", raw_html, flags=re.DOTALL)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            text = text[:5000]  # Limit size

            entry = KnowledgeEntry(
                client_id=client_id,
                title=f"Page web: {url[:100]}",
                content=text,
                source_type="url",
                source_url=url,
            )
            db.add(entry)
            await db.flush()
            return entry
        except Exception as e:
            logger.error(f"URL ingestion failed ({url}): {e}")
            raise

    async def ingest_pdf(self, client_id: str, filename: str, pdf_bytes: bytes, db: AsyncSession) -> KnowledgeEntry:
        """Extract text from PDF bytes using pypdf."""
        try:
            import io
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(pdf_bytes))
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            text = re.sub(r"\s+", " ", text).strip()[:8000]

            entry = KnowledgeEntry(
                client_id=client_id,
                title=f"Document: {filename}",
                content=text,
                source_type="pdf",
            )
            db.add(entry)
            await db.flush()
            return entry
        except ImportError:
            raise RuntimeError("pypdf not installed. Add it to requirements.txt")
        except Exception as e:
            logger.error(f"PDF ingestion failed: {e}")
            raise

    async def add_manual_faq(
        self,
        client_id: str,
        question: str,
        answer: str,
        db: AsyncSession,
    ) -> KnowledgeEntry:
        entry = KnowledgeEntry(
            client_id=client_id,
            title=question,
            content=f"Q: {question}\nR: {answer}",
            source_type="faq",
        )
        db.add(entry)
        await db.flush()
        return entry
