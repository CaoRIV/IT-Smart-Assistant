"""Database models."""

# ruff: noqa: I001, RUF022 - Imports structured for Jinja2 template conditionals
from app.db.models.user import User
from app.db.models.session import Session
from app.db.models.item import Item
from app.db.models.conversation import Conversation, Message, ToolCall
from app.db.models.feedback import MessageFeedback
from app.db.models.knowledge import (
    KnowledgeChunk,
    KnowledgeCourse,
    KnowledgeCourseCatalog,
    KnowledgeDocument,
    KnowledgeEntry,
    KnowledgeFaq,
    KnowledgeForm,
    KnowledgeInteraction,
    KnowledgeProcedure,
    KnowledgeSource,
    KnowledgeSourceFile,
    KnowledgeSourceVersion,
    KnowledgeTable,
    KnowledgeTableRow,
)

__all__ = [
    "User",
    "Session",
    "Item",
    "Conversation",
    "Message",
    "ToolCall",
    "MessageFeedback",
    "KnowledgeSource",
    "KnowledgeSourceVersion",
    "KnowledgeSourceFile",
    "KnowledgeChunk",
    "KnowledgeCourseCatalog",
    "KnowledgeCourse",
    "KnowledgeTable",
    "KnowledgeTableRow",
    "KnowledgeFaq",
    "KnowledgeInteraction",
    "KnowledgeProcedure",
    "KnowledgeForm",
    "KnowledgeDocument",
    "KnowledgeEntry",
]
