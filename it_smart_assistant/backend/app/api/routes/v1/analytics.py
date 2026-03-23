"""Admin analytics routes."""

from fastapi import APIRouter

from app.api.deps import AnalyticsSvc, CurrentAdmin
from app.schemas.analytics import AnalyticsOverviewRead

router = APIRouter()


@router.get("/analytics/overview", response_model=AnalyticsOverviewRead)
async def get_analytics_overview(
    analytics_service: AnalyticsSvc,
    current_user: CurrentAdmin,
):
    """Return admin dashboard analytics overview."""
    return await analytics_service.get_overview()
