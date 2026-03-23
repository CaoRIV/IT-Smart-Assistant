"""API dependencies.

Dependency injection factories for services, repositories, and authentication.
"""
# ruff: noqa: I001, E402 - Imports structured for Jinja2 template conditionals

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.db.session import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

DBSession = Annotated[AsyncSession, Depends(get_db_session)]
from fastapi import Request

from app.clients.redis import RedisClient


async def get_redis(request: Request) -> RedisClient:
    """Get Redis client from lifespan state."""
    return request.state.redis


Redis = Annotated[RedisClient, Depends(get_redis)]


# === Service Dependencies ===

from app.services.user import UserService
from app.services.session import SessionService
from app.services.item import ItemService
from app.services.conversation import ConversationService
from app.services.feedback import FeedbackService
from app.services.analytics import AnalyticsService


def get_user_service(db: DBSession) -> UserService:
    """Create UserService instance with database session."""
    return UserService(db)


def get_session_service(db: DBSession) -> SessionService:
    """Create SessionService instance with database session."""
    return SessionService(db)


UserSvc = Annotated[UserService, Depends(get_user_service)]
SessionSvc = Annotated[SessionService, Depends(get_session_service)]


def get_item_service(db: DBSession) -> ItemService:
    """Create ItemService instance with database session."""
    return ItemService(db)


ItemSvc = Annotated[ItemService, Depends(get_item_service)]


def get_conversation_service(db: DBSession) -> ConversationService:
    """Create ConversationService instance with database session."""
    return ConversationService(db)


ConversationSvc = Annotated[ConversationService, Depends(get_conversation_service)]


def get_feedback_service(db: DBSession) -> FeedbackService:
    """Create FeedbackService instance with database session."""
    return FeedbackService(db)


FeedbackSvc = Annotated[FeedbackService, Depends(get_feedback_service)]


def get_analytics_service(db: DBSession) -> AnalyticsService:
    """Create AnalyticsService instance with database session."""
    return AnalyticsService(db)


AnalyticsSvc = Annotated[AnalyticsService, Depends(get_analytics_service)]

# === Authentication Dependencies ===

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.db.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_service: UserSvc,
) -> User:
    """Get current authenticated user from JWT token.

    Returns the full User object including role information.

    Raises:
        AuthenticationError: If token is invalid or user not found.
    """
    from uuid import UUID

    from app.core.security import verify_token

    payload = verify_token(token)
    if payload is None:
        raise AuthenticationError(message="Invalid or expired token")

    # Ensure this is an access token, not a refresh token
    if payload.get("type") != "access":
        raise AuthenticationError(message="Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError(message="Invalid token payload")

    user = await user_service.get_by_id(UUID(user_id))
    if not user.is_active:
        raise AuthenticationError(message="User account is disabled")

    return user


class RoleChecker:
    """Dependency class for role-based access control.

    Usage:
        # Require admin role
        @router.get("/admin-only")
        async def admin_endpoint(
            user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))]
        ):
            ...

        # Require any authenticated user
        @router.get("/users")
        async def users_endpoint(
            user: Annotated[User, Depends(get_current_user)]
        ):
            ...
    """

    def __init__(self, required_role: UserRole) -> None:
        self.required_role = required_role

    async def __call__(
        self,
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        """Check if user has the required role.

        Raises:
            AuthorizationError: If user doesn't have the required role.
        """
        if not user.has_role(self.required_role):
            raise AuthorizationError(
                message=f"Role '{self.required_role.value}' required for this action"
            )
        return user


async def get_current_active_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current user and verify they are a superuser.

    Raises:
        AuthorizationError: If user is not a superuser.
    """
    if not current_user.is_superuser:
        raise AuthorizationError(message="Superuser privileges required")
    return current_user


# Type aliases for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentSuperuser = Annotated[User, Depends(get_current_active_superuser)]
CurrentAdmin = Annotated[User, Depends(RoleChecker(UserRole.ADMIN))]


# WebSocket authentication dependency
from fastapi import WebSocket, Query, Cookie


async def _get_user_from_auth_token(auth_token: str) -> User:
    """Resolve a user from a validated auth token."""
    from uuid import UUID

    from app.core.security import verify_token

    payload = verify_token(auth_token)
    if payload is None:
        raise AuthenticationError(message="Invalid or expired token")

    if payload.get("type") != "access":
        raise AuthenticationError(message="Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError(message="Invalid token payload")

    from app.db.session import get_db_context

    async with get_db_context() as db:
        user_service = UserService(db)
        user = await user_service.get_by_id(UUID(user_id))

    if not user.is_active:
        raise AuthenticationError(message="User account is disabled")

    return user


async def get_current_user_ws(
    websocket: WebSocket,
    token: str | None = Query(None, alias="token"),
    access_token: str | None = Cookie(None),
) -> User:
    """Get current user from WebSocket JWT token."""
    auth_token = token or access_token

    if not auth_token:
        await websocket.close(code=4001, reason="Missing authentication token")
        raise AuthenticationError(message="Missing authentication token")

    try:
        return await _get_user_from_auth_token(auth_token)
    except AuthenticationError as exc:
        await websocket.close(code=4001, reason=exc.message)
        raise


async def get_optional_current_user_ws(
    websocket: WebSocket,
    token: str | None = Query(None, alias="token"),
    access_token: str | None = Cookie(None),
) -> User | None:
    """Resolve the current WebSocket user when a token is present."""
    auth_token = token or access_token

    if not auth_token:
        return None

    try:
        return await _get_user_from_auth_token(auth_token)
    except AuthenticationError as exc:
        await websocket.close(code=4001, reason=exc.message)
        raise
