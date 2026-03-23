"use client";

import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types";
import { ToolCallCard } from "./tool-call-card";
import { MarkdownContent } from "./markdown-content";
import { CopyButton } from "./copy-button";
import { MessageFeedback } from "./message-feedback";
import { FileText, ImageIcon, User, Bot } from "lucide-react";

interface MessageItemProps {
  message: ChatMessage;
  groupPosition?: "first" | "middle" | "last" | "single";
}

export function MessageItem({ message, groupPosition }: MessageItemProps) {
  const isUser = message.role === "user";
  const isGrouped = groupPosition && groupPosition !== "single";

  return (
    <div
      className={cn(
        "group flex gap-2 sm:gap-4 relative overflow-visible",
        isGrouped ? "py-2 sm:py-3" : "py-3 sm:py-4",
        isUser && "flex-row-reverse"
      )}
    >
      {isGrouped && !isUser && (
        <div
          className="absolute left-[15px] sm:left-[17px] w-0.5 bg-orange-500/40"
          style={
            groupPosition === "first"
              ? { top: "24px", bottom: "0" }
              : groupPosition === "last"
                ? { top: "0", height: "24px" }
                : { top: "0", bottom: "0" }
          }
        />
      )}

      <div
        className={cn(
          "flex-shrink-0 w-8 h-8 sm:w-9 sm:h-9 rounded-full flex items-center justify-center z-10",
          isUser ? "bg-primary text-primary-foreground" : "bg-orange-500/10 text-orange-500",
          isGrouped && !isUser && "ring-2 ring-background"
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4 sm:h-5 sm:w-5" />}
      </div>

      <div
        className={cn(
          "flex-1 space-y-2 overflow-hidden max-w-[88%] sm:max-w-[85%]",
          isUser && "flex flex-col items-end"
        )}
      >
        {message.attachments && message.attachments.length > 0 && (
          <div className="flex w-full flex-wrap gap-2">
            {message.attachments.map((attachment) => (
              <div
                key={attachment.id}
                className="inline-flex items-center gap-2 rounded-full border bg-background px-3 py-1 text-xs text-muted-foreground"
              >
                {attachment.kind === "image" ? (
                  <ImageIcon className="h-3.5 w-3.5" />
                ) : (
                  <FileText className="h-3.5 w-3.5" />
                )}
                <span className="max-w-52 truncate">{attachment.file_name}</span>
              </div>
            ))}
          </div>
        )}

        {(message.content || (message.isStreaming && (!message.toolCalls || message.toolCalls.length === 0))) && (
          <div
            className={cn(
              "relative rounded-2xl px-3 py-2 sm:px-4 sm:py-2.5",
              isUser
                ? "bg-primary text-primary-foreground rounded-tr-sm"
                : "bg-muted rounded-tl-sm"
            )}
          >
            {isUser ? (
              <p className="whitespace-pre-wrap break-words text-sm">{message.content}</p>
            ) : (
              <div className="text-sm prose-sm max-w-none">
                <MarkdownContent content={message.content} />
                {message.isStreaming && (
                  <span className="inline-block w-1.5 h-4 ml-1 bg-current animate-pulse rounded-full" />
                )}
              </div>
            )}

            {!isUser && message.content && !message.isStreaming && (
              <div className="absolute -right-1 -top-1 sm:opacity-0 sm:group-hover:opacity-100">
                <CopyButton
                  text={message.content}
                  className="bg-background/80 hover:bg-background shadow-sm"
                />
              </div>
            )}
          </div>
        )}

        {!isUser && !message.isStreaming && message.backendMessageId && (
          <MessageFeedback
            messageId={message.backendMessageId}
            helpful={message.feedbackHelpful}
          />
        )}

        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="space-y-2 w-full">
            {message.toolCalls.map((toolCall) => (
              <ToolCallCard key={toolCall.id} toolCall={toolCall} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
