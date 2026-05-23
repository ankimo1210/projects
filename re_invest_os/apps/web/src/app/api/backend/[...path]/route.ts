/**
 * /api/backend/* — FastAPI 透過プロキシ (Deal Workspace 系で使用)
 *
 * ブラウザ → /api/backend/deals/...  → FastAPI /deals/...
 * 1 ファイルで GET/POST/PATCH/DELETE をハンドル。
 * 既存の per-endpoint プロキシ (analyze, max_offer 等) には触らない。
 */
import { NextResponse } from "next/server";

const API_BASE = process.env.API_BASE ?? "http://127.0.0.1:8001";

async function proxy(request: Request, params: { path: string[] }) {
  const path = "/" + params.path.join("/");
  const url = new URL(request.url);
  const target = `${API_BASE}${path}${url.search}`;

  const init: RequestInit = {
    method: request.method,
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  };
  if (request.method !== "GET" && request.method !== "DELETE") {
    init.body = await request.text();
  }

  try {
    const upstream = await fetch(target, init);
    const text = await upstream.text();
    if (upstream.status === 204 || !text) {
      return new NextResponse(null, { status: upstream.status });
    }
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

export async function GET(req: Request, ctx: { params: Promise<{ path: string[] }> }) {
  return proxy(req, await ctx.params);
}
export async function POST(req: Request, ctx: { params: Promise<{ path: string[] }> }) {
  return proxy(req, await ctx.params);
}
export async function PATCH(req: Request, ctx: { params: Promise<{ path: string[] }> }) {
  return proxy(req, await ctx.params);
}
export async function DELETE(req: Request, ctx: { params: Promise<{ path: string[] }> }) {
  return proxy(req, await ctx.params);
}
