"""Schemas for admin analytics."""

from __future__ import annotations

from app.schemas.base import BaseSchema


class AnalyticsCountItem(BaseSchema):
    """Simple label/count pair for ranking lists."""

    label: str
    count: int


class AnalyticsIntentQualityItem(BaseSchema):
    """Quality summary for a routed intent based on assistant-message feedback."""

    label: str
    total_feedback: int
    helpful_feedback: int
    unhelpful_feedback: int
    helpful_rate: float


class AnalyticsOverviewRead(BaseSchema):
    """High-level admin dashboard analytics."""

    total_conversations: int
    total_messages: int
    assistant_messages: int
    total_feedback: int
    helpful_feedback: int
    unhelpful_feedback: int
    helpful_rate: float
    forms_opened: int
    procedure_workflows: int
    top_intents: list[AnalyticsCountItem]
    weakest_intents: list[AnalyticsIntentQualityItem]
    top_questions: list[AnalyticsCountItem]
    top_tools: list[AnalyticsCountItem]
    top_procedures: list[AnalyticsCountItem]
