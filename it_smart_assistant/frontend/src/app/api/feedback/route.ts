import { NextRequest, NextResponse } from "next/server";

import { backendFetch, BackendApiError } from "@/lib/server-api";

export async function POST(request: NextRequest) {
  try {
    const accessToken = request.cookies.get("access_token")?.value;

    if (!accessToken) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }

    const body = await request.json();

    const data = await backendFetch("/api/v1/feedback", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      const detail =
        (error.data as { detail?: string } | undefined)?.detail ||
        "Không thể lưu đánh giá";
      return NextResponse.json({ detail }, { status: error.status });
    }

    return NextResponse.json(
      { detail: "Lỗi máy chủ nội bộ" },
      { status: 500 },
    );
  }
}

