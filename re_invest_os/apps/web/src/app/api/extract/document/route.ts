/**
 * /api/extract/document プロキシ → FastAPI POST /extract/document
 * multipart/form-data をストリームで中継。
 */
import { NextResponse } from "next/server";

const API_BASE = process.env.API_BASE ?? "http://127.0.0.1:8001";

export async function POST(request: Request) {
  let formData: FormData;
  try {
    formData = await request.formData();
  } catch {
    return NextResponse.json({ error: "Invalid multipart body" }, { status: 400 });
  }

  const upstreamForm = new FormData();
  for (const [key, value] of formData.entries()) {
    upstreamForm.append(key, value);
  }

  try {
    const upstream = await fetch(`${API_BASE}/extract/document`, {
      method: "POST",
      body: upstreamForm,
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
