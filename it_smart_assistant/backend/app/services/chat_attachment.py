"""Filesystem-backed chat attachment handling."""

from __future__ import annotations

import base64
import json
import mimetypes
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from pypdf import PdfReader

from app.core.exceptions import BadRequestError, NotFoundError
from app.schemas.chat_attachment import ChatAttachmentRead, PromptAttachment
from app.services.storage import get_storage_service

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHAT_ATTACHMENTS_DIR = PROJECT_ROOT / "uploads" / "chat_attachments"
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
MAX_EXTRACTED_TEXT_CHARS = 12_000
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json"}
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass
class StoredAttachment:
    id: str
    file_name: str
    media_type: str
    kind: str
    size_bytes: int
    storage_path: str
    extracted_text: str | None
    created_at: str


def ensure_chat_attachment_dir() -> None:
    """Ensure the filesystem storage for chat attachments exists."""
    CHAT_ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)


def _normalize_file_name(file_name: str) -> str:
    candidate = Path(file_name or "tep-dinh-kem").name
    return candidate or "tep-dinh-kem"


def _resolve_kind(file_name: str) -> str:
    extension = Path(file_name).suffix.lower()
    if extension in PDF_EXTENSIONS or extension in TEXT_EXTENSIONS:
        return "document"
    if extension in IMAGE_EXTENSIONS:
        return "image"
    raise BadRequestError(
        message="Unsupported file type. Supported formats: PDF, TXT, MD, CSV, JSON, PNG, JPG, JPEG, WEBP"
    )


def _resolve_media_type(file_name: str, content_type: str | None) -> str:
    if content_type:
        return content_type
    guessed_type, _ = mimetypes.guess_type(file_name)
    return guessed_type or "application/octet-stream"


def _truncate_text(value: str) -> str:
    normalized = value.strip()
    if len(normalized) <= MAX_EXTRACTED_TEXT_CHARS:
        return normalized
    return normalized[:MAX_EXTRACTED_TEXT_CHARS].strip()


def _extract_document_text(file_name: str, content: bytes) -> str | None:
    extension = Path(file_name).suffix.lower()

    if extension in TEXT_EXTENSIONS:
        return _truncate_text(content.decode("utf-8", errors="ignore"))

    if extension in PDF_EXTENSIONS:
        reader = PdfReader(BytesIO(content))
        pages: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(page_text)

        if not pages:
            return None
        return _truncate_text("\n\n".join(pages))

    return None


def _metadata_path(attachment_id: str) -> Path:
    return CHAT_ATTACHMENTS_DIR / f"{attachment_id}.json"


def _load_stored_attachment(attachment_id: str) -> StoredAttachment:
    metadata_path = _metadata_path(attachment_id)
    if not metadata_path.exists():
        raise NotFoundError(message="Attachment not found")

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    return StoredAttachment(**payload)


async def save_chat_attachment(upload: UploadFile) -> ChatAttachmentRead:
    """Persist an uploaded chat attachment and extract prompt-friendly content."""
    ensure_chat_attachment_dir()

    file_name = _normalize_file_name(upload.filename or "")
    content = await upload.read()

    if not content:
        raise BadRequestError(message="Uploaded file is empty")

    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise BadRequestError(message="Uploaded file exceeds 10 MB limit")

    kind = _resolve_kind(file_name)
    media_type = _resolve_media_type(file_name, upload.content_type)
    attachment_id = uuid4().hex
    created_at = datetime.now(UTC)
    storage_key = f"chat-attachments/{attachment_id}/{file_name}"
    storage_service = get_storage_service()
    stored_object = storage_service.upload_bytes(
        storage_key,
        content,
        content_type=media_type,
    )

    extracted_text = _extract_document_text(file_name, content) if kind == "document" else None

    stored_attachment = StoredAttachment(
        id=attachment_id,
        file_name=file_name,
        media_type=media_type,
        kind=kind,
        size_bytes=len(content),
        storage_path=stored_object.key,
        extracted_text=extracted_text,
        created_at=created_at.isoformat(),
    )
    _metadata_path(attachment_id).write_text(
        json.dumps(asdict(stored_attachment), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return ChatAttachmentRead(
        id=attachment_id,
        file_name=file_name,
        media_type=media_type,
        kind=kind,
        size_bytes=len(content),
        created_at=created_at,
    )


def load_prompt_attachments(attachment_ids: list[str]) -> list[PromptAttachment]:
    """Load persisted attachments into prompt-ready payloads for the current chat turn."""
    attachments: list[PromptAttachment] = []
    storage_service = get_storage_service()

    for attachment_id in attachment_ids:
        stored = _load_stored_attachment(attachment_id)
        data_url: str | None = None

        if stored.kind == "image":
            payload_bytes = storage_service.download_bytes(stored.storage_path)
            encoded = base64.b64encode(payload_bytes).decode("ascii")
            data_url = f"data:{stored.media_type};base64,{encoded}"

        attachments.append(
            PromptAttachment(
                id=stored.id,
                file_name=stored.file_name,
                media_type=stored.media_type,
                kind=stored.kind,  # type: ignore[arg-type]
                extracted_text=stored.extracted_text,
                data_url=data_url,
            )
        )

    return attachments


def build_attachment_history_note(attachment_ids: list[str]) -> str | None:
    """Build a compact note to persist attachment context inside conversation history."""
    attachments = load_prompt_attachments(attachment_ids)
    if not attachments:
        return None

    lines: list[str] = ["[Tep dinh kem]"]
    for attachment in attachments:
        if attachment.kind == "document" and attachment.extracted_text:
            lines.append(f"- {attachment.file_name}: {attachment.extracted_text[:1000]}")
        else:
            lines.append(f"- {attachment.file_name}")

    return "\n".join(lines)
