export interface SolveRequest {
  pot_bb: number;
  effective_stack_bb: number;
  board: string[];
  iterations: number;
  max_bets: number;
}

export interface ActionFreq {
  action: string;
  freq: number;
}

export interface SolveResponse {
  strategy: ActionFreq[];
  exploitability: number;
  iterations: number;
  backend: string;
}

export async function solveSpot(req: SolveRequest): Promise<SolveResponse> {
  const res = await fetch("/api/solver/solve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(err);
  }
  return res.json();
}
