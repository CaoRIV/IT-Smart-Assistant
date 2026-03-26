"""Student knowledge base service for static and generated retrieval data."""

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

STATIC_DOCUMENTS_DIR = Path(__file__).parent / "documents"
PROJECT_ROOT = resolve_project_root(Path(__file__))
GENERATED_CHUNKS_DIR = PROJECT_ROOT / "knowledge_processed" / "chunks"
GENERATED_TABLES_DIR = PROJECT_ROOT / "knowledge_processed" / "tables"
ADMIN_FAQS_DIR = PROJECT_ROOT / "knowledge_admin" / "faqs"
ADMIN_FORMS_DIR = PROJECT_ROOT / "knowledge_admin" / "forms"
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


@dataclass(frozen=True)
class RetrievalProfile:
    """Lightweight intent/profile extracted from the user's query."""

    tuition_query: bool = False
    per_credit_query: bool = False
    explicit_tracks: frozenset[str] = frozenset()
    default_track: str | None = None


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


def _contains_phrase(text: str | None, phrases: tuple[str, ...]) -> bool:
    if not text:
        return False
    return any(phrase in text for phrase in phrases)


class StudentKnowledgeBase:
    """Simple lexical retrieval over a local static knowledge set."""

    def __init__(self, documents: list[KnowledgeDocument], *, database_backed: bool = False) -> None:
        self.documents = documents
        self.database_backed = database_backed

    @classmethod
    def from_sources(
        cls,
        static_documents_dir: Path = STATIC_DOCUMENTS_DIR,
        generated_chunks_dir: Path = GENERATED_CHUNKS_DIR,
        generated_tables_dir: Path = GENERATED_TABLES_DIR,
        admin_faqs_dir: Path = ADMIN_FAQS_DIR,
        admin_forms_dir: Path = ADMIN_FORMS_DIR,
    ) -> "StudentKnowledgeBase":
        documents: list[KnowledgeDocument] = []

        for path in sorted(static_documents_dir.glob("*.json")):
            raw = json.loads(path.read_text(encoding="utf-8"))
            documents.append(
                KnowledgeDocument(
                    id=raw.get("id", ""),
                    title=raw.get("title", ""),
                    category=raw.get("category", ""),
                    summary=raw.get("summary", ""),
                    content=raw.get("content", ""),
                    source_url=raw.get("source_url", ""),
                    keywords=raw.get("keywords", []),
                )
            )

        if generated_chunks_dir.exists():
            for path in sorted(generated_chunks_dir.glob("*.json")):
                raw = json.loads(path.read_text(encoding="utf-8"))
                for chunk in raw.get("chunks", []):
                    documents.append(
                        KnowledgeDocument(
                            id=chunk.get("chunk_id", ""),
                            title=raw.get("title", ""),
                            category=raw.get("category", ""),
                            summary=chunk.get("summary", ""),
                            content=chunk.get("content", ""),
                            source_url=raw.get("source_url", ""),
                            keywords=chunk.get("keywords", raw.get("keywords", [])),
                            source_kind="chunk",
                            source_document_id=raw.get("document_id"),
                            section_title=chunk.get("section_title"),
                            page_from=chunk.get("page_from"),
                            page_to=chunk.get("page_to"),
                            source_path=raw.get("source_path"),
                            entry_metadata={"document_id": raw.get("document_id")},
                        )
                    )

        if generated_tables_dir.exists():
            for path in sorted(generated_tables_dir.glob("*.json")):
                raw = json.loads(path.read_text(encoding="utf-8"))
                for table in raw.get("tables", []):
                    for row in table.get("rows", []):
                        amount_text = row.get("amount_text", "")
                        amount_value = row.get("amount_value")
                        amount_value_text = f" ({amount_value} dong)" if amount_value else ""
                        content = (
                            f"{table.get('title', '')}. {row.get('label', '')}. "
                            f"Muc hoc phi: {amount_text}{amount_value_text}."
                        )
                        documents.append(
                            KnowledgeDocument(
                                id=f"{table.get('table_id', '')}-{row.get('row_id', '')}",
                                title=raw.get("title", ""),
                                category=raw.get("category", ""),
                                summary=content,
                                content=row.get("search_text") or content,
                                source_url=raw.get("source_url", ""),
                                keywords=[
                                    raw.get("category", ""),
                                    raw.get("title", ""),
                                    table.get("title", ""),
                                    row.get("label", ""),
                                    amount_text,
                                    *row.get("track_tags", []),
                                    *row.get("basis_tags", []),
                                ],
                                source_kind="table_row",
                                source_document_id=raw.get("document_id"),
                                section_title=table.get("title"),
                                page_from=row.get("page_from", table.get("page_from")),
                                page_to=row.get("page_to", table.get("page_to")),
                                source_path=raw.get("source_path"),
                                entry_metadata={
                                    "document_id": raw.get("document_id"),
                                    "amount_value": row.get("amount_value"),
                                    "track_tags": row.get("track_tags", []),
                                    "basis_tags": row.get("basis_tags", []),
                                    "raw_table_title": table.get("title"),
                                },
                            )
                        )

        if admin_faqs_dir.exists():
            for path in sorted(admin_faqs_dir.glob("*.json")):
                raw = json.loads(path.read_text(encoding="utf-8"))
                documents.append(
                    KnowledgeDocument(
                        id=raw.get("id", ""),
                        title=raw.get("title", ""),
                        category=raw.get("category", ""),
                        summary=raw.get("question", ""),
                        content=f"Cau hoi: {raw.get('question', '')}\n\nTra loi: {raw.get('answer', '')}",
                        source_url=raw.get("source_url", ""),
                        keywords=raw.get("keywords", []),
                        source_kind="faq",
                    )
                )

        if admin_forms_dir.exists():
            for path in sorted(admin_forms_dir.glob("*.json")):
                raw = json.loads(path.read_text(encoding="utf-8"))
                field_descriptions = [
                    f"{field.get('label', '')} ({field.get('name', '')}, {field.get('type', 'text')})"
                    for field in raw.get("fields", [])
                ]
                documents.append(
                    KnowledgeDocument(
                        id=raw.get("id", ""),
                        title=raw.get("title", ""),
                        category=raw.get("category", ""),
                        summary=raw.get("description", ""),
                        content=(
                            f"Bieu mau: {raw.get('title', '')}\n\n"
                            f"Mo ta: {raw.get('description', '')}\n\n"
                            f"Cac truong: {', '.join(field_descriptions) if field_descriptions else 'Khong co'}"
                        ),
                        source_url=raw.get("source_url", ""),
                        keywords=raw.get("keywords", []),
                        source_kind="form_template",
                    )
                )

        return cls(documents)

    @classmethod
    def from_database(cls) -> "StudentKnowledgeBase":
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
            logger.warning("Falling back to filesystem knowledge sources: %s", exc)
            return cls([])
        finally:
            engine.dispose()

        return cls(documents, database_backed=True)

    def _score_document(
        self,
        query: str,
        query_tokens: set[str],
        query_token_sequence: list[str],
        document: KnowledgeDocument,
        profile: RetrievalProfile,
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

        score += self._source_kind_bonus(query_tokens, document)
        score += self._profile_bonus(profile, document)

        return score

    def _build_profile(self, query: str, query_tokens: set[str]) -> RetrievalProfile:
        """Infer simple structured intent from the query."""
        normalized = _normalize_text(query)
        tuition_query = bool(
            {"hoc", "phi"} <= query_tokens
            or _contains_phrase(normalized, ("hoc phi", "muc thu", "tin chi", "hoc phi"))
        )
        per_credit_query = bool(
            "tin" in query_tokens
            or "chi" in query_tokens
            or _contains_phrase(normalized, ("tin chi", "1 tin chi", "theo tin chi"))
        )

        explicit_tracks: set[str] = set()
        if _contains_phrase(normalized, ("cao hoc", "thac si")):
            explicit_tracks.add("cao_hoc")
        if _contains_phrase(normalized, ("chinh quy", "he chinh quy", "dai hoc")):
            explicit_tracks.add("chinh_quy")
        if _contains_phrase(normalized, ("chat luong cao", "chata luong cao", "clc", "tien tien")):
            explicit_tracks.add("chat_luong_cao")
        if _contains_phrase(normalized, ("lien thong", "bang 2")):
            explicit_tracks.add("lien_thong")
        if _contains_phrase(normalized, ("vua lam vua hoc", "vua lam vira hoc", "vua lam")):
            explicit_tracks.add("vua_lam_vua_hoc")
        if _contains_phrase(normalized, ("giao duc the chat", "quoc phong", "the chat", "gdqp", "gdtc")):
            explicit_tracks.add("the_chat_quoc_phong")

        default_track = None
        if tuition_query and not explicit_tracks:
            default_track = "chinh_quy"

        return RetrievalProfile(
            tuition_query=tuition_query,
            per_credit_query=per_credit_query,
            explicit_tracks=frozenset(explicit_tracks),
            default_track=default_track,
        )

    def _document_track_tags(self, document: KnowledgeDocument) -> set[str]:
        """Infer tuition/program tags from the retrieved document text."""
        if document.entry_metadata and document.entry_metadata.get("track_tags"):
            return set(document.entry_metadata["track_tags"])

        text_blob = _normalize_text(
            " ".join(
                filter(
                    None,
                    [
                        document.title,
                        document.summary,
                        document.content,
                        document.section_title,
                        " ".join(k for k in document.keywords if k),
                    ],
                )
            )
        )
        tags: set[str] = set()

        if _contains_phrase(text_blob, ("cao hoc", "thac si")):
            tags.add("cao_hoc")
        if _contains_phrase(text_blob, ("chinh quy", "he chinh quy", "dai hoc")):
            tags.add("chinh_quy")
        if _contains_phrase(text_blob, ("chat luong cao", "chata luong cao", "clc", "tien tien")):
            tags.add("chat_luong_cao")
        if _contains_phrase(text_blob, ("lien thong", "bang 2")):
            tags.add("lien_thong")
        if _contains_phrase(text_blob, ("vua lam vua hoc", "vua lam vira hoc", "vua lam")):
            tags.add("vua_lam_vua_hoc")
        if _contains_phrase(text_blob, ("giao duc the chat", "quoc phong", "the chat", "gdqp", "gdtc")):
            tags.add("the_chat_quoc_phong")

        return tags

    def _document_basis_tags(self, document: KnowledgeDocument) -> set[str]:
        """Infer billing basis tags like per-credit or full-program."""
        if document.entry_metadata and document.entry_metadata.get("basis_tags"):
            return set(document.entry_metadata["basis_tags"])

        text_blob = _normalize_text(
            " ".join(
                filter(
                    None,
                    [
                        document.summary,
                        document.content,
                        document.section_title,
                        " ".join(k for k in document.keywords if k),
                    ],
                )
            )
        )
        tags: set[str] = set()
        if _contains_phrase(text_blob, ("1 tin chi", "theo tin chi", "tin chi")):
            tags.add("per_credit")
        return tags

    def _profile_bonus(self, profile: RetrievalProfile, document: KnowledgeDocument) -> int:
        """Apply business-specific ranking for tuition/program queries."""
        if not profile.tuition_query:
            return 0

        tags = self._document_track_tags(document)
        basis_tags = self._document_basis_tags(document)
        if not tags:
            tags = set()

        bonus = 0
        if document.source_kind == "table_row":
            bonus += 22
            if profile.per_credit_query and "per_credit" in basis_tags:
                bonus += 18
            if profile.per_credit_query and "full_program" in basis_tags:
                bonus -= 10
        elif document.source_kind == "chunk":
            bonus -= 10

        non_default_tracks = {"cao_hoc", "lien_thong", "vua_lam_vua_hoc", "chat_luong_cao"}
        if profile.explicit_tracks:
            if tags & profile.explicit_tracks:
                bonus += 24
                conflicting_tracks = (tags - profile.explicit_tracks) & non_default_tracks
                if conflicting_tracks:
                    bonus -= 6 * len(conflicting_tracks)
            elif document.source_kind == "table_row":
                bonus -= 18
        elif profile.default_track == "chinh_quy":
            conflicting_tracks = tags & non_default_tracks
            if "chinh_quy" in tags and not conflicting_tracks:
                bonus += 26
            elif "chinh_quy" in tags:
                bonus += 10
            if conflicting_tracks:
                bonus -= 14 * len(conflicting_tracks)

        return bonus

    def _document_allowed(self, profile: RetrievalProfile, document: KnowledgeDocument) -> bool:
        """Apply hard business filters before scoring."""
        if not profile.tuition_query or document.source_kind != "table_row":
            return True

        tags = self._document_track_tags(document)
        if not tags:
            return True

        non_default_tracks = {"cao_hoc", "lien_thong", "vua_lam_vua_hoc", "chat_luong_cao"}
        if profile.explicit_tracks:
            return bool(tags & profile.explicit_tracks)

        if profile.default_track == "chinh_quy" and tags & non_default_tracks:
            return False

        return True

    def _source_kind_bonus(self, query_tokens: set[str], document: KnowledgeDocument) -> int:
        """Prefer the right knowledge shape for the detected question type."""
        tuition_tokens = {
            "hoc",
            "phi",
            "muc",
            "thu",
            "khoi",
            "nganh",
            "tin",
            "chi",
            "dong",
            "bao",
            "nhieu",
        }
        form_tokens = {"don", "bieu", "mau", "mau", "lam", "dien", "tai"}
        faq_tokens = {"hoi", "dap", "faq", "huong", "dan"}
        course_tokens = {
            "mon",
            "hoc",
            "hocphan",
            "hocphan",
            "hoc",
            "phan",
            "ma",
            "tin",
            "chi",
            "tien",
            "quyet",
            "hoc",
            "ky",
            "cu",
            "nhan",
            "ky",
            "su",
        }

        if document.source_kind == "table_row" and query_tokens & tuition_tokens:
            return 28
        if document.source_kind == "course_record" and query_tokens & course_tokens:
            return 24
        if document.source_kind == "course_summary" and query_tokens & course_tokens:
            return 18
        if document.source_kind == "form_template" and query_tokens & form_tokens:
            return 14
        if document.source_kind == "faq" and query_tokens & faq_tokens:
            return 10
        if document.source_kind == "chunk":
            return 2
        return 0

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
                        WHERE embedding IS NOT NULL
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
        profile = self._build_profile(query, query_tokens)
        semantic_scores = self._semantic_scores(
            query,
            candidate_limit=max(settings.VECTOR_SEARCH_CANDIDATES, top_k * 4),
        )
        scored_results: list[tuple[int, KnowledgeDocument]] = []

        for document in self.documents:
            if not self._document_allowed(profile, document):
                continue
            lexical_score = self._score_document(
                normalized_query,
                query_tokens,
                query_token_sequence,
                document,
                profile,
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
def get_student_knowledge_base() -> StudentKnowledgeBase:
    """Get the cached default knowledge base instance."""
    database_knowledge = StudentKnowledgeBase.from_database()
    if database_knowledge.documents:
        return database_knowledge
    return StudentKnowledgeBase.from_sources()


def reset_student_knowledge_base_cache() -> None:
    """Clear the cached knowledge base so new syncs are visible immediately."""
    get_student_knowledge_base.cache_clear()
