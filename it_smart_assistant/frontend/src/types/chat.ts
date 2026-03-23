/**
 * Chat and AI Agent types.
 */

export type MessageRole = "user" | "assistant" | "system";

export interface ChatAttachment {
  id: string;
  file_name: string;
  media_type: string;
  kind: "document" | "image";
  size_bytes: number;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  backendMessageId?: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  attachments?: ChatAttachment[];
  toolCalls?: ToolCall[];
  isStreaming?: boolean;
  feedbackHelpful?: boolean | null;
  /** Group ID for related messages (e.g., CrewAI agent chain) */
  groupId?: string;
}

export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result?: unknown;
  status: "pending" | "running" | "completed" | "error";
}

// WebSocket event types from backend
export type WSEventType =
  // PydanticAI / LangChain / LangGraph events
  | "user_prompt"
  | "user_prompt_processed"
  | "model_request_start"
  | "part_start"
  | "text_delta"
  | "tool_call_delta"
  | "call_tools_start"
  | "tool_call"
  | "tool_result"
  | "final_result_start"
  | "final_result"
  | "complete"
  | "error"
  | "conversation_created"
  | "assistant_message_saved"
  | "message_saved"
  // CrewAI-specific events
  | "crew_start"
  | "crew_started"
  | "crew_complete"
  | "agent_started"
  | "agent_completed"
  | "task_started"
  | "task_completed"
  | "tool_started"
  | "tool_finished"
  | "llm_started"
  | "llm_completed";

export interface WSEvent {
  type: WSEventType;
  data?: unknown;
  timestamp?: string;
}

export interface TextDeltaEvent {
  type: "text_delta";
  data: {
    content: string;
  };
}

export interface ToolCallEvent {
  type: "tool_call";
  data: {
    tool_name: string;
    args: Record<string, unknown>;
    tool_call_id: string;
  };
}

export interface ToolResultEvent {
  type: "tool_result";
  data: {
    tool_call_id: string;
    content: unknown;
  };
}

export interface FinalResultEvent {
  type: "final_result";
  data: {
    output: string;
    tool_events: ToolCall[];
  };
}

export interface ChatState {
  messages: ChatMessage[];
  isConnected: boolean;
  isProcessing: boolean;
}
