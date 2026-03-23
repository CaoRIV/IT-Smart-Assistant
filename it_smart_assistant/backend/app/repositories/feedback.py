"""Repository helpers for feedback and analytics."""

from __future__ import annotations

from collections import Counter
from uuid import UUID
import json

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation, Message, ToolCall
from app.db.models.feedback import MessageFeedback


async def get_feedback_for_message_and_user(
    db: AsyncSession,
    *,
    message_id: UUID,
    user_id: UUID,
) -> MessageFeedback | None:
    query = select(MessageFeedback).where(
        MessageFeedback.message_id == message_id,
        MessageFeedback.user_id == user_id,
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_feedback(
    db: AsyncSession,
    *,
    message_id: UUID,
    user_id: UUID,
    helpful: bool,
    comment: str | None,
) -> MessageFeedback:
    feedback = MessageFeedback(
        message_id=message_id,
        user_id=user_id,
        helpful=helpful,
        comment=comment,
    )
    db.add(feedback)
    await db.flush()
    await db.refresh(feedback)
    return feedback


async def update_feedback(
    db: AsyncSession,
    *,
    db_feedback: MessageFeedback,
    helpful: bool,
    comment: str | None,
) -> MessageFeedback:
    db_feedback.helpful = helpful
    db_feedback.comment = comment
    db.add(db_feedback)
    await db.flush()
    await db.refresh(db_feedback)
    return db_feedback


async def get_message_with_conversation(
    db: AsyncSession,
    *,
    message_id: UUID,
) -> tuple[Message, Conversation] | None:
    query = (
        select(Message, Conversation)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Message.id == message_id)
    )
    result = await db.execute(query)
    row = result.first()
    if not row:
        return None
    return row[0], row[1]


async def count_conversations(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(Conversation.id)))
    return result.scalar() or 0


async def count_messages(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(Message.id)))
    return result.scalar() or 0


async def count_assistant_messages(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(Message.id)).where(Message.role == "assistant"))
    return result.scalar() or 0


async def count_feedback_summary(db: AsyncSession) -> tuple[int, int, int]:
    total_result = await db.execute(select(func.count(MessageFeedback.id)))
    helpful_result = await db.execute(
        select(func.count(MessageFeedback.id)).where(MessageFeedback.helpful == True)  # noqa: E712
    )
    unhelpful_result = await db.execute(
        select(func.count(MessageFeedback.id)).where(MessageFeedback.helpful == False)  # noqa: E712
    )
    return (
        total_result.scalar() or 0,
        helpful_result.scalar() or 0,
        unhelpful_result.scalar() or 0,
    )


async def get_top_questions(db: AsyncSession, *, limit: int = 5) -> list[tuple[str, int]]:
    query = (
        select(Message.content, func.count(Message.id).label("count"))
        .where(Message.role == "user")
        .group_by(Message.content)
        .order_by(func.count(Message.id).desc(), func.max(Message.created_at).desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return [(content, count) for content, count in result.all()]


async def get_top_intents(db: AsyncSession, *, limit: int = 5) -> list[tuple[str, int]]:
    query = (
        select(Message.router_intent, func.count(Message.id).label("count"))
        .where(
            Message.role == "user",
            Message.router_intent.is_not(None),
        )
        .group_by(Message.router_intent)
        .order_by(func.count(Message.id).desc(), Message.router_intent.asc())
        .limit(limit)
    )
    result = await db.execute(query)
    return [(intent, count) for intent, count in result.all() if intent]


async def get_intent_feedback_quality(
    db: AsyncSession,
    *,
    limit: int = 5,
) -> list[tuple[str, int, int, int, float]]:
    helpful_case = case((MessageFeedback.helpful.is_(True), 1), else_=0)
    unhelpful_case = case((MessageFeedback.helpful.is_(False), 1), else_=0)

    query = (
        select(
            Message.router_intent,
            func.count(MessageFeedback.id).label("total_feedback"),
            func.sum(helpful_case).label("helpful_feedback"),
            func.sum(unhelpful_case).label("unhelpful_feedback"),
        )
        .join(MessageFeedback, MessageFeedback.message_id == Message.id)
        .where(
            Message.role == "assistant",
            Message.router_intent.is_not(None),
        )
        .group_by(Message.router_intent)
        .order_by(
            func.sum(unhelpful_case).desc(),
            func.count(MessageFeedback.id).desc(),
            Message.router_intent.asc(),
        )
        .limit(limit)
    )
    result = await db.execute(query)

    rows: list[tuple[str, int, int, int, float]] = []
    for intent, total_feedback, helpful_feedback, unhelpful_feedback in result.all():
        if not intent:
            continue
        total = int(total_feedback or 0)
        helpful = int(helpful_feedback or 0)
        unhelpful = int(unhelpful_feedback or 0)
        helpful_rate = round((helpful / total * 100) if total else 0.0, 2)
        rows.append((intent, total, helpful, unhelpful, helpful_rate))
    return rows


async def get_top_tools(db: AsyncSession, *, limit: int = 5) -> list[tuple[str, int]]:
    query = (
        select(ToolCall.tool_name, func.count(ToolCall.id).label("count"))
        .group_by(ToolCall.tool_name)
        .order_by(func.count(ToolCall.id).desc(), ToolCall.tool_name.asc())
        .limit(limit)
    )
    result = await db.execute(query)
    return [(tool_name, count) for tool_name, count in result.all()]


async def count_tool_calls(db: AsyncSession, *, tool_name: str) -> int:
    result = await db.execute(select(func.count(ToolCall.id)).where(ToolCall.tool_name == tool_name))
    return result.scalar() or 0


async def get_top_procedures(db: AsyncSession, *, limit: int = 5) -> list[tuple[str, int]]:
    query = select(ToolCall.result).where(
        ToolCall.tool_name == "build_procedure_workflow",
        ToolCall.status == "completed",
        ToolCall.result.is_not(None),
    )
    result = await db.execute(query)
    counter: Counter[str] = Counter()

    for (raw_result,) in result.all():
        try:
            payload = json.loads(raw_result)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("matched") is not True:
            continue
        label = payload.get("title") or payload.get("procedure_id")
        if isinstance(label, str) and label.strip():
            counter[label.strip()] += 1

    return counter.most_common(limit)
