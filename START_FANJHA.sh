#!/usr/bin/env bash
# FANJHA AI Model Factory - One command launcher
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

AUTO_BUILD=0
SKIP_INSTALL=0
for arg in "$@"; do
  case "$arg" in
    --auto-build) AUTO_BUILD=1 ;;
    --skip-install) SKIP_INSTALL=1 ;;
    --help|-h)
      cat <<EOF
Usage: $0 [--auto-build] [--skip-install]

  --auto-build    Immediately create a build and start the pipeline after backend ready
  --skip-install  Skip dependency installation even if missing
EOF
      exit 0
      ;;
  esac
done

echo "==> FANJHA AI Model Factory"
echo "Working directory: $ROOT"

# 1. venv
if [[ ! -d ".venv" ]]; then
  echo "==> Creating Python virtual environment"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# 2. backend deps
if [[ "$SKIP_INSTALL" != "1" ]]; then
  if ! python -c "import fastapi, sqlalchemy, uvicorn" 2>/dev/null; then
    echo "==> Installing backend dependencies (this may take a while for torch)"
    pip install --upgrade pip >/dev/null
    pip install -r requirements.txt
  else
    echo "==> Backend dependencies already satisfied"
  fi
fi

# 3. frontend deps + build
if [[ "$SKIP_INSTALL" != "1" ]]; then
  if [[ ! -d "frontend/node_modules" ]]; then
    echo "==> Installing frontend dependencies"
    (cd frontend && npm install --silent)
  fi
fi
if [[ ! -d "frontend/dist" ]] || [[ frontend/src -nt frontend/dist ]]; then
  echo "==> Building frontend"
  (cd frontend && npm run build --silent)
fi

# 4. directories
mkdir -p logs outputs data/synthetic

# 5. start backend
echo "==> Starting backend on 127.0.0.1:8765"
uvicorn backend.main:app --host 127.0.0.1 --port 8765 --log-level info &
BACKEND_PID=$!

cleanup() {
  echo "==> Shutting down"
  kill "$BACKEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# 6. wait for health
echo "==> Waiting for backend health check"
READY=0
for i in $(seq 1 60); do
  if curl -sf http://127.0.0.1:8765/api/system/health >/dev/null 2>&1; then
    echo "==> Backend healthy"
    READY=1
    break
  fi
  sleep 0.5
done
if [[ "$READY" != "1" ]]; then
  echo "ERROR: Backend did not become healthy" >&2
  exit 1
fi

# 7. open browser
URL="http://127.0.0.1:8765"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
  open "$URL" >/dev/null 2>&1 &
elif command -v start >/dev/null 2>&1; then
  start "$URL" >/dev/null 2>&1 &
fi

# 8. auto-build mode
if [[ "$AUTO_BUILD" == "1" ]]; then
  echo "==> Auto-build mode: creating build and starting pipeline"
  BUILD_ID=$(curl -sf -X POST http://127.0.0.1:8765/api/builds \
    -H 'Content-Type: application/json' \
    -d '{}' | python -c "import sys,json;print(json.load(sys.stdin)['build_id'])")
  echo "==> Build ID: $BUILD_ID"
  curl -sf -X POST "http://127.0.0.1:8765/api/builds/$BUILD_ID/start" >/dev/null
fi

echo ""
echo "==============================================="
echo "  FANJHA AI Model Factory is running"
echo "  Dashboard: $URL"
echo "  Press Ctrl+C to stop"
echo "==============================================="
echo ""

wait "$BACKEND_PID"
