#!/bin/bash
# Ubuntu/Debian 编译脚本（请用 bash 运行，不要用 sh）
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="${BUILD_DIR:-$ROOT/build-linux}"
JOBS="${JOBS:-$(nproc 2>/dev/null || echo 2)}"

echo "==> 安装依赖 (需要 sudo)..."
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    qt5-qmake \
    qtbase5-dev \
    qttools5-dev-tools \
    libopencv-dev \
    python3 \
    python3-opencv \
    v4l-utils \
    pkg-config

echo "==> 检查 OpenCV..."
if pkg-config --exists opencv4 2>/dev/null; then
    echo "OpenCV4: $(pkg-config --modversion opencv4)"
elif pkg-config --exists opencv 2>/dev/null; then
    echo "OpenCV: $(pkg-config --modversion opencv)"
else
    echo "警告: pkg-config 未找到 opencv，qmake 将尝试系统路径"
fi

echo "==> 编译 (本机)..."
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"
/usr/bin/qmake "$ROOT/untitled_1.pro" CONFIG+=release CONFIG+=native_build
make clean
make -j"$JOBS"

echo ""
echo "完成: $BUILD_DIR/drug_recognition"
