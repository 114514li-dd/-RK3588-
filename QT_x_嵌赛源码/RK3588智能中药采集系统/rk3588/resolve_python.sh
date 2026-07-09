#!/bin/bash
# 选择板端推理用的 Python（避免 miniconda 3.13 与 cp38 rknnlite 不匹配）
if [ -n "${RK3588_PYTHON:-}" ] && [ -x "$RK3588_PYTHON" ]; then
  echo "$RK3588_PYTHON"
  exit 0
fi

candidates=(
  "$HOME/miniconda3/envs/rk3588/bin/python"
  "/usr/bin/python3.10"
  "/usr/bin/python3.8"
  "/usr/bin/python3"
)

for py in "${candidates[@]}"; do
  [ -x "$py" ] || continue
  if "$py" -c "import cv2, numpy, yaml, rknnlite" 2>/dev/null; then
    echo "$py"
    exit 0
  fi
done

# 尚未装齐依赖时，优先系统 Python（apt 的 opencv 装在这里）
for py in /usr/bin/python3.10 /usr/bin/python3.8 /usr/bin/python3; do
  [ -x "$py" ] || continue
  echo "$py"
  exit 0
done

echo "python3"
