#!/bin/bash
# 板端离线安装 GUI 依赖（无外网时使用）
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WHEELS="$ROOT/rk3588/offline_wheels"

if [ -f "$ROOT/rk3588/resolve_python.sh" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/rk3588/resolve_python.sh"
fi
PY="${RK3588_PYTHON:-/usr/bin/python3}"

echo "Python: $PY ($("$PY" --version 2>&1))"

try_import() {
  "$PY" -c "import $1" 2>/dev/null
}

echo ""
echo "=== 1. 尝试系统 apt（若曾配置过离线源或预装）==="
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get install -y python3-pyqt6 python3-pyqt5 python3-pil fonts-wqy-microhei 2>/dev/null || true
fi

echo ""
echo "=== 2. 检查 PyQt / Pillow ==="
if try_import PyQt6; then
  echo "  PyQt6 OK"
elif try_import PyQt5; then
  echo "  PyQt5 OK（可用）"
else
  echo "  PyQt 未安装"
fi
try_import PIL && echo "  Pillow OK" || echo "  Pillow 未安装（中文框将用英文 fallback）"

echo ""
echo "=== 3. 从 offline_wheels 安装 ==="
if [ -d "$WHEELS" ] && ls "$WHEELS"/*.whl >/dev/null 2>&1; then
  "$PY" -m pip install --user --no-index --find-links="$WHEELS" \
    PyQt6 Pillow pyyaml 2>/dev/null || \
  "$PY" -m pip install --user --no-index --find-links="$WHEELS" \
    $(ls "$WHEELS"/*.whl) || true
else
  echo "  [!] 未找到 $WHEELS/*.whl"
  echo "  请在有网 PC 运行: bash rk3588/download_gui_wheels_pc.sh"
  echo "  再用 MobaXterm 上传 offline_wheels 目录"
fi

echo ""
echo "=== 4. 最终检查 ==="
try_import PyQt6 && echo "  PyQt6: OK" || try_import PyQt5 && echo "  PyQt5: OK" || echo "  PyQt: 仍缺失"
try_import PIL && echo "  Pillow: OK" || echo "  Pillow: 可选，缺失时检测框用英文"
try_import cv2 && echo "  cv2: OK" || echo "  cv2: 缺失"
try_import rknnlite && echo "  rknnlite: OK" || echo "  rknnlite: 需 pip install xxx.whl --no-index"

echo ""
echo "若 PyQt 仍不可用，可先用 OpenCV 版:"
echo "  bash rk3588/启动枸杞检测.sh --camera /dev/video21"
