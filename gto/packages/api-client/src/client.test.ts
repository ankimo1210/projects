import { test } from "node:test";
import assert from "node:assert/strict";
import { ApiError, createApiClient } from "./client.ts";

type Call = { url: string; init: RequestInit };

function mockFetch(
  responder: (url: string, init: RequestInit) => Response | Promise<Response>,
): { fetchFn: typeof fetch; calls: Call[] } {
  const calls: Call[] = [];
  const fetchFn = (async (input: any, init?: any) => {
    calls.push({ url: String(input), init: init ?? {} });
    return responder(String(input), init ?? {});
  }) as typeof fetch;
  return { fetchFn, calls };
}

const json = (body: unknown, status = 200, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });

test("GET /api/health hits the right URL without auth header", async () => {
  const { fetchFn, calls } = mockFetch(() => json({ status: "ok" }));
  const client = createApiClient({ baseUrl: "https://api.example.com/", fetchFn });
  const res = await client.health();
  assert.deepEqual(res, { status: "ok" });
  assert.equal(calls[0]!.url, "https://api.example.com/api/health");
  const headers = calls[0]!.init.headers as Record<string, string>;
  assert.equal(headers["Authorization"], undefined);
});

test("bearer token from getToken is attached; JSON body posted", async () => {
  const { fetchFn, calls } = mockFetch(() => json({ hands: [], errors: [] }));
  const client = createApiClient({
    baseUrl: "https://api.example.com",
    fetchFn,
    getToken: async () => "jwt-123",
  });
  await client.parseHandHistory("PokerStars Hand #1 ...");
  const call = calls[0]!;
  assert.equal(call.url, "https://api.example.com/api/review/parse");
  const headers = call.init.headers as Record<string, string>;
  assert.equal(headers["Authorization"], "Bearer jwt-123");
  assert.equal(headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(String(call.init.body)), { text: "PokerStars Hand #1 ..." });
});

test("FastAPI detail body becomes the ApiError message", async () => {
  const { fetchFn } = mockFetch(() => json({ detail: "login required" }, 401));
  const client = createApiClient({ baseUrl: "http://x", fetchFn });
  await assert.rejects(
    () => client.health(),
    (e: unknown) => e instanceof ApiError && e.status === 401 && e.message === "login required",
  );
});

test("429 exposes Retry-After seconds", async () => {
  const { fetchFn } = mockFetch(() =>
    json({ detail: "rate limited" }, 429, { "Retry-After": "37" }),
  );
  const client = createApiClient({ baseUrl: "http://x", fetchFn });
  await assert.rejects(
    () => client.health(),
    (e: unknown) => e instanceof ApiError && e.status === 429 && e.retryAfterS === 37,
  );
});

test("non-JSON error body falls back to raw text", async () => {
  const { fetchFn } = mockFetch(() => new Response("Bad Gateway", { status: 502 }));
  const client = createApiClient({ baseUrl: "http://x", fetchFn });
  await assert.rejects(
    () => client.health(),
    (e: unknown) => e instanceof ApiError && e.status === 502 && e.message === "Bad Gateway",
  );
});

test("network failure wraps into ApiError with null status", async () => {
  const fetchFn = (async () => {
    throw new TypeError("Network request failed");
  }) as unknown as typeof fetch;
  const client = createApiClient({ baseUrl: "http://x", fetchFn });
  await assert.rejects(
    () => client.health(),
    (e: unknown) =>
      e instanceof ApiError && e.status === null && /Network request failed/.test(e.message),
  );
});

test("caller cancellation propagates the original abort error", async () => {
  const controller = new AbortController();
  const fetchFn = (async (_input: any, init?: any) => {
    controller.abort();
    (init?.signal as AbortSignal).throwIfAborted();
    return json({});
  }) as typeof fetch;
  const client = createApiClient({ baseUrl: "http://x", fetchFn });
  await assert.rejects(
    () => client.parseHandHistory("text", controller.signal),
    (e: unknown) => !(e instanceof ApiError), // raw AbortError, not wrapped
  );
});

test("timeout produces an ApiError mentioning the timeout", async () => {
  const fetchFn = (async (_input: any, init?: any) => {
    const signal = init?.signal as AbortSignal;
    await new Promise((_, reject) => {
      signal.addEventListener("abort", () => reject(signal.reason));
    });
    return json({});
  }) as typeof fetch;
  const client = createApiClient({ baseUrl: "http://x", fetchFn, timeoutMs: 20 });
  // AbortSignal.timeout timers are unref'ed in Node — hold the event loop
  // open long enough for the 20ms timeout to actually fire.
  const keepAlive = setTimeout(() => {}, 1_000);
  try {
    await assert.rejects(
      () => client.health(),
      (e: unknown) => e instanceof ApiError && /timed out after 20ms/.test(e.message),
    );
  } finally {
    clearTimeout(keepAlive);
  }
});
