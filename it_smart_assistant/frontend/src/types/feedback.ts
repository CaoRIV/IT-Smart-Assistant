export interface MessageFeedbackRequest {
  message_id: string;
  helpful: boolean;
  comment?: string | null;
}

export interface MessageFeedback {
  id: string;
  message_id: string;
  user_id: string;
  helpful: boolean;
  comment?: string | null;
  created_at: string;
  updated_at?: string | null;
}
