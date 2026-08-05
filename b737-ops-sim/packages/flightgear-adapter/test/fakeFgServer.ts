import { WebSocketServer, type WebSocket } from 'ws';

/**
 * Minimal emulation of FlightGear's httpd /PropertyListener endpoint for
 * protocol-level adapter tests (FlightGear itself is not installed in CI).
 * Semantics mirrored: addListener/get/set commands, {path,value} pushes.
 */
export class FakeFgServer {
  private wss: WebSocketServer;
  readonly properties = new Map<string, number | boolean | string>();
  readonly listenedPaths = new Set<string>();
  readonly setLog: { path: string; value: number | boolean | string }[] = [];
  private clients = new Set<WebSocket>();
  private respondToGets = true;

  constructor(port: number) {
    this.wss = new WebSocketServer({ port, path: '/PropertyListener' });
    this.wss.on('connection', (ws) => {
      this.clients.add(ws);
      ws.on('close', () => this.clients.delete(ws));
      ws.on('message', (data) => {
        const msg = JSON.parse(String(data)) as {
          command: string;
          node: string;
          value?: number | boolean | string;
        };
        if (msg.command === 'addListener') {
          this.listenedPaths.add(msg.node);
        } else if (msg.command === 'get') {
          const value = this.properties.get(msg.node);
          if (this.respondToGets && value !== undefined) {
            ws.send(JSON.stringify({ path: msg.node, value }));
          }
        } else if (msg.command === 'set' && msg.value !== undefined) {
          this.properties.set(msg.node, msg.value);
          this.setLog.push({ path: msg.node, value: msg.value });
        }
      });
    });
  }

  /** Open client sockets — used to prove the adapter keeps exactly one. */
  get clientCount(): number {
    return this.clients.size;
  }

  /** Update a property and push to clients listening on it (like real FG). */
  push(path: string, value: number | boolean | string): void {
    this.properties.set(path, value);
    if (!this.listenedPaths.has(path)) return;
    const frame = JSON.stringify({ path, value });
    for (const ws of this.clients) ws.send(frame);
  }

  /** Send an arbitrary frame to exercise the adapter's untrusted boundary. */
  sendRaw(frame: string | Record<string, unknown>): void {
    const payload = typeof frame === 'string' ? frame : JSON.stringify(frame);
    for (const ws of this.clients) ws.send(payload);
  }

  setGetResponsesEnabled(enabled: boolean): void {
    this.respondToGets = enabled;
  }

  async close(): Promise<void> {
    for (const ws of this.clients) ws.terminate();
    await new Promise<void>((resolve) => this.wss.close(() => resolve()));
  }
}
