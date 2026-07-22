import { useEffect, useRef, useState } from "react";
import { initialDsky, reduceServerMsg } from "./reducer";
import type { DskyView } from "./types";

const WS_URL = "ws://127.0.0.1:8642/ws";

export function useDskySocket(): [DskyView, (key: string) => void, (pressed: boolean) => void] {
  const [state, setState] = useState<DskyView>(initialDsky);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    let closed = false;
    const connect = () => {
      const sock = new WebSocket(WS_URL);
      ws.current = sock;
      sock.onopen = () => setState((s) => ({ ...s, connected: true }));
      sock.onmessage = (ev) =>
        setState((s) => reduceServerMsg(s, JSON.parse(ev.data)));
      sock.onclose = () => {
        setState((s) => ({ ...s, connected: false }));
        if (!closed) setTimeout(connect, 1000);
      };
    };
    connect();
    return () => { closed = true; ws.current?.close(); };
  }, []);

  const sendKey = (key: string) =>
    ws.current?.send(JSON.stringify({ type: "key", key }));
  const sendPro = (pressed: boolean) =>
    ws.current?.send(JSON.stringify({ type: "pro", pressed }));
  return [state, sendKey, sendPro];
}
