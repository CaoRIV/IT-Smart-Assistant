import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const accessToken = request.cookies.get("access_token")?.value;

    if (!accessToken) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }

    const formData = await request.formData();
    const response = await fetch(`${BACKEND_URL}/api/v1/knowledge-admin/documents/upload`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: formData,
    });

    const text = await response.text();
    const payload = text ? JSON.parse(text) : null;

    if (!response.ok) {
      return NextResponse.json(
      { detail: payload?.detail || payload?.message || "Không thể tải tài liệu lên" },
        { status: response.status }
      );
    }

    return NextResponse.json(payload, { status: 201 });
  } catch {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
