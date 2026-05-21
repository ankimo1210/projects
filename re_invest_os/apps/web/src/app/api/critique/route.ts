import { NextResponse } from "next/server";
const API_BASE = process.env.API_BASE ?? "http://127.0.0.1:8001";
export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body) return NextResponse.json({ error: "Invalid body" }, { status: 400 });
  try {
    const r = await fetch(`${API_BASE}/critique`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body), cache: "no-store",
    });
    return new NextResponse(await r.text(), { status: r.status, headers: { "Content-Type": "application/json" } });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 502 });
  }
}
