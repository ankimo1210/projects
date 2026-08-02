import { BackendModeSchema, type BackendMode } from '@b737/shared';

/** Bridge configuration from environment variables (documented in README). */
export interface BridgeConfig {
  backendMode: BackendMode;
  port: number;
  host: string;
  stateRateHz: number;
  fgHost: string;
  fgHttpPort: number;
  logLevel: string;
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): BridgeConfig {
  const mode = BackendModeSchema.safeParse(env.FLIGHT_BACKEND ?? 'mock');
  if (!mode.success) {
    throw new Error(`FLIGHT_BACKEND must be 'mock' or 'flightgear', got '${env.FLIGHT_BACKEND}'`);
  }
  const stateRateHz = Number(env.STATE_RATE_HZ ?? 30);
  if (!(stateRateHz >= 5 && stateRateHz <= 60)) {
    throw new Error(`STATE_RATE_HZ must be 5..60, got '${env.STATE_RATE_HZ}'`);
  }
  return {
    backendMode: mode.data,
    port: Number(env.BRIDGE_PORT ?? 8737),
    host: env.BRIDGE_HOST ?? '127.0.0.1',
    stateRateHz,
    // In WSL2 NAT mode the Windows host is NOT 127.0.0.1 — see FLIGHTGEAR_SETUP.md.
    fgHost: env.FG_HOST ?? '127.0.0.1',
    fgHttpPort: Number(env.FG_HTTP_PORT ?? 5500),
    logLevel: env.LOG_LEVEL ?? 'info',
  };
}
