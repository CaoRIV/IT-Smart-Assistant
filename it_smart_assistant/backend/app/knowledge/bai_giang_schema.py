"""Schema definitions for bài giảng (lecture materials).

Bước 2: Gắn metadata môn học cho từng chunk.
Mỗi đoạn text có: subject, chapter, style_hint (định nghĩa → ví dụ → bài tập).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SubjectType(Enum):
    """Danh sách các môn học được hỗ trợ."""

    TOAN = "Toán"
    VAT_LY = "Vật lý"
    HOA_HOC = "Hóa học"
    LAP_TRINH = "Lập trình"
    CSDL = "Cơ sở dữ liệu"
    MANG = "Mạng máy tính"
    AI = "Trí tuệ nhân tạo"
    WEB = "Phát triển Web"
    KHAC = "Khác"


# Mapping từ tên môn sang enum
SUBJECT_NAME_MAPPING: dict[str, SubjectType] = {
    "toan": SubjectType.TOAN,
    "math": SubjectType.TOAN,
    "calculus": SubjectType.TOAN,
    "algebra": SubjectType.TOAN,
    "giai tich": SubjectType.TOAN,
    "dai so": SubjectType.TOAN,
    "vat ly": SubjectType.VAT_LY,
    "physics": SubjectType.VAT_LY,
    "co hoc": SubjectType.VAT_LY,
    "hoa": SubjectType.HOA_HOC,
    "chemistry": SubjectType.HOA_HOC,
    "lap trinh": SubjectType.LAP_TRINH,
    "programming": SubjectType.LAP_TRINH,
    "code": SubjectType.LAP_TRINH,
    "python": SubjectType.LAP_TRINH,
    "java": SubjectType.LAP_TRINH,
    "c++": SubjectType.LAP_TRINH,
    "csdl": SubjectType.CSDL,
    "database": SubjectType.CSDL,
    "sql": SubjectType.CSDL,
    "dbms": SubjectType.CSDL,
    "mang": SubjectType.MANG,
    "network": SubjectType.MANG,
    "networking": SubjectType.MANG,
    "tcp/ip": SubjectType.MANG,
    "ai": SubjectType.AI,
    "artificial intelligence": SubjectType.AI,
    "machine learning": SubjectType.AI,
    "ml": SubjectType.AI,
    "deep learning": SubjectType.AI,
    "hoc may": SubjectType.AI,
    "web": SubjectType.WEB,
    "html": SubjectType.WEB,
    "css": SubjectType.WEB,
    "frontend": SubjectType.WEB,
    "backend": SubjectType.WEB,
}


def parse_subject(subject_name: str) -> SubjectType:
    """Parse subject name to SubjectType enum."""
    name_lower = subject_name.lower().strip()
    return SUBJECT_NAME_MAPPING.get(name_lower, SubjectType.KHAC)


def get_all_subjects() -> list[SubjectType]:
    """Get list of all available subjects."""
    return list(SubjectType)


def get_subject_names() -> list[str]:
    """Get list of all subject display names."""
    return [s.value for s in SubjectType]


@dataclass
class BaiGiangMetadata:
    """Metadata cho mỗi chunk của bài giảng.

    Attributes:
        subject: Môn học (Toán, Vật lý, Lập trình, ...)
        chapter: Tên chương/bài học
        style_hint: Phong cách trình bày (định nghĩa → ví dụ → bài tập)
    """

    subject: SubjectType = SubjectType.KHAC
    chapter: str = ""
    style_hint: str = ""  # e.g., "định nghĩa → ví dụ → bài tập"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "subject": self.subject.value,
            "chapter": self.chapter,
            "style_hint": self.style_hint,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaiGiangMetadata":
        """Create from dictionary."""
        subject = data.get("subject", "Khác")
        if isinstance(subject, str):
            subject = parse_subject(subject)
        elif isinstance(subject, SubjectType):
            pass
        else:
            subject = SubjectType.KHAC

        return cls(
            subject=subject,
            chapter=data.get("chapter", ""),
            style_hint=data.get("style_hint", ""),
        )


@dataclass
class BaiGiangChunk:
    """A single chunk of lecture material with metadata and optional embedding.

    Attributes:
        chunk_id: Unique identifier for this chunk
        content: Text content of the chunk
        metadata: Subject/chapter/style metadata
        embedding: Vector embedding (optional, populated after generation)
    """

    chunk_id: str
    content: str
    metadata: BaiGiangMetadata = field(default_factory=BaiGiangMetadata)
    embedding: list[float] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "metadata": self.metadata.to_dict(),
            "embedding": self.embedding,  # Will be serialized as list
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaiGiangChunk":
        """Create from dictionary."""
        return cls(
            chunk_id=data.get("chunk_id", ""),
            content=data.get("content", ""),
            metadata=BaiGiangMetadata.from_dict(data.get("metadata", {})),
            embedding=data.get("embedding"),
        )

    def get_embedding_text(self) -> str:
        """Build text for embedding generation."""
        meta = self.metadata
        return (
            f"Môn học: {meta.subject.value}\n"
            f"Chương: {meta.chapter}\n"
            f"Phong cách: {meta.style_hint}\n\n"
            f"Nội dung: {self.content[:3000]}"
        )

    def get_display_info(self) -> str:
        """Get human-readable display info."""
        return f"[{self.metadata.subject.value}] {self.metadata.chapter} - {self.metadata.style_hint}"


@dataclass
class BaiGiangDocument:
    """A complete lecture document containing multiple chunks.

    Attributes:
        document_id: Unique identifier for this document
        file_name: Original PDF file name
        title: Document title
        subject: Primary subject
        chunks: List of content chunks
    """

    document_id: str
    file_name: str
    title: str
    subject: SubjectType
    chunks: list[BaiGiangChunk] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "document_id": self.document_id,
            "file_name": self.file_name,
            "title": self.title,
            "subject": self.subject.value,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaiGiangDocument":
        """Create from dictionary."""
        subject = data.get("subject", "Khác")
        if isinstance(subject, str):
            subject = parse_subject(subject)

        return cls(
            document_id=data.get("document_id", ""),
            file_name=data.get("file_name", ""),
            title=data.get("title", ""),
            subject=subject,
            chunks=[BaiGiangChunk.from_dict(c) for c in data.get("chunks", [])],
        )

    @property
    def chunk_count(self) -> int:
        """Get total number of chunks."""
        return len(self.chunks)

    def get_all_embeddings(self) -> list[list[float]]:
        """Get all chunk embeddings."""
        return [chunk.embedding for chunk in self.chunks if chunk.embedding is not None]
