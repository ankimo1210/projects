// Thin client for the v1.0 app-facing API surface: health + hand-history
// parse (spec §7 — the app calls nothing else except the entitlement
// endpoints, which land here once the P4 backend routes exist).
//
// Auth contract (src/gto/api/auth.py): "Authorization: Bearer <supabase JWT>";
// errors arrive as FastAPI {"detail": "..."} bodies; 429 carries Retry-After.

import type { ParseResponse } from "./review-types.ts";

export interface ApiClientOptions {
  baseUrl: string;
  /** Returns the current Supabase access token, or null when signed out. */
  getToken?: () => Promise<string | null> | string | null;
  /** Injectable for tests and custom runtimes. Defaults to global fetch. */
  fetchFn?: typeof fetch;
  /** Per-request timeout in milliseconds (default 15000). */
  timeoutMs?: number;
}

export class ApiError extends Error {
  override name = "ApiError";
  readonly status: number | null;
  /** Seconds from a 429 Retry-After header, when present. */
  readonly retryAfterS: number | null;

  // No TS parameter properties here: node runs these files in strip-only
  // mode, which rejects constructor-parameter modifiers.
  constructor(message: string, status: number | null, retryAfterS: number | null = null) {
    super(message);
    this.status = status;
    this.retryAfterS = retryAfterS;
  }
}

export interface ApiClient {
  health(): Promise<{ status: string }>;
  parseHandHistory(text: string, signal?: AbortSignal): Promise<ParseResponse>;
}

export function createApiClient(options: ApiClientOptions): ApiClient {
  const { baseUrl, getToken, timeoutMs = 15_000 } = options;
  const fetchFn = options.fetchFn ?? fetch;
  const root = baseUrl.replace(/\/+$/, "");

  async function request<T>(
    path: string,
    init: { method: "GET" | "POST"; body?: unknown; signal?: AbortSignal },
  ): Promise<T> {
    const headers: Record<string, string> = {};
    if (init.body !== undefined) headers["Content-Type"] = "application/json";
    const token = await (typeof getToken === "function" ? getToken() : null);
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const timeout = AbortSignal.timeout(timeoutMs);
    const signal = init.signal ? AbortSignal.any([init.signal, timeout]) : timeout;

    let res: Response;
    try {
      res = await fetchFn(`${root}${path}`, {
        method: init.method,
        headers,
        body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
        signal,
      });
    } catch (e) {
      if (init.signal?.aborted) throw e; // caller cancelled — propagate as-is
      if (timeout.aborted) throw new ApiError(`request timed out after ${timeoutMs}ms`, null);
      throw new ApiError(e instanceof Error ? e.message : String(e), null);
    }

    if (!res.ok) {
      let detail: string | null = null;
      const body = await res.text().catch(() => "");
      try {
        const parsed: unknown = JSON.parse(body);
        if (
          typeof parsed === "object" && parsed !== null &&
          typeof (parsed as { detail?: unknown }).detail === "string"
        ) {
          detail = (parsed as { detail: string }).detail;
        }
      } catch {
        // non-JSON error body — fall through to raw text
      }
      const retryHeader = res.headers.get("Retry-After");
      const retryAfterS =
        res.status === 429 && retryHeader !== null && /^\d+$/.test(retryHeader)
          ? Number(retryHeader)
          : null;
      throw new ApiError(detail ?? (body || res.statusText), res.status, retryAfterS);
    }
    return res.json() as Promise<T>;
  }

  return {
    health: () => request("/api/health", { method: "GET" }),
    parseHandHistory: (text, signal) =>
      request("/api/review/parse", { method: "POST", body: { text }, signal }),
  };
}
