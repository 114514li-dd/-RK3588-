#!/bin/bash
# 从 Ubuntu 虚拟机把编译产物部署到 ELF2 板卡
#
# 用法：
#   ./deploy_to_board.sh
#   BOARD_IP=192.168.1.100 BOARD_USER=root ./deploy_to_board.sh
#
# 前提：虚拟机可 ssh 到板卡（板卡已联网，ssh 已开启）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_TYPE="${BUILD_TYPE:-release}"
OUT_DIR="${OUT_DIR:-${SCRIPT_DIR}/build-elf2-${BUILD_TYPE}}"
BOARD_IP="${BOARD_IP:-192.168.1.136}"
BOARD_USER="${BOARD_USER:-root}"
BOARD_DIR="${BOARD_DIR:-/opt/onenet}"

APP="${OUT_DIR}/OneNetMonitor"
if [ ! -f "${APP}" ]; then
    echo "错误：未找到 ${APP}，请先执行 ./build_elf2.sh"
    exit 1
fi

echo "==> 目标: ${BOARD_USER}@${BOARD_IP}:${BOARD_DIR}"
ssh "${BOARD_USER}@${BOARD_IP}" "mkdir -p '${BOARD_DIR}'"

rsync -avz --progress \
    "${APP}" \
    "${SCRIPT_DIR}/run_elf2.sh" \
    "${BOARD_USER}@${BOARD_IP}:${BOARD_DIR}/"

ssh "${BOARD_USER}@${BOARD_IP}" "chmod +x '${BOARD_DIR}/OneNetMonitor' '${BOARD_DIR}/run_elf2.sh'"

echo ""
echo "部署完成。登录板卡运行："
echo "  ssh ${BOARD_USER}@${BOARD_IP}"
echo "  cd ${BOARD_DIR} && ./run_elf2.sh"
