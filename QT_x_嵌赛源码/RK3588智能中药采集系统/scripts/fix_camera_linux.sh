#!/bin/bash
# 修复 Linux 摄像头：安装 OpenCV 依赖并用【本机 qmake】重新编译
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> [1/4] 安装依赖 (需要 sudo)..."
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    pkg-config \
    qt5-qmake \
    qtbase5-dev \
    libopencv-dev \
    v4l-utils

echo "==> [2/4] 检查 OpenCV..."
if [ -f /usr/include/opencv4/opencv2/opencv.hpp ]; then
    echo "  OK: /usr/include/opencv4"
else
    echo "  错误: 未找到 OpenCV 头文件"
    exit 1
fi

echo "==> [3/3] 检查摄像头设备..."
if ls /dev/video* >/dev/null 2>&1; then
    echo "  发现设备:"
    ls -l /dev/video* 2>/dev/null || true
    v4l2-ctl --list-devices 2>/dev/null || true
else
    echo "  警告: 未找到 /dev/video*"
    echo "  虚拟机请在 VMware 菜单: 虚拟机 -> 可移动设备 -> 摄像头 -> 连接"
    echo "  无摄像头时仍可用「打开图片」测试检测与 AI 识物"
fi

echo "==> [4/4] 本机编译（非交叉编译）..."
bash "$ROOT/scripts/build_native_linux.sh"
