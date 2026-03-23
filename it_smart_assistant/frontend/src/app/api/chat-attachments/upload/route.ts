import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const accessToken = request.cookies.get("access_token")?.value;
    const formData = await request.formData();

    const response = await fetch(`${BACKEND_URL}/api/v1/chat-attachments/upload`, {
      method: "POST",
      headers: accessToken
        ? {
            Authorization: `Bearer ${accessToken}`,
          }
        : undefined,
      body: formData,
    });

    const text = await response.text();
    const payload = text ? JSON.parse(text) : null;

    if (!response.ok) {
      return NextResponse.json(
        { detail: payload?.detail || payload?.message || "Không thể tải tệp đính kèm lên" },
        { status: response.status }
      );
    }

    return NextResponse.json(payload, { status: 201 });
  } catch {
    return NextResponse.json({ detail: "Lỗi máy chủ nội bộ" }, { status: 500 });
  }
}
