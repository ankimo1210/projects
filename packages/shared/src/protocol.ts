import { z } from 'zod';
import { AircraftStateSchema } from './aircraftState.js';
import {
  AircraftCommandSchema,
  CommandResultSchema,
  ScenarioInitialStateSchema,
} from './commands.js';

/** WebSocket wire protocol, browser ⇄ bridge. Versioned; both sides check. */
export const PROTOCOL_VERSION = 1;

export const BackendModeSchema = z.enum(['mock', 'flightgear']);
export type BackendMode = z.infer<typeof BackendModeSchema>;

export const BackendStatusSchema = z.object({
  mode: BackendModeSchema,
  connected: z.boolean(),
  detail: z.string(),
  /** ms since the backend last produced a state sample; null = never. */
  lastStateAgeMs: z.number().nullable(),
  stateRateHz: z.number(),
});
export type BackendStatus = z.infer<typeof BackendStatusSchema>;

// ---------------------------------------------------------------- client → bridge

export const ClientMessageSchema = z.discriminatedUnion('t', [
  z.object({
    t: z.literal('hello'),
    protocolVersion: z.number().int(),
    clientName: z.string().optional(),
  }),
  z.object({
    t: z.literal('command'),
    seq: z.number().int(),
    sentAtMs: z.number(),
    command: AircraftCommandSchema,
  }),
  z.object({ t: z.literal('ping'), seq: z.number().int(), sentAtMs: z.number() }),
  z.object({
    t: z.literal('reset_scenario'),
    seq: z.number().int(),
    config: ScenarioInitialStateSchema,
  }),
]);
export type ClientMessage = z.infer<typeof ClientMessageSchema>;

// ---------------------------------------------------------------- bridge → client

export const ServerMessageSchema = z.discriminatedUnion('t', [
  z.object({
    t: z.literal('welcome'),
    protocolVersion: z.number().int(),
    backendMode: BackendModeSchema,
    stateRateHz: z.number(),
    serverTimeMs: z.number(),
  }),
  z.object({
    t: z.literal('state'),
    /** Monotonic per-connection sequence for stale/out-of-order detection. */
    seq: z.number().int(),
    state: AircraftStateSchema,
  }),
  z.object({
    t: z.literal('command_ack'),
    /** Echoes the client's command seq. */
    seq: z.number().int(),
    result: CommandResultSchema,
  }),
  z.object({
    t: z.literal('pong'),
    seq: z.number().int(),
    clientSentAtMs: z.number(),
    serverTimeMs: z.number(),
  }),
  z.object({ t: z.literal('backend_status'), status: BackendStatusSchema }),
  z.object({ t: z.literal('protocol_error'), message: z.string() }),
]);
export type ServerMessage = z.infer<typeof ServerMessageSchema>;

/** Parse helpers returning discriminated results instead of throwing. */
export function parseClientMessage(raw: string): ClientMessage | { parseError: string } {
  try {
    const parsed = ClientMessageSchema.safeParse(JSON.parse(raw));
    return parsed.success ? parsed.data : { parseError: parsed.error.message };
  } catch (e) {
    return { parseError: `invalid JSON: ${String(e)}` };
  }
}

export function parseServerMessage(raw: string): ServerMessage | { parseError: string } {
  try {
    const parsed = ServerMessageSchema.safeParse(JSON.parse(raw));
    return parsed.success ? parsed.data : { parseError: parsed.error.message };
  } catch (e) {
    return { parseError: `invalid JSON: ${String(e)}` };
  }
}
