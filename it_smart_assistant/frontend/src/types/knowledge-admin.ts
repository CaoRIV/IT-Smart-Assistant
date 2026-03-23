/**
 * Knowledge admin types.
 */

export interface KnowledgeDocument {
  id: string;
  title: string;
  category: string;
  file_name: string;
  relative_path: string;
  page_count?: number | null;
  status: string;
  source_office?: string | null;
  issued_date?: string | null;
  effective_date?: string | null;
  version?: string | null;
  source_url?: string | null;
  notes?: string | null;
  workbook_type?: string | null;
  sheet_schema_config?: Record<string, unknown> | null;
  uploaded_at?: string | null;
}

export interface KnowledgeDocumentMetadataUpdateRequest {
  relative_path: string;
  title: string;
  category: string;
  status: string;
  source_office?: string | null;
  issued_date?: string | null;
  effective_date?: string | null;
  version?: string | null;
  source_url?: string | null;
  notes?: string | null;
  workbook_type?: string | null;
  sheet_schema_config?: Record<string, unknown> | null;
}

export interface KnowledgeDocumentBatchMetadataUpdateRequest {
  relative_paths: string[];
  status: string;
  source_office?: string | null;
  issued_date?: string | null;
  effective_date?: string | null;
  version?: string | null;
  notes?: string | null;
  workbook_type?: string | null;
  sheet_schema_config?: Record<string, unknown> | null;
}

export interface KnowledgePreviewChunk {
  chunk_id: string;
  section_title?: string | null;
  summary: string;
  page_from?: number | null;
  page_to?: number | null;
}

export interface KnowledgePreviewTableRow {
  row_id: string;
  label: string;
  amount_text?: string | null;
  page_from?: number | null;
  page_to?: number | null;
}

export interface KnowledgePreviewTable {
  table_id: string;
  title: string;
  page_from?: number | null;
  page_to?: number | null;
  rows: KnowledgePreviewTableRow[];
}

export interface KnowledgeDocumentPreview {
  relative_path: string;
  document_id?: string | null;
  chunk_count: number;
  table_count: number;
  chunks: KnowledgePreviewChunk[];
  tables: KnowledgePreviewTable[];
}

export interface FAQEntry {
  id: string;
  title: string;
  category: string;
  question: string;
  answer: string;
  source_url?: string | null;
  keywords: string[];
  created_at: string;
  updated_at: string;
}

export interface FAQCreateRequest {
  title: string;
  category: string;
  question: string;
  answer: string;
  source_url?: string;
  keywords: string[];
}

export interface FormTemplateField {
  name: string;
  label: string;
  type: string;
  required: boolean;
  placeholder?: string | null;
}

export interface FormTemplate {
  id: string;
  title: string;
  category: string;
  description: string;
  source_url?: string | null;
  keywords: string[];
  fields: FormTemplateField[];
  created_at: string;
  updated_at: string;
}

export interface FormTemplateCreateRequest {
  title: string;
  category: string;
  description: string;
  source_url?: string;
  keywords: string[];
  fields: FormTemplateField[];
}

export interface KnowledgeRebuildResponse {
  success: boolean;
  message?: string | null;
  documents: number;
  chunks: number;
}

export interface KnowledgeAdminOverview {
  total_documents: number;
  status_counts: Record<string, number>;
  normalized_counts: Record<string, number>;
  runtime_counts: Record<string, number>;
}
