"""Filesystem-backed storage helpers for knowledge admin MVP."""

from __future__ import annotations

import csv
import json
import mimetypes
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.paths import resolve_project_root
from app.knowledge.ingest import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RAW_DIR,
    SUPPORTED_DOCUMENT_EXTENSIONS,
    ingest_knowledge_base,
    slugify,
)
from app.knowledge.workbook_schema import detect_workbook_schema
from app.knowledge.service import get_student_knowledge_base
from app.schemas.knowledge_admin import (
    FAQCreate,
    FAQRead,
    FormFieldInput,
    FormTemplateCreate,
    FormTemplateRead,
    KnowledgeDocumentRead,
    KnowledgeDocumentBatchMetadataUpdate,
    KnowledgeDocumentMetadataUpdate,
    KnowledgeDocumentPreviewRead,
    KnowledgePreviewChunkRead,
    KnowledgePreviewTableRead,
    KnowledgePreviewTableRowRead,
)
from app.services.storage import get_storage_service


PROJECT_ROOT = resolve_project_root(Path(__file__))
KNOWLEDGE_ADMIN_DIR = PROJECT_ROOT / "knowledge_admin"
DOCUMENTS_DIR = KNOWLEDGE_ADMIN_DIR / "documents"
FAQS_DIR = KNOWLEDGE_ADMIN_DIR / "faqs"
FORMS_DIR = KNOWLEDGE_ADMIN_DIR / "forms"
VALID_DOCUMENT_STATUSES = {"draft", "published", "archived", "needs_review"}
DEPRECATED_FORM_IDS = {"hoc-vu-on-xin-bao-luu-hoc-tap"}


DEFAULT_FORM_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "hoc-vu-don-xin-bao-luu-hoc-tap",
        "title": "Đơn xin bảo lưu học tập",
        "category": "Học vụ",
        "description": "Biểu mẫu dành cho sinh viên xin tạm ngừng học trong một thời gian.",
        "keywords": ["bảo lưu", "tạm ngừng học", "đơn bảo lưu"],
        "fields": [
            {"name": "full_name", "label": "Họ và tên", "type": "text", "required": True, "placeholder": "Nhập họ và tên"},
            {"name": "student_id", "label": "Mã sinh viên", "type": "text", "required": True, "placeholder": "Nhập mã sinh viên"},
            {"name": "class_name", "label": "Lớp", "type": "text", "required": True, "placeholder": "Nhập lớp"},
            {"name": "faculty", "label": "Khoa", "type": "text", "required": True, "placeholder": "Nhập khoa"},
            {"name": "reason", "label": "Lý do bảo lưu", "type": "text", "required": True, "placeholder": "Nhập lý do"},
            {"name": "duration", "label": "Thời gian bảo lưu", "type": "text", "required": True, "placeholder": "Ví dụ: Học kỳ 1 năm học 2026-2027"},
        ],
    },
    {
        "id": "hanh-chinh-don-xin-xac-nhan-sinh-vien",
        "title": "Đơn xin xác nhận sinh viên",
        "category": "Hành chính",
        "description": "Biểu mẫu để sinh viên xin giấy xác nhận phục vụ các mục đích hành chính.",
        "keywords": ["xác nhận sinh viên", "giấy xác nhận", "vay vốn"],
        "fields": [
            {"name": "full_name", "label": "Họ và tên", "type": "text", "required": True, "placeholder": "Nhập họ và tên"},
            {"name": "student_id", "label": "Mã sinh viên", "type": "text", "required": True, "placeholder": "Nhập mã sinh viên"},
            {"name": "birth_date", "label": "Ngày sinh", "type": "text", "required": True, "placeholder": "dd/mm/yyyy"},
            {"name": "class_name", "label": "Lớp", "type": "text", "required": True, "placeholder": "Nhập lớp"},
            {"name": "purpose", "label": "Mục đích sử dụng", "type": "text", "required": True, "placeholder": "Ví dụ: vay vốn, bổ sung hồ sơ"},
        ],
    },
    {
        "id": "hoc-vu-don-xin-hoc-lai-cai-thien-diem",
        "title": "Đơn xin học lại/cải thiện điểm",
        "category": "Học vụ",
        "description": "Biểu mẫu để đăng ký học lại hoặc học cải thiện điểm cho học phần.",
        "keywords": ["học lại", "cải thiện điểm", "đăng ký học lại"],
        "fields": [
            {"name": "full_name", "label": "Họ và tên", "type": "text", "required": True, "placeholder": "Nhập họ và tên"},
            {"name": "student_id", "label": "Mã sinh viên", "type": "text", "required": True, "placeholder": "Nhập mã sinh viên"},
            {"name": "course_code", "label": "Mã học phần", "type": "text", "required": True, "placeholder": "Nhập mã học phần"},
            {"name": "course_name", "label": "Tên học phần", "type": "text", "required": True, "placeholder": "Nhập tên học phần"},
            {"name": "semester", "label": "Học kỳ đăng ký", "type": "text", "required": True, "placeholder": "Ví dụ: HK2 2026-2027"},
            {"name": "reason", "label": "Ghi chú", "type": "text", "required": False, "placeholder": "Thông tin bổ sung nếu có"},
        ],
    },
    {
        "id": "hoc-phi-don-xin-mien-giam-hoc-phi",
        "title": "Đơn xin miễn giảm học phí",
        "category": "Học phí",
        "description": "Biểu mẫu để đề nghị xem xét miễn giảm học phí theo đối tượng ưu tiên.",
        "keywords": ["miễn giảm học phí", "học phí", "hỗ trợ học phí"],
        "fields": [
            {"name": "full_name", "label": "Họ và tên", "type": "text", "required": True, "placeholder": "Nhập họ và tên"},
            {"name": "student_id", "label": "Mã sinh viên", "type": "text", "required": True, "placeholder": "Nhập mã sinh viên"},
            {"name": "policy_group", "label": "Đối tượng chính sách", "type": "text", "required": True, "placeholder": "Nhập đối tượng"},
            {"name": "support_level", "label": "Mức đề nghị", "type": "text", "required": True, "placeholder": "Ví dụ: miễn 100%, giảm 50%"},
            {"name": "support_reason", "label": "Căn cứ đề nghị", "type": "text", "required": True, "placeholder": "Nhập căn cứ đề nghị"},
        ],
    },
    {
        "id": "hanh-chinh-don-xin-cap-lai-the-sinh-vien",
        "title": "Đơn xin cấp lại thẻ sinh viên",
        "category": "Hành chính",
        "description": "Biểu mẫu để đề nghị cấp lại thẻ sinh viên khi mất, hỏng hoặc thay đổi thông tin.",
        "keywords": ["cấp lại thẻ", "thẻ sinh viên", "mất thẻ"],
        "fields": [
            {"name": "full_name", "label": "Họ và tên", "type": "text", "required": True, "placeholder": "Nhập họ và tên"},
            {"name": "student_id", "label": "Mã sinh viên", "type": "text", "required": True, "placeholder": "Nhập mã sinh viên"},
            {"name": "reason", "label": "Lý do cấp lại", "type": "text", "required": True, "placeholder": "Ví dụ: mất thẻ, hỏng thẻ"},
            {"name": "phone", "label": "Số điện thoại", "type": "text", "required": False, "placeholder": "Nhập số điện thoại"},
        ],
    },
    {
        "id": "hoc-vu-don-xin-rut-hoc-phan",
        "title": "Đơn xin rút học phần",
        "category": "Học vụ",
        "description": "Biểu mẫu để đề nghị rút học phần đã đăng ký trong học kỳ.",
        "keywords": ["rút học phần", "hủy môn", "rút môn học"],
        "fields": [
            {"name": "full_name", "label": "Họ và tên", "type": "text", "required": True, "placeholder": "Nhập họ và tên"},
            {"name": "student_id", "label": "Mã sinh viên", "type": "text", "required": True, "placeholder": "Nhập mã sinh viên"},
            {"name": "course_code", "label": "Mã học phần", "type": "text", "required": True, "placeholder": "Nhập mã học phần"},
            {"name": "course_name", "label": "Tên học phần", "type": "text", "required": True, "placeholder": "Nhập tên học phần"},
            {"name": "reason", "label": "Lý do rút học phần", "type": "text", "required": True, "placeholder": "Nhập lý do"},
        ],
    },
    {
        "id": "thuc-tap-don-dang-ky-thuc-tap",
        "title": "Đơn đăng ký thực tập",
        "category": "Thực tập",
        "description": "Biểu mẫu để đăng ký thông tin thực tập của sinh viên.",
        "keywords": ["thực tập", "đăng ký thực tập", "đơn thực tập"],
        "fields": [
            {"name": "full_name", "label": "Họ và tên", "type": "text", "required": True, "placeholder": "Nhập họ và tên"},
            {"name": "student_id", "label": "Mã sinh viên", "type": "text", "required": True, "placeholder": "Nhập mã sinh viên"},
            {"name": "company_name", "label": "Đơn vị thực tập", "type": "text", "required": True, "placeholder": "Nhập tên công ty"},
            {"name": "supervisor", "label": "Người hướng dẫn", "type": "text", "required": False, "placeholder": "Nhập tên người hướng dẫn"},
            {"name": "start_date", "label": "Ngày bắt đầu", "type": "text", "required": True, "placeholder": "dd/mm/yyyy"},
            {"name": "end_date", "label": "Ngày kết thúc", "type": "text", "required": True, "placeholder": "dd/mm/yyyy"},
        ],
    },
    {
        "id": "hoc-vu-don-xin-hoan-nghia-vu-hoc-tap",
        "title": "Đơn xin hoãn nghĩa vụ học tập",
        "category": "Học vụ",
        "description": "Biểu mẫu để sinh viên đề nghị hoãn nghĩa vụ học tập theo quy định.",
        "keywords": ["hoãn nghĩa vụ", "nghĩa vụ học tập", "gia hạn học tập"],
        "fields": [
            {"name": "full_name", "label": "Họ và tên", "type": "text", "required": True, "placeholder": "Nhập họ và tên"},
            {"name": "student_id", "label": "Mã sinh viên", "type": "text", "required": True, "placeholder": "Nhập mã sinh viên"},
            {"name": "request_detail", "label": "Nội dung đề nghị", "type": "text", "required": True, "placeholder": "Nhập nội dung đề nghị"},
            {"name": "reason", "label": "Lý do", "type": "text", "required": True, "placeholder": "Nhập lý do"},
        ],
    },
]
DEFAULT_FORM_TEMPLATES_BY_ID = {item["id"]: item for item in DEFAULT_FORM_TEMPLATES}


def ensure_admin_dirs() -> None:
    """Ensure all filesystem-backed admin directories exist."""
    DEFAULT_RAW_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    FAQS_DIR.mkdir(parents=True, exist_ok=True)
    FORMS_DIR.mkdir(parents=True, exist_ok=True)
    _seed_default_forms()


def _now() -> datetime:
    return datetime.now(UTC)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _seed_default_forms() -> None:
    """Ensure starter student form templates exist in the admin store."""
    timestamp = _now()
    for item in DEFAULT_FORM_TEMPLATES:
        form_id = item["id"]
        file_path = FORMS_DIR / f"{form_id}.json"
        if file_path.exists():
            continue
        payload = FormTemplateRead(
            id=form_id,
            title=item["title"],
            category=item["category"],
            description=item["description"],
            source_url=None,
            keywords=_build_keywords([*item["keywords"], item["category"], item["title"]]),
            fields=item["fields"],
            created_at=timestamp,
            updated_at=timestamp,
        )
        _write_json(file_path, payload.serializable_dict())


def _canonicalize_default_form(form: FormTemplateRead) -> FormTemplateRead:
    """Normalize seeded default forms so legacy JSON files still display proper Vietnamese text."""
    canonical = DEFAULT_FORM_TEMPLATES_BY_ID.get(form.id)
    if canonical is None:
        return form

    return form.model_copy(
        update={
            "title": canonical["title"],
            "category": canonical["category"],
            "description": canonical["description"],
            "keywords": _build_keywords([*canonical["keywords"], canonical["category"], canonical["title"]]),
            "fields": [FormFieldInput.model_validate(field) for field in canonical["fields"]],
        }
    )


def _build_keywords(values: list[str]) -> list[str]:
    unique_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique_values.append(normalized)
    return unique_values


def _document_title_from_filename(file_name: str) -> str:
    return Path(file_name).stem.replace("_", " ").strip()


def _manifest_rows() -> dict[str, dict[str, str]]:
    manifest_path = DEFAULT_OUTPUT_DIR / "knowledge_manifest.csv"
    if not manifest_path.exists():
        return {}

    with manifest_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return {row["relative_path"]: row for row in reader if row.get("relative_path")}


def _document_metadata_path(relative_path: str) -> Path:
    return DOCUMENTS_DIR / f"{slugify(relative_path)}.json"


def _load_document_metadata(relative_path: str) -> dict[str, Any]:
    path = _document_metadata_path(relative_path)
    if not path.exists():
        return {}
    return _read_json(path)


def load_document_metadata_map() -> dict[str, dict[str, Any]]:
    """Load all persisted document metadata overrides keyed by relative_path."""
    ensure_admin_dirs()
    metadata_map: dict[str, dict[str, Any]] = {}
    for path in DOCUMENTS_DIR.glob("*.json"):
        raw = _read_json(path)
        relative_path = raw.get("relative_path")
        if not relative_path:
            continue
        metadata_map[relative_path] = raw
    return metadata_map


def _build_document_read(
    path: Path,
    *,
    manifest_row: dict[str, str],
    metadata: dict[str, Any],
) -> KnowledgeDocumentRead:
    relative_path = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    stat = path.stat()
    title = metadata.get("title") or manifest_row.get("title") or _document_title_from_filename(path.name)
    category = (
        metadata.get("category")
        or manifest_row.get("category")
        or path.parent.name.replace("_", " ").title()
    )
    status = (
        metadata.get("status")
        or manifest_row.get("status")
        or ("published" if manifest_row else "draft")
    )
    detected_workbook = detect_workbook_schema(path, category=category)
    workbook_type = metadata.get("workbook_type") or (detected_workbook or {}).get("workbook_type")
    sheet_schema_config = metadata.get("sheet_schema_config") or (detected_workbook or {}).get("sheet_schema_config")

    return KnowledgeDocumentRead(
        id=slugify(relative_path),
        title=title,
        category=category,
        file_name=path.name,
        relative_path=relative_path,
        page_count=int(manifest_row["page_count"]) if manifest_row.get("page_count") else None,
        status=status,
        source_office=metadata.get("source_office") or manifest_row.get("source_office") or None,
        issued_date=metadata.get("issued_date") or manifest_row.get("issued_date") or None,
        effective_date=metadata.get("effective_date") or manifest_row.get("effective_date") or None,
        version=metadata.get("version") or manifest_row.get("version") or None,
        source_url=metadata.get("source_url") or manifest_row.get("source_url") or None,
        notes=metadata.get("notes") or manifest_row.get("notes") or None,
        workbook_type=workbook_type,
        sheet_schema_config=sheet_schema_config,
        uploaded_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
    )


def list_documents() -> list[KnowledgeDocumentRead]:
    """List uploaded raw documents merged with processed manifest metadata."""
    ensure_admin_dirs()
    manifest_rows = _manifest_rows()
    metadata_map = load_document_metadata_map()
    documents: list[KnowledgeDocumentRead] = []

    for path in sorted(
        item
        for item in DEFAULT_RAW_DIR.rglob("*")
        if item.is_file() and item.suffix.lower() in SUPPORTED_DOCUMENT_EXTENSIONS
    ):
        relative_path = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        documents.append(
            _build_document_read(
                path,
                manifest_row=manifest_rows.get(relative_path, {}),
                metadata=metadata_map.get(relative_path, {}),
            )
        )

    return documents


def save_uploaded_document(
    file_name: str,
    content: bytes,
    category: str,
    workbook_type: str | None = None,
) -> KnowledgeDocumentRead:
    """Persist an uploaded document into the raw knowledge directory."""
    ensure_admin_dirs()

    safe_file_name = Path(file_name).name
    suffix = Path(safe_file_name).suffix.lower()
    if suffix not in SUPPORTED_DOCUMENT_EXTENSIONS:
        raise BadRequestError(message="Only PDF, CSV, XLSX, and XLS files are supported")

    category_slug = slugify(category).replace("-", "_")
    if not category_slug:
        raise BadRequestError(message="Category is required")

    category_dir = DEFAULT_RAW_DIR / category_slug
    category_dir.mkdir(parents=True, exist_ok=True)

    destination = category_dir / safe_file_name
    destination.write_bytes(content)
    storage_service = get_storage_service()
    storage_key = f"knowledge/raw/{category_slug}/{safe_file_name}"
    resolved_content_type = mimetypes.guess_type(safe_file_name)[0] or "application/octet-stream"
    storage_service.upload_bytes(storage_key, content, content_type=resolved_content_type)

    rebuild_knowledge()

    relative_path = str(destination.relative_to(PROJECT_ROOT)).replace("\\", "/")
    workbook_metadata = detect_workbook_schema(destination, category=category_slug.replace("_", " ").title()) or {}
    resolved_workbook_type = workbook_type or workbook_metadata.get("workbook_type")
    _write_json(
        _document_metadata_path(relative_path),
        {
            "relative_path": relative_path,
            "title": _document_title_from_filename(safe_file_name),
            "category": category_slug.replace("_", " ").title(),
            "status": "draft",
            "source_office": None,
            "issued_date": None,
            "effective_date": None,
            "version": None,
            "source_url": None,
            "notes": None,
            "workbook_type": resolved_workbook_type,
            "sheet_schema_config": workbook_metadata.get("sheet_schema_config"),
            "updated_at": _now().isoformat(),
        },
    )
    manifest_row = _manifest_rows().get(relative_path, {})
    return _build_document_read(
        destination,
        manifest_row=manifest_row,
        metadata=_load_document_metadata(relative_path),
    )


def delete_document(relative_path: str) -> None:
    """Delete a tracked raw PDF document and its sidecar metadata."""
    ensure_admin_dirs()
    document_path = PROJECT_ROOT / relative_path
    if not document_path.exists():
        raise NotFoundError(message="Document not found")

    storage_service = get_storage_service()
    category_slug = document_path.parent.name
    storage_key = f"knowledge/raw/{category_slug}/{document_path.name}"

    metadata_path = _document_metadata_path(relative_path)
    if metadata_path.exists():
        metadata_path.unlink()

    if document_path.exists():
        document_path.unlink()

    try:
        storage_service.delete_object(storage_key)
    except Exception:
        pass

    rebuild_knowledge()


def update_document_metadata(payload: KnowledgeDocumentMetadataUpdate) -> KnowledgeDocumentRead:
    """Update editable metadata and publish state for a tracked raw document."""
    ensure_admin_dirs()
    document_path = PROJECT_ROOT / payload.relative_path
    if not document_path.exists():
        raise NotFoundError(message="Document not found")
    if payload.status not in VALID_DOCUMENT_STATUSES:
        raise BadRequestError(message="Invalid document status")

    metadata_payload = payload.serializable_dict()
    if metadata_payload.get("workbook_type") is None or metadata_payload.get("sheet_schema_config") is None:
        detected = detect_workbook_schema(document_path, category=payload.category) or {}
        metadata_payload["workbook_type"] = metadata_payload.get("workbook_type") or detected.get("workbook_type")
        metadata_payload["sheet_schema_config"] = metadata_payload.get("sheet_schema_config") or detected.get(
            "sheet_schema_config"
        )
    metadata_payload["updated_at"] = _now().isoformat()
    _write_json(_document_metadata_path(payload.relative_path), metadata_payload)

    manifest_row = _manifest_rows().get(payload.relative_path, {})
    return _build_document_read(
        document_path,
        manifest_row=manifest_row,
        metadata=metadata_payload,
    )


def batch_update_document_metadata(
    payload: KnowledgeDocumentBatchMetadataUpdate,
) -> list[KnowledgeDocumentRead]:
    """Update status and optional shared metadata for multiple tracked documents."""
    ensure_admin_dirs()
    if payload.status not in VALID_DOCUMENT_STATUSES:
        raise BadRequestError(message="Invalid document status")

    updated_documents: list[KnowledgeDocumentRead] = []
    manifest_rows = _manifest_rows()

    for relative_path in payload.relative_paths:
        document_path = PROJECT_ROOT / relative_path
        if not document_path.exists():
            raise NotFoundError(message=f"Document not found: {relative_path}")

        existing_metadata = _load_document_metadata(relative_path)
        next_metadata = {
            "relative_path": relative_path,
            "title": existing_metadata.get("title")
            or manifest_rows.get(relative_path, {}).get("title")
            or _document_title_from_filename(document_path.name),
            "category": existing_metadata.get("category")
            or manifest_rows.get(relative_path, {}).get("category")
            or document_path.parent.name.replace("_", " ").title(),
            "status": payload.status,
            "source_office": payload.source_office
            if payload.source_office is not None
            else existing_metadata.get("source_office"),
            "issued_date": payload.issued_date
            if payload.issued_date is not None
            else existing_metadata.get("issued_date"),
            "effective_date": payload.effective_date
            if payload.effective_date is not None
            else existing_metadata.get("effective_date"),
            "version": payload.version if payload.version is not None else existing_metadata.get("version"),
            "source_url": existing_metadata.get("source_url"),
            "notes": payload.notes if payload.notes is not None else existing_metadata.get("notes"),
            "workbook_type": payload.workbook_type
            if payload.workbook_type is not None
            else existing_metadata.get("workbook_type"),
            "sheet_schema_config": payload.sheet_schema_config
            if payload.sheet_schema_config is not None
            else existing_metadata.get("sheet_schema_config"),
            "updated_at": _now().isoformat(),
        }
        if next_metadata.get("workbook_type") is None or next_metadata.get("sheet_schema_config") is None:
            detected = detect_workbook_schema(document_path, category=next_metadata["category"]) or {}
            next_metadata["workbook_type"] = next_metadata.get("workbook_type") or detected.get("workbook_type")
            next_metadata["sheet_schema_config"] = next_metadata.get("sheet_schema_config") or detected.get(
                "sheet_schema_config"
            )
        _write_json(_document_metadata_path(relative_path), next_metadata)
        updated_documents.append(
            _build_document_read(
                document_path,
                manifest_row=manifest_rows.get(relative_path, {}),
                metadata=next_metadata,
            )
        )

    return updated_documents


def get_document_preview(relative_path: str) -> KnowledgeDocumentPreviewRead:
    """Preview processed chunks and tables for a raw knowledge document."""
    ensure_admin_dirs()
    manifest_row = _manifest_rows().get(relative_path)
    if not manifest_row:
        raise NotFoundError(message="Document preview not found. Rebuild knowledge first.")

    document_id = manifest_row.get("document_id")
    if not document_id:
        raise NotFoundError(message="Document preview is missing document_id metadata")

    chunks_path = DEFAULT_OUTPUT_DIR / "chunks" / f"{document_id}.json"
    tables_path = DEFAULT_OUTPUT_DIR / "tables" / f"{document_id}.json"

    chunk_items: list[KnowledgePreviewChunkRead] = []
    table_items: list[KnowledgePreviewTableRead] = []

    if chunks_path.exists():
        raw_chunks = _read_json(chunks_path)
        for chunk in raw_chunks.get("chunks", [])[:6]:
            chunk_items.append(
                KnowledgePreviewChunkRead(
                    chunk_id=chunk["chunk_id"],
                    section_title=chunk.get("section_title"),
                    summary=chunk.get("summary") or chunk.get("content") or "",
                    page_from=chunk.get("page_from"),
                    page_to=chunk.get("page_to"),
                )
            )

    if tables_path.exists():
        raw_tables = _read_json(tables_path)
        for table in raw_tables.get("tables", [])[:4]:
            rows: list[KnowledgePreviewTableRowRead] = []
            for row in table.get("rows", [])[:4]:
                rows.append(
                    KnowledgePreviewTableRowRead(
                        row_id=str(row.get("row_id", "")),
                        label=row.get("label", ""),
                        amount_text=row.get("amount_text"),
                        page_from=row.get("page_from", table.get("page_from")),
                        page_to=row.get("page_to", table.get("page_to")),
                    )
                )
            table_items.append(
                KnowledgePreviewTableRead(
                    table_id=table["table_id"],
                    title=table.get("title") or "Bang du lieu",
                    page_from=table.get("page_from"),
                    page_to=table.get("page_to"),
                    rows=rows,
                )
            )

    return KnowledgeDocumentPreviewRead(
        relative_path=relative_path,
        document_id=document_id,
        chunk_count=int(manifest_row.get("chunk_count") or 0),
        table_count=int(manifest_row.get("table_count") or 0),
        chunks=chunk_items,
        tables=table_items,
    )


def list_faqs() -> list[FAQRead]:
    """List admin-managed FAQs."""
    ensure_admin_dirs()
    faqs: list[FAQRead] = []
    for path in sorted(FAQS_DIR.glob("*.json")):
        faqs.append(FAQRead.model_validate(_read_json(path)))
    return faqs


def create_faq(payload: FAQCreate) -> FAQRead:
    """Create a new FAQ JSON document and refresh retrieval cache."""
    ensure_admin_dirs()
    faq_id = slugify(f"{payload.category}-{payload.title}-{payload.question[:40]}")
    file_path = FAQS_DIR / f"{faq_id}.json"
    timestamp = _now()

    faq = FAQRead(
        id=faq_id,
        title=payload.title,
        category=payload.category,
        question=payload.question,
        answer=payload.answer,
        source_url=payload.source_url,
        keywords=_build_keywords([*payload.keywords, payload.category, payload.title]),
        created_at=timestamp,
        updated_at=timestamp,
    )
    _write_json(file_path, faq.serializable_dict())
    get_student_knowledge_base.cache_clear()
    return faq


def update_faq(faq_id: str, payload: FAQCreate) -> FAQRead:
    """Update an existing FAQ entry."""
    path = FAQS_DIR / f"{faq_id}.json"
    if not path.exists():
        raise NotFoundError(message="FAQ not found")

    existing = FAQRead.model_validate(_read_json(path))
    faq = FAQRead(
        id=faq_id,
        title=payload.title,
        category=payload.category,
        question=payload.question,
        answer=payload.answer,
        source_url=payload.source_url,
        keywords=_build_keywords([*payload.keywords, payload.category, payload.title]),
        created_at=existing.created_at,
        updated_at=_now(),
    )
    _write_json(path, faq.serializable_dict())
    get_student_knowledge_base.cache_clear()
    return faq


def delete_faq(faq_id: str) -> None:
    """Delete an FAQ entry."""
    path = FAQS_DIR / f"{faq_id}.json"
    if not path.exists():
        raise NotFoundError(message="FAQ not found")
    path.unlink()
    get_student_knowledge_base.cache_clear()


def list_forms() -> list[FormTemplateRead]:
    """List admin-managed form templates."""
    ensure_admin_dirs()
    forms: list[FormTemplateRead] = []
    for path in sorted(FORMS_DIR.glob("*.json")):
        form = FormTemplateRead.model_validate(_read_json(path))
        if form.id in DEPRECATED_FORM_IDS:
            continue
        forms.append(_canonicalize_default_form(form))
    return forms


def create_form_template(payload: FormTemplateCreate) -> FormTemplateRead:
    """Create a form template JSON document and refresh retrieval cache."""
    ensure_admin_dirs()
    form_id = slugify(f"{payload.category}-{payload.title}")
    file_path = FORMS_DIR / f"{form_id}.json"
    timestamp = _now()

    form_template = FormTemplateRead(
        id=form_id,
        title=payload.title,
        category=payload.category,
        description=payload.description,
        source_url=payload.source_url,
        keywords=_build_keywords([*payload.keywords, payload.category, payload.title]),
        fields=payload.fields,
        created_at=timestamp,
        updated_at=timestamp,
    )
    _write_json(file_path, form_template.serializable_dict())
    get_student_knowledge_base.cache_clear()
    return form_template


def update_form_template(form_id: str, payload: FormTemplateCreate) -> FormTemplateRead:
    """Update an existing form template."""
    path = FORMS_DIR / f"{form_id}.json"
    if not path.exists():
        raise NotFoundError(message="Form template not found")

    existing = FormTemplateRead.model_validate(_read_json(path))
    form_template = FormTemplateRead(
        id=form_id,
        title=payload.title,
        category=payload.category,
        description=payload.description,
        source_url=payload.source_url,
        keywords=_build_keywords([*payload.keywords, payload.category, payload.title]),
        fields=payload.fields,
        created_at=existing.created_at,
        updated_at=_now(),
    )
    _write_json(path, form_template.serializable_dict())
    get_student_knowledge_base.cache_clear()
    return form_template


def delete_form_template(form_id: str) -> None:
    """Delete a form template."""
    path = FORMS_DIR / f"{form_id}.json"
    if not path.exists():
        raise NotFoundError(message="Form template not found")
    path.unlink()
    get_student_knowledge_base.cache_clear()


def rebuild_knowledge() -> dict[str, int]:
    """Rebuild processed knowledge artifacts and clear cached retrieval state."""
    ensure_admin_dirs()
    result = ingest_knowledge_base(raw_dir=DEFAULT_RAW_DIR, output_dir=DEFAULT_OUTPUT_DIR)
    get_student_knowledge_base.cache_clear()
    return {"documents": result.document_count, "chunks": result.chunk_count}
