#!/bin/bash
# Ubuntu/VMware 网络与 DNS 诊断（用 bash 运行）
set -e

echo "========== 1. 网卡 =========="
ip -br addr 2>/dev/null || ifconfig -a 2>/dev/null || true

echo ""
echo "========== 2. 默认路由 =========="
ip route 2>/dev/null || route -n 2>/dev/null || true

echo ""
echo "========== 3. DNS 配置 =========="
if [ -f /etc/resolv.conf ]; then
    cat /etc/resolv.conf
else
    echo "/etc/resolv.conf 不存在"
fi

echo ""
echo "========== 4. 连通性测试 =========="
if ping -c 2 -W 3 8.8.8.8 >/dev/null 2>&1; then
    echo "[OK] 能 ping 通 8.8.8.8（IP 网络正常）"
else
    echo "[FAIL] 不能 ping 8.8.8.8（检查 VMware 网络适配器是否 NAT/已连接）"
fi

if ping -c 2 -W 3 mirrors.aliyun.com >/dev/null 2>&1; then
    echo "[OK] 能解析并 ping mirrors.aliyun.com"
else
    echo "[FAIL] 不能解析 mirrors.aliyun.com（DNS 问题）"
fi

echo ""
echo "========== 5. 建议修复 =========="
cat <<'EOF'
若 IP 能通但域名不通（常见 VMware 问题）：

  sudo bash -c 'printf "nameserver 114.114.114.114\nnameserver 8.8.8.8\n" > /etc/resolv.conf'

若仍不行，在 VMware 中：
  虚拟机 → 设置 → 网络适配器 → 选 NAT 或桥接，并勾选“已连接”
  然后在 Ubuntu：设置 → 网络 → 打开有线/Wi-Fi

修复后执行：
  sudo apt update
  sudo apt install -y libopencv-dev pkg-config qt5-qmake qtbase5-dev build-essential
  bash scripts/fix_camera_linux.sh

若阿里云源仍失败，可临时改官方源：
  sudo sed -i 's|http://mirrors.aliyun.com/ubuntu|http://archive.ubuntu.com/ubuntu|g' /etc/apt/sources.list
  sudo apt update
EOF
