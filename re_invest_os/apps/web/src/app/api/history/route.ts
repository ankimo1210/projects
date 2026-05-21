import { NextResponse } from "next/server";
const API_BASE = process.env.API_BASE ?? "http://127.0.0.1:8001";
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limit = searchParams.get("limit") ?? "20";
  try {
    const r = await fetch(`${API_BASE}/analyses?limit=${limit}`, { cache: "no-store" });
    return new NextResponse(await r.text(), { status: r.status, headers: { "Content-Type": "application/json" } });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 502 });
  }
}
