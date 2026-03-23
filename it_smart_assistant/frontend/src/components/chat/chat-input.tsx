"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui";
import type { ChatAttachment } from "@/types";
import { Loader2, Send, X } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  isProcessing?: boolean;
  pendingAttachments?: ChatAttachment[];
  onRemoveAttachment?: (attachmentId: string) => void;
}

export function ChatInput({
  onSend,
  disabled,
  isProcessing,
  pendingAttachments = [],
  onRemoveAttachment,
}: ChatInputProps) {
  const [message, setMessage] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!isProcessing && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isProcessing]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [message]);

  const canSubmit = Boolean(message.trim() || pendingAttachments.length);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (canSubmit && !disabled) {
      onSend(message.trim());
      setMessage("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative space-y-3">
      {pendingAttachments.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {pendingAttachments.map((attachment) => (
            <div
              key={attachment.id}
              className="inline-flex items-center gap-2 rounded-full border bg-muted px-3 py-1 text-xs"
            >
              <span className="max-w-48 truncate">{attachment.file_name}</span>
              <button
                type="button"
                onClick={() => onRemoveAttachment?.(attachment.id)}
                className="text-muted-foreground transition-colors hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="relative">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Nhập tin nhắn hoặc gửi tệp để trò chuyện..."
          disabled={disabled}
          rows={1}
          className="w-full resize-none bg-transparent pr-14 text-sm sm:text-base placeholder:text-muted-foreground focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
        />
        <Button
          type="submit"
          size="icon"
          disabled={disabled || !canSubmit}
          className="absolute right-0 top-0 h-10 w-10 rounded-lg"
        >
          {isProcessing ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Send className="h-5 w-5" />
          )}
          <span className="sr-only">Gửi tin nhắn</span>
        </Button>
      </div>
    </form>
  );
}
