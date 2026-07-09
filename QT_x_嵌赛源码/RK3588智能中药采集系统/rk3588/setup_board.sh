#!/bin/bash
# 飞凌 ELF2 (RK3588) 板端一次性环境配置
set +e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "项目根目录: $ROOT"

echo ""
echo "=== Python 环境（重要）==="
echo "  当前默认 python3: $(command -v python3) ($(python3 --version 2>&1))"
if [ -x /usr/bin/python3 ]; then
  echo "  系统 /usr/bin/python3: $(/usr/bin/python3 --version 2>&1)"
fi
echo "  说明: miniconda 的 Python 3.13 不能装 cp38 的 rknnlite whl"
echo "  推荐: conda create -n rk3588 python=3.8  或直接用 /usr/bin/python3"

check_py() {
  local py="$1"
  [ -x "$py" ] || return 1
  echo ""
  echo "--- $py ($("$py" --version 2>&1)) ---"
  "$py" -c "import cv2; print('  cv2 OK')" 2>/dev/null || echo "  cv2 缺失"
  "$py" -c "import numpy; print('  numpy OK')" 2>/dev/null || echo "  numpy 缺失"
  "$py" -c "import yaml; print('  yaml OK')" 2>/dev/null || echo "  yaml 缺失"
  "$py" -c "import rknnlite; print('  rknnlite OK')" 2>/dev/null || echo "  rknnlite 缺失"
}

check_py /usr/bin/python3
[ -x "$HOME/miniconda3/envs/rk3588/bin/python" ] && check_py "$HOME/miniconda3/envs/rk3588/bin/python"
[ "$(command -v python3)" != "/usr/bin/python3" ] && check_py "$(command -v python3)"

mkdir -p "$ROOT/rk3588/artifacts"

echo ""
echo "=== RKNN 模型 ==="
ls -lh "$ROOT/rk3588/artifacts/"*.rknn 2>/dev/null || echo "  [!] artifacts/ 为空，需在 PC/虚拟机导出后上传"

echo ""
echo "=== NPU ==="
[ -e /dev/rknpu ] && echo "  /dev/rknpu 存在" || echo "  未找到 /dev/rknpu"

echo ""
echo "=== 摄像头 ==="
v4l2-ctl --list-devices 2>/dev/null | head -n 20 || ls /dev/video* 2>/dev/null
echo "  插 USB 摄像头后再 v4l2-ctl；UVC 常见 /dev/video21"

echo ""
echo "=== 推荐安装（板端离线）==="
echo "  ~/miniconda3/bin/conda create -n rk3588 python=3.8 -y"
echo "  ~/miniconda3/envs/rk3588/bin/pip install ~/rknn_toolkit_lite2-2.3.2-cp38-cp38-linux_aarch64.whl --no-index"
echo "  # opencv/numpy 需从 PC 拷 aarch64 whl 或配网 pip install opencv-python-headless numpy pyyaml"

PY="$(bash "$ROOT/rk3588/resolve_python.sh" 2>/dev/null || echo python3)"
if "$PY" -c "import cv2, numpy, yaml, rknnlite" 2>/dev/null && ls "$ROOT/rk3588/artifacts/"*.rknn >/dev/null 2>&1; then
  echo ""
  echo "[OK] 可以运行: bash rk3588/启动枸杞检测.sh"
else
  echo ""
  echo "[!] 还差: rknnlite + cv2 + artifacts/*.rknn"
fi
