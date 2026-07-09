#!/bin/bash
# OneNetMonitor — 在 ELF2 板卡上启动（buildroot / Ubuntu 文件系统通用）
#
# 用法（板卡上）：
#   chmod +x run_elf2.sh OneNetMonitor
#   ./run_elf2.sh
#
# 可选环境变量：
#   QT_PLATFORM   eglfs（默认，无桌面环境）| wayland | xcb | linuxfb
#   QT_QPA_EGLFS_PHYSICAL_WIDTH   触摸屏物理宽度 mm（可选，改善 DPI）
#   QT_QPA_EGLFS_PHYSICAL_HEIGHT  触摸屏物理高度 mm（可选）

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
APP="${APP_DIR}/OneNetMonitor"
PLATFORM="${QT_PLATFORM:-eglfs}"

if [ ! -x "${APP}" ]; then
    echo "错误：未找到可执行文件 ${APP}"
    exit 1
fi

# Qt 插件路径（ELF2 SDK 常见安装位置，按实际系统调整）
for p in \
    /usr/lib/qt/plugins \
    /usr/lib/aarch64-linux-gnu/qt5/plugins \
    /opt/qt5/plugins
do
    if [ -d "${p}" ]; then
        export QT_PLUGIN_PATH="${p}"
        break
    fi
done

export QT_QPA_PLATFORM="${PLATFORM}"
export QT_QPA_EGLFS_ALWAYS_SET_MODE=1

cd "${APP_DIR}"
exec "${APP}" "$@"
