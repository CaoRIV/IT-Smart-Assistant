import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.text();
    const response = await fetch(`${BACKEND_URL}/api/v1/form-exports/pdf`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body,
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      return NextResponse.json(
        { detail: payload?.detail || "Không thể tạo PDF" },
        { status: response.status }
      );
    }

    const pdfBuffer = await response.arrayBuffer();
    return new NextResponse(pdfBuffer, {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition":
          response.headers.get("Content-Disposition") ?? 'attachment; filename="bieu_mau.pdf"',
      },
    });
  } catch {
    return NextResponse.json({ detail: "Lỗi máy chủ nội bộ" }, { status: 500 });
  }
}
