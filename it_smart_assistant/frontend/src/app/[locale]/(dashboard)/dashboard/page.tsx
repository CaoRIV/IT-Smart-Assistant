"use client";

import { useEffect, useState } from "react";
import {
  Bot,
  FileSignature,
  Loader2,
  MessageSquare,
  Star,
  Workflow,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui";
import { useAuth } from "@/hooks";
import { apiClient } from "@/lib/api-client";
import type {
  AnalyticsCountItem,
  AnalyticsIntentQualityItem,
  AnalyticsOverview,
} from "@/types";

const INTENT_LABELS: Record<string, string> = {
  knowledge_qa: "Tra cứu thông tin",
  tuition_lookup: "Tra cứu học phí",
  procedure_workflow: "Hướng dẫn thủ tục",
  form_fill: "Điền biểu mẫu",
  attachment_qa: "Hỏi đáp từ tệp đính kèm",
  course_catalog: "Tra cứu môn học",
  casual: "Trao đổi chung",
};

const TOOL_LABELS: Record<string, string> = {
  search_student_knowledge: "Tra cứu tri thức",
  build_procedure_workflow: "Hướng dẫn thủ tục",
  generate_form: "Tạo biểu mẫu",
  search_course_catalog: "Tra cứu môn học",
};

function formatIntentLabel(label: string) {
  return INTENT_LABELS[label] ?? label.replaceAll("_", " ");
}

function formatToolLabel(label: string) {
  return TOOL_LABELS[label] ?? label.replaceAll("_", " ");
}

function formatCountItems(items: AnalyticsCountItem[], kind: "intent" | "tool" | "default") {
  if (kind === "intent") {
    return items.map((item) => ({ ...item, label: formatIntentLabel(item.label) }));
  }

  if (kind === "tool") {
    return items.map((item) => ({ ...item, label: formatToolLabel(item.label) }));
  }

  return items;
}

function formatIntentQualityItems(items: AnalyticsIntentQualityItem[]) {
  return items.map((item) => ({ ...item, label: formatIntentLabel(item.label) }));
}

export default function DashboardPage() {
  const { user, isLoading: isAuthLoading } = useAuth();
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthLoading) {
      return;
    }

    if (user && user.role !== "admin") {
      setIsLoading(false);
      return;
    }

    const loadAnalytics = async () => {
      try {
        const data = await apiClient.get<AnalyticsOverview>("/analytics/overview");
        setAnalytics(data);
        setLoadError(null);
      } catch {
        setLoadError("Không thể tải dữ liệu thống kê");
      } finally {
        setIsLoading(false);
      }
    };

    loadAnalytics();
  }, [isAuthLoading, user]);

  if (!isAuthLoading && user && user.role !== "admin") {
    return (
      <div className="space-y-4 sm:space-y-6">
        <div>
          <h1 className="text-2xl font-bold sm:text-3xl">Tổng quan</h1>
          <p className="text-sm text-muted-foreground sm:text-base">
            Chào mừng quay lại{user.full_name ? `, ${user.full_name}` : ""}.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Trang này dành cho admin</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Tài khoản hiện tại không có quyền xem thống kê vận hành hệ thống.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const metricCards = analytics
    ? [
        { title: "Tổng cuộc trò chuyện", value: analytics.total_conversations, icon: MessageSquare },
        { title: "Câu trả lời của CHATBOT", value: analytics.assistant_messages, icon: Bot },
        { title: "Tỷ lệ phản hồi tốt", value: `${analytics.helpful_rate}%`, icon: Star },
        { title: "Lượt mở biểu mẫu", value: analytics.forms_opened, icon: FileSignature },
        { title: "Lượt hướng dẫn thủ tục", value: analytics.procedure_workflows, icon: Workflow },
        { title: "Tổng đánh giá", value: analytics.total_feedback, icon: MessageSquare },
      ]
    : [];

  return (
    <div className="space-y-4 sm:space-y-6">
      <div>
        <h1 className="text-2xl font-bold sm:text-3xl">Bảng điều hành</h1>
        <p className="text-sm text-muted-foreground sm:text-base">
          Theo dõi mức sử dụng và chất lượng phục vụ của CHATBOT.
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Đang tải thống kê...
        </div>
      ) : loadError ? (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-destructive">{loadError}</p>
          </CardContent>
        </Card>
      ) : analytics ? (
        <>
          <div className="space-y-2">
            <h2 className="text-lg font-semibold">Tổng quan vận hành</h2>
            <p className="text-sm text-muted-foreground">
              Nhìn nhanh số lượng trao đổi, mức độ hài lòng và nhu cầu hỗ trợ biểu mẫu.
            </p>
          </div>
          <div className="grid gap-4 sm:gap-6 md:grid-cols-2 xl:grid-cols-3">
            {metricCards.map((metric) => {
              const Icon = metric.icon;
              return (
                <Card key={metric.title}>
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center justify-between text-base">
                      <span>{metric.title}</span>
                      <Icon className="h-4 w-4 text-muted-foreground" />
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-semibold">{metric.value}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          <div className="space-y-2">
            <h2 className="text-lg font-semibold">Nội dung được quan tâm</h2>
            <p className="text-sm text-muted-foreground">
              Cho biết sinh viên đang hỏi nhiều về nội dung nào và đang dùng chức năng nào nhiều nhất.
            </p>
          </div>
          <div className="grid gap-4 sm:gap-6 lg:grid-cols-3">
            <RankingCard
              title="Nhóm nhu cầu được hỏi nhiều"
              items={formatCountItems(analytics.top_intents, "intent")}
              emptyText="Chưa có dữ liệu phân loại nhu cầu."
            />
            <RankingCard
              title="Câu hỏi được gửi nhiều"
              items={formatCountItems(analytics.top_questions, "default")}
              emptyText="Chưa có dữ liệu hội thoại."
            />
            <RankingCard
              title="Chức năng được dùng nhiều"
              items={formatCountItems(analytics.top_tools, "tool")}
              emptyText="Chưa có dữ liệu chức năng."
            />
          </div>

          <div className="space-y-2">
            <h2 className="text-lg font-semibold">Chất lượng cần theo dõi</h2>
            <p className="text-sm text-muted-foreground">
              Xác định nhóm câu hỏi còn yếu để ưu tiên bổ sung dữ liệu hoặc điều chỉnh luồng xử lý.
            </p>
          </div>
          <div className="grid gap-4 sm:gap-6 lg:grid-cols-2">
            <IntentQualityCard
              title="Nhóm cần cải thiện"
              items={formatIntentQualityItems(analytics.weakest_intents)}
              emptyText="Chưa có dữ liệu đánh giá theo nhóm."
            />
            <RankingCard
              title="Thủ tục được quan tâm"
              items={formatCountItems(analytics.top_procedures, "default")}
              emptyText="Chưa có dữ liệu thủ tục."
            />
          </div>
        </>
      ) : null}
    </div>
  );
}

interface RankingCardProps {
  title: string;
  items: AnalyticsCountItem[];
  emptyText: string;
}

function RankingCard({ title, items, emptyText }: RankingCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">{emptyText}</p>
        ) : (
          <div className="space-y-3">
            {items.map((item, index) => (
              <div
                key={`${title}-${item.label}-${index}`}
                className="flex items-start justify-between gap-3 text-sm"
              >
                <span className="line-clamp-2 flex-1">{item.label}</span>
                <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium">
                  {item.count} lượt
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface IntentQualityCardProps {
  title: string;
  items: AnalyticsIntentQualityItem[];
  emptyText: string;
}

function IntentQualityCard({ title, items, emptyText }: IntentQualityCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">{emptyText}</p>
        ) : (
          <div className="space-y-3">
            {items.map((item, index) => (
              <div
                key={`${title}-${item.label}-${index}`}
                className="rounded-lg border bg-background/60 p-3 text-sm"
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="font-medium">{item.label}</span>
                  <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium">
                    {item.helpful_rate}%
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
                  <span>Tổng đánh giá: {item.total_feedback}</span>
                  <span>Hữu ích: {item.helpful_feedback}</span>
                  <span>Chưa đúng: {item.unhelpful_feedback}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
