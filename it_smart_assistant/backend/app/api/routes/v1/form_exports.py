"""Routes for exporting filled forms."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from app.schemas.form_export import FormExportRequest
from app.services.form_export import persist_rendered_form_pdf, render_form_pdf

router = APIRouter(prefix="/form-exports")


@router.post("/pdf")
async def export_form_pdf(payload: FormExportRequest) -> Response:
    """Render a filled student form as a downloadable PDF."""
    pdf_content = render_form_pdf(payload)
    storage_key = persist_rendered_form_pdf(payload, pdf_content)
    file_name = payload.title.lower().replace(" ", "_")
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}.pdf"',
            "X-Storage-Key": storage_key,
        },
    )
