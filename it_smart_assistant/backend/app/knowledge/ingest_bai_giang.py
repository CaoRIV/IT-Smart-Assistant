"""Ingest pipeline for bài giảng (lecture materials).

Bước 1: PDF bài giảng → chunk text → embedding → lưu vào PostgreSQL/pgvector.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import settings
from app.core.paths import resolve_project_root
from app.knowledge.bai_giang_schema import BaiGiangChunk, BaiGiangMetadata, SubjectType

logger = logging.getLogger(__name__)

PROJECT_ROOT = resolve_project_root(Path(__file__))
DEFAULT_RAW_DIR = PROJECT_ROOT / "knowledge_raw" / "bai_giang"
DEFAULT_PROCESSED_DIR = PROJECT_ROOT / "knowledge_processed" / "bai_giang"

# Use embedding model from settings
GOOGLE_EMBEDDING_DIMENSIONS = settings.EMBEDDING_DIMENSIONS

import asyncio
from sentence_transformers import SentenceTransformer

# Lazy-loaded local embedding model
_local_model: SentenceTransformer | None = None

def _get_local_model() -> SentenceTransformer:
    """Get or load local sentence transformer model."""
    global _local_model
    if _local_model is None:
        logger.info("Loading local embedding model (sentence-transformers)...")
        _local_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        logger.info("Local embedding model loaded successfully")
    return _local_model


async def _embed_with_local(texts: list[str]) -> list[list[float]]:
    """Generate embeddings using local model."""
    model = _get_local_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings.tolist()


async def _embed_texts_batch(texts: list[str], batch_size: int = 10) -> list[list[float]]:
    """Generate embeddings using Google API with fallback to local model."""
    if not settings.GOOGLE_API_KEY:
        logger.warning("No GOOGLE_API_KEY, using local embeddings...")
        return await _embed_with_local(texts)

    client = GoogleGenerativeAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        output_dimensionality=GOOGLE_EMBEDDING_DIMENSIONS,
    )

    all_embeddings = []
    max_retries = 3
    use_local = False

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]

        if use_local:
            # Switch to local embeddings
            local_embs = await _embed_with_local(batch)
            all_embeddings.extend(local_embs)
            continue

        for attempt in range(max_retries):
            try:
                if i > 0:
                    await asyncio.sleep(1.0)

                embeddings = client.embed_documents(batch)
                all_embeddings.extend(embeddings)
                logger.info(f"Embedded batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
                break

            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limited, waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.warning("Google API quota exceeded, switching to local embeddings...")
                        use_local = True
                        break
                else:
                    raise

    return all_embeddings

# Chunking parameters for lecture materials
TARGET_CHUNK_LENGTH = 1500
MAX_CHUNK_LENGTH = 2000
MIN_CHUNK_LENGTH = 300
OVERLAP_SIZE = 200


@dataclass(frozen=True)
class IngestResult:
    """Summary returned after ingesting lecture materials."""

    raw_dir: Path
    processed_dir: Path
    document_count: int
    chunk_count: int
    chunks: list[BaiGiangChunk]


def slugify(value: str) -> str:
    """Convert a title into an ASCII-safe identifier."""
    import unicodedata

    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    collapsed = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value.lower()).strip("-")
    return collapsed or "document"


def normalize_whitespace(text: str) -> str:
    """Collapse repeated whitespace while keeping paragraph breaks."""
    text = text.replace("\u00a0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text from a PDF file."""
    reader = PdfReader(str(pdf_path))
    pages_text = []

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text:
            pages_text.append(f"--- Page {page_num} ---\n{normalize_whitespace(text)}")

    return "\n\n".join(pages_text)


def detect_subject_from_filename(filename: str) -> SubjectType:
    """Detect subject type from filename patterns."""
    name_lower = filename.lower()

    subject_patterns = {
        SubjectType.TOAN: ["toan", "math", "calculus", "algebra", "giai tich", "dai so"],
        SubjectType.VAT_LY: ["vat ly", "physics", "co hoc", "dien", "quang"],
        SubjectType.HOA_HOC: ["hoa", "chemistry", "chem"],
        SubjectType.LAP_TRINH: ["lap trinh", "programming", "code", "python", "java", "c++", "javascript"],
        SubjectType.CSDL: ["csdl", "database", "sql", "dbms"],
        SubjectType.MANG: ["mang", "network", "networking", "tcp/ip"],
        SubjectType.AI: ["ai", "artificial intelligence", "machine learning", "ml", "deep learning"],
        SubjectType.WEB: ["web", "html", "css", "frontend", "backend"],
    }

    for subject, patterns in subject_patterns.items():
        if any(pattern in name_lower for pattern in patterns):
            return subject

    return SubjectType.KHAC


def infer_chapter_from_text(text: str) -> str:
    """Infer chapter name from text content."""
    # Look for chapter patterns
    chapter_patterns = [
        r"Chương\s+(\d+|[IVX]+)[.:\s]*([^\n]{3,80})",
        r"Chuong\s+(\d+|[IVX]+)[.:\s]*([^\n]{3,80})",
        r"Chapter\s+(\d+|[IVX]+)[.:\s]*([^\n]{3,80})",
        r"Phần\s+(\d+|[IVX]+)[.:\s]*([^\n]{3,80})",
        r"Phan\s+(\d+|[IVX]+)[.:\s]*([^\n]{3,80})",
        r"Part\s+(\d+|[IVX]+)[.:\s]*([^\n]{3,80})",
        r"Mục\s+(\d+[.\d]*)[.:\s]*([^\n]{3,80})",
        r"Muc\s+(\d+[.\d]*)[.:\s]*([^\n]{3,80})",
    ]

    for pattern in chapter_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(2).strip()[:80]

    return ""


def detect_style_hint(text: str) -> str:
    """Detect teaching style hint from content patterns."""
    text_lower = text.lower()

    # Check for definition patterns
    has_definition = any(kw in text_lower for kw in ["định nghĩa", "dinh nghia", "definition", "là gì", "la gi"])

    # Check for example patterns
    has_example = any(kw in text_lower for kw in ["ví dụ", "vi du", "example", "vd:", "eg:", "e.g."])

    # Check for exercise patterns
    has_exercise = any(kw in text_lower for kw in ["bài tập", "bai tap", "exercise", "problem", "câu hỏi", "cau hoi"])

    # Check for proof/theory patterns
    has_proof = any(kw in text_lower for kw in ["chứng minh", "chung minh", "proof", "định lý", "dinh ly", "theorem"])

    # Build style hint
    styles = []
    if has_definition:
        styles.append("định nghĩa")
    if has_example:
        styles.append("ví dụ")
    if has_exercise:
        styles.append("bài tập")
    if has_proof:
        styles.append("lý thuyết/chứng minh")

    if styles:
        return " → ".join(styles)

    return "lý thuyết"


def split_into_chunks(text: str, chunk_id_prefix: str, metadata: BaiGiangMetadata) -> list[BaiGiangChunk]:
    """Split text into overlapping chunks with metadata."""
    chunks: list[BaiGiangChunk] = []

    # Split by paragraphs first
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    current_chunk_texts: list[str] = []
    current_chunk_length = 0
    chunk_index = 0

    for i, para in enumerate(paragraphs):
        para_length = len(para)

        # If paragraph itself is too long, split it by sentences
        if para_length > MAX_CHUNK_LENGTH:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            for sentence in sentences:
                if current_chunk_length + len(sentence) > MAX_CHUNK_LENGTH and current_chunk_texts:
                    # Save current chunk
                    chunk_text = "\n\n".join(current_chunk_texts)
                    chunks.append(
                        BaiGiangChunk(
                            chunk_id=f"{chunk_id_prefix}-{chunk_index:04d}",
                            content=chunk_text,
                            metadata=BaiGiangMetadata(
                                subject=metadata.subject,
                                chapter=metadata.chapter or infer_chapter_from_text(chunk_text),
                                style_hint=detect_style_hint(chunk_text),
                            ),
                        )
                    )
                    # Start new chunk with overlap
                    overlap_text = current_chunk_texts[-1] if len(current_chunk_texts) > 0 else ""
                    current_chunk_texts = [overlap_text[-OVERLAP_SIZE:] if len(overlap_text) > OVERLAP_SIZE else overlap_text, sentence]
                    current_chunk_length = sum(len(t) for t in current_chunk_texts)
                    chunk_index += 1
                else:
                    current_chunk_texts.append(sentence)
                    current_chunk_length += len(sentence)
        else:
            if current_chunk_length + para_length > MAX_CHUNK_LENGTH and current_chunk_texts:
                # Save current chunk
                chunk_text = "\n\n".join(current_chunk_texts)
                chunks.append(
                    BaiGiangChunk(
                        chunk_id=f"{chunk_id_prefix}-{chunk_index:04d}",
                        content=chunk_text,
                        metadata=BaiGiangMetadata(
                            subject=metadata.subject,
                            chapter=metadata.chapter or infer_chapter_from_text(chunk_text),
                            style_hint=detect_style_hint(chunk_text),
                        ),
                    )
                )
                # Start new chunk with overlap
                overlap_text = current_chunk_texts[-1] if len(current_chunk_texts) > 0 else ""
                current_chunk_texts = [overlap_text[-OVERLAP_SIZE:] if len(overlap_text) > OVERLAP_SIZE else overlap_text, para]
                current_chunk_length = sum(len(t) for t in current_chunk_texts)
                chunk_index += 1
            else:
                current_chunk_texts.append(para)
                current_chunk_length += para_length

    # Don't forget the last chunk
    if current_chunk_texts:
        chunk_text = "\n\n".join(current_chunk_texts)
        chunks.append(
            BaiGiangChunk(
                chunk_id=f"{chunk_id_prefix}-{chunk_index:04d}",
                content=chunk_text,
                metadata=BaiGiangMetadata(
                    subject=metadata.subject,
                    chapter=metadata.chapter or infer_chapter_from_text(chunk_text),
                    style_hint=detect_style_hint(chunk_text),
                ),
            )
        )

    return chunks


async def generate_embeddings_for_chunks(chunks: list[BaiGiangChunk]) -> list[BaiGiangChunk]:
    """Generate embeddings for chunks using Google Gemini API v1."""
    if not chunks:
        return []

    # Build embedding texts
    texts_to_embed = []
    for chunk in chunks:
        # Combine metadata with content for better semantic search
        meta = chunk.metadata
        text = (
            f"Môn học: {meta.subject.value}\n"
            f"Chương: {meta.chapter}\n"
            f"Phong cách: {meta.style_hint}\n\n"
            f"Nội dung: {chunk.content[:3000]}"
        )
        texts_to_embed.append(text)

    try:
        # Use Google API v1 directly
        embeddings = await _embed_texts_batch(texts_to_embed)

        # Attach embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding

        logger.info(f"Generated {len(embeddings)} embeddings using Google Gemini API v1")
        return chunks

    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        # Return chunks without embeddings
        return chunks


def save_chunks_to_json(chunks: list[BaiGiangChunk], output_dir: Path, document_id: str) -> Path:
    """Save chunks to JSON file for backup/reuse."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{document_id}.json"

    data = {
        "document_id": document_id,
        "chunk_count": len(chunks),
        "chunks": [chunk.to_dict() for chunk in chunks],
    }

    output_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Saved {len(chunks)} chunks to {output_file}")
    return output_file


def load_chunks_from_json(json_path: Path) -> list[BaiGiangChunk]:
    """Load chunks from JSON file."""
    if not json_path.exists():
        return []

    data = json.loads(json_path.read_text(encoding="utf-8"))
    chunks = [BaiGiangChunk.from_dict(chunk_data) for chunk_data in data.get("chunks", [])]
    return chunks


async def ingest_pdf_file(
    pdf_path: Path,
    subject: SubjectType | None = None,
    chapter: str | None = None,
    processed_dir: Path = DEFAULT_PROCESSED_DIR,
) -> list[BaiGiangChunk]:
    """Ingest a single PDF file and return chunks."""
    logger.info(f"Ingesting PDF: {pdf_path}")

    # Extract text
    text = extract_text_from_pdf(pdf_path)
    if not text.strip():
        logger.warning(f"No text extracted from {pdf_path}")
        return []

    # Detect subject if not provided
    if subject is None:
        subject = detect_subject_from_filename(pdf_path.name)

    # Build metadata
    metadata = BaiGiangMetadata(
        subject=subject,
        chapter=chapter or infer_chapter_from_text(text[:2000]),
        style_hint="",
    )

    # Generate document ID
    document_id = f"{slugify(pdf_path.stem)}-{uuid.uuid4().hex[:8]}"

    # Split into chunks
    chunks = split_into_chunks(text, document_id, metadata)
    logger.info(f"Created {len(chunks)} chunks from {pdf_path.name}")

    # Generate embeddings
    chunks = await generate_embeddings_for_chunks(chunks)

    # Save to JSON
    save_chunks_to_json(chunks, processed_dir, document_id)

    return chunks


async def ingest_bai_giang_directory(
    raw_dir: Path = DEFAULT_RAW_DIR,
    processed_dir: Path = DEFAULT_PROCESSED_DIR,
) -> IngestResult:
    """Ingest all PDF files in the raw directory."""
    logger.info(f"Ingesting lecture materials from {raw_dir}")

    if not raw_dir.exists():
        logger.warning(f"Raw directory does not exist: {raw_dir}")
        raw_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list(raw_dir.glob("**/*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files")

    all_chunks: list[BaiGiangChunk] = []

    for pdf_file in pdf_files:
        try:
            chunks = await ingest_pdf_file(pdf_file, processed_dir=processed_dir)
            all_chunks.extend(chunks)
        except Exception as e:
            logger.error(f"Failed to ingest {pdf_file}: {e}")

    result = IngestResult(
        raw_dir=raw_dir,
        processed_dir=processed_dir,
        document_count=len(pdf_files),
        chunk_count=len(all_chunks),
        chunks=all_chunks,
    )

    logger.info(f"Ingest complete: {result.document_count} documents, {result.chunk_count} chunks")
    return result


# CLI interface for manual ingestion
if __name__ == "__main__":
    import asyncio

    async def main():
        print(settings.GOOGLE_API_KEY)
        print(settings.EMBEDDING_MODEL)
        result = await ingest_bai_giang_directory()
        print(f"\nIngestion Complete!")
        print(f"  Documents: {result.document_count}")
        print(f"  Chunks: {result.chunk_count}")
        print(f"  Processed dir: {result.processed_dir}")

    asyncio.run(main())
