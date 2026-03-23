export interface AnalyticsCountItem {
  label: string;
  count: number;
}

export interface AnalyticsIntentQualityItem {
  label: string;
  total_feedback: number;
  helpful_feedback: number;
  unhelpful_feedback: number;
  helpful_rate: number;
}

export interface AnalyticsOverview {
  total_conversations: number;
  total_messages: number;
  assistant_messages: number;
  total_feedback: number;
  helpful_feedback: number;
  unhelpful_feedback: number;
  helpful_rate: number;
  forms_opened: number;
  procedure_workflows: number;
  top_intents: AnalyticsCountItem[];
  weakest_intents: AnalyticsIntentQualityItem[];
  top_questions: AnalyticsCountItem[];
  top_tools: AnalyticsCountItem[];
  top_procedures: AnalyticsCountItem[];
}
