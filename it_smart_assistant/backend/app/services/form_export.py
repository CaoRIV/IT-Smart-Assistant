"""Simple PDF export for filled student forms."""

from __future__ import annotations

import textwrap
import unicodedata
from uuid import uuid4

from app.schemas.form_export import FormExportRequest
from app.services.storage import get_storage_service

PAGE_WIDTH = 595
PAGE_HEIGHT = 842
LEFT_MARGIN = 50
TOP_START = 790
LINE_HEIGHT = 18


def _ascii_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_value.replace("\r", " ").strip()


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_lines(payload: FormExportRequest) -> list[str]:
    lines = [_ascii_text(payload.title)]
    if payload.description:
      lines.append("")
      lines.extend(textwrap.wrap(_ascii_text(payload.description), width=85))

    lines.append("")
    lines.append("Thong tin da dien:")
    lines.append("")

    for item in payload.values:
        value = _ascii_text(item.value or "")
        label = _ascii_text(item.label)
        wrapped_values = textwrap.wrap(value or "-", width=70) or ["-"]
        lines.append(f"{label}: {wrapped_values[0]}")
        for extra_line in wrapped_values[1:]:
            lines.append(f"  {extra_line}")

    lines.append("")
    lines.append("Noi dung bieu mau:")
    lines.append("")

    template_lines = _ascii_text(payload.template).splitlines() or ["-"]
    for line in template_lines:
        wrapped_line = textwrap.wrap(line, width=85) or [""]
        lines.extend(wrapped_line)

    return lines


def _content_stream(lines: list[str]) -> bytes:
    commands = ["BT", "/F1 12 Tf", f"{LEFT_MARGIN} {TOP_START} Td"]
    first = True
    for line in lines:
        escaped = _escape_pdf_text(line)
        if first:
            commands.append(f"({escaped}) Tj")
            first = False
        else:
            commands.append("T*")
            commands.append(f"({escaped}) Tj")
    commands.append("ET")
    return "\n".join(commands).encode("latin-1", errors="ignore")


def render_form_pdf(payload: FormExportRequest) -> bytes:
    """Render a very lightweight PDF containing the filled form values."""
    lines = _build_lines(payload)
    content = _content_stream(lines)

    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
        f"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>".encode("latin-1")
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(
        f"<< /Length {len(content)} >>\nstream\n".encode("latin-1") + content + b"\nendstream"
    )

    pdf = bytearray(b"%PDF-1.4\n")
    xref_positions = [0]
    for index, obj in enumerate(objects, start=1):
        xref_positions.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("latin-1"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for position in xref_positions[1:]:
        pdf.extend(f"{position:010} 00000 n \n".encode("latin-1"))

    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF"
        ).encode("latin-1")
    )
    return bytes(pdf)


def persist_rendered_form_pdf(payload: FormExportRequest, pdf_content: bytes) -> str:
    """Store a generated PDF artifact in the configured storage backend."""
    storage_service = get_storage_service()
    slug = _ascii_text(payload.title or "bieu_mau").lower().replace(" ", "_") or "bieu_mau"
    object_key = f"generated-forms/{uuid4().hex}_{slug}.pdf"
    stored_object = storage_service.upload_bytes(
        object_key,
        pdf_content,
        content_type="application/pdf",
    )
    return stored_object.key
