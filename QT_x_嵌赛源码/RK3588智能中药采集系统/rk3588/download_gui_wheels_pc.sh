#!/bin/bash
# 在有网的 PC / WSL 上下载 RK3588 (aarch64, Python 3.10) GUI 依赖 whl
# 下载完成后将整个 offline_wheels/ 目录上传到板子
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/rk3588/offline_wheels"
mkdir -p "$OUT"

PYVER=310
PLATFORM=manylinux2014_aarch64

echo "目标: $PLATFORM cp$PYVER -> $OUT"
echo ""

pip download -d "$OUT" \
  --platform "$PLATFORM" \
  --python-version "$PYVER" \
  --only-binary=:all: \
  PyQt6 PyQt6-Qt6 PyQt6-sip \
  Pillow \
  pyyaml \
  2>/dev/null || pip download -d "$OUT" \
  --platform "$PLATFORM" \
  --python-version "$PYVER" \
  PyQt6 PyQt6-Qt6 PyQt6-sip Pillow pyyaml

echo ""
echo "完成。请上传:"
echo "  rk3588/offline_wheels/*.whl  -> 板子 ~/ultralytics-main/rk3588/offline_wheels/"
echo "然后在板子运行:"
echo "  bash rk3588/setup_gui_offline.sh"
