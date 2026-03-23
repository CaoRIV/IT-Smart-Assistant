"""Analytics service for admin dashboard."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import feedback as feedback_repo
from app.schemas.analytics import (
    AnalyticsCountItem,
    AnalyticsIntentQualityItem,
    AnalyticsOverviewRead,
)


class AnalyticsService:
    """Service for admin analytics overview."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_overview(self) -> AnalyticsOverviewRead:
        total_conversations = await feedback_repo.count_conversations(self.db)
        total_messages = await feedback_repo.count_messages(self.db)
        assistant_messages = await feedback_repo.count_assistant_messages(self.db)
        total_feedback, helpful_feedback, unhelpful_feedback = await feedback_repo.count_feedback_summary(
            self.db
        )
        forms_opened = await feedback_repo.count_tool_calls(self.db, tool_name="generate_form")
        procedure_workflows = await feedback_repo.count_tool_calls(
            self.db,
            tool_name="build_procedure_workflow",
        )
        top_intents = await feedback_repo.get_top_intents(self.db)
        weakest_intents = await feedback_repo.get_intent_feedback_quality(self.db)
        top_questions = await feedback_repo.get_top_questions(self.db)
        top_tools = await feedback_repo.get_top_tools(self.db)
        top_procedures = await feedback_repo.get_top_procedures(self.db)

        helpful_rate = (helpful_feedback / total_feedback * 100) if total_feedback else 0.0

        return AnalyticsOverviewRead(
            total_conversations=total_conversations,
            total_messages=total_messages,
            assistant_messages=assistant_messages,
            total_feedback=total_feedback,
            helpful_feedback=helpful_feedback,
            unhelpful_feedback=unhelpful_feedback,
            helpful_rate=round(helpful_rate, 2),
            forms_opened=forms_opened,
            procedure_workflows=procedure_workflows,
            top_intents=[
                AnalyticsCountItem(label=label, count=count) for label, count in top_intents
            ],
            weakest_intents=[
                AnalyticsIntentQualityItem(
                    label=label,
                    total_feedback=total_feedback,
                    helpful_feedback=helpful_feedback,
                    unhelpful_feedback=unhelpful_feedback,
                    helpful_rate=helpful_rate,
                )
                for label, total_feedback, helpful_feedback, unhelpful_feedback, helpful_rate in weakest_intents
            ],
            top_questions=[
                AnalyticsCountItem(label=label, count=count) for label, count in top_questions
            ],
            top_tools=[
                AnalyticsCountItem(label=label, count=count) for label, count in top_tools
            ],
            top_procedures=[
                AnalyticsCountItem(label=label, count=count) for label, count in top_procedures
            ],
        )
