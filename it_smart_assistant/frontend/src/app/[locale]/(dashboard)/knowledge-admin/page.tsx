"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Label,
} from "@/components/ui";
import type {
  FAQCreateRequest,
  FAQEntry,
  FormTemplate,
  FormTemplateCreateRequest,
  FormTemplateField,
  KnowledgeAdminOverview,
  KnowledgeDocument,
  KnowledgeDocumentBatchMetadataUpdateRequest,
  KnowledgeDocumentMetadataUpdateRequest,
  KnowledgeDocumentPreview,
} from "@/types";
import { FileText, Loader2, RefreshCw, Save, Table2, Trash2, Upload } from "lucide-react";

const STATUS_OPTIONS = [
  { value: "draft", label: "Bản nháp" },
  { value: "published", label: "Đã phát hành" },
  { value: "needs_review", label: "Cần rà soát" },
  { value: "archived", label: "Lưu trữ" },
] as const;

const WORKBOOK_TYPE_OPTIONS = [
  { value: "", label: "Tự nhận diện" },
  { value: "course_catalog", label: "Chương trình đào tạo" },
  { value: "generic_tabular", label: "Bảng dữ liệu chung" },
] as const;

const EMPTY_DOCUMENT_EDITOR: KnowledgeDocumentMetadataUpdateRequest = {
  relative_path: "",
  title: "",
  category: "",
  status: "draft",
  source_office: "",
  issued_date: "",
  effective_date: "",
  version: "",
  source_url: "",
  notes: "",
  workbook_type: "",
  sheet_schema_config: null,
};

const EMPTY_FAQ_FORM: FAQCreateRequest = {
  title: "",
  category: "",
  question: "",
  answer: "",
  source_url: "",
  keywords: [],
};

const EMPTY_FORM_TEMPLATE: FormTemplateCreateRequest = {
  title: "",
  category: "",
  description: "",
  source_url: "",
  keywords: [],
  fields: [],
};

const EMPTY_FIELD: FormTemplateField = {
  name: "",
  label: "",
  type: "text",
  required: false,
  placeholder: "",
};

function parseKeywordInput(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function serializeKeywordInput(value: string[] | undefined): string {
  return (value ?? []).join(", ");
}

function statusBadgeVariant(status: string) {
  switch (status) {
    case "published":
      return "default";
    case "archived":
      return "secondary";
    case "needs_review":
      return "destructive";
    default:
      return "outline";
  }
}

function formatStatus(status: string) {
  return STATUS_OPTIONS.find((item) => item.value === status)?.label ?? status;
}

function formatWorkbookType(workbookType: string | null | undefined) {
  if (!workbookType) {
    return "";
  }

  return WORKBOOK_TYPE_OPTIONS.find((item) => item.value === workbookType)?.label ?? workbookType;
}

export default function KnowledgeAdminPage() {
  const [overview, setOverview] = useState<KnowledgeAdminOverview | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [faqs, setFaqs] = useState<FAQEntry[]>([]);
  const [forms, setForms] = useState<FormTemplate[]>([]);
  const [selectedDocumentPath, setSelectedDocumentPath] = useState<string>("");
  const [documentEditor, setDocumentEditor] =
    useState<KnowledgeDocumentMetadataUpdateRequest>(EMPTY_DOCUMENT_EDITOR);
  const [documentPreview, setDocumentPreview] = useState<KnowledgeDocumentPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  const [savingMetadata, setSavingMetadata] = useState(false);
  const [batchPublishing, setBatchPublishing] = useState(false);
  const [message, setMessage] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [uploadCategory, setUploadCategory] = useState("hoc-vu");
  const [uploadWorkbookType, setUploadWorkbookType] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [faqForm, setFaqForm] = useState<FAQCreateRequest>(EMPTY_FAQ_FORM);
  const [editingFaqId, setEditingFaqId] = useState<string | null>(null);
  const [faqSubmitting, setFaqSubmitting] = useState(false);
  const [formTemplate, setFormTemplate] = useState<FormTemplateCreateRequest>(EMPTY_FORM_TEMPLATE);
  const [editingFormId, setEditingFormId] = useState<string | null>(null);
  const [formSubmitting, setFormSubmitting] = useState(false);

  const selectedDocument = useMemo(
    () => documents.find((item) => item.relative_path === selectedDocumentPath) ?? null,
    [documents, selectedDocumentPath]
  );
  const tuitionDocumentPaths = useMemo(
    () =>
      documents
        .filter(
          (item) =>
            item.relative_path.includes("/hoc_phi/")
            || item.category.toLowerCase().includes("hoc phi")
        )
        .map((item) => item.relative_path),
    [documents]
  );
  const reviewDocumentPaths = useMemo(
    () => documents.filter((item) => item.status === "needs_review").map((item) => item.relative_path),
    [documents]
  );

  async function loadAll() {
    setPageLoading(true);
    setError("");
    try {
      const [documentsResponse, faqsResponse, formsResponse] = await Promise.all([
        fetch("/api/knowledge-admin/documents", { cache: "no-store" }),
        fetch("/api/knowledge-admin/faqs", { cache: "no-store" }),
        fetch("/api/knowledge-admin/forms", { cache: "no-store" }),
      ]);

      if (!documentsResponse.ok || !faqsResponse.ok || !formsResponse.ok) {
        throw new Error("Không thể tải dữ liệu quản trị tri thức.");
      }

      const [documentsData, faqsData, formsData] = await Promise.all([
        documentsResponse.json(),
        faqsResponse.json(),
        formsResponse.json(),
      ]);

      setDocuments(documentsData);
      setFaqs(faqsData);
      setForms(formsData);
      const overviewResponse = await fetch("/api/knowledge-admin/overview", { cache: "no-store" });
      if (!overviewResponse.ok) {
        throw new Error("Không thể tải tổng quan tri thức.");
      }
      const overviewData = await overviewResponse.json();
      setOverview(overviewData);

      if (selectedDocumentPath) {
        const nextSelected = documentsData.find(
          (item: KnowledgeDocument) => item.relative_path === selectedDocumentPath
        );
        if (nextSelected) {
          hydrateDocumentEditor(nextSelected);
        } else {
          setSelectedDocumentPath("");
          setDocumentEditor(EMPTY_DOCUMENT_EDITOR);
          setDocumentPreview(null);
        }
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Không thể tải dữ liệu.");
    } finally {
      setPageLoading(false);
    }
  }

  function hydrateDocumentEditor(document: KnowledgeDocument) {
    setDocumentEditor({
      relative_path: document.relative_path,
      title: document.title,
      category: document.category,
      status: document.status || "draft",
      source_office: document.source_office ?? "",
      issued_date: document.issued_date ?? "",
      effective_date: document.effective_date ?? "",
      version: document.version ?? "",
      source_url: document.source_url ?? "",
      notes: document.notes ?? "",
      workbook_type: document.workbook_type ?? "",
      sheet_schema_config: document.sheet_schema_config ?? null,
    });
  }

  async function loadPreview(relativePath: string) {
    setPreviewLoading(true);
    setError("");
    try {
      const response = await fetch(
        `/api/knowledge-admin/documents/preview?relative_path=${encodeURIComponent(relativePath)}`,
        { cache: "no-store" }
      );
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail ?? "Không thể tải bản xem trước.");
      }
      setDocumentPreview(data);
    } catch (previewError) {
      setDocumentPreview(null);
      setError(previewError instanceof Error ? previewError.message : "Không thể tải bản xem trước.");
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handleSelectDocument(document: KnowledgeDocument) {
    setSelectedDocumentPath(document.relative_path);
    hydrateDocumentEditor(document);
    await loadPreview(document.relative_path);
  }

  async function persistDocumentMetadata(nextStatus?: string) {
    if (!documentEditor.relative_path) {
      setError("Chưa chọn tài liệu để cập nhật.");
      return;
    }

    const payload: KnowledgeDocumentMetadataUpdateRequest = {
      ...documentEditor,
      status: nextStatus ?? documentEditor.status,
    };

    setSavingMetadata(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch("/api/knowledge-admin/documents/metadata", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail ?? "Không thể cập nhật thông tin tài liệu.");
      }

      setMessage(
        payload.status === "published"
          ? "Đã phát hành tài liệu và làm mới kho tri thức."
          : "Đã cập nhật thông tin tài liệu."
      );
      await loadAll();
      await loadPreview(payload.relative_path);
      setSelectedDocumentPath(payload.relative_path);
      hydrateDocumentEditor(data);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Không thể cập nhật thông tin tài liệu.");
    } finally {
      setSavingMetadata(false);
    }
  }

  async function handleDeleteDocument() {
    if (!selectedDocument) {
      setError("Chưa chọn tài liệu để xóa.");
      return;
    }

    const confirmed = window.confirm(`Xóa tài liệu "${selectedDocument.file_name}"?`);
    if (!confirmed) {
      return;
    }

    setSavingMetadata(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch(
        `/api/knowledge-admin/documents?relative_path=${encodeURIComponent(selectedDocument.relative_path)}`,
        { method: "DELETE" }
      );
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail ?? "Không thể xóa tài liệu.");
      }
      setMessage("Đã xóa tài liệu và làm mới kho tri thức.");
      setSelectedDocumentPath("");
      setDocumentEditor(EMPTY_DOCUMENT_EDITOR);
      setDocumentPreview(null);
      await loadAll();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Không thể xóa tài liệu.");
    } finally {
      setSavingMetadata(false);
    }
  }

  async function handleUpload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!uploadFile) {
      setError("Chọn tệp PDF trước khi tải lên.");
      return;
    }

    setUploading(true);
    setError("");
    setMessage("");

    try {
      const formData = new FormData();
      formData.append("file", uploadFile);
      formData.append("category", uploadCategory);
      if (uploadWorkbookType) {
        formData.append("workbook_type", uploadWorkbookType);
      }

      const response = await fetch("/api/knowledge-admin/documents/upload", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail ?? "Không thể tải tài liệu lên.");
      }

      setMessage("Đã tải tài liệu lên. Tài liệu mới đang ở trạng thái bản nháp.");
      setUploadFile(null);
      setUploadWorkbookType("");
      await loadAll();
      await handleSelectDocument(data);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Không thể tải tài liệu lên.");
    } finally {
      setUploading(false);
    }
  }

  async function handleRebuild() {
    setRebuilding(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch("/api/knowledge-admin/documents/rebuild", {
        method: "POST",
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail ?? "Không thể làm mới kho tri thức.");
      }
      setMessage(
        `Đã làm mới kho tri thức. Tài liệu: ${data.documents ?? 0}, đoạn: ${data.chunks ?? 0}.`
      );
      await loadAll();
      if (selectedDocumentPath) {
        await loadPreview(selectedDocumentPath);
      }
    } catch (rebuildError) {
      setError(rebuildError instanceof Error ? rebuildError.message : "Không thể làm mới kho tri thức.");
    } finally {
      setRebuilding(false);
    }
  }

  async function handleBatchPublish(
    relativePaths: string[],
    successMessage: string,
    extra?: Omit<KnowledgeDocumentBatchMetadataUpdateRequest, "relative_paths" | "status">
  ) {
    if (relativePaths.length === 0) {
      setError("Không có tài liệu phù hợp để phát hành.");
      return;
    }

    setBatchPublishing(true);
    setError("");
    setMessage("");

    try {
      const payload: KnowledgeDocumentBatchMetadataUpdateRequest = {
        relative_paths: relativePaths,
        status: "published",
        ...extra,
      };

      const response = await fetch("/api/knowledge-admin/documents/metadata/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail ?? "Không thể phát hành hàng loạt.");
      }

      setMessage(successMessage);
      await loadAll();
      if (selectedDocumentPath) {
        await loadPreview(selectedDocumentPath);
      }
    } catch (batchError) {
      setError(batchError instanceof Error ? batchError.message : "Không thể phát hành hàng loạt.");
    } finally {
      setBatchPublishing(false);
    }
  }

  async function handleCreateFaq(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFaqSubmitting(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch("/api/knowledge-admin/faqs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(faqForm),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail ?? "Không thể tạo FAQ.");
      }
      setFaqForm(EMPTY_FAQ_FORM);
      setMessage("Đã thêm FAQ mới.");
      await loadAll();
    } catch (faqError) {
      setError(faqError instanceof Error ? faqError.message : "Không thể tạo FAQ.");
    } finally {
      setFaqSubmitting(false);
    }
  }

  async function handleDeleteFaq(id: string) {
    setError("");
    setMessage("");
    const response = await fetch(`/api/knowledge-admin/faqs/${id}`, { method: "DELETE" });
    const data = await response.json();
    if (!response.ok) {
      setError(data?.detail ?? "Không thể xóa FAQ.");
      return;
    }
    setMessage("Đã xóa FAQ.");
    if (editingFaqId === id) {
      cancelEditFaq();
    }
    await loadAll();
  }

  async function handleCreateForm(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormSubmitting(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch("/api/knowledge-admin/forms", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formTemplate),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail ?? "Không thể tạo biểu mẫu.");
      }
      setFormTemplate(EMPTY_FORM_TEMPLATE);
      setMessage("Đã thêm biểu mẫu mới.");
      await loadAll();
    } catch (formError) {
      setError(formError instanceof Error ? formError.message : "Không thể tạo biểu mẫu.");
    } finally {
      setFormSubmitting(false);
    }
  }

  async function handleDeleteForm(id: string) {
    setError("");
    setMessage("");
    const response = await fetch(`/api/knowledge-admin/forms/${id}`, { method: "DELETE" });
    const data = await response.json();
    if (!response.ok) {
      setError(data?.detail ?? "Không thể xóa biểu mẫu.");
      return;
    }
    setMessage("Đã xóa biểu mẫu.");
    if (editingFormId === id) {
      cancelEditForm();
    }
    await loadAll();
  }

  async function submitFaq(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFaqSubmitting(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch(
        editingFaqId ? `/api/knowledge-admin/faqs/${editingFaqId}` : "/api/knowledge-admin/faqs",
        {
          method: editingFaqId ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(faqForm),
        }
      );
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail ?? (editingFaqId ? "Không thể cập nhật FAQ." : "Không thể tạo FAQ."));
      }
      setFaqForm(EMPTY_FAQ_FORM);
      setEditingFaqId(null);
      setMessage(editingFaqId ? "Đã cập nhật FAQ." : "Đã thêm FAQ mới.");
      await loadAll();
    } catch (faqError) {
      setError(
        faqError instanceof Error
          ? faqError.message
          : editingFaqId
            ? "Không thể cập nhật FAQ."
            : "Không thể tạo FAQ."
      );
    } finally {
      setFaqSubmitting(false);
    }
  }

  function startEditFaq(faq: FAQEntry) {
    setEditingFaqId(faq.id);
    setFaqForm({
      title: faq.title,
      category: faq.category,
      question: faq.question,
      answer: faq.answer,
      source_url: faq.source_url ?? "",
      keywords: faq.keywords,
    });
  }

  function cancelEditFaq() {
    setEditingFaqId(null);
    setFaqForm(EMPTY_FAQ_FORM);
  }

  async function submitFormTemplate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormSubmitting(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch(
        editingFormId ? `/api/knowledge-admin/forms/${editingFormId}` : "/api/knowledge-admin/forms",
        {
          method: editingFormId ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(formTemplate),
        }
      );
      const data = await response.json();
      if (!response.ok) {
        throw new Error(
          data?.detail ?? (editingFormId ? "Không thể cập nhật biểu mẫu." : "Không thể tạo biểu mẫu.")
        );
      }
      setFormTemplate(EMPTY_FORM_TEMPLATE);
      setEditingFormId(null);
      setMessage(editingFormId ? "Đã cập nhật biểu mẫu." : "Đã thêm biểu mẫu mới.");
      await loadAll();
    } catch (formError) {
      setError(
        formError instanceof Error
          ? formError.message
          : editingFormId
            ? "Không thể cập nhật biểu mẫu."
            : "Không thể tạo biểu mẫu."
      );
    } finally {
      setFormSubmitting(false);
    }
  }

  function startEditForm(form: FormTemplate) {
    setEditingFormId(form.id);
    setFormTemplate({
      title: form.title,
      category: form.category,
      description: form.description,
      source_url: form.source_url ?? "",
      keywords: form.keywords,
      fields: form.fields,
    });
  }

  function cancelEditForm() {
    setEditingFormId(null);
    setFormTemplate(EMPTY_FORM_TEMPLATE);
  }

  function addField() {
    setFormTemplate((current) => ({
      ...current,
      fields: [...current.fields, { ...EMPTY_FIELD }],
    }));
  }

  function updateField(index: number, patch: Partial<FormTemplateField>) {
    setFormTemplate((current) => ({
      ...current,
      fields: current.fields.map((field, fieldIndex) =>
        fieldIndex === index ? { ...field, ...patch } : field
      ),
    }));
  }

  function removeField(index: number) {
    setFormTemplate((current) => ({
      ...current,
      fields: current.fields.filter((_, fieldIndex) => fieldIndex !== index),
    }));
  }

  useEffect(() => {
    void loadAll();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h1 className="text-3xl font-bold">Quản lý tri thức</h1>
        </div>
        <Button type="button" variant="outline" onClick={handleRebuild} disabled={rebuilding}>
          {rebuilding ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Làm mới kho tri thức
        </Button>
        <Button
          type="button"
          variant="destructive"
          onClick={() => void handleDeleteDocument()}
          disabled={savingMetadata || !selectedDocument}
        >
          <Trash2 className="mr-2 h-4 w-4" />
          Xóa tài liệu đã chọn
        </Button>
      </div>

      {message ? (
        <div className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
          {message}
        </div>
      ) : null}
      {error ? (
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      {overview ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Nguồn tài liệu</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm text-muted-foreground">
              <p>Tổng: {overview.total_documents}</p>
              <p>Đã phát hành: {overview.status_counts.published ?? 0}</p>
              <p>Cần rà soát: {overview.status_counts.needs_review ?? 0}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Dữ liệu chuẩn hóa</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm text-muted-foreground">
              <p>Đoạn: {overview.normalized_counts.chunks ?? 0}</p>
              <p>Bảng: {overview.normalized_counts.tables ?? 0}</p>
              <p>Dòng: {overview.normalized_counts.table_rows ?? 0}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Tri thức quản trị</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm text-muted-foreground">
              <p>FAQ: {overview.normalized_counts.faqs ?? 0}</p>
              <p>Biểu mẫu: {overview.normalized_counts.forms ?? 0}</p>
              <p>Thủ tục: {overview.normalized_counts.procedures ?? 0}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Dữ liệu đang dùng</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm text-muted-foreground">
              <p>Tài liệu: {overview.runtime_counts.documents ?? 0}</p>
              <p>Bản ghi: {overview.runtime_counts.entries ?? 0}</p>
            </CardContent>
          </Card>
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[1.1fr,1.3fr]">
        <Card>
          <CardHeader>
            <CardTitle>Tài liệu</CardTitle>
            <CardDescription>Thêm và rà soát tài liệu.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <form className="space-y-4" onSubmit={handleUpload}>
              <div className="space-y-2">
                <Label htmlFor="upload-workbook-type">Loại bảng tính</Label>
                <select
                  id="upload-workbook-type"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={uploadWorkbookType}
                  onChange={(event) => setUploadWorkbookType(event.target.value)}
                >
                  {WORKBOOK_TYPE_OPTIONS.map((option) => (
                    <option key={option.value || "auto"} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="upload-category">Danh mục</Label>
                <Input
                  id="upload-category"
                  value={uploadCategory}
                  onChange={(event) => setUploadCategory(event.target.value)}
                  placeholder="Ví dụ: hoc-vu"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="upload-file">Tệp</Label>
                <Input
                  id="upload-file"
                  type="file"
                  accept=".pdf,.csv,.xlsx,.xls,application/pdf,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
                  onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
                />
                <p className="text-xs text-muted-foreground">Hỗ trợ PDF, CSV, XLSX và XLS.</p>
              </div>
              <Button type="submit" disabled={uploading}>
                {uploading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="mr-2 h-4 w-4" />
                )}
                Tải tài liệu lên
              </Button>
            </form>

            <div className="flex flex-wrap gap-3">
              <Button
                type="button"
                variant="secondary"
                disabled={batchPublishing || tuitionDocumentPaths.length === 0}
                onClick={() =>
                  void handleBatchPublish(tuitionDocumentPaths, "Đã phát hành toàn bộ tài liệu học phí.", {
                    source_office: "Phòng Tài chính",
                    notes: "Phát hành học phí",
                  })
                }
              >
                {batchPublishing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Phát hành học phí
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={batchPublishing || reviewDocumentPaths.length === 0}
                onClick={() =>
                  void handleBatchPublish(reviewDocumentPaths, "Đã phát hành toàn bộ tài liệu cần rà soát.")
                }
              >
                Phát hành tài liệu cần rà soát
              </Button>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                  Danh sách tài liệu
                </h2>
                <span className="text-sm text-muted-foreground">{documents.length} mục</span>
              </div>
              <div className="max-h-[520px] space-y-3 overflow-y-auto pr-1">
                {pageLoading ? (
                  <div className="flex items-center gap-2 rounded-lg border border-border px-3 py-4 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Đang tải dữ liệu...
                  </div>
                ) : documents.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-border px-3 py-4 text-sm text-muted-foreground">
                    Chưa có tài liệu nào.
                  </div>
                ) : (
                  documents.map((document) => (
                    <button
                      key={document.relative_path}
                      type="button"
                      onClick={() => void handleSelectDocument(document)}
                      className={`w-full rounded-xl border p-4 text-left transition-colors ${
                        selectedDocumentPath === document.relative_path
                          ? "border-primary bg-primary/5"
                          : "border-border hover:border-primary/40"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate font-medium">{document.title}</p>
                          <p className="mt-1 text-xs text-muted-foreground">{document.relative_path}</p>
                        </div>
                        <Badge variant={statusBadgeVariant(document.status)}>
                          {formatStatus(document.status)}
                        </Badge>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                        <span>{document.category}</span>
                        {document.page_count ? <span>{document.page_count} trang</span> : null}
                        {document.source_office ? <span>{document.source_office}</span> : null}
                        {document.workbook_type ? (
                          <span>Loại bảng tính: {formatWorkbookType(document.workbook_type)}</span>
                        ) : null}
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Rà soát tài liệu</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {!selectedDocument ? (
              <div className="rounded-lg border border-dashed border-border px-4 py-10 text-sm text-muted-foreground">
                Chọn một tài liệu ở danh sách bên trái để bắt đầu rà soát.
              </div>
            ) : (
              <>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="document-title">Tiêu đề</Label>
                    <Input
                      id="document-title"
                      value={documentEditor.title}
                      onChange={(event) =>
                        setDocumentEditor((current) => ({ ...current, title: event.target.value }))
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="document-category">Danh mục</Label>
                    <Input
                      id="document-category"
                      value={documentEditor.category}
                      onChange={(event) =>
                        setDocumentEditor((current) => ({ ...current, category: event.target.value }))
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="document-status">Trạng thái</Label>
                    <select
                      id="document-status"
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={documentEditor.status}
                      onChange={(event) =>
                        setDocumentEditor((current) => ({ ...current, status: event.target.value }))
                      }
                    >
                      {STATUS_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="document-workbook-type">Loại bảng tính</Label>
                    <select
                      id="document-workbook-type"
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={documentEditor.workbook_type ?? ""}
                      onChange={(event) =>
                        setDocumentEditor((current) => ({
                          ...current,
                          workbook_type: event.target.value,
                        }))
                      }
                    >
                      {WORKBOOK_TYPE_OPTIONS.map((option) => (
                        <option key={option.value || "auto"} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="document-office">Đơn vị ban hành</Label>
                    <Input
                      id="document-office"
                      value={documentEditor.source_office ?? ""}
                      onChange={(event) =>
                        setDocumentEditor((current) => ({ ...current, source_office: event.target.value }))
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="document-issued-date">Ngày ban hành</Label>
                    <Input
                      id="document-issued-date"
                      type="date"
                      value={documentEditor.issued_date ?? ""}
                      onChange={(event) =>
                        setDocumentEditor((current) => ({ ...current, issued_date: event.target.value }))
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="document-effective-date">Ngày hiệu lực</Label>
                    <Input
                      id="document-effective-date"
                      type="date"
                      value={documentEditor.effective_date ?? ""}
                      onChange={(event) =>
                        setDocumentEditor((current) => ({ ...current, effective_date: event.target.value }))
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="document-version">Phiên bản</Label>
                    <Input
                      id="document-version"
                      value={documentEditor.version ?? ""}
                      onChange={(event) =>
                        setDocumentEditor((current) => ({ ...current, version: event.target.value }))
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="document-source-url">Liên kết nguồn</Label>
                    <Input
                      id="document-source-url"
                      value={documentEditor.source_url ?? ""}
                      onChange={(event) =>
                        setDocumentEditor((current) => ({ ...current, source_url: event.target.value }))
                      }
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="document-notes">Ghi chú</Label>
                  <textarea
                    id="document-notes"
                    className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={documentEditor.notes ?? ""}
                    onChange={(event) =>
                      setDocumentEditor((current) => ({ ...current, notes: event.target.value }))
                    }
                    placeholder="Ghi chú nguồn hoặc phạm vi áp dụng..."
                  />
                </div>

                {documentEditor.sheet_schema_config ? (
                  <div className="rounded-lg border border-border bg-secondary/20 px-4 py-3 text-sm text-muted-foreground">
                    <p>
                      Sheet chính:{" "}
                      <span className="font-medium text-foreground">
                        {String(
                          (documentEditor.sheet_schema_config as Record<string, unknown>).canonical_sheet ?? "-"
                        )}
                      </span>
                    </p>
                  </div>
                ) : null}

                <div className="flex flex-wrap gap-3">
                  <Button type="button" onClick={() => void persistDocumentMetadata()} disabled={savingMetadata}>
                    {savingMetadata ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Save className="mr-2 h-4 w-4" />
                    )}
                    Lưu thông tin
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => void persistDocumentMetadata("published")}
                    disabled={savingMetadata}
                  >
                    Phát hành
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => void persistDocumentMetadata("draft")}
                    disabled={savingMetadata}
                  >
                    Chuyển về nháp
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => void loadPreview(selectedDocument.relative_path)}
                    disabled={previewLoading}
                  >
                    {previewLoading ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <RefreshCw className="mr-2 h-4 w-4" />
                    )}
                    Tải lại xem trước
                  </Button>
                </div>

                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="rounded-xl border border-border p-4">
                    <div className="mb-3 flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      <h3 className="font-medium">
                        Đoạn trích ({documentPreview?.chunk_count ?? 0})
                      </h3>
                    </div>
                    <div className="max-h-[360px] space-y-3 overflow-y-auto pr-1">
                      {documentPreview?.chunks?.length ? (
                        documentPreview.chunks.map((chunk) => (
                          <div key={chunk.chunk_id} className="rounded-lg border border-border p-3">
                            <p className="text-sm font-medium">
                              {chunk.section_title || "Đoạn không có tiêu đề"}
                            </p>
                            <p className="mt-2 text-sm text-muted-foreground">{chunk.summary}</p>
                            <p className="mt-2 text-xs text-muted-foreground">
                              Trang {chunk.page_from ?? "?"}
                              {chunk.page_to && chunk.page_to !== chunk.page_from
                                ? ` - ${chunk.page_to}`
                                : ""}
                            </p>
                          </div>
                        ))
                      ) : (
                        <p className="text-sm text-muted-foreground">
                          Chưa có đoạn trích cho tài liệu này.
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="rounded-xl border border-border p-4">
                    <div className="mb-3 flex items-center gap-2">
                      <Table2 className="h-4 w-4" />
                      <h3 className="font-medium">
                        Bảng dữ liệu ({documentPreview?.table_count ?? 0})
                      </h3>
                    </div>
                    <div className="max-h-[360px] space-y-3 overflow-y-auto pr-1">
                      {documentPreview?.tables?.length ? (
                        documentPreview.tables.map((table) => (
                          <div key={table.table_id} className="rounded-lg border border-border p-3">
                            <p className="text-sm font-medium">{table.title}</p>
                            <p className="mt-1 text-xs text-muted-foreground">
                              Trang {table.page_from ?? "?"}
                              {table.page_to && table.page_to !== table.page_from
                                ? ` - ${table.page_to}`
                                : ""}
                            </p>
                            <div className="mt-3 space-y-2">
                              {table.rows.map((row) => (
                                <div
                                  key={row.row_id}
                                  className="rounded-md bg-secondary/40 px-3 py-2 text-sm"
                                >
                                  <p className="font-medium">{row.label}</p>
                                  {row.amount_text ? (
                                    <p className="text-muted-foreground">{row.amount_text}</p>
                                  ) : null}
                                </div>
                              ))}
                            </div>
                          </div>
                        ))
                      ) : (
                        <p className="text-sm text-muted-foreground">
                          Chưa có bảng biểu được tách từ tài liệu này.
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>FAQ</CardTitle>
            <CardDescription>Quản lý câu hỏi thường gặp.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <form className="space-y-4" onSubmit={submitFaq}>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="faq-title">Tiêu đề</Label>
                  <Input
                    id="faq-title"
                    value={faqForm.title}
                    onChange={(event) => setFaqForm((current) => ({ ...current, title: event.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="faq-category">Danh mục</Label>
                  <Input
                    id="faq-category"
                    value={faqForm.category}
                    onChange={(event) =>
                      setFaqForm((current) => ({ ...current, category: event.target.value }))
                    }
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="faq-question">Câu hỏi</Label>
                <textarea
                  id="faq-question"
                  className="min-h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={faqForm.question}
                  onChange={(event) => setFaqForm((current) => ({ ...current, question: event.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="faq-answer">Câu trả lời</Label>
                <textarea
                  id="faq-answer"
                  className="min-h-28 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={faqForm.answer}
                  onChange={(event) => setFaqForm((current) => ({ ...current, answer: event.target.value }))}
                />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="faq-source-url">Liên kết nguồn</Label>
                  <Input
                    id="faq-source-url"
                    value={faqForm.source_url ?? ""}
                    onChange={(event) =>
                      setFaqForm((current) => ({ ...current, source_url: event.target.value }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="faq-keywords">Từ khóa</Label>
                  <Input
                    id="faq-keywords"
                    value={serializeKeywordInput(faqForm.keywords)}
                    onChange={(event) =>
                      setFaqForm((current) => ({
                        ...current,
                        keywords: parseKeywordInput(event.target.value),
                      }))
                    }
                    placeholder="học phí, học bổng, bảo lưu"
                  />
                </div>
              </div>
              <Button type="submit" disabled={faqSubmitting}>
                {faqSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Thêm FAQ
              </Button>
              {editingFaqId ? (
                <Button type="button" variant="outline" onClick={cancelEditFaq}>
                  Hủy sửa
                </Button>
              ) : null}
            </form>

            <div className="space-y-3">
              {faqs.map((faq) => (
                <div key={faq.id} className="rounded-xl border border-border p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium">{faq.title}</p>
                      <p className="mt-1 text-sm text-muted-foreground">{faq.question}</p>
                    </div>
                    <div className="flex items-center gap-1">
                      <Button type="button" variant="ghost" size="sm" onClick={() => startEditFaq(faq)}>
                        Sửa
                      </Button>
                      <Button type="button" variant="ghost" size="icon" onClick={() => void handleDeleteFaq(faq.id)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span>{faq.category}</span>
                    {faq.keywords.length ? <span>{serializeKeywordInput(faq.keywords)}</span> : null}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Biểu mẫu</CardTitle>
            <CardDescription>Quản lý biểu mẫu cho CHATBOT.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <form className="space-y-4" onSubmit={submitFormTemplate}>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="form-title">Tên biểu mẫu</Label>
                  <Input
                    id="form-title"
                    value={formTemplate.title}
                    onChange={(event) =>
                      setFormTemplate((current) => ({ ...current, title: event.target.value }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="form-category">Danh mục</Label>
                  <Input
                    id="form-category"
                    value={formTemplate.category}
                    onChange={(event) =>
                      setFormTemplate((current) => ({ ...current, category: event.target.value }))
                    }
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="form-description">Mô tả</Label>
                <textarea
                  id="form-description"
                  className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={formTemplate.description}
                  onChange={(event) =>
                    setFormTemplate((current) => ({ ...current, description: event.target.value }))
                  }
                />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="form-source-url">Liên kết nguồn</Label>
                  <Input
                    id="form-source-url"
                    value={formTemplate.source_url ?? ""}
                    onChange={(event) =>
                      setFormTemplate((current) => ({ ...current, source_url: event.target.value }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="form-keywords">Từ khóa</Label>
                  <Input
                    id="form-keywords"
                    value={serializeKeywordInput(formTemplate.keywords)}
                    onChange={(event) =>
                      setFormTemplate((current) => ({
                        ...current,
                        keywords: parseKeywordInput(event.target.value),
                      }))
                    }
                  />
                </div>
              </div>
              <div className="space-y-3 rounded-xl border border-border p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-medium">Trường dữ liệu</p>
                  </div>
                  <Button type="button" variant="outline" onClick={addField}>
                    Thêm trường
                  </Button>
                </div>
                <div className="space-y-4">
                  {formTemplate.fields.map((field, index) => (
                    <div key={`${field.name}-${index}`} className="rounded-lg border border-border p-4">
                      <div className="grid gap-4 md:grid-cols-2">
                        <div className="space-y-2">
                          <Label>Tên kỹ thuật</Label>
                          <Input
                            value={field.name}
                            onChange={(event) => updateField(index, { name: event.target.value })}
                            placeholder="student_id"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Nhãn hiển thị</Label>
                          <Input
                            value={field.label}
                            onChange={(event) => updateField(index, { label: event.target.value })}
                            placeholder="Mã sinh viên"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Kiểu dữ liệu</Label>
                          <select
                            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                            value={field.type}
                            onChange={(event) => updateField(index, { type: event.target.value })}
                          >
                            <option value="text">Một dòng</option>
                            <option value="textarea">Nhiều dòng</option>
                            <option value="number">Số</option>
                            <option value="date">Ngày</option>
                            <option value="email">Email</option>
                          </select>
                        </div>
                        <div className="space-y-2">
                          <Label>Gợi ý nhập</Label>
                          <Input
                            value={field.placeholder ?? ""}
                            onChange={(event) => updateField(index, { placeholder: event.target.value })}
                          />
                        </div>
                      </div>
                      <div className="mt-4 flex items-center justify-between">
                        <label className="flex items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={field.required}
                            onChange={(event) => updateField(index, { required: event.target.checked })}
                          />
                          Bắt buộc
                        </label>
                        <Button type="button" variant="ghost" size="sm" onClick={() => removeField(index)}>
                          Xóa trường
                        </Button>
                      </div>
                    </div>
                  ))}
                  {formTemplate.fields.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Chưa có trường nào. Bấm Thêm trường để bắt đầu.</p>
                  ) : null}
                </div>
              </div>
              <Button type="submit" disabled={formSubmitting}>
                {formSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Thêm biểu mẫu
              </Button>
              {editingFormId ? (
                <Button type="button" variant="outline" onClick={cancelEditForm}>
                  Hủy sửa
                </Button>
              ) : null}
            </form>

            <div className="space-y-3">
              {forms.map((form) => (
                <div key={form.id} className="rounded-xl border border-border p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium">{form.title}</p>
                      <p className="mt-1 text-sm text-muted-foreground">{form.description}</p>
                    </div>
                    <div className="flex items-center gap-1">
                      <Button type="button" variant="ghost" size="sm" onClick={() => startEditForm(form)}>
                        Sửa
                      </Button>
                      <Button type="button" variant="ghost" size="icon" onClick={() => void handleDeleteForm(form.id)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span>{form.category}</span>
                    <span>{form.fields.length} trường</span>
                    {form.keywords.length ? <span>{serializeKeywordInput(form.keywords)}</span> : null}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
