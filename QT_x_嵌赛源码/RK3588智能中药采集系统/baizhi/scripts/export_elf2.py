#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ELF2 端侧部署 — 步骤1: Windows 导出 ONNX（供 WSL/Linux 转 RKNN）。

参考飞凌 ELF2 AI 端侧部署:
  训练 best.pt -> ONNX -> (WSL) RKNN -> 板端 rknnlite2 推理

用法:
    conda activate baizhi
    python baizhi/scripts/export_elf2.py
    python baizhi/scripts/export_elf2.py --weights baizhi/runs/detect/baizhi_yolov8s_ca_v2/weights/best.pt
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ultralytics import YOLO

ARTIFACTS = ROOT / "baizhi/elf2/artifacts"
DEPLOY_CFG = ROOT / "baizhi/elf2/deploy.yaml"


def parse_args():
    p = argparse.ArgumentParser(description="Export Bai Zhi model for Forlinx ELF2 deployment")
    p.add_argument(
        "--weights",
        type=str,
        default=str(ROOT / "baizhi/runs/detect/baizhi_yolov8s_ca_v2/weights/best.pt"),
    )
    p.add_argument("--data", type=str, default=str(ROOT / "baizhi/dataset/data.yaml"))
    p.add_argument("--imgsz", type=int, default=640)
    return p.parse_args()


def main():
    args = parse_args()
    weights = Path(args.weights)
    if not weights.is_absolute():
        weights = (ROOT / weights).resolve()
    if not weights.exists():
        raise FileNotFoundError(f"权重不存在: {weights}\n请先完成 train_elf2.py 或 train.py v2 训练")

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(weights))

    print("=" * 72)
    print("ELF2 部署导出 [1/2] ONNX")
    print(f"  权重: {weights}")
    print(f"  目标: RK3588 INT8 (Forlinx ELF2)")
    print("=" * 72)

    onnx_path = model.export(
        format="onnx",
        imgsz=args.imgsz,
        batch=1,
        simplify=True,
        opset=12,
        dynamic=False,
    )
    onnx_path = Path(onnx_path)
    dst_onnx = ARTIFACTS / "baizhi_yolov8s_ca.onnx"
    shutil.copy2(onnx_path, dst_onnx)

    # 复制校准用数据集列表
    calib_list = ARTIFACTS / "calib_images.txt"
    img_dir = ROOT / "baizhi/dataset/images/train"
    imgs = sorted(img_dir.glob("*.jpg"))[:200]
    calib_list.write_text("\n".join(str(p.resolve()) for p in imgs), encoding="utf-8")

    # 更新 deploy.yaml
    if DEPLOY_CFG.exists():
        with open(DEPLOY_CFG, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        cfg["model"]["weights_pt"] = str(weights.relative_to(ROOT)).replace("\\", "/")
        cfg["model"]["weights_onnx"] = str(dst_onnx.relative_to(ROOT)).replace("\\", "/")
        with open(DEPLOY_CFG, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, allow_unicode=True, sort_keys=False)

    print(f"\n[OK] ONNX: {dst_onnx}")
    print(f"[OK] 校准列表: {calib_list} ({len(imgs)} 张)")
    print("\n" + "=" * 72)
    print("下一步 [2/2] 在 WSL2/Ubuntu 中转换 RKNN:")
    print("  cd /mnt/c/Users/LWH/Desktop/ultralytics-main")
    print("  bash baizhi/elf2/convert_rknn.sh")
    print("\n然后拷贝到 ELF2 板端:")
    print("  baizhi/elf2/artifacts/baizhi_yolov8s_ca_rk3588.rknn")
    print("  baizhi/elf2/board_infer.py")
    print("  baizhi/elf2/yolov8_postprocess.py")
    print("  baizhi/elf2/deploy.yaml")
    print("=" * 72)


if __name__ == "__main__":
    main()
