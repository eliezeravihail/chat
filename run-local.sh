#!/usr/bin/env bash
# One-command local launch: starts the Python core service and the Baileys
# bridge together. Copy .env.example to .env, fill it in, then run ./run-local.sh
set -euo pipefail
cd "$(dirname "$0")"

# Load .env if present (exports every KEY=value line).
if [ -f .env ]; then set -a; . ./.env; set +a; fi

: "${OPENROUTER_KEY:?missing OPENROUTER_KEY — copy .env.example to .env and fill it in}"
: "${ALLOWED_WA_ID:?missing ALLOWED_WA_ID — your dedicated number, digits only e.g. 972501234567}"

echo "▶ starting core service on 127.0.0.1:8090 …"
uvicorn local_server:app --host 127.0.0.1 --port 8090 &
CORE_PID=$!
trap 'echo; echo "stopping core (pid $CORE_PID)"; kill $CORE_PID 2>/dev/null || true' EXIT

# Wait until the core is healthy (up to ~15s).
for _ in $(seq 1 30); do
  curl -sf http://127.0.0.1:8090/health >/dev/null 2>&1 && break
  sleep 0.5
done

echo "▶ starting Baileys bridge — scan the QR on first run …"
cd baileys
[ -d node_modules ] || npm install
exec node index.js
