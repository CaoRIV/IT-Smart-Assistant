import logging
from typing import Annotated, Literal, TypedDict
from pydantic import SecretStr
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import settings
from app.agents.prompts import MANAGEMENT_SUPERVISOR_PROMPT
from app.agents.tools.management_tools import (
    summarize_meeting_minutes, 
    compare_legal_regulations, 
    get_student_and_lecturer_insights
)
# Có thể import thêm tool của sinh viên nếu cần cho Supervisor tự dùng
from app.agents.tools.student_knowledge import search_student_knowledge

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# Gắn tools cho Supervisor
MANAGEMENT_TOOLS = [
    summarize_meeting_minutes, 
    compare_legal_regulations, 
    get_student_and_lecturer_insights,
    search_student_knowledge # Để supervisor tra cứu giùm nếu cần
]

class ManagementSupervisor:
    def __init__(self):
        self.model = ChatOpenAI(
            model=settings.AI_MODEL,
            temperature=0.2, # Để temperature thấp cho tính chính xác
            api_key=SecretStr(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None,
            streaming=True
        )
        self.model_with_tools = self.model.bind_tools(MANAGEMENT_TOOLS)
        self._graph = None
        self._checkpointer = MemorySaver()

    def _agent_node(self, state: AgentState) -> dict[str, list[BaseMessage]]:
        messages = [SystemMessage(content=MANAGEMENT_SUPERVISOR_PROMPT)] + state["messages"]
        response = self.model_with_tools.invoke(messages)
        return {"messages": [response]}

    def _tools_node(self, state: AgentState) -> dict[str, list[BaseMessage]]:
        from langchain_core.messages import ToolMessage
        last_message = state["messages"][-1]
        tool_results = []
        
        # Dictionary mapping tool names to functions
        tool_map = {t.name: t for t in MANAGEMENT_TOOLS}
        
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            for call in last_message.tool_calls:
                tool_name = call["name"]
                tool_args = call["args"]
                
                if tool_name in tool_map:
                    try:
                        result = tool_map[tool_name].invoke(tool_args)
                        tool_results.append(ToolMessage(content=str(result), tool_call_id=call["id"], name=tool_name))
                    except Exception as e:
                        tool_results.append(ToolMessage(content=f"Error: {e}", tool_call_id=call["id"], name=tool_name))
        
        return {"messages": tool_results}

    def _should_continue(self, state: AgentState) -> Literal["tools", "__end__"]:
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        return "__end__"

    def build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("supervisor", self._agent_node)
        workflow.add_node("tools", self._tools_node)
        
        workflow.add_edge(START, "supervisor")
        workflow.add_conditional_edges("supervisor", self._should_continue, {"tools": "tools", "__end__": END})
        workflow.add_edge("tools", "supervisor")
        
        return workflow.compile(checkpointer=self._checkpointer)

    @property
    def graph(self):
        if not self._graph:
            self._graph = self.build_graph()
        return self._graph

def get_management_agent() -> ManagementSupervisor:
    return ManagementSupervisor()