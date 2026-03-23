"use client";

import { memo, useMemo, useState } from "react";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@/components/ui";
import type { ToolCall } from "@/types";
import {
  Wrench,
  CheckCircle,
  Loader2,
  AlertCircle,
  FileEdit,
  ChevronDown,
  ChevronRight,
  ListChecks,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { CopyButton } from "./copy-button";
import { useFormPanelStore } from "@/stores";

interface ToolCallCardProps {
  toolCall: ToolCall;
}

interface JsonSectionProps {
  label: string;
  text: string;
  defaultOpen?: boolean;
}

function JsonSection({ label, text, defaultOpen = false }: JsonSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const preview = useMemo(() => {
    const normalized = text.replace(/\s+/g, " ").trim();
    return normalized.length > 120 ? `${normalized.slice(0, 117)}...` : normalized;
  }, [text]);

  return (
    <div className="rounded-lg border bg-background/70">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left"
        onClick={() => setIsOpen((current) => !current)}
      >
        <div className="min-w-0">
          <p className="text-xs font-medium text-foreground">{label}</p>
          <p className="truncate text-[11px] text-muted-foreground">{preview || "Trống"}</p>
        </div>
        {isOpen ? (
          <ChevronDown className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
        )}
      </button>

      {isOpen && (
        <div className="border-t px-3 py-2">
          <div className="mb-2 flex items-center justify-end">
            <CopyButton text={text} />
          </div>
          <pre className="max-h-56 overflow-auto rounded bg-background p-2 text-xs whitespace-pre-wrap break-words">
            {text}
          </pre>
        </div>
      )}
    </div>
  );
}

export const ToolCallCard = memo(function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const statusConfig = {
    pending: { icon: Loader2, color: "text-muted-foreground", animate: true },
    running: { icon: Loader2, color: "text-blue-500", animate: true },
    completed: { icon: CheckCircle, color: "text-green-500", animate: false },
    error: { icon: AlertCircle, color: "text-red-500", animate: false },
  };

  const { icon: StatusIcon, color, animate } = statusConfig[toolCall.status];

  const argsText = useMemo(() => JSON.stringify(toolCall.args, null, 2), [toolCall.args]);
  const resultText = useMemo(() => {
    if (toolCall.result === undefined) {
      return "";
    }

    return typeof toolCall.result === "string"
      ? toolCall.result
      : JSON.stringify(toolCall.result, null, 2);
  }, [toolCall.result]);

  const { openPanel } = useFormPanelStore();
  const parsedResult = useMemo(() => {
    try {
      return typeof toolCall.result === "string" ? JSON.parse(toolCall.result) : toolCall.result;
    } catch {
      return null;
    }
  }, [toolCall.result]);

  const handleFillForm = () => {
    try {
      const rawData = parsedResult;
      const data = rawData as {
        template_id?: string | null;
        title?: string;
        description?: string;
        template: string;
        fields: Array<{ id?: string; name?: string; label: string; type: string }>;
        workflow?: {
          procedureId?: string;
          title: string;
          summary?: string;
          eligibility?: string[];
          requiredDocuments?: string[];
          steps?: string[];
          contactOffice?: string;
        };
      };
      openPanel({
        templateId: data.template_id ?? null,
        title: data.title,
        description: data.description,
        template: data.template,
        fields: (data.fields || []).map((field, index) => ({
          id: field.id || field.name || `field_${index + 1}`,
          label: field.label,
          type: field.type || "text",
        })),
        workflow: data.workflow ?? null,
      });
    } catch (e) {
      console.error("Không thể đọc dữ liệu biểu mẫu", e);
    }
  };

  const handleOpenProcedureForm = () => {
    try {
      const rawData = parsedResult as {
        matched_form?: {
          template_id?: string | null;
          title?: string;
          description?: string;
          template: string;
          fields: Array<{ id?: string; name?: string; label: string; type: string }>;
        } | null;
        procedure_id?: string;
        title?: string;
        summary?: string;
        eligibility?: string[];
        required_documents?: string[];
        steps?: string[];
        contact_office?: string;
      } | null;

      if (!rawData?.matched_form) {
        return;
      }

      openPanel({
        templateId: rawData.matched_form.template_id ?? null,
        title: rawData.matched_form.title,
        description: rawData.matched_form.description,
        template: rawData.matched_form.template,
        fields: (rawData.matched_form.fields || []).map((field, index) => ({
          id: field.id || field.name || `field_${index + 1}`,
          label: field.label,
          type: field.type || "text",
        })),
        workflow: {
          procedureId: rawData.procedure_id,
          title: rawData.title || "Thu tuc hanh chinh",
          summary: rawData.summary,
          eligibility: rawData.eligibility,
          requiredDocuments: rawData.required_documents,
          steps: rawData.steps,
          contactOffice: rawData.contact_office,
        },
      });
    } catch (error) {
      console.error("Khong the mo workflow bieu mau", error);
    }
  };

  return (
    <Card className="bg-muted/50">
      <CardHeader className="py-2 px-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wrench className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-sm font-medium">
              {toolCall.name}
            </CardTitle>
          </div>
          <StatusIcon
            className={cn("h-4 w-4", color, animate && "animate-spin")}
          />
        </div>
      </CardHeader>
      <CardContent className="py-2 px-3 space-y-2">
        <JsonSection label="Tham số" text={argsText} />

        {toolCall.result !== undefined && <JsonSection label="Kết quả" text={resultText} />}

        {toolCall.name === "generate_form" && toolCall.status === "completed" && (
          <div className="pt-2">
            <Button size="sm" onClick={handleFillForm} className="w-full sm:w-auto">
              <FileEdit className="mr-2 h-4 w-4" />
              Điền biểu mẫu
            </Button>
          </div>
        )}
        {toolCall.name === "build_procedure_workflow" &&
          toolCall.status === "completed" &&
          parsedResult &&
          typeof parsedResult === "object" &&
          "matched" in parsedResult &&
          parsedResult.matched && (
            <div className="space-y-3 pt-2">
              <div className="rounded-lg border border-border/70 bg-background/60 p-3">
                <div className="flex items-start gap-2">
                  <ListChecks className="mt-0.5 h-4 w-4 text-primary" />
                  <div className="min-w-0 space-y-1">
                    <p className="text-sm font-medium text-foreground">
                      {"title" in parsedResult && typeof parsedResult.title === "string"
                        ? parsedResult.title
                        : "Quy trinh thu tuc"}
                    </p>
                    {"summary" in parsedResult && typeof parsedResult.summary === "string" && (
                      <p className="text-xs text-muted-foreground">{parsedResult.summary}</p>
                    )}
                  </div>
                </div>

                {"steps" in parsedResult &&
                  Array.isArray(parsedResult.steps) &&
                  parsedResult.steps.length > 0 && (
                    <div className="mt-3 space-y-1">
                      {parsedResult.steps.slice(0, 3).map((step: string, index: number) => (
                        <p key={`${index}-${step}`} className="text-xs text-muted-foreground">
                          {index + 1}. {step}
                        </p>
                      ))}
                    </div>
                  )}
              </div>

              {"matched_form" in parsedResult && parsedResult.matched_form && (
                <Button size="sm" onClick={handleOpenProcedureForm} className="w-full sm:w-auto">
                  <FileEdit className="mr-2 h-4 w-4" />
                  Mo workflow va bieu mau
                </Button>
              )}
            </div>
          )}
      </CardContent>
    </Card>
  );
});
