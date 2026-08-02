#!/usr/bin/env bash
# Print the Windows-host IP as seen from WSL2 (NAT mode) for FG_HOST.
# Usage:  FG_HOST=$(./scripts/fg-host-ip.sh) pnpm dev:fg
set -euo pipefail

# In WSL2 NAT mode the Windows host is the default gateway of eth0.
ip route show default | awk '{print $3; exit}'
