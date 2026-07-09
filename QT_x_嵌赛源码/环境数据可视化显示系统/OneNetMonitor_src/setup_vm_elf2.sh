#!/bin/bash
# ELF2(RK3588) Ubuntu 虚拟机 — 开发环境一键配置
#
# 适用：Ubuntu 22.04 x86_64 虚拟机（VirtualBox / VMware / Hyper-V）
# 在虚拟机内以普通用户执行：
#   chmod +x setup_vm_elf2.sh
#   ./setup_vm_elf2.sh
#
# 完成后重新打开终端，或执行：source ~/.bashrc

set -euo pipefail

ELF2_SDK_DEFAULT="${HOME}/aarch64-buildroot-linux-gnu_sdk-buildroot"
SDK_TAR_NAME="aarch64-buildroot-linux-gnu_sdk-buildroot.tar.gz"
WORK_DIR="${HOME}/work"

echo "========================================"
echo " OneNetMonitor — ELF2 虚拟机环境配置"
echo "========================================"

# ---------- 1. 基础依赖 ----------
echo "==> 安装编译依赖..."
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    git \
    ssh \
    rsync \
    curl \
    wget \
    unzip \
    libgl1-mesa-dev \
    libfontconfig1-dev \
    libfreetype6-dev \
    libxcb-xinerama0-dev \
    libxkbcommon-dev \
    libxcb-cursor-dev \
    pkg-config

# ---------- 2. 交叉编译 SDK ----------
if [ -d "${ELF2_SDK_DEFAULT}/bin" ] && command -v qmake >/dev/null 2>&1; then
    echo "==> 已检测到 ELF2 SDK: ${ELF2_SDK_DEFAULT}"
else
    echo ""
    echo "未找到 ELF2 交叉编译 SDK。"
    echo "请从开发板资料包复制以下文件到虚拟机 ${HOME}/ 目录："
    echo "  06-常用工具/06-1编译工具安装脚本/${SDK_TAR_NAME}"
    echo ""
    read -r -p "SDK 压缩包完整路径（直接回车跳过解压）: " SDK_TAR || true

    if [ -n "${SDK_TAR:-}" ] && [ -f "${SDK_TAR}" ]; then
        echo "==> 解压 SDK 到 ${HOME} ..."
        tar -xzf "${SDK_TAR}" -C "${HOME}"
    else
        echo "跳过 SDK 解压。请手动解压后重新运行本脚本，或设置 ELF2_SDK 环境变量。"
    fi
fi

# ---------- 3. 写入 ~/.bashrc ----------
MARKER="# >>> ELF2 OneNetMonitor >>>"
if ! grep -q "${MARKER}" "${HOME}/.bashrc" 2>/dev/null; then
    cat >> "${HOME}/.bashrc" <<EOF

${MARKER}
export ELF2_SDK="${ELF2_SDK_DEFAULT}"
export PATH="\${ELF2_SDK}/bin:\${PATH}"
# <<< ELF2 OneNetMonitor <<<
EOF
    echo "==> 已写入 ~/.bashrc（ELF2_SDK / PATH）"
else
    echo "==> ~/.bashrc 已配置，跳过"
fi

# ---------- 4. 工作目录 ----------
mkdir -p "${WORK_DIR}"
echo "==> 工作目录: ${WORK_DIR}"

# ---------- 5. 验证 ----------
export ELF2_SDK="${ELF2_SDK_DEFAULT}"
export PATH="${ELF2_SDK}/bin:${PATH}"

echo ""
echo "========================================"
echo " 环境检查"
echo "========================================"
if command -v qmake >/dev/null 2>&1; then
    echo "[OK] qmake: $(command -v qmake)"
    qmake -v | head -1
else
    echo "[!!] qmake 未找到 — 请先安装 ELF2 SDK"
fi

if command -v aarch64-buildroot-linux-gnu-g++ >/dev/null 2>&1; then
    echo "[OK] g++:   $(aarch64-buildroot-linux-gnu-g++ --version | head -1)"
elif command -v aarch64-linux-gnu-g++ >/dev/null 2>&1; then
    echo "[OK] g++:   $(aarch64-linux-gnu-g++ --version | head -1)"
else
    echo "[!!] 交叉编译器未找到"
fi

echo ""
echo "========================================"
echo " 下一步（在虚拟机内）"
echo "========================================"
cat <<'NEXT'

1. 重新打开终端，或执行：  source ~/.bashrc

2. 把 Windows 上的工程拷进虚拟机（任选一种）：
   · 共享文件夹：VirtualBox 挂载后 cp -r /media/sf_WD3/OneNetMonitor ~/work/
   · SCP：       scp -r user@windows-ip:/path/OneNetMonitor ~/work/
   · U盘：       cp -r /media/$USER/U盘/OneNetMonitor ~/work/

3. 交叉编译：
   cd ~/work/OneNetMonitor
   chmod +x build_elf2.sh deploy_to_board.sh
   ./build_elf2.sh

4. 部署到板卡（板卡与虚拟机同一网段，默认 IP 192.168.1.136）：
   ./deploy_to_board.sh

5. 板卡上运行：
   ssh root@192.168.1.136
   cd /opt/onenet
   ./run_elf2.sh

NEXT
