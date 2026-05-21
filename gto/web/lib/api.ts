// Empty string = use relative path (proxied through Next.js rewrites)
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export interface EquityResult {
  hero_equity: number;
  villain_equity: number;
  tie: number;
  iterations: number;
}

export async function fetchEquity(params: {
  hero: string;
  villain: string;
  board?: string;
  iterations?: number;
}): Promise<EquityResult> {
  const base = API_BASE || (typeof window !== "undefined" ? window.location.origin : "");
  const url = new URL(`${base}/api/equity`);
  url.searchParams.set("hero", params.hero);
  url.searchParams.set("villain", params.villain);
  if (params.board) url.searchParams.set("board", params.board);
  if (params.iterations) url.searchParams.set("iterations", String(params.iterations));

  const res = await fetch(url.toString());
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "API error");
  }
  return res.json();
}
