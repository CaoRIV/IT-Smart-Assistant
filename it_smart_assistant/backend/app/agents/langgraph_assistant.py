"""LangGraph ReAct Agent implementation.

A simple ReAct (Reasoning + Acting) agent built with LangGraph.
Uses a graph-based architecture with conditional edges for tool execution.
"""

import json
import logging
from typing import Annotated, Any, Literal, TypedDict
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.agents.intent_router import IntentRoute, route_human_message, route_human_message_async
from app.agents.prompts import DEFAULT_SYSTEM_PROMPT, LECTURER_SYSTEM_PROMPT
from app.agents.tools.course_catalog import search_course_catalog
from app.agents.tools.form_generator import generate_form
from app.agents.tools.procedure_workflow import build_procedure_workflow
from app.agents.tools.student_knowledge import search_student_knowledge
from app.agents.tools.lecturer_knowledge import search_lecturer_knowledge_base
from app.agents.tools.evaluate_course_regulation import search_course_evaluation_rules
from app.agents.tools.lecture_knowledge import search_lecture_knowledge
from app.agents.tools.search_lecture_tool import search_lecture
from app.agents.tools.solve_exercise_tool import solve_with_style
from app.agents.tools import get_current_datetime
from app.core.config import settings
from app.schemas.chat_attachment import PromptAttachment
from app.agents.management_supervisor import get_management_agent

from app.agents.guardrails import check_image_quality
from app.services.conversation_state import ConversationStateManager, get_state_manager
from app.services.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


class AgentContext(TypedDict, total=False):
    """Runtime context for the agent.

    Passed via config parameter to the graph.
    """

    user_id: str | None
    user_name: str | None
    user_role: str | None
    metadata: dict[str, Any]
    conversation_id: str | None
    bypass_image_check: bool  # Allow bypass for testing


class AgentAttachment(TypedDict):
    """Attachment payload injected into the current user turn."""

    id: str
    file_name: str
    media_type: str
    kind: str
    extracted_text: str | None
    data_url: str | None


class AgentState(TypedDict):
    """State for the LangGraph agent.

    This is what flows through the agent graph.
    The messages field uses add_messages reducer to properly
    append new messages to the conversation history.
    """

    messages: Annotated[list[BaseMessage], add_messages]


@tool
def current_datetime() -> str:
    """Get the current date and time.

    Use this tool when you need to know the current date or time.
    """
    return get_current_datetime()


# List of all available tools
ALL_TOOLS = [
    current_datetime,
    search_student_knowledge,
    search_course_catalog,
    build_procedure_workflow,
    generate_form,
    search_lecturer_knowledge_base,
    search_course_evaluation_rules,
    search_lecture_knowledge,
    search_lecture,
    solve_with_style,
]

# Create a dictionary for quick tool lookup by name
TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}


def _serialize_tool_result(result: Any) -> str:
    """Serialize tool output as JSON when possible so the frontend can parse it reliably."""
    if isinstance(result, str):
        return result

    try:
        return json.dumps(result, ensure_ascii=False, default=str)
    except TypeError:
        return str(result)


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    pass


class LangGraphAssistant:
    """ReAct agent wrapper using LangGraph.

    Implements a graph-based agent with:
    - An agent node that processes messages and decides actions
    - A tools node that executes tool calls
    - Conditional edges that loop back for tool execution or end

    The ReAct pattern:
    1. Agent receives input and reasons about it
    2. If tool calls are needed, execute them
    3. Tool results are added to messages
    4. Agent reasons again with new information
    5. Repeat until agent provides final response
    """

    def __init__(
        self,
        model_name: str | None = None,
        temperature: float | None = None,
        system_prompt: str | None = None,
        user_role: str = "student",
    ):
        self.model_name = model_name or settings.AI_MODEL
        self.temperature = temperature or settings.AI_TEMPERATURE
        if system_prompt:
            self.system_prompt = system_prompt
        elif user_role == "lecturer":
            self.system_prompt = LECTURER_SYSTEM_PROMPT
        else:
            self.system_prompt = DEFAULT_SYSTEM_PROMPT
        self._graph = None
        self._checkpointer = MemorySaver()

    def _create_model(self):
        """Create the LLM model with tools bound."""
        provider = settings.LLM_PROVIDER.lower()

        if provider == "google":
            if not settings.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY is required when LLM_PROVIDER=google")

            model = ChatGoogleGenerativeAI(
                model=self.model_name,
                temperature=self.temperature,
                google_api_key=settings.GOOGLE_API_KEY,
            )
        elif provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

            model = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                api_key=settings.OPENAI_API_KEY,
                streaming=True,
            )
        else:
            raise ValueError(
                f"Unsupported LLM_PROVIDER: {provider}. "
                "Supported providers are 'google' and 'openai'."
            )

        return model.bind_tools(ALL_TOOLS)

    async def _create_model_with_rate_limit(self, user_id: str | None = None):
        """Create model with rate limit check."""
        if user_id:
            limiter = await get_rate_limiter()
            allowed, info = await limiter.check_rate_limit(user_id)
            if not allowed:
                retry_after = info.get("retry_after_seconds", 60)
                raise RateLimitExceeded(
                    f"Rate limit exceeded. Please try again in {retry_after} seconds."
                )
            # Record the request
            await limiter.record_request(user_id)
        return self._create_model()

    @staticmethod
    def _find_last_human_message(messages: list[BaseMessage]) -> HumanMessage | None:
        """Find the last human message in the conversation."""
        for message in reversed(messages):
            if isinstance(message, HumanMessage):
                return message
        return None

    @staticmethod
    def _parse_tool_payload(content: Any) -> dict[str, Any] | None:
        if isinstance(content, dict):
            return content
        if not isinstance(content, str):
            return None
        try:
            payload = json.loads(content)
        except Exception:
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _tool_names_since_last_human(messages: list[BaseMessage]) -> set[str]:
        names: set[str] = set()
        for message in reversed(messages):
            if isinstance(message, HumanMessage):
                break
            if isinstance(message, ToolMessage) and message.name:
                names.add(message.name)
        return names

    def _fallback_after_tool(self, state: AgentState) -> IntentRoute | None:
        if not state["messages"] or not isinstance(state["messages"][-1], ToolMessage):
            return None

        last_tool_message = state["messages"][-1]
        payload = self._parse_tool_payload(last_tool_message.content)
        last_human = self._find_last_human_message(state["messages"])
        seen_tool_names = self._tool_names_since_last_human(state["messages"])
        if payload is None or last_human is None:
            return None

        last_human_text = self._build_plain_human_text(last_human)
        if not last_human_text:
            return None

        if (
            last_tool_message.name == "search_course_catalog"
            and payload.get("result_count") == 0
            and "search_student_knowledge" not in seen_tool_names
        ):
            return IntentRoute(
                intent="knowledge_qa",
                reason="fallback from empty course catalog retrieval",
                force_tool_calls=[
                    {
                        "id": f"router_fallback_{uuid.uuid4().hex}",
                        "name": "search_student_knowledge",
                        "args": {"query": last_human_text, "top_k": 4},
                        "type": "tool_call",
                    }
                ],
                system_hint="Khong tim thay du lieu mon hoc co cau truc. Thu tim trong knowledge chung de tra loi bo sung.",
            )

        if (
            last_tool_message.name == "build_procedure_workflow"
            and payload.get("matched") is False
            and "search_student_knowledge" not in seen_tool_names
        ):
            return IntentRoute(
                intent="knowledge_qa",
                reason="fallback from unmatched procedure workflow",
                force_tool_calls=[
                    {
                        "id": f"router_fallback_{uuid.uuid4().hex}",
                        "name": "search_student_knowledge",
                        "args": {"query": last_human_text, "top_k": 4},
                        "type": "tool_call",
                    }
                ],
                system_hint="Workflow khong khop. Thu hoi dap bang knowledge base de tranh tra loi bi cut.",
            )

        if (
            last_tool_message.name == "search_student_knowledge"
            and payload.get("result_count") == 0
            and "build_procedure_workflow" not in seen_tool_names
        ):
            route = route_human_message(last_human)
            if route.intent == "tuition_lookup":
                return IntentRoute(
                    intent="knowledge_qa",
                    reason="fallback from empty tuition retrieval",
                    force_tool_calls=[
                        {
                            "id": f"router_fallback_{uuid.uuid4().hex}",
                            "name": "build_procedure_workflow",
                            "args": {"request": last_human_text},
                            "type": "tool_call",
                        }
                    ],
                    system_hint="Knowledge retrieval rong. Thu kiem tra xem day co phai cau hoi thu tuc hay khong.",
                )

        return None

    @staticmethod
    def _build_plain_human_text(message: HumanMessage) -> str:
        content = message.content
        if isinstance(content, str):
            return content

        parts: list[str] = []
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text")
                    if isinstance(text, str):
                        parts.append(text)
                elif isinstance(block, str):
                    parts.append(block)
        return "\n".join(parts).strip()

    def route_user_input(
        self,
        user_input: str,
        attachments: list[PromptAttachment] | None = None,
    ) -> IntentRoute:
        return route_human_message(self._build_user_message(user_input, attachments))

    async def _agent_node(self, state: AgentState, agent_context: AgentContext | None = None) -> dict[str, list[BaseMessage]]:
        """Agent node that processes messages and decides whether to call tools.

        This is the main reasoning node in the ReAct pattern.
        """
        agent_context = agent_context or {}
        fallback_route = self._fallback_after_tool(state)
        if fallback_route and fallback_route.force_tool_calls:
            logger.info(
                "Intent router fallback forced tool call(s): %s (%s)",
                fallback_route.intent,
                fallback_route.reason,
            )
            return {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=fallback_route.force_tool_calls,
                    )
                ]
            }

        if state["messages"] and isinstance(state["messages"][-1], HumanMessage):
            route = await route_human_message_async(state["messages"][-1])
            if route.force_tool_calls:
                logger.info("Intent router forced tool call(s): %s (%s)", route.intent, route.reason)
                return {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=route.force_tool_calls,
                        )
                    ]
                }

        model = await self._create_model_with_rate_limit(agent_context.get("user_id"))

        # Prepend system message to the conversation
        system_prompt = self.system_prompt
        route_hint: IntentRoute | None = None
        if state["messages"] and isinstance(state["messages"][-1], HumanMessage):
            route_hint = await route_human_message_async(state["messages"][-1])
        elif fallback_route:
            route_hint = fallback_route
        if route_hint and route_hint.system_hint:
            system_prompt = f"{self.system_prompt}\n\nRouter hint:\n{route_hint.system_hint}"

        messages = [SystemMessage(content=system_prompt), *state["messages"]]

        response = model.invoke(messages)

        logger.info(
            f"Agent processed message - Tool calls: {len(response.tool_calls) if hasattr(response, 'tool_calls') else 0}"
        )

        return {"messages": [response]}

    def _tools_node(self, state: AgentState) -> dict[str, list[ToolMessage]]:
        """Tools node that executes tool calls from the agent.

        Processes each tool call and returns results as ToolMessages.
        """
        messages = state["messages"]
        last_message = messages[-1]

        tool_results = []

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]

                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                try:
                    tool_fn = TOOLS_BY_NAME.get(tool_name)
                    if tool_fn:
                        result = tool_fn.invoke(tool_args)
                        tool_results.append(
                            ToolMessage(
                                content=_serialize_tool_result(result),
                                tool_call_id=tool_id,
                                name=tool_name,
                            )
                        )
                        logger.info(f"Tool {tool_name} completed successfully")
                    else:
                        error_msg = f"Unknown tool: {tool_name}"
                        logger.error(error_msg)
                        tool_results.append(
                            ToolMessage(
                                content=error_msg,
                                tool_call_id=tool_id,
                                name=tool_name,
                            )
                        )
                except Exception as e:
                    error_msg = f"Error executing {tool_name}: {e!s}"
                    logger.error(error_msg, exc_info=True)
                    tool_results.append(
                        ToolMessage(
                            content=error_msg,
                            tool_call_id=tool_id,
                            name=tool_name,
                        )
                    )

        return {"messages": tool_results}

    def _should_continue(self, state: AgentState) -> Literal["tools", "__end__"]:
        """Conditional edge that decides whether to continue to tools or end.

        Returns:
            - "tools" if the agent made tool calls (needs to execute tools)
            - "__end__" if the agent provided a final response (no tool calls)
        """
        messages = state["messages"]
        last_message = messages[-1]

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            logger.info(f"Continuing to tools - {len(last_message.tool_calls)} tool(s) to execute")
            return "tools"

        logger.info("No tool calls - ending conversation")
        return "__end__"

    def _build_graph(self) -> StateGraph:
        """Build and compile the LangGraph state graph."""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", self._tools_node)

        # Add edges
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {"tools": "tools", "__end__": END},
        )
        workflow.add_edge("tools", "agent")

        return workflow.compile(checkpointer=self._checkpointer)

    @property
    def graph(self):
        """Get or create the compiled graph instance."""
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph

    @staticmethod
    def _convert_history(
        history: list[dict[str, str]] | None,
    ) -> list[HumanMessage | AIMessage | SystemMessage]:
        """Convert conversation history to LangChain message format."""
        messages: list[HumanMessage | AIMessage | SystemMessage] = []

        for msg in history or []:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
            elif msg["role"] == "system":
                messages.append(SystemMessage(content=msg["content"]))

        return messages

    @staticmethod
    def _build_user_message(
        user_input: str,
        attachments: list[PromptAttachment] | None = None,
        skip_image_check: bool = False,
    ) -> HumanMessage:
        """Build the current user message, enriching it with attachment context."""
        if not attachments:
            return HumanMessage(content=user_input)

        document_sections: list[str] = []
        image_attachments: list[PromptAttachment] = []
        failed_image_checks: list[str] = []

        for attachment in attachments:
            if attachment.kind == "image" and attachment.data_url:
                # Check image quality if not skipped
                if not skip_image_check:
                    quality_result = check_image_quality(attachment.data_url)
                    if not quality_result.is_acceptable:
                        failed_image_checks.append(quality_result.suggestion or "Ảnh không đạt yêu cầu")
                        continue  # Skip this image
                image_attachments.append(attachment)
                continue

            if attachment.extracted_text:
                document_sections.append(
                    f"Tep dinh kem: {attachment.file_name}\n{attachment.extracted_text}"
                )
            else:
                document_sections.append(
                    f"Tep dinh kem: {attachment.file_name}\nKhong trich xuat duoc noi dung van ban."
                )

        # If any images failed quality check, return warning message
        if failed_image_checks:
            error_msg = "\n\n".join(failed_image_checks)
            return HumanMessage(content=f"[LỖI ẢNH] {error_msg}")

        if not image_attachments:
            prompt_parts = [user_input]
            if document_sections:
                prompt_parts.append(
                    "Day la noi dung duoc trich tu tep dinh kem cua nguoi dung:\n\n"
                    + "\n\n".join(document_sections)
                )
            return HumanMessage(content="\n\n".join(prompt_parts).strip())

        text_parts = [user_input]
        if document_sections:
            text_parts.append(
                "Day la noi dung duoc trich tu tep dinh kem cua nguoi dung:\n\n"
                + "\n\n".join(document_sections)
            )
        text_parts.append("Nguoi dung cung gui kem anh de ban phan tich.")

        content_blocks: list[dict[str, Any]] = [{"type": "text", "text": "\n\n".join(text_parts)}]
        for attachment in image_attachments:
            content_blocks.append(
                {
                    "type": "image_url",
                    "image_url": {"url": attachment.data_url},
                }
            )

        return HumanMessage(content=content_blocks)

    async def run(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        context: AgentContext | None = None,
        thread_id: str = "default",
        attachments: list[PromptAttachment] | None = None,
        conversation_id: str | None = None,
    ) -> tuple[str, list[Any], AgentContext]:
        """Run agent and return the output along with tool call events.

        Args:
            user_input: User's message.
            history: Conversation history as list of {"role": "...", "content": "..."}.
            context: Optional runtime context with user info.
            thread_id: Thread ID for conversation continuity.
            conversation_id: Optional conversation ID for Redis state management.

        Returns:
            Tuple of (output_text, tool_events, context).
        """
        agent_context: AgentContext = context if context is not None else {}
        if conversation_id:
            agent_context["conversation_id"] = conversation_id

        # Load state from Redis if conversation_id provided
        if conversation_id:
            try:
                state_mgr = await get_state_manager()
                state = await state_mgr.get_full_state(conversation_id)

                # Restore subject if available
                if state.get("subject") and not agent_context.get("subject"):
                    agent_context["subject"] = state["subject"]

                # Restore extracted text for "giải lại" scenarios
                if state.get("extracted_text") and not attachments:
                    # User might be asking about previous image
                    user_input = f"[Nội dung ảnh trước đó: {state['extracted_text']}]\n\n{user_input}"
            except Exception as e:
                logger.warning(f"Failed to load conversation state: {e}")

        # Check image quality
        skip_image_check = agent_context.get("bypass_image_check", False)
        messages = self._convert_history(history)
        user_message = self._build_user_message(user_input, attachments, skip_image_check)

        # Handle image quality error
        if user_message.content and isinstance(user_message.content, str) and user_message.content.startswith("[LỖI ẢNH]"):
            return user_message.content.replace("[LỖI ẢNH] ", ""), [], agent_context

        messages.append(user_message)

        logger.info(f"Running agent with user input: {user_input[:100]}...")

        config = {
            "configurable": {
                "thread_id": thread_id,
                **agent_context,
            }
        }

        result = await self.graph.ainvoke({"messages": messages}, config=config)

        # Extract the final response and tool events
        output = ""
        tool_events: list[Any] = []

        for message in result.get("messages", []):
            if isinstance(message, AIMessage):
                if message.content:
                    output = (
                        message.content
                        if isinstance(message.content, str)
                        else str(message.content)
                    )
                if hasattr(message, "tool_calls") and message.tool_calls:
                    tool_events.extend(message.tool_calls)

        # Save state to Redis if conversation_id provided
        if conversation_id and output:
            try:
                state_mgr = await get_state_manager()
                await state_mgr.save_history(conversation_id, history_for_redis)

                # Save subject if detected in route
                if route and hasattr(route, 'intent'):
                    if route.intent in ['exercise_solving', 'lecture_qa']:
                        # Extract subject from output or input
                        subject = self._extract_subject(output, user_input)
                        if subject:
                            await state_mgr.save_subject(conversation_id, subject)

                # Save extracted text from attachments
                if attachments:
                    for att in attachments:
                        if att.extracted_text:
                            await state_mgr.save_extracted_text(
                                conversation_id,
                                att.extracted_text,
                                att.id
                            )
            except Exception as e:
                logger.warning(f"Failed to save conversation state: {e}")

        logger.info(f"Agent run complete. Output length: {len(output)} chars")

        return output, tool_events, agent_context

    def _extract_subject(self, output: str, user_input: str) -> str | None:
        """Extract subject from output or input."""
        # Simple heuristic - can be improved
        subjects = ['toán', 'lý', 'hóa', 'lập trình', 'cơ sở dữ liệu', 'mạng máy tính']
        text = (user_input + ' ' + output).lower()
        for subj in subjects:
            if subj in text:
                return subj
        return None

    async def stream(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        context: AgentContext | None = None,
        thread_id: str = "default",
        attachments: list[PromptAttachment] | None = None,
    ):
        """Stream agent execution with message and state update streaming.

        Args:
            user_input: User's message.
            history: Conversation history.
            context: Optional runtime context.
            thread_id: Thread ID for conversation continuity.

        Yields:
            Tuples of (stream_mode, data) for streaming responses.
            - stream_mode="messages": (chunk, metadata) for LLM tokens
            - stream_mode="updates": state updates after each node
        """
        messages = self._convert_history(history)
        messages.append(self._build_user_message(user_input, attachments))

        agent_context: AgentContext = context if context is not None else {}

        config = {
            "configurable": {
                "thread_id": thread_id,
                **agent_context,
            }
        }

        logger.info(f"Starting stream for user input: {user_input[:100]}...")

        async for stream_mode, data in self.graph.astream(
            {"messages": messages},
            config=config,
            stream_mode=["messages", "updates"],
        ):
            yield stream_mode, data


def get_agent(user_role: str = "student") -> LangGraphAssistant:
    """Factory function to create a LangGraphAssistant or ManagementSupervisor."""
    if user_role == "admin" or user_role == "management":
        return get_management_agent()
    # Default trả về agent sinh viên/giảng viên thông thường
    return LangGraphAssistant(user_role=user_role)


async def run_agent(
    user_input: str,
    history: list[dict[str, str]],
    context: AgentContext | None = None,
    thread_id: str = "default",
) -> tuple[str, list[Any], AgentContext]:
    """Run agent and return the output along with tool call events.

    This is a convenience function for backwards compatibility.

    Args:
        user_input: User's message.
        history: Conversation history.
        context: Optional runtime context.
        thread_id: Thread ID for conversation continuity.

    Returns:
        Tuple of (output_text, tool_events, context).
    """
    user_role = context.get("user_role", "student") if context else "student"
    agent = get_agent(user_role=user_role)
    return await agent.run(user_input, history, context, thread_id)
