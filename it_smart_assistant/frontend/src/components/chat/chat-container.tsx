"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useChat, useConversations, useLocalChat } from "@/hooks";
import { MessageList } from "./message-list";
import { ChatInput } from "./chat-input";
import { Button } from "@/components/ui";
import type { ChatAttachment, ChatMessage } from "@/types";
import {
  Bot,
  Loader2,
  Paperclip,
  RotateCcw,
  Wifi,
  WifiOff,
} from "lucide-react";
import { useConversationStore, useChatStore, useAuthStore, useFormPanelStore } from "@/stores";
import { FormSidePanel } from "./form-side-panel";

interface ChatContainerProps {
  useLocalStorage?: boolean;
}

export function ChatContainer({ useLocalStorage = false }: ChatContainerProps) {
  const { isAuthenticated } = useAuthStore();

  const shouldUseLocal = useLocalStorage || !isAuthenticated;

  if (shouldUseLocal) {
    return <LocalChatContainer />;
  }

  return <AuthenticatedChatContainer />;
}

function AuthenticatedChatContainer() {
  const { currentConversationId, currentMessages } = useConversationStore();
  const { addMessage: addChatMessage } = useChatStore();
  const { fetchConversations } = useConversations();
  const prevConversationIdRef = useRef<string | null | undefined>(undefined);

  const handleConversationCreated = useCallback(() => {
    fetchConversations();
  }, [fetchConversations]);

  const { messages, isConnected, isProcessing, connect, disconnect, sendMessage, clearMessages } =
    useChat({
      conversationId: currentConversationId,
      onConversationCreated: handleConversationCreated,
    });

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prevId = prevConversationIdRef.current;
    const currId = currentConversationId;

    if (prevId === undefined) {
      prevConversationIdRef.current = currId;
      return;
    }

    const shouldClear = currId === null || (prevId !== null && prevId !== currId);

    if (shouldClear) {
      clearMessages();
    }

    prevConversationIdRef.current = currId;
  }, [currentConversationId, clearMessages]);

  useEffect(() => {
    if (currentMessages.length > 0) {
      currentMessages.forEach((msg) => {
        addChatMessage({
          id: msg.id,
          backendMessageId: msg.id,
          role: msg.role,
          content: msg.content,
          timestamp: new Date(msg.created_at),
          feedbackHelpful: null,
          toolCalls: msg.tool_calls?.map((tc) => ({
            id: tc.tool_call_id,
            name: tc.tool_name,
            args: tc.args,
            result: tc.result,
            status: tc.status === "failed" ? "error" : tc.status,
          })),
        });
      });
    }
  }, [currentMessages, addChatMessage]);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: isProcessing ? "auto" : "smooth" });
  }, [messages, isProcessing]);

  return (
    <ChatUI
      messages={messages}
      isConnected={isConnected}
      isProcessing={isProcessing}
      sendMessage={sendMessage}
      clearMessages={clearMessages}
      messagesEndRef={messagesEndRef}
    />
  );
}

function LocalChatContainer() {
  const { messages, isConnected, isProcessing, connect, disconnect, sendMessage, clearMessages } =
    useLocalChat();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: isProcessing ? "auto" : "smooth" });
  }, [messages, isProcessing]);

  return (
    <ChatUI
      messages={messages}
      isConnected={isConnected}
      isProcessing={isProcessing}
      sendMessage={sendMessage}
      clearMessages={clearMessages}
      messagesEndRef={messagesEndRef}
    />
  );
}

interface ChatUIProps {
  messages: ChatMessage[];
  isConnected: boolean;
  isProcessing: boolean;
  sendMessage: (content: string, attachments?: ChatAttachment[]) => void;
  clearMessages: () => void;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
}

async function uploadChatAttachment(file: File): Promise<ChatAttachment> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/api/chat-attachments/upload", {
    method: "POST",
    body: formData,
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload?.detail || "Không thể tải tệp đính kèm lên");
  }

  return payload as ChatAttachment;
}

function ChatUI({
  messages,
  isConnected,
  isProcessing,
  sendMessage,
  clearMessages,
  messagesEndRef,
}: ChatUIProps) {
  const { isOpen, formData, closePanel } = useFormPanelStore();
  const [pendingAttachments, setPendingAttachments] = useState<ChatAttachment[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSendMessage = useCallback(
    (content: string) => {
      sendMessage(content, pendingAttachments);
      setPendingAttachments([]);
      setUploadError(null);
    },
    [pendingAttachments, sendMessage]
  );

  const handleAttachmentSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    if (files.length === 0) {
      return;
    }

    setIsUploading(true);
    setUploadError(null);

    try {
      const uploadedAttachments = await Promise.all(files.map((file) => uploadChatAttachment(file)));
      setPendingAttachments((current) => [...current, ...uploadedAttachments]);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Không thể tải tệp đính kèm lên");
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  };

  const handleRemoveAttachment = (attachmentId: string) => {
    setPendingAttachments((current) =>
      current.filter((attachment) => attachment.id !== attachmentId)
    );
  };

  return (
    <div className="flex flex-row h-full w-full overflow-hidden">
      <div className="flex flex-col flex-1 h-full min-w-0 transition-all duration-300">
        <div className="flex flex-col h-full max-w-4xl mx-auto w-full">
          <div className="flex-1 overflow-y-auto px-2 py-4 sm:px-4 sm:py-6 scrollbar-thin">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-4">
                <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-full bg-secondary flex items-center justify-center">
                  <Bot className="h-7 w-7 sm:h-8 sm:w-8" />
                </div>
                <div className="text-center px-4">
                  <p className="text-base sm:text-lg font-medium text-foreground">IT - Smart - UTC</p>
                  <p className="text-sm">Bắt đầu cuộc trò chuyện để nhận hỗ trợ.</p>
                </div>
              </div>
            ) : (
              <MessageList messages={messages} />
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="px-2 pb-2 sm:px-4 sm:pb-4">
            <div className="rounded-xl border bg-card shadow-sm p-3 sm:p-4">
              <ChatInput
                onSend={handleSendMessage}
                disabled={!isConnected || isProcessing || isUploading}
                isProcessing={isProcessing || isUploading}
                pendingAttachments={pendingAttachments}
                onRemoveAttachment={handleRemoveAttachment}
              />

              {uploadError && (
                <p className="mt-3 text-xs text-destructive">{uploadError}</p>
              )}

              <div className="mt-3 flex items-center justify-between border-t pt-3">
                <div className="flex items-center gap-2">
                  {isConnected ? (
                    <Wifi className="h-3.5 w-3.5 text-green-500" />
                  ) : (
                    <WifiOff className="h-3.5 w-3.5 text-red-500" />
                  )}
                  <span className="text-xs text-muted-foreground">
                    {isConnected ? "Đã kết nối" : "Mất kết nối"}
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-8 px-2 text-xs"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploading || isProcessing}
                  >
                    {isUploading ? (
                      <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Paperclip className="mr-1.5 h-3.5 w-3.5" />
                    )}
                    Gửi tệp/ảnh
                  </Button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.txt,.md,.csv,.json,.png,.jpg,.jpeg,.webp"
                    multiple
                    className="hidden"
                    onChange={handleAttachmentSelect}
                  />
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearMessages}
                  className="text-xs h-8 px-3"
                >
                  <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
                  Làm mới
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
      <FormSidePanel isOpen={isOpen} onClose={closePanel} formData={formData} />
    </div>
  );
}
