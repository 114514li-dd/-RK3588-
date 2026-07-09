#!/bin/bash
# PC/WSL/x86 Ubuntu 虚拟机 导出枸杞+白芷 RKNN（不要在 RK3588 板子上运行！）
# 默认 FP16（int8=False），INT8 量化易导致板端 raw 不变、检不出
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ART="$ROOT/rk3588/artifacts"
mkdir -p "$ART"

ARCH="$(uname -m)"
if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
  echo "=============================================="
  echo "[错误] 当前是 ARM 板端 ($ARCH)，不能在此导出 RKNN"
  echo "  RKNN 导出必须在 PC/WSL/x86 Ubuntu 虚拟机上完成"
  echo "  板端只需运行推理，不需要 ultralytics/torchvision"
  echo ""
  echo "  Windows 请双击: 启动RK3588导出FP16.bat"
  echo "  或虚拟机执行: bash rk3588/export_models_wsl.sh fp16"
  echo "  导出后上传: rk3588/artifacts/*_fp16.rknn"
  echo "=============================================="
  exit 1
fi

# 用法: bash export_models_wsl.sh [fp16|int8]
QUANT="${1:-fp16}"

pick_weight() {
  local dir="$1"
  shift
  for name in "$@"; do
    local p="$ROOT/$dir/runs/detect/$name/weights/best.pt"
    if [ -f "$p" ]; then
      echo "$p"
      return 0
    fi
  done
  return 1
}

GOUQI_PT="$(pick_weight gouqi gouqi_yolov8s_ca_v6 gouqi_yolov8s_ca_v8 gouqi_yolov8s_ca_v7 gouqi_yolov8s_ca || true)"
BAIZHI_PT="$(pick_weight baizhi baizhi_yolov8s_ca_v7 baizhi_yolov8s_ca_v6 baizhi_yolov8s_ca_v5 baizhi_yolov8s_ca || true)"

if [ -z "$GOUQI_PT" ] || [ -z "$BAIZHI_PT" ]; then
  echo "[错误] 缺少 best.pt"
  exit 1
fi

echo "量化模式: $QUANT"
echo "枸杞: $GOUQI_PT"
echo "白芷: $BAIZHI_PT"

pip install -q ultralytics "onnx<1.19.0" "rknn-toolkit2>=2.3.2" 2>/dev/null || true

export_one() {
  local pt="$1"
  local data="$2"
  local out_name="$3"
  local quant="$4"
  python3 - << EOF
from ultralytics import YOLO
from pathlib import Path
import shutil

pt = Path("$pt")
data = Path("$data")
out_name = "$out_name"
quant = "$quant"
art = Path("$ART")
use_int8 = quant == "int8"

model = YOLO(str(pt))
onnx = model.export(format="onnx", imgsz=640, batch=1, simplify=True, opset=12, dynamic=False)
print(f"ONNX: {onnx}")

kwargs = dict(format="rknn", imgsz=640, batch=1, name="rk3588", int8=use_int8)
if use_int8:
    kwargs["data"] = str(data)
rknn_dir = model.export(**kwargs)
print(f"RKNN dir: {rknn_dir}")

matches = list(Path(rknn_dir).parent.rglob("*rk3588*.rknn")) if Path(rknn_dir).is_dir() else []
if not matches and Path(rknn_dir).suffix == ".rknn":
    matches = [Path(rknn_dir)]
if not matches:
    raise SystemExit("未找到 rknn 输出")

suffix = "_rk3588.rknn" if use_int8 else "_rk3588_fp16.rknn"
dst = art / f"{out_name}{suffix}"
shutil.copy2(matches[0], dst)
print(f"[OK] -> {dst}")
EOF
}

export_one "$GOUQI_PT" "$ROOT/gouqi/dataset/data.yaml" "gouqi_yolov8s_ca" "$QUANT"
export_one "$BAIZHI_PT" "$ROOT/baizhi/dataset/data.yaml" "baizhi_yolov8s_ca" "$QUANT"

echo ""
echo "完成。FP16 文件: rk3588/artifacts/*_fp16.rknn"
echo "请更新 deploy.yaml 中 rknn 路径后上传到板子"
