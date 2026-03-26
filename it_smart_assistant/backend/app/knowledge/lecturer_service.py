"""Lecturer knowledge base service for static and generated retrieval data."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from app.core.config import settings
from app.core.paths import resolve_project_root
from app.services.knowledge_embedding import embed_query_sync, embeddings_enabled

PROJECT_ROOT = resolve_project_root(Path(__file__))
LECTURER_DOCUMENTS_DIR = PROJECT_ROOT / "knowledge_lecturer"
TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+", re.UNICODE)
logger = logging.getLogger(__name__)
ROMAN_NUMERAL_TOKENS = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}
STOPWORDS = {
    "a",
    "an",
    "and",
    "bao",
    "cac",
    "can",
    "cho",
    "co",
    "cua",
    "da",
    "de",
    "den",
    "duoc",
    "hoc",
    "la",
    "lam",
    "mot",
    "nam",
    "nhung",
    "noi",
    "o",
    "quy",
    "se",
    "sinh",
    "tai",
    "the",
    "theo",
    "thu",
    "trong",
    "tu",
    "va",
    "ve",
    "vien",
    "voi",
}


@dataclass(frozen=True)
class KnowledgeDocument:
    """A single knowledge document used by the advisor assistant."""

    id: str
    title: str
    category: str
    summary: str
    content: str
    source_url: str
    keywords: list[str]
    source_kind: str = "document"
    source_document_id: str | None = None
    section_title: str | None = None
    page_from: int | None = None
    page_to: int | None = None
    source_path: str | None = None
    entry_metadata: dict[str, Any] | None = None


def _strip_accents(text: str | None) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def _normalize_text(text: str | None) -> str:
    if not text:
        return ""
    return _strip_accents(text).lower().strip()


def _tokenize(text: str | None) -> list[str]:
    if not text:
        return []
    return [
        token
        for token in TOKEN_PATTERN.findall(_normalize_text(text))
        if (len(token) > 1 or token in ROMAN_NUMERAL_TOKENS) and token not in STOPWORDS
    ]


class LecturerKnowledgeBase:
    """Simple lexical retrieval over a local static knowledge set for lecturers."""

    def __init__(self, documents: list[KnowledgeDocument], *, database_backed: bool = False) -> None:
        self.documents = documents
        self.database_backed = database_backed

    @classmethod
    def from_sources(
        cls,
        lecturer_documents_dir: Path = LECTURER_DOCUMENTS_DIR,
    ) -> "LecturerKnowledgeBase":
        documents: list[KnowledgeDocument] = []

        if lecturer_documents_dir.exists():
            for path in sorted(lecturer_documents_dir.glob("*.json")):
                raw = json.loads(path.read_text(encoding="utf-8"))
                documents.append(
                    KnowledgeDocument(
                        id=raw.get("id", ""),
                        title=raw.get("title", ""),
                        category=raw.get("category", "lecturer"),
                        summary=raw.get("summary", ""),
                        content=raw.get("content", ""),
                        source_url=raw.get("source_url", ""),
                        keywords=raw.get("keywords", []),
                        source_kind=raw.get("source_kind", "document"),
                    )
                )

        return cls(documents)

    @classmethod
    def from_database(cls) -> "LecturerKnowledgeBase":
        """Load knowledge entries from the PostgreSQL snapshot if available."""
        engine = create_engine(settings.DATABASE_URL_SYNC, future=True)
        documents: list[KnowledgeDocument] = []

        try:
            with engine.connect() as connection:
                table_exists = connection.execute(
                    text("SELECT to_regclass('public.knowledge_entries') IS NOT NULL")
                ).scalar()
                if not table_exists:
                    return cls([])

                rows = connection.execute(
                    text(
                        """
                        SELECT
                            ke.external_id,
                            kd.external_id AS source_document_id,
                            ke.source_kind,
                            ke.title,
                            ke.category,
                            ke.summary,
                            ke.content,
                            ke.keywords,
                            ke.source_url,
                            ke.source_path,
                            ke.section_title,
                            ke.page_from,
                            ke.page_to,
                            ke.entry_metadata
                        FROM knowledge_entries ke
                        LEFT JOIN knowledge_documents kd ON kd.id = ke.document_id
                        WHERE ke.category LIKE '%lecturer%' OR ke.category LIKE '%giang_vien%'
                        ORDER BY ke.created_at ASC
                        """
                    )
                ).mappings()

                for row in rows:
                    documents.append(
                        KnowledgeDocument(
                            id=row["external_id"],
                            source_document_id=row["source_document_id"],
                            source_kind=row["source_kind"],
                            title=row["title"] or "",
                            category=row["category"] or "",
                            summary=row["summary"] or "",
                            content=row["content"] or "",
                            source_url=row["source_url"] or "",
                            source_path=row["source_path"] or "",
                            section_title=row["section_title"] or "",
                            page_from=row["page_from"],
                            page_to=row["page_to"],
                            keywords=row["keywords"] or [],
                            entry_metadata=row.get("entry_metadata") or {},
                        )
                    )
        except Exception as exc:
            logger.warning("Falling back to filesystem knowledge sources for lecturers: %s", exc)
            return cls.from_sources()
        finally:
            engine.dispose()

        return cls(documents, database_backed=True)

    def _score_document(
        self,
        query: str,
        query_tokens: set[str],
        query_token_sequence: list[str],
        document: KnowledgeDocument,
    ) -> int:
        title_text = _normalize_text(document.title)
        category_text = _normalize_text(document.category)
        summary_text = _normalize_text(document.summary)
        content_text = _normalize_text(document.content)
        keyword_text = " ".join(_normalize_text(keyword) for keyword in document.keywords if keyword)

        score = 0

        if query and query in title_text:
            score += 12
        if query and query in keyword_text:
            score += 10
        if query and query in summary_text:
            score += 8
        if query and query in content_text:
            score += 5

        title_token_list = _tokenize(document.title)
        category_token_list = _tokenize(document.category)
        summary_token_list = _tokenize(document.summary)
        keyword_token_list = _tokenize(" ".join(k for k in document.keywords if k))
        content_token_list = _tokenize(document.content)

        title_tokens = set(title_token_list)
        category_tokens = set(category_token_list)
        summary_tokens = set(summary_token_list)
        keyword_tokens = set(keyword_token_list)
        content_tokens = set(content_token_list)
        combined_tokens = title_tokens | category_tokens | summary_tokens | keyword_tokens | content_tokens
        title_phrase_text = " ".join(title_token_list)
        summary_phrase_text = " ".join(summary_token_list)
        content_phrase_text = " ".join(content_token_list)

        query_phrases = {
            " ".join(query_token_sequence[index : index + length])
            for length in (2, 3)
            for index in range(0, max(0, len(query_token_sequence) - length + 1))
        }

        for token in query_tokens:
            if token in title_tokens:
                score += 5
            if token in category_tokens:
                score += 4
            if token in keyword_tokens:
                score += 4
            if token in summary_tokens:
                score += 3
            if token in content_tokens:
                score += 1

        matched_token_count = sum(1 for token in query_tokens if token in combined_tokens)
        score += matched_token_count**3

        for phrase in query_phrases:
            if phrase in title_phrase_text:
                score += 9
            if phrase in summary_phrase_text:
                score += 6
            if phrase in content_phrase_text:
                score += 4

        return score

    def _build_excerpt(self, query_tokens: set[str], document: KnowledgeDocument) -> str:
        if not document.content:
            return document.summary or ""

        sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", document.content) if sentence.strip()]

        for sentence in sentences:
            normalized = _normalize_text(sentence)
            if any(token in normalized for token in query_tokens):
                return sentence

        return document.summary or ""

    def _semantic_scores(self, query: str, *, candidate_limit: int) -> dict[str, float]:
        """Fetch semantic similarity scores from PostgreSQL pgvector when available."""
        if not self.database_backed or not embeddings_enabled():
            return {}

        try:
            embedding = embed_query_sync(query)
        except Exception as exc:
            logger.warning("Semantic query embedding failed, using lexical fallback only: %s", exc)
            return {}

        if not embedding:
            return {}

        engine = create_engine(settings.DATABASE_URL_SYNC, future=True)
        try:
            with engine.connect() as connection:
                rows = connection.execute(
                    text(
                        """
                        SELECT
                            external_id,
                            1 - (embedding <=> CAST(:query_embedding AS vector)) AS similarity
                        FROM knowledge_entries
                        WHERE (embedding IS NOT NULL)
                          AND (category LIKE '%lecturer%' OR category LIKE '%giang_vien%')
                        ORDER BY embedding <=> CAST(:query_embedding AS vector)
                        LIMIT :candidate_limit
                        """
                    ),
                    {
                        "query_embedding": "[" + ",".join(f"{value:.9f}" for value in embedding) + "]",
                        "candidate_limit": candidate_limit,
                    },
                ).mappings()

                scores: dict[str, float] = {}
                for row in rows:
                    similarity = float(row["similarity"] or 0.0)
                    scores[row["external_id"]] = max(similarity, 0.0)
                return scores
        except Exception as exc:
            logger.warning("Semantic pgvector lookup failed, using lexical fallback only: %s", exc)
            return {}
        finally:
            engine.dispose()

    def search(self, query: str, *, top_k: int = 3) -> list[dict[str, Any]]:
        """Search the knowledge base and return ranked results."""
        normalized_query = _normalize_text(query)
        query_token_sequence = _tokenize(query)
        query_tokens = set(query_token_sequence)
        semantic_scores = self._semantic_scores(
            query,
            candidate_limit=max(settings.VECTOR_SEARCH_CANDIDATES, top_k * 4),
        )
        scored_results: list[tuple[int, KnowledgeDocument]] = []

        for document in self.documents:
            lexical_score = self._score_document(
                normalized_query,
                query_tokens,
                query_token_sequence,
                document,
            )
            semantic_score = semantic_scores.get(document.id, 0.0)
            combined_score = (
                lexical_score * settings.HYBRID_LEXICAL_WEIGHT
                + semantic_score * settings.HYBRID_VECTOR_WEIGHT
            )
            if combined_score > 0:
                scored_results.append((int(round(combined_score)), document))

        scored_results.sort(key=lambda item: item[0], reverse=True)

        results: list[dict[str, Any]] = []
        for score, document in scored_results[:top_k]:
            results.append(
                {
                    "source_id": document.id,
                    "source_document_id": document.source_document_id,
                    "source_kind": document.source_kind,
                    "title": document.title,
                    "category": document.category,
                    "summary": document.summary,
                    "excerpt": self._build_excerpt(query_tokens, document),
                    "source_url": document.source_url,
                    "source_path": document.source_path,
                    "section_title": document.section_title,
                    "page_from": document.page_from,
                    "page_to": document.page_to,
                    "keywords": document.keywords,
                    "entry_metadata": document.entry_metadata or {},
                    "score": score,
                }
            )

        return results


@lru_cache(maxsize=1)
def get_lecturer_knowledge_base() -> LecturerKnowledgeBase:
    """Get the cached default lecturer knowledge base instance."""
    database_knowledge = LecturerKnowledgeBase.from_database()
    if database_knowledge.documents:
        return database_knowledge
    return LecturerKnowledgeBase.from_sources()


def reset_lecturer_knowledge_base_cache() -> None:
    """Clear the cached lecturer knowledge base so new syncs are visible immediately."""
    get_lecturer_knowledge_base.cache_clear()
