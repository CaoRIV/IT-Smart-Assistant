"""AI Agent WebSocket routes with streaming support (LangGraph ReAct Agent)."""

import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    ToolMessage,
)

from app.agents.langgraph_assistant import AgentContext, get_agent
from app.api.deps import get_conversation_service, get_optional_current_user_ws
from app.db.models.user import User
from app.db.session import get_db_context
from app.schemas.conversation import (
    ConversationCreate,
    MessageCreate,
)
from app.services.chat_attachment import build_attachment_history_note, load_prompt_attachments

logger = logging.getLogger(__name__)

router = APIRouter()


class AgentConnectionManager:
    """WebSocket connection manager for AI agent."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Agent WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(
            f"Agent WebSocket disconnected. Total connections: {len(self.active_connections)}"
        )

    async def send_event(self, websocket: WebSocket, event_type: str, data: Any) -> bool:
        """Send a JSON event to a specific WebSocket client.

        Returns True if sent successfully, False if connection is closed.
        """
        try:
            await websocket.send_json({"type": event_type, "data": data})
            return True
        except (WebSocketDisconnect, RuntimeError):
            # Connection already closed
            return False


manager = AgentConnectionManager()


def serialize_message_history(messages: list[Any]) -> list[dict[str, str]]:
    """Convert persisted conversation messages to agent history format."""
    history: list[dict[str, str]] = []

    for message in messages:
        if message.role in {"user", "assistant", "system"}:
            history.append({"role": message.role, "content": message.content})

    return history


@router.websocket("/ws/agent")
async def agent_websocket(
    websocket: WebSocket,
    current_user: Annotated[User | None, Depends(get_optional_current_user_ws)],
) -> None:
    """WebSocket endpoint for LangGraph ReAct agent with streaming support.

    Uses LangGraph astream_events() to stream all agent events including:
    - user_prompt: When user input is received
    - model_request_start: When model request begins
    - text_delta: Streaming text from the model
    - tool_call: When a tool is called
    - tool_result: When a tool returns a result
    - final_result: When the final result is ready
    - complete: When processing is complete
    - error: When an error occurs

    Expected input message format:
    {
        "message": "user message here",
        "history": [{"role": "user|assistant|system", "content": "..."}],
        "conversation_id": "optional-uuid-to-continue-existing-conversation"
    }

    Persistence: Set 'conversation_id' to continue an existing conversation.
    If not provided, a new conversation is created. The conversation_id is
    returned in the 'conversation_created' event.
    """

    await manager.connect(websocket)

    # Conversation state per connection
    conversation_history: list[dict[str, str]] = []
    context: AgentContext = {}
    current_conversation_id: str | None = None

    if current_user is not None:
        context = {
            "user_id": str(current_user.id),
            "user_name": current_user.full_name or current_user.email,
            "user_role": current_user.role # Lấy role từ DB (vd: "admin" / "management")
        }

    try:
        while True:
            # Receive user message
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            attachment_ids = data.get("attachment_ids", []) or []
            # Optionally accept history from client (or use server-side tracking)
            if "history" in data:
                conversation_history = data["history"]

            if not user_message and attachment_ids:
                user_message = "Hay doc va tom tat cac tep dinh kem nay."

            if not user_message:
                await manager.send_event(websocket, "error", {"message": "Empty message"})
                continue

            history_for_agent = conversation_history
            user_id = current_user.id if current_user is not None else None
            prompt_attachments = load_prompt_attachments(attachment_ids) if attachment_ids else []
            attachment_note = build_attachment_history_note(attachment_ids) if attachment_ids else None
            persisted_user_message = (
                f"{user_message}\n\n{attachment_note}" if attachment_note else user_message
            )
            assistant = get_agent()
            route = assistant.route_user_input(user_message, prompt_attachments)

            # Handle conversation persistence
            try:
                async with get_db_context() as db:
                    conv_service = get_conversation_service(db)

                    # Get or create conversation
                    requested_conv_id = data.get("conversation_id")
                    if requested_conv_id:
                        current_conversation_id = requested_conv_id
                        conversation = await conv_service.get_conversation(
                            UUID(requested_conv_id),
                            include_messages=True,
                            user_id=user_id,
                        )
                        if current_user is None and conversation.user_id is not None:
                            raise ValueError("Conversation not available")
                        history_for_agent = serialize_message_history(conversation.messages)
                    elif not current_conversation_id:
                        # Create new conversation
                        conv_data = ConversationCreate(
                            title=user_message[:50] if len(user_message) > 50 else user_message,
                            user_id=user_id,
                        )
                        conversation = await conv_service.create_conversation(conv_data)
                        current_conversation_id = str(conversation.id)
                        history_for_agent = []
                        await manager.send_event(
                            websocket,
                            "conversation_created",
                            {"conversation_id": current_conversation_id},
                        )
                    else:
                        conversation = await conv_service.get_conversation(
                            UUID(current_conversation_id),
                            include_messages=True,
                            user_id=user_id,
                        )
                        if current_user is None and conversation.user_id is not None:
                            raise ValueError("Conversation not available")
                        history_for_agent = serialize_message_history(conversation.messages)

                    # Save user message
                    await conv_service.add_message(
                        UUID(current_conversation_id),
                        MessageCreate(
                            role="user",
                            content=persisted_user_message,
                            router_intent=route.intent,
                            router_reason=route.reason,
                        ),
                        user_id=user_id,
                    )
            except Exception as e:
                logger.warning(f"Failed to persist conversation: {e}")
                if "history" in data and isinstance(data["history"], list):
                    history_for_agent = data["history"]
                else:
                    history_for_agent = conversation_history

            await manager.send_event(websocket, "user_prompt", {"content": user_message})

            try:
                final_output = ""
                tool_events: list[Any] = []
                seen_tool_call_ids: set[str] = set()

                await manager.send_event(websocket, "model_request_start", {})

                # Use LangGraph's astream with messages and updates modes
                async for stream_mode, data in assistant.stream(
                    user_message,
                    history=history_for_agent,
                    context=context,
                    attachments=prompt_attachments,
                ):
                    if stream_mode == "messages":
                        chunk, _metadata = data

                        if isinstance(chunk, AIMessageChunk):
                            if chunk.content:
                                text_content = ""
                                if isinstance(chunk.content, str):
                                    text_content = chunk.content
                                elif isinstance(chunk.content, list):
                                    for block in chunk.content:
                                        if isinstance(block, dict) and block.get("type") == "text":
                                            text_content += block.get("text", "")
                                        elif isinstance(block, str):
                                            text_content += block

                                if text_content:
                                    await manager.send_event(
                                        websocket,
                                        "text_delta",
                                        {"content": text_content},
                                    )
                                    final_output += text_content

                            # Handle tool call chunks
                            if chunk.tool_call_chunks:
                                for tc_chunk in chunk.tool_call_chunks:
                                    tc_id = tc_chunk.get("id")
                                    tc_name = tc_chunk.get("name")
                                    if tc_id and tc_name and tc_id not in seen_tool_call_ids:
                                        seen_tool_call_ids.add(tc_id)
                                        await manager.send_event(
                                            websocket,
                                            "tool_call",
                                            {
                                                "tool_name": tc_name,
                                                "args": {},
                                                "tool_call_id": tc_id,
                                            },
                                        )

                    elif stream_mode == "updates":
                        # Handle state updates from nodes
                        for node_name, update in data.items():
                            if node_name == "tools":
                                # Tool node completed - extract tool results
                                for msg in update.get("messages", []):
                                    if isinstance(msg, ToolMessage):
                                        await manager.send_event(
                                            websocket,
                                            "tool_result",
                                            {
                                                "tool_call_id": msg.tool_call_id,
                                                "content": msg.content,
                                            },
                                        )
                            elif node_name == "agent":
                                # Agent node completed - check for tool calls
                                for msg in update.get("messages", []):
                                    if isinstance(msg, AIMessage) and msg.tool_calls:
                                        for tc in msg.tool_calls:
                                            tc_id = tc.get("id", "")
                                            if tc_id not in seen_tool_call_ids:
                                                seen_tool_call_ids.add(tc_id)
                                                tool_events.append(tc)
                                                await manager.send_event(
                                                    websocket,
                                                    "tool_call",
                                                    {
                                                        "tool_name": tc.get("name", ""),
                                                        "args": tc.get("args", {}),
                                                        "tool_call_id": tc_id,
                                                    },
                                                )

                await manager.send_event(
                    websocket,
                    "final_result",
                    {"output": final_output},
                )

                # Update conversation history
                conversation_history = [
                    *history_for_agent,
                    {"role": "user", "content": persisted_user_message},
                ]
                if final_output:
                    conversation_history.append({"role": "assistant", "content": final_output})

                # Save assistant response to database
                if current_conversation_id and final_output:
                    try:
                        async with get_db_context() as db:
                            conv_service = get_conversation_service(db)
                            saved_message = await conv_service.add_message(
                                UUID(current_conversation_id),
                                MessageCreate(
                                    role="assistant",
                                    content=final_output,
                                    model_name=assistant.model_name
                                    if hasattr(assistant, "model_name")
                                    else None,
                                    router_intent=route.intent,
                                    router_reason=route.reason,
                                ),
                                user_id=user_id,
                            )
                            await manager.send_event(
                                websocket,
                                "assistant_message_saved",
                                {
                                    "message_id": str(saved_message.id),
                                    "conversation_id": current_conversation_id,
                                },
                            )
                    except Exception as e:
                        logger.warning(f"Failed to persist assistant response: {e}")

                await manager.send_event(
                    websocket,
                    "complete",
                    {
                        "conversation_id": current_conversation_id,
                    },
                )

            except WebSocketDisconnect:
                # Client disconnected during processing - this is normal
                logger.info("Client disconnected during agent processing")
                break
            except Exception as e:
                logger.exception(f"Error processing agent request: {e}")
                # Try to send error, but don't fail if connection is closed
                await manager.send_event(websocket, "error", {"message": str(e)})

    except WebSocketDisconnect:
        pass  # Normal disconnect
    finally:
        manager.disconnect(websocket)
