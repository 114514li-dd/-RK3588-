#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""枸杞摄像头场景微调 — 在已有 best.pt 上继续训练，提升实时识别置信度。

用法:
    python gouqi/scripts/finetune_camera.py --device 0
    # 先采集摄像头样本再微调（推荐）:
    python gouqi/scripts/collect_camera_samples.py --frames 30
    python gouqi/scripts/finetune_camera.py --device 0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baizhi.scripts.train import check_rtx50_gpu_env
from ultralytics import YOLO


def default_base() -> str:
    v1 = ROOT / "gouqi/runs/detect/gouqi_yolov8s_ca/weights/best.pt"
    return str(v1)


def parse_args():
    p = argparse.ArgumentParser(description="Finetune Gouqi for camera scenes")
    p.add_argument("--weights", default=default_base(), help="已有枸杞 best.pt")
    p.add_argument("--data", default=str(ROOT / "gouqi/dataset/data.yaml"))
    p.add_argument("--epochs", type=int, default=80)
    p.add_argument("--patience", type=int, default=25)
    p.add_argument("--batch", type=int, default=2)
    p.add_argument("--device", default="0")
    p.add_argument("--name", default="gouqi_yolov8s_ca_v2")
    return p.parse_args()


def main():
    args = parse_args()
    if not Path(args.weights).exists():
        print(f"未找到: {args.weights}，请先运行 启动枸杞训练.bat")
        sys.exit(1)
    check_rtx50_gpu_env(args.device)
    model = YOLO(args.weights)
    model.train(
        data=args.data,
        epochs=args.epochs,
        patience=args.patience,
        imgsz=640,
        batch=args.batch,
        device=args.device,
        workers=2,
        project=str(ROOT / "gouqi/runs/detect"),
        name=args.name,
        optimizer="AdamW",
        lr0=0.00025,
        lrf=0.01,
        cls=0.5,
        box=7.5,
        mosaic=0.8,
        copy_paste=0.4,
        mixup=0.15,
        hsv_h=0.02,
        hsv_s=0.8,
        hsv_v=0.5,
        degrees=15.0,
        fliplr=0.5,
        flipud=0.5,
        close_mosaic=10,
        exist_ok=True,
        verbose=True,
    )
    print(f"\n完成: gouqi/runs/detect/{args.name}/weights/best.pt")
    print("检测会自动优先使用 v2 权重")


if __name__ == "__main__":
    main()
