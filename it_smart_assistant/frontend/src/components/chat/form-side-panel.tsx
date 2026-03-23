"use client";

import { useEffect, useMemo, useState } from "react";
import { Check, Download, FileText, Loader2, X } from "lucide-react";
import { Button, Card, CardContent, Input, Label } from "@/components/ui";
import { MarkdownContent } from "./markdown-content";

interface FormField {
  id: string;
  label: string;
  type: string;
}

interface ProcedureWorkflow {
  procedureId?: string;
  title: string;
  summary?: string;
  eligibility?: string[];
  requiredDocuments?: string[];
  steps?: string[];
  contactOffice?: string;
}

interface FormTemplate {
  templateId?: string | null;
  title?: string;
  description?: string;
  template: string;
  fields: FormField[];
  workflow?: ProcedureWorkflow | null;
}

interface FormSidePanelProps {
  isOpen: boolean;
  onClose: () => void;
  formData: FormTemplate | null;
}

function fillTemplate(template: string, values: Record<string, string>) {
  let nextTemplate = template;
  Object.entries(values).forEach(([key, value]) => {
    const placeholder = `{{${key}}}`;
    nextTemplate = nextTemplate.replace(new RegExp(placeholder, "g"), value || `[${key}]`);
  });
  return nextTemplate;
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function getValue(values: Record<string, string>, ...keys: string[]) {
  for (const key of keys) {
    const value = values[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return "";
}

function getProcedureRecipients(workflow?: ProcedureWorkflow | null) {
  switch (workflow?.procedureId) {
    case "mien_giam_hoc_phi":
      return ["Phòng Tài chính - Kế toán", "Phòng Công tác sinh viên"];
    case "bao_luu_hoc_tap":
    case "rut_hoc_phan":
    case "hoc_lai_cai_thien":
    case "hoan_nghia_vu_hoc_tap":
      return ["Phòng Đào tạo", "Bộ phận học vụ khoa"];
    case "xac_nhan_sinh_vien":
      return ["Phòng Công tác sinh viên"];
    case "dang_ky_thuc_tap":
      return ["Khoa/Bộ môn phụ trách thực tập"];
    default:
      return workflow?.contactOffice ? [workflow.contactOffice] : ["Phòng/Ban liên quan"];
  }
}

function buildAdministrativeBody(formData: FormTemplate, values: Record<string, string>) {
  const procedureId = formData.workflow?.procedureId;
  const applicantName = getValue(values, "full_name", "student_name") || "................................";
  const studentId = getValue(values, "student_id") || "................................";

  switch (procedureId) {
    case "mien_giam_hoc_phi":
      return [
        "Nay tôi làm đơn này kính đề nghị Nhà trường xem xét miễn giảm học phí cho tôi theo diện chính sách.",
        `Tôi là sinh viên ${applicantName}, mã sinh viên ${studentId}. Căn cứ vào hồ sơ và thông tin đã kê khai ở trên, kính mong Nhà trường xem xét và giải quyết theo quy định hiện hành.`,
      ];
    case "bao_luu_hoc_tap":
      return [
        "Nay tôi làm đơn này kính đề nghị Nhà trường cho phép tôi được bảo lưu kết quả học tập.",
        `Tôi là sinh viên ${applicantName}, mã sinh viên ${studentId}. Vì lý do đã nêu trong đơn, kính mong Nhà trường xem xét và chấp thuận cho tôi được bảo lưu theo quy định.`,
      ];
    case "xac_nhan_sinh_vien":
      return [
        "Nay tôi làm đơn này kính đề nghị Nhà trường xác nhận tình trạng sinh viên cho tôi.",
        `Tôi là sinh viên ${applicantName}, mã sinh viên ${studentId}. Kính mong Nhà trường xem xét và hỗ trợ cấp giấy xác nhận theo nội dung tôi đã kê khai.`,
      ];
    case "rut_hoc_phan":
      return [
        "Nay tôi làm đơn này kính đề nghị Nhà trường cho phép tôi được rút học phần đã đăng ký.",
        `Tôi là sinh viên ${applicantName}, mã sinh viên ${studentId}. Kính mong Nhà trường xem xét và giải quyết đề nghị của tôi theo quy định hiện hành.`,
      ];
    case "hoc_lai_cai_thien":
      return [
        "Nay tôi làm đơn này kính đề nghị Nhà trường cho phép tôi đăng ký học lại/cải thiện điểm.",
        `Tôi là sinh viên ${applicantName}, mã sinh viên ${studentId}. Kính mong Nhà trường xem xét và phê duyệt đề nghị đã nêu ở trên.`,
      ];
    case "dang_ky_thuc_tap":
      return [
        "Nay tôi làm đơn này kính đề nghị Khoa/Bộ môn xem xét cho tôi được đăng ký thực tập.",
        `Tôi là sinh viên ${applicantName}, mã sinh viên ${studentId}. Kính mong Khoa/Bộ môn xem xét và chấp thuận kế hoạch thực tập theo thông tin tôi đã kê khai.`,
      ];
    case "hoan_nghia_vu_hoc_tap":
      return [
        "Nay tôi làm đơn này kính đề nghị Nhà trường xem xét hoãn nghĩa vụ học tập cho tôi.",
        `Tôi là sinh viên ${applicantName}, mã sinh viên ${studentId}. Kính mong Nhà trường xem xét và giải quyết đề nghị của tôi theo quy định hiện hành.`,
      ];
    default:
      return [
        "Nay tôi làm đơn này kính đề nghị Nhà trường xem xét nội dung đề nghị của tôi.",
        `Tôi là sinh viên ${applicantName}, mã sinh viên ${studentId}. Kính mong Nhà trường xem xét và giải quyết theo quy định.`,
      ];
  }
}

function renderBodyHtml(formData: FormTemplate, values: Record<string, string>) {
  return buildAdministrativeBody(formData, values)
    .map((line) => `<p>${escapeHtml(line)}</p>`)
    .join("");
}

function buildPrintableFormHtml(
  formData: FormTemplate,
  values: Record<string, string>
) {
  const today = new Date();
  const title = formData.title || "Biểu mẫu sinh viên";
  const applicantName = getValue(values, "full_name", "student_name");
  const recipients = getProcedureRecipients(formData.workflow);
  const className = getValue(values, "class_name");
  const faculty = getValue(values, "faculty");
  const dateLine = `Hà Nội, ngày ${today.getDate()} tháng ${today.getMonth() + 1} năm ${today.getFullYear()}`;

  const introSuffix = [className ? `lớp ${className}` : "", faculty ? `khoa ${faculty}` : ""]
    .filter(Boolean)
    .join(", ");

  const fieldRows = formData.fields
    .map((field) => {
      const renderedValue =
        escapeHtml(values[field.id] || "").trim() ||
        '<span class="empty">........................................</span>';
      return `
        <tr>
          <td class="label">${escapeHtml(field.label)}</td>
          <td class="value">${renderedValue}</td>
        </tr>`;
    })
    .join("");

  const recipientsHtml = recipients
    .map((recipient) => `<div class="recipient-line">${escapeHtml(recipient)}</div>`)
    .join("");

  return `<!DOCTYPE html>
  <html lang="vi">
    <head>
      <meta charset="utf-8" />
      <title></title>
      <style>
        @page { size: A4; margin: 15mm 18mm 15mm 22mm; }
        * { box-sizing: border-box; }
        html, body {
          margin: 0;
          padding: 0;
          color: #111827;
          background: white;
          font-family: "Times New Roman", Times, serif;
          font-size: 12.6pt;
          line-height: 1.42;
        }
        .document {
          width: 100%;
          max-width: 171mm;
          margin: 0 auto;
        }
        .header {
          display: flex;
          justify-content: space-between;
          gap: 18px;
          margin-bottom: 14px;
        }
        .header-block {
          width: 48%;
          text-align: center;
        }
        .header-block strong {
          display: block;
          text-transform: uppercase;
          font-size: 12.6pt;
          line-height: 1.35;
        }
        .subline {
          margin-top: 4px;
          font-weight: 700;
        }
        .divider {
          width: 120px;
          margin: 4px auto 0;
          border-top: 1px solid #111827;
        }
        .title {
          margin: 10px 0 12px;
          text-align: center;
          text-transform: uppercase;
          font-size: 16pt;
          font-weight: 700;
          line-height: 1.25;
        }
        .recipient,
        .intro,
        .commitment {
          margin-top: 6px;
        }
        .recipient strong,
        .commitment strong {
          text-transform: uppercase;
        }
        .recipient-line {
          margin-left: 76px;
        }
        .section {
          margin-top: 12px;
        }
        .section-title {
          margin-bottom: 4px;
          font-weight: 700;
        }
        table {
          width: 100%;
          border-collapse: collapse;
        }
        td {
          padding: 3px 0;
          vertical-align: top;
        }
        td.label {
          width: 32%;
          padding-right: 10px;
          font-weight: 700;
        }
        td.value {
          border-bottom: 1px dotted #6b7280;
        }
        .empty {
          color: #9ca3af;
        }
        .body-copy p {
          margin: 0 0 4px;
          text-align: justify;
        }
        .footer {
          margin-top: 20px;
          display: flex;
          justify-content: flex-end;
        }
        .signature-box {
          width: 250px;
          text-align: center;
        }
        .signature-box .date {
          margin-bottom: 6px;
          font-style: italic;
        }
        .signature-box .role {
          font-weight: 700;
          text-transform: uppercase;
        }
        .signature-box .note {
          margin-top: 54px;
          font-style: italic;
        }
      </style>
    </head>
    <body>
      <div class="document">
        <div class="header">
          <div class="header-block">
            <strong>Trường Đại học Giao thông Vận tải</strong>
            <div class="subline">Hệ thống IT - Smart - UTC</div>
            <div class="divider"></div>
          </div>
          <div class="header-block">
            <strong>Cộng hòa Xã hội Chủ nghĩa Việt Nam</strong>
            <div class="subline">Độc lập - Tự do - Hạnh phúc</div>
            <div class="divider"></div>
          </div>
        </div>

        <div class="title">${escapeHtml(title)}</div>

        <div class="recipient">
          <strong>Kính gửi:</strong>
          ${recipientsHtml}
        </div>

        <div class="intro">
          Tôi tên là ${escapeHtml(applicantName || "........................................................")},
          ${introSuffix ? escapeHtml(introSuffix) + "," : ""}
          là sinh viên có nhu cầu làm đơn theo nội dung dưới đây.
        </div>

        <div class="section">
          <div class="section-title">Thông tin người làm đơn</div>
          <table>
            <tbody>${fieldRows}</tbody>
          </table>
        </div>

        <div class="section">
          <div class="section-title">Nội dung đề nghị</div>
          <div class="body-copy">
            ${renderBodyHtml(formData, values)}
          </div>
        </div>

        <div class="commitment">
          <strong>Cam kết:</strong> Tôi xin cam đoan những thông tin trên là đúng sự thật và chịu trách nhiệm trước Nhà trường về nội dung đã khai.
        </div>

        <div class="footer">
          <div class="signature-box">
            <div class="date">${dateLine}</div>
            <div class="role">Người làm đơn</div>
            <div class="note">(Ký và ghi rõ họ tên)</div>
          </div>
        </div>
      </div>
    </body>
  </html>`;
}

function printHtmlDocument(html: string) {
  const iframe = document.createElement("iframe");
  iframe.style.position = "fixed";
  iframe.style.right = "0";
  iframe.style.bottom = "0";
  iframe.style.width = "0";
  iframe.style.height = "0";
  iframe.style.border = "0";
  iframe.setAttribute("aria-hidden", "true");
  document.body.appendChild(iframe);

  const frameWindow = iframe.contentWindow;
  const frameDocument = frameWindow?.document;
  if (!frameWindow || !frameDocument) {
    iframe.remove();
    throw new Error("Không thể khởi tạo khung in tài liệu.");
  }

  frameDocument.open();
  frameDocument.write(html);
  frameDocument.close();

  const cleanup = () => {
    window.setTimeout(() => {
      iframe.remove();
    }, 500);
  };

  frameWindow.onafterprint = cleanup;
  window.setTimeout(() => {
    frameWindow.focus();
    frameWindow.print();
  }, 250);
}

export function FormSidePanel({ isOpen, onClose, formData }: FormSidePanelProps) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (formData) {
      const initialValues: Record<string, string> = {};
      formData.fields.forEach((field) => {
        initialValues[field.id] = "";
      });
      setValues(initialValues);
      setError(null);
    }
  }, [formData]);

  const filledTemplate = useMemo(() => {
    if (!formData) {
      return "";
    }
    return fillTemplate(formData.template, values);
  }, [formData, values]);

  const handleInputChange = (id: string, value: string) => {
    setValues((prev) => ({ ...prev, [id]: value }));
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(filledTemplate);
  };

  const handleDownloadPdf = async () => {
    if (!formData) {
      return;
    }

    setIsDownloading(true);
    setError(null);

    try {
      printHtmlDocument(buildPrintableFormHtml(formData, values));
    } catch (downloadError) {
      setError(
        downloadError instanceof Error ? downloadError.message : "Không thể tạo bản in PDF"
      );
    } finally {
      setIsDownloading(false);
    }
  };

  if (!isOpen || !formData) return null;

  return (
    <div className="flex h-full w-[420px] flex-col border-l bg-background shadow-xl transition-all duration-300 ease-in-out">
      <div className="flex items-center justify-between border-b bg-muted/30 p-4">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-primary" />
          <div>
            <h3 className="text-lg font-semibold">{formData.title || "Biểu mẫu"}</h3>
            {formData.description ? (
              <p className="text-xs text-muted-foreground">{formData.description}</p>
            ) : null}
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex-1 space-y-6 overflow-y-auto p-4">
        {formData.workflow ? (
          <div className="space-y-4 rounded-xl border bg-muted/20 p-4">
            <div>
              <h4 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
                Thủ tục
              </h4>
              <p className="mt-2 font-medium">{formData.workflow.title}</p>
              {formData.workflow.summary ? (
                <p className="mt-1 text-sm text-muted-foreground">{formData.workflow.summary}</p>
              ) : null}
            </div>

            {formData.workflow.eligibility?.length ? (
              <div>
                <p className="text-sm font-medium">Điều kiện</p>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                  {formData.workflow.eligibility.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {formData.workflow.requiredDocuments?.length ? (
              <div>
                <p className="text-sm font-medium">Hồ sơ cần chuẩn bị</p>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                  {formData.workflow.requiredDocuments.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {formData.workflow.steps?.length ? (
              <div>
                <p className="text-sm font-medium">Các bước thực hiện</p>
                <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-muted-foreground">
                  {formData.workflow.steps.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ol>
              </div>
            ) : null}

            {formData.workflow.contactOffice ? (
              <div>
                <p className="text-sm font-medium">Đơn vị liên hệ</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {formData.workflow.contactOffice}
                </p>
              </div>
            ) : null}
          </div>
        ) : null}

        <div className="space-y-4">
          <h4 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
            Điền thông tin
          </h4>
          <div className="grid gap-4">
            {formData.fields.map((field) => (
              <div key={field.id} className="space-y-2">
                <Label htmlFor={field.id}>{field.label}</Label>
                <Input
                  id={field.id}
                  value={values[field.id] || ""}
                  onChange={(e) => handleInputChange(field.id, e.target.value)}
                  placeholder={`Nhập ${field.label.toLowerCase()}...`}
                />
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4 border-t pt-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
              Xem trước
            </h4>
          </div>
          <Card className="border-dashed bg-muted/30">
            <CardContent className="prose prose-sm max-w-none p-4 text-sm dark:prose-invert">
              <MarkdownContent content={filledTemplate} />
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="space-y-3 border-t bg-muted/30 p-4">
        {error ? <p className="text-xs text-destructive">{error}</p> : null}
        <div className="flex gap-3">
          <Button className="flex-1" onClick={handleCopy}>
            <Check className="mr-2 h-4 w-4" /> Sao chép nội dung
          </Button>
          <Button
            className="flex-1"
            variant="outline"
            onClick={handleDownloadPdf}
            disabled={isDownloading}
          >
            {isDownloading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Download className="mr-2 h-4 w-4" />
            )}
            In / lưu PDF
          </Button>
        </div>
      </div>
    </div>
  );
}
