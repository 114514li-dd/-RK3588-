#!/bin/bash
# 在 Ubuntu 虚拟机本机编译（x86_64，用于调试 UI/逻辑）
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="${BUILD_DIR:-$ROOT/build-native}"

QMAKE_BIN="/usr/bin/qmake"
if [ ! -x "$QMAKE_BIN" ]; then
    QMAKE_BIN="$(command -v qmake)"
fi

echo "==> 使用本机 qmake: $QMAKE_BIN"
"$QMAKE_BIN" -query QMAKE_CXX 2>/dev/null || true

if "$QMAKE_BIN" -query QMAKE_CXX 2>/dev/null | grep -qE 'aarch64|buildroot'; then
    echo "错误: 当前 qmake 指向交叉编译器，请安装 qt5-qmake: sudo apt install qt5-qmake qtbase5-dev"
    exit 1
fi

echo "==> 本机编译..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# CONFIG+=native_build 强制走本机 OpenCV 路径
"$QMAKE_BIN" "$ROOT/untitled_1.pro" CONFIG+=release CONFIG+=native_build
make -j"$(nproc 2>/dev/null || echo 2)"

echo ""
echo "本机编译完成: $BUILD_DIR/drug_recognition"
echo "运行: cd $BUILD_DIR && ./drug_recognition"
