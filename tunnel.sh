#!/usr/bin/env bash
# tunnel.sh — reverse tunnel: the relay host 127.0.0.1:8091 -> this machine 127.0.0.1:8081
# Run from the provider machine. The relay host's nginx proxies /capability -> 127.0.0.1:8091.
set -euo pipefail
RELAY_HOST="${RELAY_HOST:-user@relay.example.com}"
REMOTE_PORT="${REMOTE_PORT:-8091}"
LOCAL_PORT="${LOCAL_PORT:-8081}"

exec ssh -N -R "${REMOTE_PORT}:127.0.0.1:${LOCAL_PORT}" "$RELAY_HOST" \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3
