#!/bin/bash
# RK3588 中药材识别 GUI 启动
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f rk3588/resolve_python.sh ]; then
  # shellcheck disable=SC1091
  source rk3588/resolve_python.sh
fi
PY="${RK3588_PYTHON:-python3}"

export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
export DISPLAY="${DISPLAY:-:0}"

echo "Python: $PY"
echo "启动 GUI ..."

exec "$PY" rk3588/gui/app.py --herb both "$@"
