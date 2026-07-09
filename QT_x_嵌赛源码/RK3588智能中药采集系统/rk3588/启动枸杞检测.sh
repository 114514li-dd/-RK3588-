#!/bin/bash
# RK3588 枸杞摄像头检测
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="$(bash rk3588/resolve_python.sh)"
echo "使用 Python: $PY ($("$PY" --version 2>&1))"
exec "$PY" rk3588/infer_camera.py --herb gouqi "$@"
