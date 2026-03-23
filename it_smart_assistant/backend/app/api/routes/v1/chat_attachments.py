"""Chat attachment upload routes."""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from app.schemas.chat_attachment import ChatAttachmentRead
from app.services.chat_attachment import save_chat_attachment

router = APIRouter(prefix="/chat-attachments")


@router.post("/upload", response_model=ChatAttachmentRead, status_code=201)
async def upload_chat_attachment(
    file: UploadFile = File(...),
) -> ChatAttachmentRead:
    """Upload a file or image to use in the current chat turn."""
    return await save_chat_attachment(file)
