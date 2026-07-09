#!/bin/bash
# OneNetMonitor — ELF2(RK3588) 交叉编译脚本
# 在 Ubuntu 虚拟机内执行（先运行 setup_vm_elf2.sh 配置环境）。
#
# 用法：
#   source ~/.bashrc          # 加载 ELF2_SDK
#   ./build_elf2.sh
#   ./deploy_to_board.sh      # 部署到板卡
#
# 可选环境变量：
#   ELF2_SDK      SDK 根目录（含 bin/qmake、bin/aarch64-*-gcc）
#   BUILD_TYPE    release（默认）或 debug
#   OUT_DIR       输出目录（默认 build-elf2-release）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_TYPE="${BUILD_TYPE:-release}"
OUT_DIR="${OUT_DIR:-${SCRIPT_DIR}/build-elf2-${BUILD_TYPE}}"

# 自动探测常见 SDK 路径（虚拟机默认 ~/aarch64-buildroot-linux-gnu_sdk-buildroot）
if [ -z "${ELF2_SDK:-}" ]; then
    for candidate in \
        "${HOME}/aarch64-buildroot-linux-gnu_sdk-buildroot" \
        "${HOME}/work/aarch64-buildroot-linux-gnu_sdk-buildroot" \
        "/opt/elf2/aarch64-buildroot-linux-gnu_sdk-buildroot"
    do
        if [ -x "${candidate}/bin/qmake" ]; then
            ELF2_SDK="${candidate}"
            break
        fi
    done
fi

if [ -z "${ELF2_SDK:-}" ] || [ ! -d "${ELF2_SDK}/bin" ]; then
    echo "错误：未找到 ELF2 SDK。请先运行 ./setup_vm_elf2.sh"
    echo "或手动设置：export ELF2_SDK=/home/你的用户名/aarch64-buildroot-linux-gnu_sdk-buildroot"
    exit 1
fi

export PATH="${ELF2_SDK}/bin:${PATH}"

if ! command -v qmake >/dev/null 2>&1; then
    echo "错误：未找到 qmake，请确认 ELF2_SDK/bin 已加入 PATH"
    exit 1
fi

echo "==> SDK:       ${ELF2_SDK}"
echo "==> qmake:     $(command -v qmake)"
echo "==> 编译器:    $(command -v aarch64-buildroot-linux-gnu-g++ 2>/dev/null || command -v aarch64-linux-gnu-g++ 2>/dev/null || echo '使用 SDK 默认 gcc')"
echo "==> 输出目录:  ${OUT_DIR}"

mkdir -p "${OUT_DIR}"
cd "${OUT_DIR}"

qmake "${SCRIPT_DIR}/OneNetMonitor.pro" CONFIG+="${BUILD_TYPE}"
make -j"$(nproc)"

echo ""
echo "编译完成：${OUT_DIR}/OneNetMonitor"
echo "将可执行文件与 threshold.cfg 拷贝到板卡后运行："
echo "  ./run_elf2.sh"
