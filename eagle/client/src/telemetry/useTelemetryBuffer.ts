import { useCallback, useRef, useState } from "react";
import { TelemetryRing } from "./telemetryRing";
import type { PhaseChange, TelemetryFrame } from "./types";

export interface TelemetryBuffer {
  ring: TelemetryRing;
  version: number;
  latest: TelemetryFrame | null;
  phases: PhaseChange[];
  push: (f: TelemetryFrame) => void;
}

/**
 * A telemetry ring held in a ref (so 10 Hz pushes don't churn React state),
 * exposed with a monotonic `version` that bumps once per push to trigger a
 * render. Charts read `ring.frames()` and diff on `version`.
 */
export function useTelemetryBuffer(): TelemetryBuffer {
  const ring = useRef<TelemetryRing | null>(null);
  if (!ring.current) ring.current = new TelemetryRing();
  const [version, setVersion] = useState(0);

  const push = useCallback((f: TelemetryFrame) => {
    ring.current!.push(f);
    setVersion(ring.current!.version);
  }, []);

  return {
    ring: ring.current,
    version,
    latest: ring.current.latest,
    phases: ring.current.phases,
    push,
  };
}
