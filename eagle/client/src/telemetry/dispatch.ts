import type { ServerMsg } from "../dsky/types";
import type { TelemetryFrame } from "./types";

/** A classified WS frame: a DSKY update, a telemetry frame, or ignorable. */
export type Dispatched =
  | { kind: "dsky"; msg: ServerMsg }
  | { kind: "telemetry"; frame: TelemetryFrame }
  | { kind: "ignore" };

/**
 * Parse and classify one raw WS payload. Malformed JSON and unknown types
 * are silently ignored (never thrown), so a stray frame can't kill the
 * socket handler.
 */
export function parseServerMsg(data: string): Dispatched {
  let msg: unknown;
  try {
    msg = JSON.parse(data);
  } catch {
    return { kind: "ignore" };
  }
  if (typeof msg !== "object" || msg === null || !("type" in msg)) {
    return { kind: "ignore" };
  }
  const type = (msg as { type: unknown }).type;
  if (type === "dsky_state") return { kind: "dsky", msg: msg as ServerMsg };
  if (type === "telemetry") {
    return { kind: "telemetry", frame: msg as unknown as TelemetryFrame };
  }
  return { kind: "ignore" };
}
