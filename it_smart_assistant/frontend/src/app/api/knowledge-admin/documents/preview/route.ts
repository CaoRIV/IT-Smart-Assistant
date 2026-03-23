import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";

export async function GET(request: NextRequest) {
  try {
    const accessToken = request.cookies.get("access_token")?.value;

    if (!accessToken) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }

    const relativePath = request.nextUrl.searchParams.get("relative_path");
    if (!relativePath) {
      return NextResponse.json({ detail: "relative_path is required" }, { status: 400 });
    }

    const data = await backendFetch("/api/v1/knowledge-admin/documents/preview", {
      params: { relative_path: relativePath },
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof BackendApiError) {
      return NextResponse.json(
        { detail: error.data ?? "Khong the tai ban xem truoc tai lieu" },
        { status: error.status }
      );
    }

    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
