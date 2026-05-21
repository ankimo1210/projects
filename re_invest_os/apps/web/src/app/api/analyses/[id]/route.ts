/**
 * /api/analyses/[id] — GET /analyses/:id (FastAPI) プロキシ
 */
import { NextResponse } from "next/server";

const API_BASE = process.env.API_BASE ?? "http://127.0.0.1:8001";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  try {
    const upstream = await fetch(`${API_BASE}/analyses/${id}`, {
      cache: "no-store",
    });
    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json(
      { error: "Upstream API unreachable", detail: message },
      { status: 502 },
    );
  }
}
