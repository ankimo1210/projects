// GameSpec client for POST /api/solve (mode-matrix M1a).
//
// Like hu-api.ts, this fetches relative `/api/...` URLs — Next dev/prod and
// the FastAPI backend are reachable on the same origin (rewrite/proxy), so no
// explicit base or NEXT_PUBLIC_API_BASE is hardcoded.

export interface SolveRequest {
  stack_bb: number;
  iterations?: number;
  rake: { model: "none" | "site" | "live" };
  config: {
    pot_bb: number;
    pot_type: "srp" | "3bet" | "4bet";
    board: string[];
    ranges: { ip?: string; oop?: string };
    action_tree?: { bet_sizes_pct?: number[]; max_raises?: number };
  };
}

export interface SolveResult {
  strategy: { action: string; freq: number }[];
  actions: string[];
  combo_strategies: { card_a: string; card_b: string; freqs: number[]; ev: number }[];
  ev: { ip: number; oop: number };
  equity: { ip: number; oop: number };
  exploitability: {
    nashconv_bb: number;
    per_hand_bb: number;
    br_gain_ip: number;
    br_gain_oop: number;
  };
  meta: {
    street: string;
    iterations: number;
    elapsed_s: number;
    rake: { pct: number; cap_bb: number };
    equilibrium_claim: boolean;
  };
}

export async function customSolve(req: SolveRequest): Promise<SolveResult> {
  const res = await fetch(`/api/solve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ game: "cash", variant: "nlhe", table: "hu", spot: "postflop", ...req }),
  });
  if (!res.ok) {
    const body = await res.text().catch(() => res.statusText);
    throw new Error(`solve failed (${res.status}): ${body}`);
  }
  return res.json();
}
