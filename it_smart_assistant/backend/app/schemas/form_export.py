"""Schemas for exporting filled forms."""

from __future__ import annotations

from pydantic import Field

from app.schemas.base import BaseSchema


class FormExportFieldValue(BaseSchema):
    """Single field value submitted for PDF export."""

    field_id: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=255)
    value: str = Field(default="")


class FormExportRequest(BaseSchema):
    """Payload used to render a filled form into PDF."""

    title: str = Field(min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    template: str = Field(min_length=3)
    values: list[FormExportFieldValue] = Field(default_factory=list)
