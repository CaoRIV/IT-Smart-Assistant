"""Lecture search tool for bài giảng (lecture materials).

Bước 3: Tool search_lecture(subject, query)
Nhận môn học + câu hỏi → semantic search → trả về đoạn bài giảng liên quan nhất.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import tool

from app.core.paths import resolve_project_root
from app.knowledge.bai_giang_schema import BaiGiangChunk, BaiGiangDocument, SubjectType, parse_subject
from app.services.knowledge_embedding import embed_query_sync, embeddings_enabled

logger = logging.getLogger(__name__)

# Load processed chunks from JSON files
from pathlib import Path

PROJECT_ROOT = resolve_project_root(Path(__file__))
BAI_GIANG_DIR = PROJECT_ROOT / "knowledge_processed" / "bai_giang"


def _load_all_chunks() -> list[BaiGiangChunk]:
    """Load all lecture chunks from processed files."""
    all_chunks: list[BaiGiangChunk] = []

    if not BAI_GIANG_DIR.exists():
        logger.warning(f"Bai giang directory does not exist: {BAI_GIANG_DIR}")
        return all_chunks

    for json_file in BAI_GIANG_DIR.glob("*.json"):
        try:
            import json

            data = json.loads(json_file.read_text(encoding="utf-8"))
            for chunk_data in data.get("chunks", []):
                chunk = BaiGiangChunk.from_dict(chunk_data)
                all_chunks.append(chunk)
        except Exception as e:
            logger.error(f"Failed to load chunks from {json_file}: {e}")

    return all_chunks


# Cache for loaded chunks
_chunks_cache: list[BaiGiangChunk] | None = None


def get_cached_chunks() -> list[BaiGiangChunk]:
    """Get cached chunks or load from disk."""
    global _chunks_cache
    if _chunks_cache is None:
        _chunks_cache = _load_all_chunks()
    return _chunks_cache


def clear_chunks_cache() -> None:
    """Clear the chunks cache to reload on next access."""
    global _chunks_cache
    _chunks_cache = None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    import math

    if len(a) != len(b):
        return 0.0

    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def _lexical_score(query: str, chunk: BaiGiangChunk) -> float:
    """Calculate lexical matching score."""
    query_lower = query.lower()
    content_lower = chunk.content.lower()
    meta = chunk.metadata

    score = 0.0

    # Subject match
    if meta.subject.value.lower() in query_lower:
        score += 10.0

    # Chapter match
    if meta.chapter and meta.chapter.lower() in query_lower:
        score += 8.0

    # Content keyword matching
    query_words = set(query_lower.split())
    content_words = set(content_lower.split())
    matching_words = query_words & content_words
    score += len(matching_words) * 2.0

    # Style hint matching
    if meta.style_hint:
        style_lower = meta.style_hint.lower()
        if any(kw in query_lower for kw in style_lower.split(" → ")):
            score += 5.0

    return score


def search_lecture_chunks(
    query: str,
    subject: SubjectType | None = None,
    top_k: int = 4,
    use_embeddings: bool = True,
) -> list[BaiGiangChunk]:
    """Search for relevant lecture chunks.

    Args:
        query: The search query
        subject: Optional subject filter
        top_k: Number of results to return
        use_embeddings: Whether to use vector similarity (requires embeddings)

    Returns:
        List of most relevant chunks
    """
    chunks = get_cached_chunks()
    if not chunks:
        logger.warning("No chunks available for search")
        return []

    # Filter by subject if specified
    if subject and subject != SubjectType.KHAC:
        chunks = [c for c in chunks if c.metadata.subject == subject]

    if not chunks:
        logger.warning(f"No chunks found for subject: {subject}")
        return []

    scored_chunks: list[tuple[float, BaiGiangChunk]] = []

    # Get query embedding if enabled
    query_embedding = None
    if use_embeddings and embeddings_enabled():
        query_embedding = embed_query_sync(query)

    for chunk in chunks:
        score = 0.0

        # Lexical score
        score += _lexical_score(query, chunk)

        # Vector similarity score
        if query_embedding and chunk.embedding:
            similarity = _cosine_similarity(query_embedding, chunk.embedding)
            score += similarity * 50.0  # Weight vector similarity higher

        scored_chunks.append((score, chunk))

    # Sort by score descending
    scored_chunks.sort(key=lambda x: x[0], reverse=True)

    # Return top_k results
    top_results = [chunk for _, chunk in scored_chunks[:top_k]]

    logger.info(
        f"Search query='{query[:50]}...' subject={subject} "
        f"found {len(top_results)} results from {len(chunks)} chunks"
    )

    return top_results


@tool
def search_lecture(
    query: str,
    subject: str | None = None,
    chapter: str | None = None,
    top_k: int = 4,
) -> str:
    """Search the lecture knowledge base for relevant content.

    Use this tool when the user asks about specific course content,
    asks to solve a problem based on lecture style, or needs help
    understanding concepts from their course materials.

    Args:
        query: The search query (exercise description or topic)
        subject: Optional subject name to filter results (e.g., "Toán", "Lập trình")
        chapter: Optional chapter name to filter results
        top_k: Number of relevant results to return (default 4)

    Returns:
        JSON string containing search results with chunk content and metadata.
    """
    # Parse subject
    subject_enum = None
    if subject:
        subject_enum = parse_subject(subject)

    # Get all chunks
    chunks = get_cached_chunks()
    
    if not chunks:
        return json.dumps(
            {
                "query": query,
                "subject": subject,
                "chapter": chapter,
                "result_count": 0,
                "max_score": 0.0,
                "results": [],
                "warning": "Không có dữ liệu bài giảng.",
            },
            ensure_ascii=False,
            indent=2,
        )

    # Filter by subject if specified
    if subject_enum:
        chunks = [c for c in chunks if c.metadata.subject == subject_enum]

    # Score chunks by similarity to query
    query_lower = query.lower()
    scored_chunks = []
    for chunk in chunks:
        score = 0.0
        content_lower = chunk.content.lower()
        
        # Query appears in content (high relevance)
        if query_lower in content_lower:
            score += 50.0
            # Exact phrase match bonus
            score += 20.0 * content_lower.count(query_lower)
        
        # Partial word matches
        query_words = [w for w in query_lower.split() if len(w) > 3]
        for word in query_words:
            if word in content_lower:
                score += 10.0
        
        # Style hint relevance
        if any(s in chunk.metadata.style_hint.lower() for s in ["định nghĩa", "ví dụ", "bài tập"]):
            score += 5.0
        
        # Prefer longer content for better context
        if len(chunk.content) > 200:
            score += 3.0
        
        scored_chunks.append((score, chunk))

    # Sort by score descending
    scored_chunks.sort(key=lambda x: x[0], reverse=True)

    # Filter by chapter if specified
    if chapter and scored_chunks:
        chapter_lower = chapter.lower()
        chapter_scored = [(s, c) for s, c in scored_chunks if chapter_lower in c.metadata.chapter.lower()]
        if chapter_scored:
            scored_chunks = chapter_scored

    # Build response payload with scores
    top_scored = scored_chunks[:top_k]
    
    payload: dict[str, Any] = {
        "query": query,
        "subject": subject,
        "chapter": chapter,
        "result_count": len(top_scored),
        "max_score": round(top_scored[0][0], 3) if top_scored else 0.0,
        "results": [],
    }

    for i, (score, chunk) in enumerate(top_scored, 1):
        meta = chunk.metadata
        result_item = {
            "rank": i,
            "chunk_id": chunk.chunk_id,
            "content": chunk.content[:1500],  # Truncate for response
            "subject": meta.subject.value,
            "chapter": meta.chapter,
            "style_hint": meta.style_hint,
            "score": round(score, 3),  # Độ tương đồng (0-100+)
            "has_high_confidence": score >= 60.0,  # Ngưỡng tin cậy
        }
        payload["results"].append(result_item)

    return json.dumps(payload, ensure_ascii=False, indent=2)


@tool
def get_lecture_by_style(
    subject: str,
    style_hint: str,
    top_k: int = 3,
) -> str:
    """Find lecture content by teaching style.

    Use this when you need to find specific types of content like:
    - "định nghĩa" (definitions)
    - "ví dụ" (examples)
    - "bài tập" (exercises)
    - "lý thuyết" (theory)

    Args:
        subject: The subject name (e.g., "Toán", "Lập trình")
        style_hint: The style to search for (e.g., "ví dụ", "bài tập")
        top_k: Number of results to return

    Returns:
        JSON string with matching lecture chunks.
    """
    subject_enum = parse_subject(subject)
    chunks = get_cached_chunks()

    if not chunks:
        return json.dumps(
            {"error": "No lecture data available", "subject": subject, "style_hint": style_hint},
            ensure_ascii=False,
        )

    # Filter by subject and style
    style_lower = style_hint.lower()
    matching_chunks = [
        c for c in chunks
        if c.metadata.subject == subject_enum
        and (style_lower in c.metadata.style_hint.lower() or style_lower in c.content.lower())
    ]

    # Sort by relevance to style
    scored = []
    for chunk in matching_chunks:
        score = 0.0
        content_lower = chunk.content.lower()
        style_lower = style_hint.lower()

        # Direct style hint match
        if style_lower in chunk.metadata.style_hint.lower():
            score += 20.0

        # Content contains the style pattern
        if style_lower in content_lower:
            score += 10.0

        # Prefer longer content for examples/exercises
        if len(chunk.content) > 500:
            score += 5.0

        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_results = [chunk for _, chunk in scored[:top_k]]

    payload = {
        "subject": subject,
        "style_hint": style_hint,
        "result_count": len(top_results),
        "results": [
            {
                "chunk_id": c.chunk_id,
                "content": c.content[:1500],
                "chapter": c.metadata.chapter,
                "style_hint": c.metadata.style_hint,
            }
            for c in top_results
        ],
    }

    return json.dumps(payload, ensure_ascii=False, indent=2)


@tool
def list_available_subjects() -> str:
    """List all available subjects that have lecture materials.

    Returns:
        JSON string with list of subjects and their document counts.
    """
    chunks = get_cached_chunks()

    if not chunks:
        return json.dumps(
            {"subjects": [], "message": "No lecture materials available"},
            ensure_ascii=False,
        )

    # Count chunks per subject
    subject_counts: dict[str, int] = {}
    for chunk in chunks:
        subject_name = chunk.metadata.subject.value
        subject_counts[subject_name] = subject_counts.get(subject_name, 0) + 1

    # Build sorted list
    subjects = [
        {"name": name, "chunk_count": count}
        for name, count in sorted(subject_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    return json.dumps(
        {"subjects": subjects, "total_chunks": len(chunks)},
        ensure_ascii=False,
        indent=2,
    )


# For backward compatibility with existing code
search_lecture_tool = search_lecture
