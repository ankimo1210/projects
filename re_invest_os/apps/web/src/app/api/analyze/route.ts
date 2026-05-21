/**
 * /api/analyze プロキシ
 *
 * ブラウザ → Next.js Route Handler → FastAPI /analyze
 *
 * 目的:
 * - CORS回避 (同一オリジンで完結)
 * - 将来的にサーバ側でユーザーIDを付与・レート制限・ログを集約
 * - API_BASE をクライアントに露出しない
 */
import { NextResponse } from "next/server";

const API_BASE = process.env.API_BASE ?? "http://127.0.0.1:8001";

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  try {
    const upstream = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
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
