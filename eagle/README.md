# EAGLE: Apollo 11 Lunar Descent Simulator

EAGLE is a browser-based simulator of the Apollo 11 lunar descent phase, running the original Luminary099 Apollo Guidance Computer (AGC) code on the yaAGC virtual machine. A Rust runtime bridges the AGC core to a web-based Lunar Module DSKY (display/keyboard), enabling interactive navigation and landing sequences with authentic period-correct computer behavior.

## Quickstart

```bash
# Build AGC tools and assemble Luminary099 binary
make agc

# In one terminal: run AGC runtime
make dev-runtime

# In another terminal: serve the web client
make dev-client
```

Browse to `http://localhost:5173` to interact with the DSKY.

## Specification

See [docs/agc-channel-map.md](docs/agc-channel-map.md) for AGC I/O channel mappings and DSKY interface specification.

## References

- [VirtualAGC](https://www.ibiblio.org/apollo/) — AGC emulation and Luminary source
- [Apollo-11 repository](https://github.com/chrislgarry/Apollo-11) — annotated source code
