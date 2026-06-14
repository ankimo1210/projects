// GameSpec client for POST /api/solve (mode-matrix M1a + M1b flop async).
//
// Like hu-api.ts, this fetches relative `/api/...` URLs — Next dev/prod and
// the FastAPI backend are reachable on the same origin (rewrite/proxy), so no
// explicit base or NEXT_PUBLIC_API_BASE is hardcoded.
//
// river / turn+river resolve synchronously (one POST). flop is async: the POST
// returns 202 + a job handle, and the result is fetched by polling the job.

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
    abstraction?: { buckets_river?: number; buckets_turn?: number; max_table_gb?: number };
  };
}

export interface SolveResult {
  strategy: { action: string; freq: number }[];
  actions: string[];
  combo_strategies: { card_a: string; card_b: string; freqs: number[]; ev: number }[];
  ev: { ip: number; oop: number };
  equity: { ip: number; oop: number } | null;
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
    abstraction: { buckets_river: number; buckets_turn: number } | null;
    table_gb?: number | null;
    rake: { pct: number; cap_bb: number };
    equilibrium_claim: boolean;
  };
}

export interface FlopJobHandle {
  job_id: string;
  kind: string;
  status: string;
  est_gb: number;
  poll: string;
  note: string;
}

export interface JobStatus {
  id: string;
  kind: string;
  status: "queued" | "running" | "done" | "error" | "cancelled";
  est_gb: number;
  queued_s: number;
  elapsed_s: number | null;
  error: string | null;
  result?: SolveResult;
}

const JSON_HEADERS = { "Content-Type": "application/json" };

function body(req: SolveRequest) {
  return JSON.stringify({ game: "cash", variant: "nlhe", table: "hu", spot: "postflop", ...req });
}

/** A setTimeout that rejects with AbortError if the signal fires first. */
function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(new DOMException("aborted", "AbortError"));
    const t = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(t);
        reject(new DOMException("aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

/** Synchronous solve for river (5 cards) / turn+river (4 cards). */
export async function customSolve(req: SolveRequest, signal?: AbortSignal): Promise<SolveResult> {
  const res = await fetch(`/api/solve`, { method: "POST", headers: JSON_HEADERS, body: body(req), signal });
  if (!res.ok) {
    const b = await res.text().catch(() => res.statusText);
    throw new Error(`solve failed (${res.status}): ${b}`);
  }
  return res.json();
}

/** Submit a flop (3 cards) solve to the async job tier. Returns the handle. */
export async function submitFlop(req: SolveRequest, signal?: AbortSignal): Promise<FlopJobHandle> {
  const res = await fetch(`/api/solve`, { method: "POST", headers: JSON_HEADERS, body: body(req), signal });
  if (res.status !== 202) {
    const b = await res.text().catch(() => res.statusText);
    throw new Error(`flop submit failed (${res.status}): ${b}`);
  }
  return res.json();
}

export async function pollJob(jobId: string, signal?: AbortSignal): Promise<JobStatus> {
  const res = await fetch(`/api/solve/jobs/${jobId}`, { signal });
  if (!res.ok) {
    const b = await res.text().catch(() => res.statusText);
    throw new Error(`job poll failed (${res.status}): ${b}`);
  }
  return res.json();
}

export async function cancelJob(jobId: string): Promise<void> {
  await fetch(`/api/solve/jobs/${jobId}`, { method: "DELETE" }).catch(() => {});
}

/**
 * Submit a flop solve and poll until it finishes. `onStatus` is called on each
 * poll so the UI can show queued/running + elapsed. Resolves with the result
 * envelope, or throws on job error.
 *
 * `opts.signal` lets the caller stop polling (component unmount / new input /
 * cancel button) — the loop and any in-flight fetch abort promptly. `timeoutMs`
 * bounds a job that never finishes (e.g. stuck queued) so the loop can't spin
 * forever.
 */
export async function solveFlopAsync(
  req: SolveRequest,
  onStatus: (s: JobStatus) => void,
  onHandle?: (h: FlopJobHandle) => void,
  opts: { intervalMs?: number; timeoutMs?: number; signal?: AbortSignal } = {},
): Promise<SolveResult> {
  const { intervalMs = 1500, timeoutMs = 20 * 60_000, signal } = opts;
  const handle = await submitFlop(req, signal);
  onHandle?.(handle);
  const start = Date.now();
  for (;;) {
    if (signal?.aborted) throw new DOMException("aborted", "AbortError");
    const st = await pollJob(handle.job_id, signal);
    onStatus(st);
    if (st.status === "done" && st.result) return st.result;
    if (st.status === "error") throw new Error(st.error ?? "flop solve failed");
    if (st.status === "cancelled") throw new Error("flop solve cancelled");
    if (Date.now() - start > timeoutMs) throw new Error("flop solve timed out");
    await sleep(intervalMs, signal);
  }
}
