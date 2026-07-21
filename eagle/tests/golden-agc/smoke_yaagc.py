#!/usr/bin/env python3
"""Boot yaAGC with Luminary099, press RSET, expect packet traffic back."""
import socket, subprocess, sys, time

PORT = 19897
AGC = ["build/agc/yaAGC", "--core=build/agc/Luminary099.bin", f"--port={PORT}"]

def key_packet(code: int) -> bytes:  # DSKY keycode -> ch 015 packet
    ch, d = 0o15, code & 0x7FFF
    return bytes([ch >> 3, 0x40 | ((ch & 7) << 3) | (d >> 12),
                  0x80 | ((d >> 6) & 0x3F), 0xC0 | (d & 0x3F)])

proc = subprocess.Popen(AGC, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    s = None
    for _ in range(50):
        try:
            s = socket.create_connection(("127.0.0.1", PORT), timeout=0.2); break
        except OSError:
            time.sleep(0.1)
    assert s, "could not connect to yaAGC"
    s.sendall(key_packet(0o22))  # RSET
    s.settimeout(5.0)
    data = s.recv(4096)
    assert len(data) >= 4, "no packet traffic from yaAGC"
    print(f"OK: received {len(data)} bytes from yaAGC")
finally:
    proc.terminate(); proc.wait(timeout=5)
