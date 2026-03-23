"use client";

import { useState } from "react";
import { ThumbsDown, ThumbsUp } from "lucide-react";

import { apiClient, ApiError } from "@/lib/api-client";
import { Button } from "@/components/ui";
import type { MessageFeedback, MessageFeedbackRequest } from "@/types";

interface MessageFeedbackProps {
  messageId: string;
  helpful?: boolean | null;
  onChange?: (helpful: boolean) => void;
}

export function MessageFeedback({
  messageId,
  helpful = null,
  onChange,
}: MessageFeedbackProps) {
  const [selectedHelpful, setSelectedHelpful] = useState<boolean | null>(helpful);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submitFeedback = async (nextHelpful: boolean) => {
    if (isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const payload: MessageFeedbackRequest = {
        message_id: messageId,
        helpful: nextHelpful,
      };
      await apiClient.post<MessageFeedback>("/feedback", payload);
      setSelectedHelpful(nextHelpful);
      onChange?.(nextHelpful);
    } catch (submitError) {
      const message =
        submitError instanceof ApiError
          ? submitError.message
          : "Không thể lưu đánh giá lúc này";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1">
        <span className="text-xs text-muted-foreground">Đánh giá phản hồi:</span>
        <Button
          type="button"
          variant={selectedHelpful === true ? "default" : "ghost"}
          size="sm"
          className="h-7 px-2 text-xs"
          onClick={() => submitFeedback(true)}
          disabled={isSubmitting}
        >
          <ThumbsUp className="h-3.5 w-3.5" />
          Hữu ích
        </Button>
        <Button
          type="button"
          variant={selectedHelpful === false ? "destructive" : "ghost"}
          size="sm"
          className="h-7 px-2 text-xs"
          onClick={() => submitFeedback(false)}
          disabled={isSubmitting}
        >
          <ThumbsDown className="h-3.5 w-3.5" />
          Chưa đúng
        </Button>
      </div>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

