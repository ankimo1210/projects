import { useEffect, useRef, useState } from "react";
import { initialDsky, reduceServerMsg } from "./reducer";
import type { DskyView } from "./types";
import { parseServerMsg } from "../telemetry/dispatch";
import type { TelemetryFrame } from "../telemetry/types";

const WS_URL = "ws://127.0.0.1:8642/ws";

export interface DskySocket {
  state: DskyView;
  sendKey: (key: string) => void;
  sendPro: (pressed: boolean) => void;
  sendRod: (up: boolean) => void;
}

export function useDskySocket(
  onTelemetry?: (f: TelemetryFrame) => void,
): DskySocket {
  const [state, setState] = useState<DskyView>(initialDsky);
  const ws = useRef<WebSocket | null>(null);
  // Keep the latest callback without re-opening the socket on every render.
  const telemCb = useRef(onTelemetry);
  telemCb.current = onTelemetry;

  useEffect(() => {
    let closed = false;
    const connect = () => {
      const sock = new WebSocket(WS_URL);
      ws.current = sock;
      sock.onopen = () => setState((s) => ({ ...s, connected: true }));
      sock.onmessage = (ev) => {
        const d = parseServerMsg(ev.data);
        if (d.kind === "dsky") setState((s) => reduceServerMsg(s, d.msg));
        else if (d.kind === "telemetry") telemCb.current?.(d.frame);
      };
      sock.onclose = () => {
        setState((s) => ({ ...s, connected: false }));
        if (!closed) setTimeout(connect, 1000);
      };
    };
    connect();
    return () => {
      closed = true;
      ws.current?.close();
    };
  }, []);

  const sendKey = (key: string) =>
    ws.current?.send(JSON.stringify({ type: "key", key }));
  const sendPro = (pressed: boolean) =>
    ws.current?.send(JSON.stringify({ type: "pro", pressed }));
  const sendRod = (up: boolean) =>
    ws.current?.send(JSON.stringify({ type: "rod", up }));
  return { state, sendKey, sendPro, sendRod };
}
