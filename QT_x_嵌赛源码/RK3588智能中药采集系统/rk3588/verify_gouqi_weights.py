#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比 Windows PyTorch 与板端 RKNN 应使用的同一权重。

用法 (PC):
  python rk3588/verify_gouqi_weights.py
  python rk3588/verify_gouqi_weights.py --image gouqi/dataset/images/val/gq_val_gouqi_val_0000.jpg
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pick_gouqi_pt() -> Path:
    for name in (
        "gouqi_yolov8s_ca_v6",
        "gouqi_yolov8s_ca_v8",
        "gouqi_yolov8s_ca_v7",
        "gouqi_yolov8s_ca",
    ):
        p = ROOT / f"gouqi/runs/detect/{name}/weights/best.pt"
        if p.is_file():
            return p
    raise FileNotFoundError("未找到 gouqi best.pt，请先训练")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--image", default="")
    p.add_argument("--conf", type=float, default=0.40)
    args = p.parse_args()

    pt = pick_gouqi_pt()
    print(f"Windows 检测脚本会优先用: {pt}")
    print(f"RKNN 导出应使用同一文件。请运行:")
    print(f"  bash rk3588/export_models_wsl.sh fp16")
    print(f"然后上传 artifacts/gouqi_yolov8s_ca_rk3588_fp16.rknn\n")

    img_path = Path(args.image) if args.image else None
    if not img_path:
        for cand in sorted((ROOT / "gouqi/dataset/images/val").glob("*.jpg"))[:1]:
            img_path = cand
    if not img_path or not img_path.is_file():
        print("未指定测试图，跳过推理对比")
        return

    from ultralytics import YOLO

    img = cv2.imread(str(img_path))
    model = YOLO(str(pt))
    r = model.predict(img, conf=0.01, iou=0.45, verbose=False)[0]
    raw = float(r.boxes.conf.max()) if r.boxes is not None and len(r.boxes) else 0.0
    show = sum(1 for b in r.boxes if float(b.conf) >= args.conf) if r.boxes is not None else 0
    print(f"测试图: {img_path.name}")
    print(f"  raw_max={raw:.3f}  conf>={args.conf} 出框数={show}")
    print("\n板端 raw 应接近上述 raw_max（FP16 通常略低 0.05~0.15）")
    print("若板端 raw<0.25 而 Windows>0.6，说明 RKNN 模型未更新或导出权重不一致")


if __name__ == "__main__":
    main()
