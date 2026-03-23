"""Feedback routes for assistant message rating."""

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, FeedbackSvc
from app.schemas.feedback import MessageFeedbackCreate, MessageFeedbackRead

router = APIRouter()


@router.post("/feedback", response_model=MessageFeedbackRead, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    data: MessageFeedbackCreate,
    feedback_service: FeedbackSvc,
    current_user: CurrentUser,
):
    """Create or update feedback for an assistant message."""
    feedback = await feedback_service.create_or_update_feedback(
        data=data,
        user_id=current_user.id,
    )
    return feedback
