#!/bin/bash
# 交叉编译到 ELF/RK3588 板端（Buildroot SDK + sysroot 内 OpenCV）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="${BUILD_DIR:-$ROOT/build-aarch64}"
JOBS="${JOBS:-$(nproc 2>/dev/null || echo 2)}"

SDK_DIR="${SDK_DIR:-$HOME/aarch64-buildroot-linux-gnu_sdk-buildroot}"
SYSROOT="${SYSROOT:-}"
OPENCV_ROOT="${OPENCV_ROOT:-}"
QMAKE_BIN="${QMAKE_BIN:-}"
TOOLCHAIN_PREFIX="${TOOLCHAIN_PREFIX:-}"

if [ -z "$SYSROOT" ]; then
    for candidate in "$SDK_DIR/aarch64-buildroot-linux-gnu/sysroot" "$SDK_DIR/sysroot" "$SDK_DIR/../sysroot"; do
        if [ -d "$candidate" ]; then
            SYSROOT="$candidate"
            break
        fi
    done
fi

if [ -z "$OPENCV_ROOT" ] && [ -n "$SYSROOT" ]; then
    OPENCV_ROOT="$SYSROOT/usr"
fi

if [ -n "$TOOLCHAIN_PREFIX" ]; then
    export CC="${TOOLCHAIN_PREFIX}gcc"
    export CXX="${TOOLCHAIN_PREFIX}g++"
fi

if [ ! -d "$SDK_DIR" ]; then
    echo "错误: 未找到 SDK 目录: $SDK_DIR"
    echo "请设置: export SDK_DIR=/path/to/aarch64-buildroot-linux-gnu_sdk-buildroot"
    exit 1
fi

export PATH="$SDK_DIR/bin:$SDK_DIR/qt5/bin:$PATH"

if [ -z "$QMAKE_BIN" ]; then
    for q in \
        "$SDK_DIR/bin/qmake" \
        "$SDK_DIR/qt5/bin/qmake" \
        "$SDK_DIR/host/bin/qmake"; do
        if [ -x "$q" ]; then
            QMAKE_BIN="$q"
            break
        fi
    done
fi

if [ -z "$QMAKE_BIN" ]; then
    echo "错误: SDK 中未找到 qmake，请在 Qt Creator 中配置套件路径或设置 QMAKE_BIN"
    exit 1
fi

echo "==> SDK: $SDK_DIR"
echo "==> sysroot: ${SYSROOT:-<未设置>}"
echo "==> OpenCV root: ${OPENCV_ROOT:-<未设置>}"
echo "==> qmake: $QMAKE_BIN"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

QMAKE_ARGS=("$ROOT/untitled_1.pro" "CONFIG+=release")
if [ -n "$OPENCV_ROOT" ]; then
    QMAKE_ARGS+=("OPENCV_DIR=$OPENCV_ROOT")
fi
if [ -n "$TOOLCHAIN_PREFIX" ]; then
    QMAKE_ARGS+=("QMAKE_CC=${CC}" "QMAKE_CXX=${CXX}")
fi

"$QMAKE_BIN" "${QMAKE_ARGS[@]}"
make -j"$JOBS"

echo ""
echo "交叉编译完成: $BUILD_DIR/drug_recognition"
echo "下一步：把可执行文件与脚本复制到板端，执行 bash scripts/deploy_elf2.sh"
